"""Interactive setup wizard — walks you through everything Sellbird needs."""

import asyncio
import getpass
import logging
import os
import shutil
from pathlib import Path

import yaml

from pydantic import ValidationError

from sellbird.brain import Brain
from sellbird.config import COUNTRY_ALIASES, BrainConfig, normalize_prospect_country
from sellbird.integrations.precleared import GET_KEY_URL, SENDER_COUNTRIES, create_free_key
from sellbird.state import StateManager

logger = logging.getLogger("sellbird.setup")

from sellbird.paths import PROJECT_ROOT
from sellbird.textio import read_user_text
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
CONFIG_FILE = PROJECT_ROOT / "sellbird.yaml"


def _print_sellbird(message: str):
    """Print a message as Sellbird."""
    print(f"\n  Sellbird: {message}")


def _print_step(step: int, total: int, title: str):
    """Print a step header."""
    print(f"\n{'─'*60}")
    print(f"  Etapa {step}/{total}: {title}")
    print(f"{'─'*60}")


def _ask(prompt: str, default: str = "", required: bool = True, secret: bool = False) -> str:
    """Ask the user a question. secret=True hides input (passwords, API keys)."""
    suffix = f" [{default}]" if default else ""
    reader = getpass.getpass if secret else input
    while True:
        try:
            answer = reader(f"\n  → {prompt}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  Configuração cancelada.")
            raise SystemExit(1)

        if not answer and default:
            return default
        if not answer and required:
            print("    (obrigatório: digite um valor)")
            continue
        return answer


def _ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    suffix = " [Y/n]" if default else " [y/N]"
    try:
        answer = input(f"\n  → {prompt}{suffix}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n\n  Configuração cancelada.")
        raise SystemExit(1)

    if not answer:
        return default
    return answer in ("y", "yes")


def _read_env_file() -> dict[str, str]:
    """The KEY=value pairs already in .env (comments and blank lines skipped)."""
    existing: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in read_user_text(ENV_FILE).splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                existing[key.strip()] = value.strip()
    return existing


def _config_file() -> Path:
    """The config Sellbird loads: sellbird.local.yaml (what `sellbird train` writes)
    wins over sellbird.yaml when it exists, as in config._find_config_file.
    Setup reads and writes this file, so its answers are the ones Sellbird uses."""
    local = CONFIG_FILE.with_name("sellbird.local.yaml")
    return local if local.exists() else CONFIG_FILE


def _current_precleared() -> dict:
    """compliance.precleared in the file setup writes to, or {} if there is none."""
    try:
        data = yaml.safe_load(read_user_text(_config_file()))
    except (OSError, yaml.YAMLError):
        return {}
    compliance = data.get("compliance") if isinstance(data, dict) else None
    section = compliance.get("precleared") if isinstance(compliance, dict) else None
    return section if isinstance(section, dict) else {}


def _sender_country(value, strict: bool = True) -> str:
    """A typed or saved sender country as its two-letter code ("uk" -> "GB").

    With ``strict`` (saved values), anything Precleared doesn't take becomes
    "", so a stale or mistyped setting is asked again rather than offered as
    the default. Without it (typed answers), the code comes back as typed so
    the caller can tell a wrong code from a blank one.
    """
    code = str(value or "").strip().upper()
    code = COUNTRY_ALIASES.get(code, code)
    if strict and code not in SENDER_COUNTRIES:
        return ""
    return code


def _saved_timezone() -> str:
    """usage.quiet_hours.timezone in the file setup writes to, or ""."""
    try:
        data = yaml.safe_load(read_user_text(_config_file()))
    except (OSError, yaml.YAMLError):
        return ""
    usage = data.get("usage") if isinstance(data, dict) else None
    quiet = usage.get("quiet_hours") if isinstance(usage, dict) else None
    zone = quiet.get("timezone") if isinstance(quiet, dict) else None
    return str(zone or "").strip()


def _save_precleared(config: dict, answers: dict) -> None:
    """Lay the setup answers over config's compliance.precleared, keeping the rest."""
    compliance = config.get("compliance")
    if not isinstance(compliance, dict):
        compliance = config["compliance"] = {}
    section = compliance.get("precleared")
    if not isinstance(section, dict):
        section = compliance["precleared"] = {}
    section.update(answers)


def _merge_answers(existing: dict, answers: dict) -> None:
    """Lay manual setup answers over existing config, skipping blank answers so
    they never wipe values already in the file."""
    for key, value in answers.items():
        if isinstance(value, dict) and isinstance(existing.get(key), dict):
            _merge_answers(existing[key], value)
        elif value not in ("", [], {}, None):
            existing[key] = value


def _product_configured() -> bool:
    """Whether the config names a real company and product, not the shipped
    placeholders (the same test the dashboard uses)."""
    try:
        data = yaml.safe_load(read_user_text(_config_file()))
    except (OSError, yaml.YAMLError):
        return False
    if not isinstance(data, dict):
        return False
    persona = data.get("persona") if isinstance(data.get("persona"), dict) else {}
    product = data.get("product") if isinstance(data.get("product"), dict) else {}
    return (persona.get("company") not in (None, "", "Your Company")
            and product.get("name") not in (None, "", "Your Product"))


def _check_claude_cli() -> bool:
    """Check if Claude CLI is installed and accessible."""
    return shutil.which("claude") is not None


def _check_codex_cli() -> bool:
    """Check if Codex CLI is installed and accessible."""
    return shutil.which("codex") is not None


async def _test_claude(brain: Brain) -> bool:
    """Test that the configured brain answers (Claude or Codex)."""
    response = await brain.think(
        "Respond with exactly: SELLBIRD_READY",
        session_id="sellbird-setup-test",
    )
    return "SELLBIRD_READY" in response


def _ask_brain_config() -> BrainConfig:
    """Ask which subscription Sellbird thinks with. Claude is the default."""
    _print_sellbird("Eu penso usando uma assinatura de IA que você já paga:")
    print("    claude — seu plano do Claude, pelo Claude Code (padrão)")
    print("    codex  — seu plano do ChatGPT, pelo Codex CLI")
    while True:
        provider = _ask("Qual? (claude/codex)", default="claude").lower()
        if provider == "codex":
            from sellbird.codex import CodexError, require_supported_platform
            try:
                require_supported_platform()
            except CodexError as e:
                print(f"    ({e})")
                continue
        if provider in ("claude", "codex"):
            break
        print("    (digite claude ou codex)")
    if provider == "codex":
        from sellbird.codex import SUGGESTED_MODEL
        print(f"    {SUGGESTED_MODEL} é o modelo do Codex que o Sellbird verificou como só-texto")
        print("    (sem ferramentas de execução de código). Aperte Enter para usar, ou digite outro.")
    while True:
        if provider == "codex":
            model = _ask("Model", default=SUGGESTED_MODEL, required=False)
        else:
            model = _ask("Modelo (deixe em branco para o padrão)", required=False)
        try:
            return BrainConfig(provider=provider, model=model)
        except ValidationError:
            print("    (isso não parece um nome de modelo; tente de novo ou deixe em branco)")


async def _test_instantly(api_key: str) -> bool:
    """Test the Instantly API key."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.instantly.ai/api/v2/accounts",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return resp.status_code == 200
    except Exception:
        return False


class SetupWizard:
    def __init__(self):
        self.env_vars: dict[str, str] = {}
        self.config: dict = {}
        self.brain_config = BrainConfig()
        # compliance.precleared answers to save; None leaves the config alone.
        self.precleared: dict | None = None
        # Whether _write_config saved the config, for the summary.
        self.config_saved = False
        # True when step 5 was answered by hand: self.config then holds
        # persona/product/icp that are not in sellbird.yaml yet.
        self.manual_product = False

    async def run(self):
        """Run the full interactive setup."""
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   Assistente de configuração do Sellbird                 ║
║   Vamos colocar você para fechar negócios.               ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝""")

        _print_sellbird("Oi. Eu sou o Sellbird. Vamos me configurar para eu começar")
        _print_sellbird("a prospectar para você. Eu te guio em tudo.")
        _print_sellbird("Leva uns 5 minutos.\n")

        total_steps = 7

        # Step 1: Check prerequisites
        _print_step(1, total_steps, "Conferindo os pré-requisitos")
        await self._check_prerequisites()

        # Step 2: Connect email platform
        _print_step(2, total_steps, "Plataforma de e-mail (Instantly)")
        await self._setup_email_platform()

        # Step 3: LinkedIn (optional)
        _print_step(3, total_steps, "LinkedIn (opcional)")
        self._setup_linkedin()

        # Step 4: Cloudflare crawling (optional)
        _print_step(4, total_steps, "Leitura de sites (opcional)")
        self._setup_cloudflare()

        # Step 5: Train on product
        _print_step(5, total_steps, "Treine o Sellbird no seu produto")
        await self._setup_product()

        # Step 6: Configure behavior
        _print_step(6, total_steps, "Configure o comportamento")
        self._setup_behavior()

        # Step 7: Cold-email check (optional)
        _print_step(7, total_steps, "Checagem de e-mail frio (opcional)")
        self._setup_compliance()

        # Write everything
        self._write_env()
        self._write_config()

        # Final summary
        await self._print_summary()

    async def _check_prerequisites(self):
        """Pick the brain provider and verify its CLI is installed and working."""
        self.brain_config = _ask_brain_config()
        if self.brain_config.provider == "codex":
            await self._check_codex()
        else:
            await self._check_claude()

    async def _check_claude(self):
        # Check Claude CLI
        print("\n  Conferindo o Claude Code CLI...", end=" ")
        if _check_claude_cli():
            print("✓ Encontrado")
        else:
            print("✗ Não encontrado")
            _print_sellbird("Eu preciso do Claude Code CLI para pensar. Instale em:")
            print("         https://claude.ai/download")
            print("\n         Depois de instalar, rode 'claude login' para entrar,")
            print("         e rode esta configuração de novo.")
            raise SystemExit(1)

        # Test headless mode
        print("  Testando o Claude sem interface...", end=" ", flush=True)
        state = StateManager()
        await state.init_db()
        brain = Brain(state, self.brain_config)
        if await _test_claude(brain):
            print("✓ Funcionando")
        else:
            print("✗ Falhou")
            _print_sellbird("O Claude CLI está instalado, mas o modo sem interface não funciona.")
            _print_sellbird("Confira se você entrou: rode 'claude login'")
            print("\n         Confira também se a sua assinatura Max está ativa.")
            if not _ask_yes_no("Continuar mesmo assim?", default=False):
                raise SystemExit(1)
        self._check_python_packages()

    async def _check_codex(self):
        from sellbird.codex import (
            CODEX_INSTALL_HINT, CodexError, check_cli_version, check_native_auth,
        )

        print("\n  Conferindo o Codex CLI...", end=" ")
        if _check_codex_cli():
            print("✓ Encontrado")
        else:
            print("✗ Não encontrado")
            _print_sellbird("Eu preciso do Codex CLI para pensar com o seu plano do ChatGPT:")
            print(f"         {CODEX_INSTALL_HINT}")
            print("\n         Depois rode 'codex login', escolha 'Sign in with ChatGPT',")
            print("         e rode esta configuração de novo.")
            raise SystemExit(1)

        print("  Conferindo a versão do Codex CLI...", end=" ")
        try:
            print(f"✓ {check_cli_version()}")
        except CodexError as e:
            print("✗ Não suportado")
            _print_sellbird(str(e))
            raise SystemExit(1)

        print("  Conferindo o login do ChatGPT no Codex...", end=" ")
        try:
            check_native_auth()
            print("✓ Encontrado")
        except CodexError as e:
            print("✗ Não está pronto")
            _print_sellbird(str(e))
            raise SystemExit(1)

        # A real (subscription, not API-billed) call through the same
        # isolated runtime Sellbird uses for every prompt.
        print("  Testando o Codex (isolado, sem ferramentas)...", end=" ", flush=True)
        state = StateManager()
        await state.init_db()
        brain = Brain(state, self.brain_config)
        if await _test_claude(brain):
            print("✓ Funcionando")
        else:
            print("✗ Falhou")
            _print_sellbird("O Codex está instalado, mas a chamada de teste falhou. O registro")
            _print_sellbird("acima diz o motivo (login, limites do plano ou isolamento).")
            if not _ask_yes_no("Continuar mesmo assim?", default=False):
                raise SystemExit(1)
        self._check_python_packages()

    def _check_python_packages(self):
        # Check Python packages
        print("  Conferindo as dependências do Python...", end=" ")
        missing = []
        for pkg in ["httpx", "aiosqlite", "yaml", "pydantic", "bs4"]:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
        if not missing:
            print("✓ Tudo instalado")
        else:
            print(f"✗ Faltando: {', '.join(missing)}")
            print("\n  Rode: pip install -r requirements.txt")
            if not _ask_yes_no("Continuar mesmo assim?", default=False):
                raise SystemExit(1)

        _print_sellbird("Os pré-requisitos estão ok. Vamos em frente.")

    async def _setup_email_platform(self):
        """Configure Instantly API."""
        _print_sellbird("Eu preciso de uma plataforma de e-mail frio para enviar campanhas.")
        _print_sellbird("Nesta etapa eu configuro o Instantly. Gmail, Microsoft 365 e SMTP (Hostinger, Locaweb...) você configura no painel, em Configurações.")

        has_instantly = _ask_yes_no("Você tem conta no Instantly?")

        if has_instantly:
            api_key = _ask("Chave de API do Instantly (em Settings → Integrations; digitação oculta)", secret=True)
            self.env_vars["INSTANTLY_API_KEY"] = api_key

            # Test the key
            print("\n  Testando a chave de API...", end=" ", flush=True)
            if await _test_instantly(api_key):
                print("✓ Conectado")
                _print_sellbird("Perfeito. Agora consigo enviar campanhas pelo Instantly.")
            else:
                print("✗ Falhou")
                _print_sellbird("Não deu para conectar. A chave pode estar errada, ou você pode")
                _print_sellbird("precisar do plano Growth para ter API. Vou salvar mesmo assim;")
                _print_sellbird("você corrige depois no .env.")
        else:
            _print_sellbird("Sem problema. Use o Gmail, o Microsoft 365 ou um SMTP (configure no painel, em Configurações).")
            _print_sellbird("Se um dia quiser o Instantly: https://instantly.ai (plano Growth para ter API).")
            _print_sellbird("A chave vai no .env como INSTANTLY_API_KEY.")
            self.env_vars["INSTANTLY_API_KEY"] = ""

    def _setup_linkedin(self):
        """Configure LinkedIn credentials."""
        _print_sellbird("Eu posso pesquisar no LinkedIn para encontrar prospects do seu ICP.")
        _print_sellbird("Eu entro na sua conta do LinkedIn com um navegador, com")
        _print_sellbird("limites conservadores e ritmo de pessoa.")
        print("\n  ⚠  Atenção: automatizar o LinkedIn viola os Termos de Uso deles.")
        print("     Contas que fazem isso podem ser restringidas ou banidas. Só use uma")
        print("     conta que você aceita arriscar, e mantenha os")
        print("     limites padrão. Isto é totalmente opcional.")

        use_linkedin = _ask_yes_no("Configurar a prospecção no LinkedIn mesmo assim?", default=False)

        if use_linkedin:
            email = _ask("E-mail/usuário do LinkedIn")
            password = _ask("Senha do LinkedIn (digitação oculta)", secret=True)
            self.env_vars["LINKEDIN_EMAIL"] = email
            self.env_vars["LINKEDIN_PASSWORD"] = password

            _print_sellbird("Entendido. Vou ficar bem abaixo dos limites e agir")
            _print_sellbird("como uma pessoa cuidadosa, mas o risco dos termos de uso é seu.")
        else:
            _print_sellbird("Tudo bem. Ainda consigo encontrar prospects pelo Google")
            _print_sellbird("e pelos sites das empresas. Você pode adicionar o LinkedIn depois.")
            self.env_vars["LINKEDIN_EMAIL"] = ""
            self.env_vars["LINKEDIN_PASSWORD"] = ""

    def _setup_cloudflare(self):
        """Configure Cloudflare Browser Rendering for deep crawling."""
        _print_sellbird("Quando eu treino com o site do produto, posso ler ele a fundo")
        _print_sellbird("usando a API Browser Rendering da Cloudflare. Assim eu consigo")
        _print_sellbird("lidar com sites cheios de JavaScript e ler centenas de páginas.")
        _print_sellbird("Custa US$ 5/mês por ~12.000 páginas. Totalmente opcional.")

        use_cloudflare = _ask_yes_no("Configurar a leitura com Cloudflare?", default=False)

        if use_cloudflare:
            account_id = _ask("ID da conta Cloudflare")
            api_token = _ask("Token de API da Cloudflare (precisa da permissão Browser Rendering - Edit; digitação oculta)", secret=True)
            self.env_vars["CLOUDFLARE_ACCOUNT_ID"] = account_id
            self.env_vars["CLOUDFLARE_API_TOKEN"] = api_token
            _print_sellbird("Boa. Vou usar a Cloudflare para ler a fundo no treinamento.")
        else:
            _print_sellbird("Sem problema. Vou usar meu leitor próprio. Ele funciona")
            _print_sellbird("bem na maioria dos sites, só não roda JavaScript.")
            self.env_vars["CLOUDFLARE_ACCOUNT_ID"] = ""
            self.env_vars["CLOUDFLARE_API_TOKEN"] = ""

    async def _setup_product(self):
        """Train Sellbird on the product — either via URL or manual entry."""
        _print_sellbird("Agora a parte importante: preciso aprender o que você vende.")
        _print_sellbird("Posso ler o seu site e descobrir sozinho,")
        _print_sellbird("ou você me conta o básico à mão.\n")

        method = _ask(
            "Treinar pelo site ou digitar à mão? (url/manual)",
            default="url",
        ).lower()

        if method in ("url", "u", "website"):
            url = _ask("O site do seu produto (ex.: https://suaempresa.com.br)")

            _print_sellbird(f"Me dá um minuto: vou ler {url}")
            _print_sellbird("e aprender tudo o que puder sobre o seu produto.\n")

            from sellbird.trainer import Trainer
            trainer = Trainer(brain_config=self.brain_config)
            self.config = await trainer.train(url, str(_config_file())) or {}

            if self.config:
                _print_sellbird("Treinamento concluído. Agora entendo bem")
                _print_sellbird("o seu produto. Confira o sellbird.local.yaml para revisar")
                _print_sellbird("o que aprendi e ajuste o que estiver estranho.")
                return

            _print_sellbird("Hmm, tive problema com esse site. Vamos fazer à mão.")

        # Manual entry
        _print_sellbird("Vou fazer algumas perguntas sobre o seu produto.\n")

        company = _ask("Nome da empresa")
        product = _ask("Nome do produto/serviço")
        description = _ask("Descrição em uma linha (o que faz e para quem é?)")
        pricing = _ask("Preço", default="Sob consulta")

        print("\n  Digite de 3 a 5 benefícios principais (um por linha, linha vazia para terminar):")
        benefits = []
        while True:
            b = _ask(f"  Benefício {len(benefits) + 1}", required=False)
            if not b:
                break
            benefits.append(b)

        _print_sellbird("Agora vamos definir o seu cliente ideal.\n")

        industries = _ask("Segmentos-alvo (separados por vírgula)").split(",")
        industries = [i.strip() for i in industries if i.strip()]

        titles = _ask("Cargos de quem decide (separados por vírgula)").split(",")
        titles = [t.strip() for t in titles if t.strip()]

        company_size = _ask("Porte das empresas-alvo", default="2-50 funcionários")
        geography = _ask(
            "Região-alvo (para uma cidade, inclua o estado/país, "
            "ex.: 'Londrina, PR'; um nome de cidade sozinho pode "
            "cair no lugar errado no mapa)",
            default="Brasil",
        ).split(",")
        geography = [g.strip() for g in geography if g.strip()]

        _print_sellbird("Agora vamos falar da sua oferta: o que acontece quando alguém se interessa?\n")

        primary_offer = _ask(
            "Qual é a sua oferta principal? (ex.: 'Assinatura a R$ 99/mês', 'Gestão de marketing mensal')",
            required=False,
        )
        entry_offer = _ask(
            "Alguma oferta de entrada sem compromisso? (ex.: 'Teste grátis', 'Diagnóstico gratuito', 'Relatório de exemplo')",
            default="",
            required=False,
        )

        print("\n  Qual é o objetivo quando alguém se interessa?")
        print("    1. Marcar uma conversa")
        print("    2. Começar um teste grátis")
        print("    3. Só conseguir uma resposta / começar uma conversa")
        goal_choice = _ask("Objetivo (1/2/3)", default="1")
        goal_map = {"1": "book_call", "2": "start_trial", "3": "get_reply"}
        goal = goal_map.get(goal_choice, "book_call")

        booking_method = "suggest_times"
        booking_url = ""
        meeting_duration = "15 minutos"
        meeting_owner = ""

        if goal == "book_call":
            has_calendar = _ask_yes_no("Você tem um link de agendamento (Calendly, Cal.com, Google Agenda etc.)?")
            if has_calendar:
                booking_url = _ask("Link de agendamento")
                booking_method = "calendar_link"
            else:
                print("\n  Como o Sellbird deve sugerir horários?")
                print("    1. Sugerir horários ('Pode ser quinta às 14h?')")
                print("    2. Perguntar a preferência ('Como está sua agenda?')")
                method_choice = _ask("Método (1/2)", default="1")
                booking_method = "suggest_times" if method_choice == "1" else "ask_preference"

            meeting_duration = _ask("Quanto tempo dura a conversa?", default="15 minutos")
            meeting_owner = _ask("Quem participa da reunião? (seu nome ou cargo)", required=False)

        _print_sellbird("Com que nome eu assino a abordagem?\n")

        persona_name = _ask("Meu nome (o que os prospects veem)", default="Alex")
        persona_email = _ask("Meu e-mail")
        persona_role = _ask("Meu cargo", default="Desenvolvimento de Negócios")

        self.config = {
            "persona": {
                "name": persona_name,
                "company": company,
                "role": persona_role,
                "email": persona_email,
                "linkedin": "",
                "tone": "profissional, consultivo, confiante",
            },
            "product": {
                "name": product,
                "description": description,
                "pricing": pricing,
                "key_benefits": benefits or ["Benefício 1"],
                "objection_responses": {},
                "offer": {
                    "primary": primary_offer or "",
                    "entry": entry_offer or "",
                    "goal": goal,
                    "booking_method": booking_method,
                    "booking_url": booking_url,
                    "meeting_duration": meeting_duration,
                    "meeting_owner": meeting_owner or "",
                },
            },
            "icp": {
                "industries": industries or ["Technology"],
                "company_size": company_size,
                "titles": titles or ["VP", "Director"],
                "geography": geography,
            },
            "channels": {
                "email": {
                    "enabled": True,
                    "provider": "instantly",
                    "max_daily_sends": 50,
                },
                "linkedin": {
                    "enabled": bool(self.env_vars.get("LINKEDIN_EMAIL")),
                    "max_daily_connections": 20,
                    "max_daily_messages": 10,
                },
            },
            "usage": {
                "max_daily_claude_percent": 80,
                "heartbeat_interval_minutes": 15,
                "quiet_hours": {
                    "start": "22:00",
                    "end": "07:00",
                    "timezone": "America/New_York",
                },
            },
        }

        self.manual_product = True
        _print_sellbird("Entendido. Tenho tudo o que preciso sobre o seu produto.")

    def _setup_behavior(self):
        """Configure Sellbird's operational behavior."""
        _print_sellbird("Última coisa: algumas configurações de como eu trabalho.\n")

        # Usage limit
        print("  Eu controlo meu uso do Claude para não gastar toda a sua cota diária.")
        usage_pct = _ask(
            "% máximo do uso diário do Claude que posso consumir",
            default="80",
        )
        try:
            usage_pct = min(100.0, max(1.0, float(usage_pct)))
        except ValueError:
            print("    (não entendi; usando 80)")
            usage_pct = 80.0

        # Heartbeat interval
        print("\n  Eu acordo de tempos em tempos para ver se tem trabalho.")
        interval = _ask(
            "De quanto em quanto tempo devo conferir (minutos)?",
            default="15",
        )
        try:
            interval = max(1, int(interval))
        except ValueError:
            print("    (não entendi; usando 15)")
            interval = 15

        # Quiet hours
        print("\n  Eu não envio e-mails nem prospecto no horário de silêncio.")
        quiet_start = _ask("Início do horário de silêncio (formato 24h)", default="22:00")
        quiet_end = _ask("Fim do horário de silêncio (formato 24h)", default="07:00")
        timezone = _ask("Seu fuso horário", default="America/New_York")

        # Daily send limit
        daily_sends = _ask(
            "Máximo de e-mails por dia",
            default="50",
        )
        try:
            daily_sends = max(1, int(daily_sends))
        except ValueError:
            print("    (não entendi; usando 50)")
            daily_sends = 50
        if daily_sends > 200:
            print("\n  ⚠  200+ envios por dia num domínio novo vão acabar com a sua")
            print("     entregabilidade. Aqueça aos poucos (veja docs/pt-BR/GUIA.md).")

        # Update config
        if self.config:
            self.config["usage"] = {
                "max_daily_claude_percent": usage_pct,
                "heartbeat_interval_minutes": interval,
                "quiet_hours": {
                    "start": quiet_start,
                    "end": quiet_end,
                    "timezone": timezone,
                },
            }
            if "channels" in self.config and "email" in self.config["channels"]:
                self.config["channels"]["email"]["max_daily_sends"] = daily_sends

        _print_sellbird("Perfeito. Tudo configurado.")

    def _timezone(self) -> str:
        """The timezone this run of setup chose (step 6), else the saved one."""
        usage = self.config.get("usage") if isinstance(self.config, dict) else None
        quiet = usage.get("quiet_hours") if isinstance(usage, dict) else None
        zone = quiet.get("timezone") if isinstance(quiet, dict) else None
        return str(zone or "").strip() or _saved_timezone()

    def _setup_compliance(self):
        """Offer the optional per-recipient check through Precleared.

        Off unless the user says yes. Re-running setup offers the saved
        answers as the defaults, so pressing Enter never switches it off.
        A sender in a UK timezone is told the check is recommended, and GB
        is offered as their country; the check still waits for their yes.
        """
        current = _current_precleared()
        was_on = current.get("enabled") is True
        uk_sender = self._timezone() == "Europe/London"
        _print_sellbird("Antes do primeiro e-mail para alguém novo, posso perguntar ao Precleared")
        _print_sellbird("(precleared.dev) quais regras de e-mail frio valem para a pessoa. Ele cobre")
        _print_sellbird("EUA, Europa e outros países, mas ainda não cobre o Brasil")
        _print_sellbird("(no Brasil, siga a LGPD: veja docs/pt-BR/GUIA.md). Totalmente opcional.")
        if uk_sender:
            # Recommended, not switched on: the check stays opt-in (#93).
            _print_sellbird("Recommended for a UK sender like you: under PECR, whether a cold")
            _print_sellbird("email is allowed turns on who the recipient is (a company or a")
            _print_sellbird("sole trader), and Precleared looks each one up on Companies House.")
        print("\n  Anything that isn't a clear yes waits in the Outbox with the reason.")
        print("  It checks mail sent through Gmail, Microsoft 365 or SMTP, not Instantly.")
        print("  Precleared receives each new recipient's address, your country, how")
        print("  the address was found, your product description and the recipient's")
        print("  country when the company's location makes it certain, else your")
        print("  prospects' country if you set one. It also gets the company's and")
        print("  person's names, to find a UK company on the register; it doesn't")
        print("  store the person's name.")

        if not _ask_yes_no("Ligar a checagem de e-mail frio?", default=was_on):
            # Only touch the config to switch off a check that was on.
            self.precleared = {"enabled": False} if was_on else None
            _print_sellbird("Sem problema. Você pode ligar depois em")
            _print_sellbird(f"compliance.precleared in {_config_file().name}.")
            return

        saved_country = _sender_country(current.get("sender_country"))
        # A UK timezone makes GB the likely answer; Enter takes it.
        default_country = saved_country or ("GB" if uk_sender else "")
        codes = ", ".join(SENDER_COUNTRIES)
        while True:
            country = _sender_country(_ask(
                "Where is your business based? (two-letter code, e.g. GB or US"
                + (")" if default_country else "; blank to skip)"),
                default=default_country,
                required=False,
            ), strict=False)
            if country in SENDER_COUNTRIES:
                break
            if not country:
                self.precleared = {"enabled": False} if was_on else None
                _print_sellbird("Precleared takes a sender based in one of these countries:")
                _print_sellbird(f"{codes}. I'll leave the check off for now.")
                return
            print(f"    (type one of {codes}, or leave it blank to skip)")

        try:
            saved_prospects = normalize_prospect_country(current.get("prospect_country"))
        except ValueError:
            saved_prospects = ""
        hint = "type none if not" if saved_prospects else "blank if not"
        while True:
            answer = _ask(
                f"Your prospects' country, if they're all in one (e.g. US; {hint})",
                default=saved_prospects,
                required=False,
            )
            if answer.strip().lower() == "none":
                prospects = ""
                break
            # "no" answers "if they're all in one" but is also Norway's code.
            if answer.strip().lower() == "no" and not _ask_yes_no(
                    "NO is Norway's code. Are your prospects all in Norway?", default=False):
                prospects = ""
                break
            try:
                prospects = normalize_prospect_country(answer)
                break
            except ValueError as e:
                print(f"    ({e})")

        self.precleared = {
            "enabled": True,
            "sender_country": country,
            "prospect_country": prospects,
        }
        self._ask_precleared_key()

    def _ask_precleared_key(self):
        """Offer a free Precleared key. Enter keeps the current one, or skips.

        Without a key, Sellbird can get a free one for the user's email address
        right here, so nobody has to leave setup for a browser.
        """
        saved_key = _read_env_file().get("PRECLEARED_API_KEY", "").strip("'\" ")
        has_key = bool(saved_key or os.getenv("PRECLEARED_API_KEY", "").strip())
        if not has_key:
            _print_sellbird("Without a key Precleared allows 10 checks a day. A free key")
            _print_sellbird("gives Sellbird 100 a day for its first 14 days, then 25 a day.")
            key = self._get_free_precleared_key()
            if key:
                self.env_vars["PRECLEARED_API_KEY"] = key
                _print_sellbird("Peguei sua chave grátis e salvei no .env.")
                return
        key = _ask(
            "Precleared API key (input hidden; Enter keeps your current key)" if has_key
            else "Precleared API key (input hidden; Enter to skip)",
            required=False,
            secret=True,
        )
        if key:
            self.env_vars["PRECLEARED_API_KEY"] = key
            _print_sellbird("Chave salva no .env.")
        elif has_key:
            _print_sellbird("Mantendo a chave que você já tem.")
        else:
            self.env_vars["PRECLEARED_API_KEY"] = ""
            _print_sellbird("No problem: 10 checks a day without one. Run")
            _print_sellbird("`sellbird precleared-key` whenever you'd like a free key.")

    def _get_free_precleared_key(self) -> str:
        """Offer to get a free key for an email address. Returns the key, or
        "" to fall back to pasting one. The key is never printed."""
        if not _ask_yes_no("Get a free Precleared key now? It only needs your email address"):
            return ""
        print("\n  Precleared receives the address to make the key")
        print("  (privacy: https://precleared.dev/privacy).")
        country = (self.precleared or {}).get("sender_country", "")
        while True:
            email = _ask("Email address for the key (Enter to skip)", required=False)
            if not email:
                return ""
            result = create_free_key(email, country=country)
            if result.key:
                return result.key
            _print_sellbird(f"Couldn't get a key: {result.error}.")
            if not result.bad_email:
                _print_sellbird(f"You can paste one from {GET_KEY_URL} instead.")
                return ""

    def _write_env(self):
        """Write the .env file, preserving any existing variables we didn't touch."""
        existing = _read_env_file()

        # Wizard answers win, but never blank out a previously-set value
        # (e.g. re-running setup and skipping the LinkedIn step).
        merged = dict(existing)
        for key, value in self.env_vars.items():
            if value or key not in merged:
                merged[key] = value

        lines = [f"{key}={value}" for key, value in merged.items()]
        ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            ENV_FILE.chmod(0o600)  # credentials — owner read/write only
        except OSError:
            pass
        logger.info(f"Gravado {ENV_FILE}")

    def _write_config(self):
        """Write sellbird.yaml (only if we have manual config — trainer writes its own)."""
        from sellbird.trainer import brain_section

        config_file = _config_file()
        if self.config:
            self.config["brain"] = brain_section(self.brain_config)
        if self.config and not config_file.exists():
            if self.precleared:
                _save_precleared(self.config, self.precleared)
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Gravado {config_file}")
            self.config_saved = True
        elif self.config:
            # Config already exists (shipped or from trainer): update behavior
            # settings, plus product answers when they were entered by hand
            try:
                existing = yaml.safe_load(read_user_text(config_file)) or {}
                if self.manual_product:
                    for section in ("persona", "product", "icp"):
                        if section in self.config:
                            if not isinstance(existing.get(section), dict):
                                existing[section] = {}
                            _merge_answers(existing[section], self.config[section])
                existing["usage"] = self.config.get("usage", existing.get("usage", {}))
                existing["brain"] = self.config["brain"]
                if "LINKEDIN_EMAIL" in self.env_vars:
                    existing.setdefault("channels", {}).setdefault("linkedin", {})["enabled"] = bool(
                        self.env_vars["LINKEDIN_EMAIL"]
                    )
                if "channels" in self.config:
                    existing.setdefault("channels", {})
                    if "email" in self.config["channels"]:
                        existing["channels"].setdefault("email", {})
                        existing["channels"]["email"]["max_daily_sends"] = (
                            self.config["channels"]["email"].get("max_daily_sends", 50)
                        )
                if self.precleared:
                    _save_precleared(existing, self.precleared)
                text = yaml.dump(existing, default_flow_style=False, sort_keys=False)
                with open(config_file, "w", encoding="utf-8") as f:
                    f.write(text)
                self.config_saved = True
            except Exception as e:
                _print_sellbird(f"Não deu para salvar suas configurações em {config_file.name} ({e}).")
                _print_sellbird("Nada foi alterado. Corrija o arquivo e rode a configuração de novo.")

    async def _print_summary(self):
        """Print final summary and next steps."""
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   Configuração concluída!                                ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")

        # Show what's configured
        checks = {
            ("Codex CLI (ChatGPT plan)" if self.brain_config.provider == "codex"
             else "Claude Code CLI"): (_check_codex_cli() if self.brain_config.provider == "codex"
                                      else _check_claude_cli()),
            "Instantly API": bool(self.env_vars.get("INSTANTLY_API_KEY")),
            "LinkedIn": bool(self.env_vars.get("LINKEDIN_EMAIL")),
            "Cloudflare Crawl": bool(self.env_vars.get("CLOUDFLARE_ACCOUNT_ID")),
            "Produto treinado": _product_configured(),
            "Checagem de e-mail frio (Precleared)": bool(
                self.config_saved and self.precleared and self.precleared.get("enabled")),
        }

        for name, ok in checks.items():
            status = "✓" if ok else "–"
            print(f"  {status} {name}")

        print(f"""
  Arquivos criados:
    - .env (suas credenciais)
    - {_config_file().name} (sua configuração)

  Para ligar o Sellbird:
    sellbird run          (ou: python -m sellbird)

  Para treinar com outro produto:
    sellbird train https://outroproduto.com.br

  Para rodar esta configuração de novo:
    sellbird setup

  Antes de mandar o primeiro e-mail:
    1. Use um domínio só para envio (não o principal) com
       SPF, DKIM e DMARC configurados.
    2. Aqueça por 2 a 4 semanas antes de volume de verdade.
    3. Coloque o endereço da empresa em compliance.postal_address e
       mantenha a linha de descadastro (LGPD / CAN-SPAM).
    Veja docs/pt-BR/GUIA.md.
""")
        _print_sellbird("Estou pronto. Rode 'sellbird run' e eu começo.")
        _print_sellbird("Dê o primeiro passo.\n")


async def run_setup():
    wizard = SetupWizard()
    await wizard.run()


def main():
    asyncio.run(run_setup())


if __name__ == "__main__":
    from sellbird.textio import utf8_stdio
    utf8_stdio()
    main()
