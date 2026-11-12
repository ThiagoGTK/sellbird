"""Sellbird CLI — simple commands to install, setup, run, and manage Sellbird."""

import argparse
import asyncio
import subprocess
import sys
import textwrap
from pathlib import Path


MIN_PYTHON = (3, 11)


def _check_python_version():
    """Refuse to install on a Python that cannot run Sellbird.

    `python3 -m venv .venv` on macOS builds the venv from /usr/bin/python3,
    which is 3.9 — old enough that Sellbird's `X | Y` type syntax fails at
    import. The install itself appears to succeed and the failure surfaces
    later as an unrelated-looking ImportError, so check up front and name the
    fix.
    """
    if sys.version_info >= MIN_PYTHON:
        return

    have = f"{sys.version_info.major}.{sys.version_info.minor}"
    want = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
    print(f"\n  O Sellbird precisa do Python {want} ou mais novo. Este é o Python {have}.")
    print(f"  ({sys.executable})\n")
    print("  No macOS, o `python3` costuma ser o 3.9 do sistema, então um venv criado")
    print("  com ele também é 3.9. Crie o venv com um Python mais novo:\n")
    print("    brew install python@3.13")
    print("    rm -rf .venv")
    print("    $(brew --prefix)/bin/python3.13 -m venv .venv")
    print("    source .venv/bin/activate && pip install -e .\n")
    sys.exit(1)


def cmd_install(args):
    """Install all dependencies including Playwright browsers."""
    _check_python_version()
    print("\n  Instalando as dependências do Sellbird...\n")

    # An installed app (pipx, pip) already has its packages; only a checkout
    # installs them, from the checkout (not the home folder).
    from sellbird.paths import PACKAGE_ROOT, is_checkout
    checkout = is_checkout(PACKAGE_ROOT)
    if checkout:
        print("  [1/2] Instalando os pacotes Python...")
        requirements = PACKAGE_ROOT / "requirements.txt"
        # Fall back to an editable install from pyproject.toml
        pip_args = ["-r", "requirements.txt"] if requirements.exists() else ["-e", "."]
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", *pip_args],
            cwd=str(PACKAGE_ROOT),
        )
        if result.returncode != 0:
            print("\n  Não deu para instalar os pacotes Python.")
            print("  Dica: confira se você está dentro de um ambiente virtual "
                  "(python3 -m venv .venv && source .venv/bin/activate).")
            sys.exit(1)
        print("  ✓ Pacotes Python instalados.\n")
    else:
        print("  [1/2] Pacotes Python: já fazem parte desta instalação.")

    # Install Playwright browsers
    print("  [2/2] Instalando os navegadores do Playwright...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            timeout=600,
        )
        playwright_ok = result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        playwright_ok = False
    if not playwright_ok:
        print("\n  A instalação do navegador do Playwright falhou (opcional, só precisa para o LinkedIn).")
    else:
        print("  ✓ Navegadores do Playwright instalados.\n")

    if checkout:
        _ensure_importable(str(PACKAGE_ROOT))
    print("  O Sellbird está instalado. Agora rode 'sellbird setup'.\n")


def _ensure_importable(project_root: str):
    """Make sure `import sellbird` works outside the repo directory.

    Python 3.13 silently skips .pth files carrying the macOS 'hidden'
    file flag, and some Macs propagate that flag to everything inside
    dot-directories like .venv — which breaks editable installs. When
    that happens, fall back to symlinking the package into site-packages
    (imports don't check the hidden flag; only .pth parsing does).
    """
    check = subprocess.run(
        [sys.executable, "-c", "import sellbird"],
        cwd="/", capture_output=True,
    )
    if check.returncode == 0:
        return

    try:
        import site
        site_packages = Path(site.getsitepackages()[0])
        link = site_packages / "sellbird"
        target = Path(project_root) / "sellbird"
        if not link.exists() and target.is_dir():
            link.symlink_to(target)
            recheck = subprocess.run(
                [sys.executable, "-c", "import sellbird"],
                cwd="/", capture_output=True,
            )
            if recheck.returncode == 0:
                print("  ✓ Visibilidade do pacote corrigida (o .pth editável estava sendo "
                      "ignorado; o pacote foi ligado direto).\n")
                return
    except OSError as e:
        print(f"  Não deu para aplicar a correção de import: {e}")

    print("\n  Aviso: 'import sellbird' falha fora da pasta do projeto.")
    print("  Rode os comandos do sellbird na pasta do projeto, ou reinstale com:")
    print("    pip install -e . --config-settings editable_mode=compat\n")


def cmd_setup(args):
    """Roda o assistente de configuração."""
    from sellbird.setup import run_setup

    asyncio.run(run_setup())


def cmd_run(args):
    """Start Sellbird's heartbeat loop."""
    from sellbird.main import main

    main()


def cmd_train(args):
    """Train Sellbird on a website."""
    from sellbird.trainer import Trainer

    url = args.url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
        print(f"  Sem http/https; usando {url}")

    if args.max_pages < 1:
        print("  max_pages precisa ser pelo menos 1.")
        sys.exit(2)

    from pydantic import ValidationError
    from sellbird.config import BrainConfig, ConfigError, load_brain_config

    try:
        brain_config = load_brain_config()
        overrides = {
            k: v for k, v in (
                ("provider", args.provider),
                ("model", args.model),
                ("reasoning_effort", args.reasoning_effort),
            ) if v is not None
        }
        if overrides:
            if "provider" in overrides and overrides["provider"] != brain_config.provider:
                # A different provider never inherits the other one's model.
                brain_config = BrainConfig(**overrides)
            else:
                brain_config = BrainConfig(**{**brain_config.model_dump(), **overrides})
    except (ConfigError, ValidationError) as e:
        print(f"  {e}")
        sys.exit(2)

    trainer = Trainer(brain_config=brain_config)
    asyncio.run(trainer.train(url, max_pages=args.max_pages))


def cmd_mcp(args):
    """Serve MCP over stdio for the user's coding agent. Prints nothing else."""
    # `sellbird mcp install|uninstall [claude|codex]` and --print.
    if getattr(args, "mcp_action", None):
        from sellbird import mcp_install
        sys.exit(mcp_install.run_command(args.mcp_action, args.client,
                                         print_only=args.print_config, yes=args.yes))
    if getattr(args, "print_config", False) or getattr(args, "yes", False):
        print("  --print e --yes vão junto com install ou uninstall, "
              "ex.: sellbird mcp install --print", file=sys.stderr)
        sys.exit(2)
    from sellbird.mcp_server import run_stdio

    run_stdio()


def cmd_dashboard(args):
    """Launch the local web dashboard."""
    from sellbird.dashboard import DashboardSetupError, dashboard_url, start_dashboard
    from sellbird.dashboard_auth import TokenError

    if not 1 <= args.port <= 65535:
        print(f"  Porta inválida: {args.port}. Precisa ser de 1 a 65535.")
        sys.exit(2)

    try:
        if getattr(args, "url", False):
            # The unlock link for an already-running dashboard.
            print(dashboard_url(host=args.host, port=args.port))
            return
        start_dashboard(host=args.host, port=args.port)
    except (DashboardSetupError, TokenError) as e:
        print(f"\n  O painel não foi iniciado: {e}\n")
        sys.exit(2)


def cmd_status(args):
    """Show current pipeline status."""
    from sellbird.state import StateManager

    async def _status():
        state = StateManager()
        await state.init_db()
        summary = await state.get_state_summary()

        print("\n  Situação do funil do Sellbird")
        print("  " + "=" * 40)
        print(f"  Prospects:            {summary['prospects']}")
        print(f"  Prontos para escrever: {summary.get('writable_prospects', 0)} "
              "(novos, com e-mail verificado ou aceita-tudo)")
        write_failed = (summary.get("prospects") or {}).get("write_failed", 0)
        if write_failed:
            print(f"  Não deu para escrever: {write_failed} (os rascunhos do modelo continuaram voltando "
                  "inutilizáveis; `sellbird retry-writes` tenta de novo)")
        no_tip = (summary.get("prospects") or {}).get("no_tip", 0)
        if no_tip:
            print(f"  Nada concreto para escrever: {no_tip} (writer.require_tip pulou; "
                  "`sellbird retry-writes --no-tip` tenta de novo quando souber mais)")
        print(f"  Campanhas rascunho:   {summary['draft_campaigns']}")
        print(f"  Campanhas ativas:     {summary['active_campaigns']}")
        print(f"  Conversas abertas:    {summary['open_conversations']}")
        by_provider = summary.get("usage_today_by_provider", {})
        print(f"  Chamadas Claude hoje: {by_provider.get('claude', summary['usage_today'])}")
        print(f"  Chamadas Codex hoje:  {by_provider.get('codex', 0)}")
        from sellbird.config import compliance_notice, load_config, sending_notice
        loaded = None
        try:
            loaded = load_config()
            notice = sending_notice(loaded)
            address_notice = compliance_notice(loaded)
        except Exception:
            # Status must still print when sellbird.yaml is broken; that's
            # when people run it. The --check path reports config errors.
            notice = address_notice = ""
        from sellbird.main import unusable_backlog_notice
        backlog = unusable_backlog_notice(summary)
        if backlog:
            print("  Prospecção:           PAUSADA")
            print(textwrap.fill(backlog, width=72, initial_indent="                        ",
                                subsequent_indent="                        "))
        if notice:
            print("  Envio:                RETIDO")
            print(textwrap.fill(notice, width=72, initial_indent="                        ",
                                subsequent_indent="                        "))
        from sellbird.agents.writer import EMAIL_RULES_PROBLEM_KEY
        rules_problem = await state.get_setting(EMAIL_RULES_PROBLEM_KEY)
        if rules_problem:
            print(f"  Escrita:              PARADA (writer.email_rules: {rules_problem})")
        hold = await state.current_sends_held()
        if hold:
            from sellbird.sending_mode import held_message
            waiting = len(await state.get_outbox(status="approved", limit=500))
            title, detail = held_message(hold, waiting=waiting)
            print(f"  Envio:                NÃO ESTÁ ENVIANDO ({title.split(': ', 1)[-1]})")
            print(textwrap.fill(detail, width=72, initial_indent="                        ",
                                subsequent_indent="                        "))
        from sellbird.integrations.precleared import current_hold, hold_message
        precleared_hold = await current_hold(state, loaded)
        if precleared_hold:
            message = hold_message(precleared_hold)
            print(f"  Precleared:           SEGURANDO E-MAIL FRIO desde {precleared_hold.get('since', '?')}")
            print(textwrap.fill(f"{message['title']}. {message['detail']}", width=72,
                                initial_indent="                        ",
                                subsequent_indent="                        "))
        if address_notice:
            print("  Endereço postal:      FALTANDO")
            print(textwrap.fill(address_notice, width=72, initial_indent="                        ",
                                subsequent_indent="                        "))
        from sellbird.brain import BRAIN_STATUS_KEY, Brain, active_brain_status
        from sellbird.config import ConfigError, load_brain_config
        try:
            brain_config = load_brain_config()
        except ConfigError as e:
            brain_config, config_error = None, e
        # Only the configured provider's health: an old Codex pause says
        # nothing once sellbird.yaml has switched to Claude.
        brain_status = active_brain_status(
            await state.get_setting(BRAIN_STATUS_KEY),
            brain_config.provider if brain_config else "")
        healthy = True
        if getattr(args, "check", False):
            if brain_config is None:
                print(f"  Cérebro:              erro de configuração: {config_error}")
                healthy = False
            else:
                brain = Brain(state, brain_config)
                problem = await brain.preflight()
                label = brain.provider_label + (f" ({brain.model})" if brain.model else "")
                if problem:
                    healthy = False
                    print(f"  Cérebro:              {label} NÃO ESTÁ PRONTO")
                    print(f"                        {problem}")
                elif brain.provider == "codex":
                    print(f"  Cérebro:              {label} pronto (CLI, isolamento, login, "
                          "modelo e conta conferidos; nenhum prompt enviado)")
                else:
                    print(f"  Cérebro:              {label} flags de isolamento do CLI presentes "
                          "(login não conferido: o Claude é conferido na primeira chamada)")
        elif brain_status.get("status") == "paused":
            label = {"claude": "Claude", "codex": "Codex"}.get(brain_status.get("provider"), "Brain")
            print(f"  Cérebro:              {label} PAUSADO desde {brain_status.get('since', '?')}")
            print(f"                        {brain_status.get('reason', '')}")
        print()
        return healthy

    if not asyncio.run(_status()):
        # `sellbird status --check` failing is something scripts can act on.
        raise SystemExit(1)


def cmd_usage(args):
    """Show brain usage: active provider's quota, totals, breakdowns."""
    from sellbird.state import StateManager
    from sellbird.config import ConfigError, load_brain_config

    async def _usage():
        state = StateManager()
        await state.init_db()

        try:
            brain_config = load_brain_config()
        except ConfigError as e:
            print(f"  {e}")
            brain_config = None

        # Live quota for the ACTIVE provider only (best-effort). Each
        # subscription's gauge is read from its own source and labelled as
        # such; one is never shown as the other.
        windows = None
        provider = brain_config.provider if brain_config else None
        try:
            if provider == "codex":
                from sellbird.codex import CodexClient, CodexQuotaClient
                windows = await CodexQuotaClient(
                    CodexClient(model=brain_config.model)).get_utilization()
            elif provider == "claude":
                from sellbird.integrations.quota import QuotaClient
                windows = await QuotaClient().get_utilization()
        except Exception:
            pass

        label = {"claude": "Claude", "codex": "Codex"}.get(provider, "Brain")
        print(f"\n  {label} Uso")
        print("  " + "=" * 52)
        if windows:
            labels = {"five_hour": "Janela de 5 horas", "seven_day": "Weekly",
                      "limit_reached": "Limite de uso"}
            for key, w in windows.items():
                resets = f"  (renova {w['resets_at']})" if w.get("resets_at") else ""
                print(f"  {labels.get(key, key):<16} {w['utilization']:5.1f}% usado{resets}")
        elif provider == "codex":
            print("  Medidor de cota indisponível (confira 'codex login', a versão do Codex CLI "
                  "e a rede).")
        elif provider == "claude":
            print("  Medidor de cota indisponível (rode 'claude login' ou confira a rede).")

        totals = await state.usage_totals()
        print()
        print(f"  {'Período':<10} {'Chamadas':>8} {'Entrada':>12} {'Saída':>10} {'Leit. cache':>12}")
        for label, key in (("Hoje", "today"), ("7 dias", "week"), ("30 dias", "month")):
            t = totals.get(key) or {}
            print(
                f"  {label:<10} {t.get('calls', 0):>8} "
                f"{t.get('input_tokens', 0):>12,} {t.get('output_tokens', 0):>10,} "
                f"{t.get('cache_read_tokens', 0):>12,}"
            )

        by_provider = await state.usage_by_provider(days=args.days)
        if len(by_provider) > 1 or (by_provider and by_provider[0]["provider"] != "claude"):
            print(f"\n  Por provedor (últimos {args.days} dias):")
            for row in by_provider:
                print(
                    f"    {row['provider']:<14} {row['calls']:>5} chamadas  "
                    f"{row['output_tokens']:>10,} tokens de saída"
                )

        by_agent = await state.usage_by_agent(days=args.days)
        if by_agent:
            print(f"\n  Por agente (últimos {args.days} dias):")
            for row in by_agent:
                print(
                    f"    {row['agent']:<14} {row['calls']:>5} chamadas  "
                    f"{row['output_tokens']:>10,} tokens de saída"
                )

        by_task = await state.usage_by_task(days=args.days)
        if by_task:
            print(f"\n  Por tarefa (últimos {args.days} dias):")
            for row in by_task[:10]:
                print(
                    f"    {row['task']:<22} {row['calls']:>5} chamadas  "
                    f"{row['output_tokens']:>10,} tokens de saída"
                )
        print(
            "\n  Planos de assinatura não cobram por token: estes são contadores"
            "\n  de uso, não custos.\n"
        )

    asyncio.run(_usage())


def cmd_companies(args):
    """Write the company register to a CSV and summarise it."""
    from collections import Counter
    from datetime import date
    from sellbird.config import load_config
    from sellbird.paths import PROJECT_ROOT
    from sellbird.register import build_register, sqlite_query, to_csv
    from sellbird.state import DB_PATH

    if not DB_PATH.exists():
        print("\n  Ainda não há banco de dados: rode 'sellbird discover' ou 'sellbird run' primeiro.\n")
        return
    rows = asyncio.run(build_register(sqlite_query(DB_PATH), load_config()))
    out = Path(args.out) if args.out else (
        PROJECT_ROOT / "data" / "exports" / f"company-register-{date.today():%Y-%m-%d}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so spreadsheet apps open non-ASCII company names correctly.
    out.write_text(to_csv(rows), encoding="utf-8-sig")
    print(f"\n  Registro de empresas: {len(rows)} empresas → {out}")
    for status, n in Counter(r["status"] for r in rows).most_common():
        print(f"    {status:<18} {n}")
    print()


def cmd_export(args):
    """Export the prospect list as a sequencer-ready CSV."""
    from sellbird.state import StateManager
    from sellbird.export import export_prospects_csv

    async def _export():
        state = StateManager()
        await state.init_db()

        email_statuses = None
        if args.email_status:
            email_statuses = [s.strip() for s in args.email_status.split(",") if s.strip()]
        statuses = None
        if args.status:
            statuses = [s.strip() for s in args.status.split(",") if s.strip()]

        count, _ = await export_prospects_csv(
            state,
            out_path=args.out,
            email_statuses=email_statuses,
            min_score=args.min_score,
            statuses=statuses,
            include_all=args.all,
        )
        scope = "todos os prospects" if args.all else (
            f"situação do e-mail {email_statuses or ['verified', 'risky']}"
            + (f", nota >= {args.min_score}" if args.min_score else "")
        )
        print(f"\n  Exportados {count} prospect(s) para {args.out}  ({scope})")
        if count == 0 and not args.all:
            print("  Dica: ainda sem e-mails válidos? Adicione uma REOON_API_KEY no .env para")
            print("  o Sellbird verificar os endereços, ou use --all para a lista bruta.\n")
        else:
            print("  O CSV importa direto no Instantly, Smartlead ou qualquer ferramenta de sequência.\n")

    asyncio.run(_export())


def cmd_gmail(args):
    """Gmail provider utilities (auth / test)."""
    from sellbird.config import load_env

    env = load_env()
    if args.gmail_action == "auth":
        from sellbird.integrations.gmail import run_auth_flow
        ok = run_auth_flow(env.gmail_client_id, env.gmail_client_secret)
        sys.exit(0 if ok else 1)

    if args.gmail_action == "test":
        from sellbird.config import load_config
        from sellbird.integrations.gmail import GmailProvider

        async def _test():
            provider = GmailProvider(load_config(), env)
            ok, detail = await provider.test_connection()
            print(f"\n  {'✓' if ok else '✗'} {detail}\n")
            sys.exit(0 if ok else 1)
        asyncio.run(_test())


def cmd_microsoft(args):
    """Microsoft 365 provider utilities (auth / test)."""
    from sellbird.config import load_env

    env = load_env()
    if args.microsoft_action == "auth":
        from sellbird.integrations.microsoft import run_auth_flow
        ok = run_auth_flow(env.m365_client_id, env.m365_tenant_id)
        sys.exit(0 if ok else 1)

    if args.microsoft_action == "test":
        from sellbird.config import load_config
        from sellbird.integrations.microsoft import MicrosoftProvider

        async def _test():
            provider = MicrosoftProvider(load_config(), env)
            ok, detail = await provider.test_connection()
            print(f"\n  {'✓' if ok else '✗'} {detail}\n")
            sys.exit(0 if ok else 1)
        asyncio.run(_test())


def cmd_outbox(args):
    """Review and approve queued outgoing emails."""
    from sellbird.state import StateManager

    async def _outbox():
        state = StateManager()
        await state.init_db()

        if args.approve_all:
            n = await state.approve_outbox()
            print(f"\n  Aprovado(s) {n} e-mail(s). Vão sair no horário programado.")
            held = await state.count_held_for_review()
            if held:
                print(f"  {held} e-mail(s) que o Sellbird segurou ficaram de fora: leia cada um")
                print("  e aprove com --approve <id>.")
            print()
            return
        if args.approve:
            n = await state.approve_outbox(args.approve)
            print(f"\n  {'Approved.' if n else 'Nenhum item pendente com esse id.'}\n")
            return
        if args.reject:
            n = await state.reject_outbox_item(args.reject)
            print(f"\n  {'Rejected.' if n else 'Nada esperando envio com esse id (já está saindo ou já saiu?).'}\n")
            return

        paused = await state.get_setting("sending_paused")
        if paused:
            print(f"\n  ⚠ ENVIO PAUSADO: {paused}")
            print("  Retome com: sellbird sending resume")

        pending = await state.get_outbox(status="pending_review", limit=50)
        approved = await state.get_outbox(status="approved", limit=10)
        print(f"\n  Caixa de saída: {len(pending)} esperando aprovação, "
              f"{len(approved)}+ aprovados/agendados")
        print("  " + "=" * 60)
        for item in pending:
            print(f"\n  [{item['id']}] etapa {item['step']} ({item['kind']}) "
                  f"→ {item['to_email']}  (envio {item['send_at'][:16]})")
            print(f"  Assunto: {item['subject']}")
            body_preview = (item["body"][:200] + "...") if len(item["body"]) > 200 else item["body"]
            for line in body_preview.splitlines():
                print(f"    {line}")
        if pending:
            print("\n  Aprovar: sellbird outbox --approve <id>   |   todos: sellbird outbox --approve-all")
            print("  Rejeitar: sellbird outbox --reject <id>\n")
        else:
            print("  Nada esperando revisão.\n")

    asyncio.run(_outbox())


def cmd_profile(args):
    """Read what companies' own websites say about them. Free, no Claude calls."""
    from sellbird.state import StateManager
    from sellbird.pipeline import run_profile_stage

    async def _profile():
        state = StateManager()
        await state.init_db()

        pending = await state.count_companies_needing_profile(args.stale_days)
        if not pending:
            print("\n  Nada para analisar. Toda empresa com site já "
                  "foi lida recentemente.\n")
            return

        print(f"\n  {pending} empresas precisam ser analisadas. Lendo até "
              f"{args.limit}...\n")
        try:
            from sellbird.config import load_config
            config = load_config()
        except Exception:
            config = None   # still profiles; no role is singled out as hiring intent
        companies, observations, _ = await run_profile_stage(
            state, limit=args.limit, stale_days=args.stale_days, config=config)
        print(f"  Lidos {companies} sites → {observations} observações (grátis)")
        print("\n  Veja o que apareceu: sellbird dashboard → Sinais\n")

    asyncio.run(_profile())


def cmd_discover(args):
    """Find businesses. The only stage that spends money, so it estimates first."""
    from sellbird.state import StateManager
    from sellbird.config import load_config, load_env
    from sellbird.collectors.discover import (
        PROVIDERS, build_queries, preset_problem, provider_menu, run_discovery,
    )

    async def _discover():
        if args.providers:
            print("\n  Fontes de busca")
            print("  " + "=" * 68)
            for m in provider_menu(load_env().model_dump()):
                mark = "ready" if m["configured"] else "precisa configurar"
                print(f"\n  {m['label']}  [{m['key']}]  ({mark})")
                print(f"    {m['blurb']}")
                print(f"    Custo: {m['cost_note']}")
                print(f"    Grátis: {m['free_tier']}")
                if m["env_keys"]:
                    print(f"    Precisa: {', '.join(m['env_keys'])} no .env  ·  {m['signup_url']}")
                if m["caveat"]:
                    print(f"    Obs.: {m['caveat']}")
            print("\n  Rode uma com: sellbird discover --provider <chave> --estimate\n")
            return

        if args.provider not in PROVIDERS:
            print(f"\n  Fonte desconhecida {args.provider!r}. "
                  f"Veja: sellbird discover --providers\n")
            return

        # Fail before collection; estimates need no credentials.
        # An unconfigured provider used to end in one quiet "stopped
        # early" line and exit code 0: a silent no-op that reads as
        # success.
        provider = PROVIDERS[args.provider]
        missing = provider.missing_keys(load_env().model_dump())
        if missing and not args.estimate:
            names = ", ".join(k.upper() for k in missing)
            print("\n  " + "!" * 68)
            print(f"  ERRO: fonte pulada: falta a chave - "
                  f"{provider.label} não está configurada, nenhuma busca pode rodar.")
            print(f"  Faltando ou vazio: {names}")
            print("  Coloque um valor real no .env (os valores de exemplo não"
                  " contam) e tente de novo.")
            print("  Todas as fontes e suas chaves: sellbird discover --providers")
            print("  " + "!" * 68 + "\n")
            raise SystemExit(1)

        config = load_config()
        state = StateManager()
        await state.init_db()

        # Semicolons, not commas: "Denver, CO" is one city, not two.
        cities = [c.strip() for c in args.city.split(";") if c.strip()] or None
        preset = getattr(args, "preset", "") or ""
        problem = preset_problem(preset, args.provider, config=config)
        if problem:
            print(f"\n  {problem}\n")
            sys.exit(2)
        queries = build_queries(config, cities=cities,
                                depth=args.depth, limit=args.limit, preset=preset)

        report = await run_discovery(state, config, args.provider, queries,
                                     max_spend=args.max_spend, dry_run=True)
        print(f"\n  {len(queries)} buscas via {PROVIDERS[args.provider].label}")
        for q in queries[:8]:
            print(f"    - {q.keyword()}" + ("" if q.coordinate else
                  "   (sem coordenadas; adicione icp.geo_coordinates para busca por raio)"))
        if len(queries) > 8:
            print(f"    ... e mais {len(queries) - 8}")
        print(f"\n  Custo estimado: US$ {report.estimated_cost:.4f}"
              f"   (limite: US$ {args.max_spend:.2f})")

        if args.estimate:
            print("\n  Só estimativa. Rode de novo sem --estimate para coletar.\n")
            return

        print("\n  Rodando...\n")
        from sellbird.pipeline import run_prospecting

        result = await run_prospecting(
            state, config, args.provider, queries,
            max_spend=args.max_spend, profile=not args.no_profile,
        )
        r = result.discover or {}
        ran = r.get("queries_ran", 0)
        print(f"  DESCOBERTA: {r.get('found', 0)} resultados em "
              f"{ran} de {r.get('queries', 0)} buscas")
        print(f"    {r.get('new_companies', 0)} empresas novas, "
              f"{r.get('known_companies', 0)} já conhecidas")
        print(f"    {r.get('junk', 0)} descartadas como diretórios/agregadores")
        # Only when it happened: a "0 skipped" line every run teaches people to
        # stop reading the block, and this is the line worth noticing.
        if r.get("excluded"):
            print(f"    {r['excluded']} puladas: estão na sua lista de não contatar")
        print(f"    {r.get('observations', 0)} observações registradas")
        print(f"    custo real: US$ {r.get('actual_cost', 0):.4f}")
        if r.get("stopped"):
            print(f"    parou antes: {r['stopped']}")

        if args.no_profile:
            print("\n  ANÁLISE: pulada (--no-profile)")
        else:
            print(f"\n  ANÁLISE: {result.profiled_companies} sites lidos, "
                  f"{result.profile_observations} observações  (grátis)")

        for err in result.errors[:5]:
            print(f"    ! {err}")

        # Empty successful searches are valid; no successful requests is not.
        # Partial success remains usable and exits zero.
        if r.get("queries_succeeded", 0) == 0:
            print("\n  " + "=" * 68)
            print(f"  A BUSCA NÃO CONCLUIU NENHUMA CONSULTA ({r.get('stopped') or 'nenhuma consulta deu certo'})"
                  "; saindo com erro")
            for err in (r.get("errors") or [])[:3]:
                print(f"    - {err}")
            print("  " + "=" * 68 + "\n")
            raise SystemExit(1)

        print("\n  Próximo: sellbird dashboard → Sinais → montador de grupos\n")

    asyncio.run(_discover())


def cmd_signals(args):
    """Review the signal vocabulary — Sellbird proposes, you confirm.

    Nothing is collected until a signal is confirmed, so a fresh install
    prospects against nothing until someone makes these decisions.
    """
    from sellbird.state import StateManager
    from sellbird.signals import is_free_cost, seed_signal_catalog

    async def _signals():
        state = StateManager()
        await state.init_db()
        await seed_signal_catalog(state)

        codes = [a.strip().upper() for a in (args.confirm or args.reject or "").split(",")
                 if a.strip()]
        if codes:
            status = "confirmed" if args.confirm else "rejected"
            if codes == ["ALL"]:
                codes = [c["code"] for c in await state.get_signal_codes()]
            elif codes == ["FREE"]:
                # Only signals whose cost note STARTS with free/included. A
                # substring match would sweep in "1 credit (free tiers
                # available)", which is not free.
                codes = [c["code"] for c in await state.get_signal_codes()
                         if is_free_cost(c["cost_note"])]
            changed = sum(
                [1 for c in codes if await state.set_signal_status(c, status)]
            )
            print(f"\n  {changed} sinal(is) {status}.\n")
            return

        rows = await state.get_signal_codes()
        counts = {c["signal_code"]: c for c in await state.signal_counts()}
        by_status = {"confirmed": 0, "proposed": 0, "rejected": 0}
        for r in rows:
            by_status[r["status"]] = by_status.get(r["status"], 0) + 1

        print(f"\n  Sinais: {by_status['confirmed']} confirmados, "
              f"{by_status['proposed']} esperando você, {by_status['rejected']} desligados")
        print("  " + "=" * 66)
        mark = {"confirmed": "[ligado] ", "proposed": "[ ? ]", "rejected": "[off]"}
        current = None
        for r in rows:
            if r["category"] != current:
                current = r["category"]
                print(f"\n  {current.upper()}")
            seen = counts.get(r["code"], {}).get("companies", 0)
            seen_txt = f"  ({seen} empresas)" if seen else ""
            print(f"    {mark.get(r['status'], '     ')} {r['code']:<22} "
                  f"{r['label']}{seen_txt}")
            print(f"          {r['cost_note']}")

        if by_status["proposed"]:
            print("\n  Confirme com: sellbird signals --confirm CÓDIGO[,CÓDIGO...]")
            print("  Tudo o que é grátis: sellbird signals --confirm free")
            print("  Detalhes e descrições: sellbird dashboard → Sinais\n")
        else:
            print("")

    asyncio.run(_signals())


def cmd_retry_writes(args):
    """Put prospects the Writer gave up on back in line for another try."""
    from sellbird.agents.writer import MAX_WRITE_ATTEMPTS
    from sellbird.state import StateManager

    async def _run():
        state = StateManager()
        await state.init_db()
        if getattr(args, "no_tip", False):
            count = await state.retry_no_tip()
            if count:
                print(f"\n  {count} prospect(s) voltaram para a fila. Com writer.require_tip "
                      "ligado, quem ainda não tiver algo concreto é pulado de novo.\n")
            else:
                print("\n  Nenhum prospect foi pulado por falta de algo para escrever.\n")
            return
        count = await state.retry_write_failed()
        if count:
            print(f"\n  {count} prospect(s) voltaram para a fila. O Writer vai tentar cada um "
                  f"até {MAX_WRITE_ATTEMPTS} vezes mais.\n")
        else:
            print("\n  Nenhum prospect esperando nova tentativa.\n")

    asyncio.run(_run())


def cmd_warmup(args):
    """Check whether the sending domain is ready for cold email."""
    import os

    from dotenv import load_dotenv

    from sellbird import deliverability as d
    from sellbird.agents.handler import BOUNCE_COUNT_KEY
    from sellbird.config import ConfigError, load_config
    from sellbird.paths import PROJECT_ROOT
    from sellbird.state import StateManager

    load_dotenv(PROJECT_ROOT / ".env")
    try:
        config = load_config()
    except ConfigError as e:
        print(f"\n  {e}\n")
        raise SystemExit(1)
    email = config.channels.email
    smtp_user = os.getenv("SMTP_USERNAME", "").strip() if email.provider == "smtp" else ""
    sender = smtp_user if "@" in smtp_user else config.persona.email
    domain = (args.domain or sender.rpartition("@")[2]).strip().lower().rstrip(".")
    if not d.DOMAIN_RE.match(domain):
        print("\n  Nenhum domínio de envio válido encontrado. Informe um: sellbird warmup seudominio.com.br\n")
        raise SystemExit(1)

    async def _history():
        state = StateManager()
        await state.init_db()
        return (await state.count_outbox_sent(),
                int(await state.get_setting(BOUNCE_COUNT_KEY) or 0))

    smtp_host = os.getenv("SMTP_HOST", "").strip() if email.provider == "smtp" else ""
    print(f"\n  Verificação de entregabilidade - {domain}")
    print("  " + "=" * 56)
    sections = [
        ("Authentication", [d.check_mx(domain), d.check_spf(domain),
                            d.check_dkim(domain, email.warmup.dkim_selector),
                            d.check_dmarc(domain)]),
        ("Reputation", [d.check_domain_age(domain), *d.check_domain_blocklists(domain)]
         + (d.check_ip_blocklists(smtp_host) if smtp_host else [])),
        ("Aquecimento e envio", [d.check_warmup(email.warmup, email.max_daily_sends,
                                             provider=email.provider),
                              _warmup_service_check(sender, email.warmup),
                              d.check_send_history(*asyncio.run(_history()))]),
    ]
    icons = {d.OK: "OK  ", d.WARN: "WARN", d.FAIL: "FAIL", d.INFO: "info"}
    failed = warned = unknown = 0
    for title, checks in sections:
        print(f"\n  {title}")
        for c in checks:
            failed += c.status == d.FAIL
            warned += c.status == d.WARN
            unknown += c.unknown and title == "Authentication"
            print(f"    [{icons[c.status]}] {c.name:<26} {c.detail}")

    print("\n  " + "=" * 56)
    if failed:
        print(f"  NÃO ESTÁ PRONTO - corrija os {failed} item(ns) com FALHA antes de qualquer e-mail frio.")
    elif unknown:
        print(f"  NÃO CONFERIDO - {unknown} consulta(s) de autenticação falharam; rode de novo.")
    elif warned:
        print(f"  PRONTO COM RESSALVAS - {warned} aviso(s); mantenha o volume baixo.")
    else:
        print("  PRONTO - envie dentro do limite de hoje e fique de olho nos bounces.")
    print("\n  O que o DNS não diz (o sinal real de reputação):")
    print("    - Google Postmaster Tools: https://postmaster.google.com - adicione o domínio;")
    print("      ele mostra a taxa de spam no Gmail e a reputação do domínio quando você tiver volume.")
    print("    - Caixa de entrada: mande um e-mail para um teste (o mail-tester.com é grátis)")
    print("      e mire em 9/10 ou mais. O TrulyInbox mostra a taxa de caixa de entrada do aquecimento, e conectado")
    print("      (sellbird trulyinbox connect) o Sellbird coloca isso neste relatório.")
    print("      Espere ~95%+ de caixa de entrada por uma semana antes de depender de envios frios.\n")
    if failed or unknown:
        raise SystemExit(1)


def _warmup_service_check(address: str, warmup):
    """The 'Warmup service' line: TrulyInbox's view of the mailbox, or the recommendation."""
    from sellbird import deliverability as d
    from sellbird.integrations import trulyinbox as ti
    from sellbird.state import StateManager

    async def _run():
        state = StateManager()
        await state.init_db()
        health, error = await ti.current_health(address)
        other = health is None and not error and await ti.get_choice(state) == "other"
        return d.check_warmup_service(health, warmup, error=error, other_service=other)
    return asyncio.run(_run())


def cmd_trulyinbox(args):
    """Connect TrulyInbox, record another warmup service, or show the status."""
    import getpass

    from dotenv import load_dotenv

    from sellbird import deliverability as d
    from sellbird.config import ConfigError, load_config
    from sellbird.integrations import trulyinbox as ti
    from sellbird.paths import PROJECT_ROOT
    from sellbird.state import StateManager

    load_dotenv(PROJECT_ROOT / ".env")
    try:
        config = load_config()
    except ConfigError as e:
        print(f"\n  {e}\n")
        raise SystemExit(1)
    address = ti.sending_address(config)
    warmup = config.channels.email.warmup

    async def _run():
        state = StateManager()
        await state.init_db()
        if args.trulyinbox_action == "other":
            await ti.set_choice(state, "other")
            print("\n  Anotado: você usa outro serviço de aquecimento. O Sellbird não vai mais perguntar do "
                  "TrulyInbox.\n")
            return 0
        if args.trulyinbox_action == "connect":
            print(f"\n  Conecte o TrulyInbox. Ainda não tem? {ti.AFFILIATE_URL} {ti.AFFILIATE_TAG}")
            print("  Você precisa do plano Starter ou superior. No TrulyInbox, abra Settings > API keys e")
            print("  crie uma chave de workspace com accounts:read, warmup:read, analytics:read")
            print("  e workspace:read.\n")
            if not address:
                print(f"\n  {ti.NO_ADDRESS}\n")
                return 1
            key = getpass.getpass("  Chave de API do TrulyInbox (oculta): ").strip()
            if not key:
                print("\n  Nenhuma chave digitada.\n")
                return 1
            workspace = ti.key_from_env()[1]
            ti.forget_rejected(key)
            try:
                client = ti.TrulyInbox(key, workspace)
                health = await client.mailbox_health(address)
            except ti.TrulyInboxError as e:
                print(f"\n  {e}\n")
                return 1
            from sellbird.dashboard import _write_env_file
            updates = {"TRULYINBOX_API_KEY": key}
            if not workspace:
                updates["TRULYINBOX_WORKSPACE_ID"] = client.workspace_id
            try:
                _write_env_file(updates)
            except OSError as e:
                print(f"\n  A chave funciona, mas o Sellbird não conseguiu salvar no .env: {e}\n")
                return 1
            await ti.set_choice(state, "connected")
            print("\n  Conectado. " + d.check_warmup_service(health, warmup).detail + "\n")
            return 0
        choice = await ti.get_choice(state)
        health, error = await ti.current_health(address)
        print(f"\n  TrulyInbox: {ti.describe_status(health, error, choice)}")
        check = d.check_warmup_service(health, warmup, error=error,
                                       other_service=choice == "other")
        print(f"  {check.detail}\n")
        return 0

    raise SystemExit(asyncio.run(_run()))


def cmd_precleared_key(args):
    """Get a free Precleared key for an email address and save it to .env.

    The same one-step key as `sellbird setup` offers, for after setup: when the
    keyless allowance runs out, or for a coding agent setting Sellbird up
    (`--email` asks nothing). The key is saved, never printed.
    """
    import os

    from dotenv import load_dotenv

    from sellbird.dashboard import _write_env_file
    from sellbird.integrations.precleared import GET_KEY_URL, create_free_key
    from sellbird.paths import PROJECT_ROOT
    from sellbird.setup import _read_env_file

    load_dotenv(PROJECT_ROOT / ".env")
    if (_read_env_file().get("PRECLEARED_API_KEY", "").strip("'\" ")
            or os.getenv("PRECLEARED_API_KEY", "").strip()):
        print("\n  Você já tem uma chave do Precleared (PRECLEARED_API_KEY), então o Sellbird manteve.")
        print("  Para pegar outra, apague essa linha do .env e rode de novo.\n")
        raise SystemExit(0)

    enabled, country = None, ""
    try:
        from sellbird.config import load_config
        settings = load_config().compliance.precleared
        enabled = settings.enabled is True
        country = settings.sender_country if enabled else ""
    except Exception:
        pass  # only used for a hint and the key's country

    email = (args.email or "").strip()
    if not email:
        print("\n  Sellbird can get you a free Precleared key: 100 checks a day for the")
        print("  first 14 days, then 25 a day. Precleared receives your email address")
        print("  to make the key (privacy: https://precleared.dev/privacy).")
        try:
            email = input("\n  → Email address for the key: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raise SystemExit(1)
        if not email:
            print("\n  Nenhum e-mail digitado.\n")
            raise SystemExit(1)

    result = create_free_key(email, country=country)
    if not result.key:
        print(f"\n  Não deu para pegar uma chave: {result.error}.")
        print(f"  Você pode pegar uma em {GET_KEY_URL} e colocar no .env como PRECLEARED_API_KEY.\n")
        raise SystemExit(1)
    try:
        _write_env_file({"PRECLEARED_API_KEY": result.key})
    except OSError as e:
        print(f"\n  Precleared made the key, but Sellbird couldn't save it to .env ({e}).")
        print(f"  Fix that and run this again, or get a key at {GET_KEY_URL}.\n")
        raise SystemExit(1)
    print("\n  Pronto: sua chave grátis do Precleared está salva no .env como PRECLEARED_API_KEY.")
    print("  It gives Sellbird 100 checks a day for 14 days, then 25 a day.")
    if enabled is False:
        print("  The check itself is off: turn it on with `sellbird setup` or set")
        print("  compliance.precleared.enabled: true in your config.")
    print("  If Sellbird is running, restart it so it uses the key.\n")
    raise SystemExit(0)


def cmd_sending(args):
    """Pause/resume the sending kill switch."""
    from sellbird.state import StateManager

    async def _run():
        state = StateManager()
        await state.init_db()
        if args.sending_action == "pause":
            await state.set_setting("sending_paused", "paused manually")
            print("\n  Envio pausado. Nada sai da caixa de saída.\n")
        elif args.sending_action == "resume":
            await state.set_setting("sending_paused", "")
            await state.set_setting("bounce_count", "0")
            print("\n  Envio retomado (contador de bounces zerado).\n")
        else:
            paused = await state.get_setting("sending_paused")
            print(f"\n  Envio: {'PAUSADO: ' + paused if paused else 'active'}\n")

    asyncio.run(_run())


def _carry_over_from_harvey():
    """Move a Harvey-era install's files to their new names and say so once."""
    import sellbird
    from sellbird.legacy import migrate_files
    notes = migrate_files()
    if sellbird.LEGACY_ENV:
        notes.append("Using your HARVEY_* settings as "
                     + ", ".join(sellbird.LEGACY_ENV)
                     + ". Rename them when convenient.")
    for note in notes:
        print(f"Sellbird (formerly Harvey): {note}", file=sys.stderr)


def cmd_suppressions(args):
    """See, add or remove suppressed addresses and domains. Removing is yours alone."""
    from sellbird.state import StateManager

    async def _run():
        state = StateManager()
        await state.init_db()
        if args.suppression_action == "add":
            kind = "domain" if "@" not in args.value else "address"
            try:
                added = await state.add_suppression(kind, args.value, "manual", source="cli")
            except ValueError:
                print(f"\n  Isso não é um e-mail nem um domínio: {args.value}\n")
                return 1
            key = state.suppression_key(kind, args.value)
            print(f"\n  {'Suppressed' if added else 'Já bloqueado'}: {key} ({kind}).\n")
        elif args.suppression_action == "remove":
            if await state.remove_suppression(args.value):
                print("\n  Removido. O Sellbird pode voltar a escrever para eles.\n")
            else:
                print(f"\n  Nenhum bloqueio com o id {args.value}. Rode `sellbird suppressions` para ver os ids.\n")
                return 1
        else:
            rows = await state.list_suppressions(limit=1000)
            if not rows:
                print("\n  Ninguém está bloqueado.\n")
            for r in rows:
                print(f"  {r['id']}  {r['kind']:<7} {r['value']:<40} {r['reason']:<10} {r['created_at']}")
        return 0

    code = asyncio.run(_run())
    if code:
        sys.exit(code)


def main():
    from sellbird.textio import utf8_stdio
    utf8_stdio()
    from sellbird.paths import PROJECT_ROOT
    project_root = str(PROJECT_ROOT)

    parser = argparse.ArgumentParser(
        prog="sellbird",
        description="Sellbird: a plataforma de prospecção de código aberto. Dê o primeiro passo.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # sellbird install
    sub = subparsers.add_parser("install", help="Instala as dependências")
    sub.set_defaults(func=cmd_install)

    # sellbird setup
    sub = subparsers.add_parser("setup", help="Roda o assistente de configuração")
    sub.set_defaults(func=cmd_setup)

    # sellbird run
    sub = subparsers.add_parser("run", help="Liga o ciclo do Sellbird")
    sub.set_defaults(func=cmd_run)

    # sellbird train <url>
    sub = subparsers.add_parser("train", help="Treina o Sellbird a partir de um site")
    sub.add_argument("url", help="URL do site para ler e aprender")
    sub.add_argument(
        "max_pages",
        nargs="?",
        type=int,
        default=100,
        help="Máximo de páginas para ler (padrão: 100)",
    )
    sub.add_argument(
        "--provider", choices=["claude", "codex"], default=None,
        help="Assinatura usada para pensar (padrão: a da sua configuração, senão claude)",
    )
    sub.add_argument("--model", default=None, help="Modelo deste provedor (padrão: o do provedor)")
    sub.add_argument(
        "--reasoning-effort", default=None,
        help="Esforço de raciocínio do Codex (minimal/low/medium/high/xhigh)",
    )
    sub.set_defaults(func=cmd_train)

    # sellbird dashboard
    sub = subparsers.add_parser("dashboard", help="Abre o painel web")
    sub.add_argument("--host", default="127.0.0.1",
                     help="Endereço local para escutar (padrão: 127.0.0.1; "
                          "outros endereços são recusados)")
    sub.add_argument("--port", type=int, default=5555, help="Porta (padrão: 5555)")
    sub.add_argument("--url", action="store_true",
                     help="Mostra o link de desbloqueio (com o token) e sai")
    sub.set_defaults(func=cmd_dashboard)

    # sellbird status
    sub = subparsers.add_parser("status", help="Mostra a situação do funil")
    sub.add_argument(
        "--check", action="store_true",
        help="Também confere o cérebro configurado agora (Codex: versão do CLI, isolamento "
             "e login; Claude: flags de isolamento do CLI; sem chamar o modelo)",
    )
    sub.set_defaults(func=cmd_status)

    # sellbird export
    sub = subparsers.add_parser(
        "export", help="Exporta os prospects num CSV pronto para ferramentas de sequência"
    )
    sub.add_argument("--out", default="prospects.csv", help="Arquivo de saída (padrão: prospects.csv)")
    sub.add_argument(
        "--email-status", default="",
        help="Situações de e-mail separadas por vírgula (padrão: verified,risky)",
    )
    sub.add_argument("--min-score", type=int, default=0, help="Nota mínima de ICP")
    sub.add_argument("--status", default="", help="Situações do funil separadas por vírgula (ex.: new,queued); quem pediu para sair continua fora")
    sub.add_argument("--all", action="store_true", help="Exporta a lista bruta sem filtros, incluindo quem pediu para sair (não use para abordagem)")
    sub.set_defaults(func=cmd_export)

    # sellbird companies
    sub = subparsers.add_parser(
        "companies", help="Exporta o registro de empresas: cada empresa, por que encaixa e por que não foi contatada"
    )
    sub.add_argument("--out", default="", help="Arquivo de saída (padrão: data/exports/company-register-<data>.csv)")
    sub.set_defaults(func=cmd_companies)

    # sellbird gmail auth|test
    sub = subparsers.add_parser("gmail", help="Configuração do Gmail")
    sub.add_argument("gmail_action", choices=["auth", "test"],
                     help="auth: login OAuth (uma vez); test: testa a conexão")
    sub.set_defaults(func=cmd_gmail)

    # sellbird microsoft auth|test
    sub = subparsers.add_parser("microsoft", help="Configuração do Microsoft 365")
    sub.add_argument("microsoft_action", choices=["auth", "test"],
                     help="auth: login (uma vez); test: testa a conexão")
    sub.set_defaults(func=cmd_microsoft)

    # sellbird outbox
    sub = subparsers.add_parser("outbox", help="Revisa/aprova os e-mails na fila")
    sub.add_argument("--approve", metavar="ID", default="", help="Aprova um item")
    sub.add_argument("--approve-all", action="store_true", help="Aprova todos os pendentes")
    sub.add_argument("--reject", metavar="ID", default="", help="Rejeita um item")
    sub.set_defaults(func=cmd_outbox)

    # sellbird sending pause|resume|status
    sub = subparsers.add_parser("discover", help="Encontra empresas que encaixam no seu ICP")
    sub.add_argument("--provider", default="osm",
                     help="Fonte de busca (padrão: osm, grátis e sem conta)")
    sub.add_argument("--providers", action="store_true",
                     help="Lista todas as fontes com custo e configuração, e sai")
    sub.add_argument("--estimate", action="store_true",
                     help="Mostra o gasto previsto e sai sem chamar nada")
    sub.add_argument("--city", default="",
                     help='Cidades separadas por ponto e vírgula, ex.: "Curitiba, PR;Londrina, PR" '
                          '(padrão: icp.geography)')
    sub.add_argument("--depth", type=int, default=30,
                     help="Profundidade da busca (padrão: 30; profundidade 100 custa 10x desde set/2025)")
    sub.add_argument("--limit", type=int, default=100,
                     help="Máximo de resultados por busca (padrão: 100)")
    sub.add_argument("--max-spend", type=float, default=1.0,
                     help="Limite de gasto em dólares (padrão: 1.00)")
    sub.add_argument("--preset", default="", choices=["", "yc", "hiring", "accelerator", "funding"],
                     help="A built-in search instead of your ICP's industries "
                          "(each needs a search provider like tinyfish, serper or dataforseo_serp). "
                          "yc: startups whose own site says they're YC-backed; "
                          "hiring: companies whose own careers pages list one of "
                          "your hiring_signals roles (else ICP titles); "
                          "accelerator: ones backed by Techstars, Antler, EF, SPC, 500 Global, "
                          "Neo, AI Grant, a16z speedrun or Plug and Play; "
                          "funding: companies announcing a raise on their own site in the last 18 months")
    sub.add_argument("--no-profile", action="store_true",
                     help="Não analisa o que foi encontrado (a análise é grátis)")
    sub.set_defaults(func=cmd_discover)

    sub = subparsers.add_parser(
        "profile", help="Lê os sites das empresas encontradas (grátis, sem Claude)")
    sub.add_argument("--limit", type=int, default=200,
                     help="Máximo de sites para ler (padrão: 200)")
    sub.add_argument("--stale-days", type=int, default=90,
                     help="Relê um site depois de tantos dias (padrão: 90)")
    sub.set_defaults(func=cmd_profile)

    sub = subparsers.add_parser(
        "signals", help="Revisa/confirma quais sinais o Sellbird usa para prospectar")
    sub.add_argument("--confirm", metavar="CODES", default="",
                     help="Códigos para confirmar, separados por vírgula ('all' ou 'free' também valem)")
    sub.add_argument("--reject", metavar="CODES", default="",
                     help="Códigos para desligar, separados por vírgula")
    sub.set_defaults(func=cmd_signals)

    sub = subparsers.add_parser(
        "retry-writes", help="Tenta de novo os prospects para quem o Writer não conseguiu escrever")
    sub.add_argument("--no-tip", action="store_true",
                     help="Tenta de novo os prospects que o writer.require_tip pulou (situação no_tip)")
    sub.set_defaults(func=cmd_retry_writes)

    sub = subparsers.add_parser("sending", help="Botão de emergência: pausa/retoma o envio")
    sub.add_argument("sending_action", nargs="?", default="status",
                     choices=["pause", "resume", "status"])
    sub.set_defaults(func=cmd_sending)

    sub = subparsers.add_parser(
        "warmup", help="Confere se o seu domínio de envio está configurado e aquecido para e-mail frio")
    sub.add_argument("domain", nargs="?", default="",
                     help="Domínio para conferir (padrão: o domínio da sua caixa de envio)")
    sub.set_defaults(func=cmd_warmup)

    sub = subparsers.add_parser(
        "trulyinbox", help="Serviço de aquecimento: conecte o TrulyInbox para o Sellbird ler a taxa de caixa de entrada")
    sub.add_argument("trulyinbox_action", nargs="?", default="status",
                     choices=["status", "connect", "other"],
                     help="connect a key, 'other' if you use another warmup service, "
                          "or show the status (default)")
    sub.set_defaults(func=cmd_trulyinbox)

    sub = subparsers.add_parser(
        "precleared-key",
        help="Pega uma chave grátis do Precleared para a checagem de e-mail frio e salva no .env")
    sub.add_argument("--email", default="",
                     help="E-mail para a chave (pergunta se não for informado)")
    sub.set_defaults(func=cmd_precleared_key)

    # sellbird usage
    sub = subparsers.add_parser("usage", help="Mostra o uso e a cota do cérebro (Claude ou Codex)")
    sub.add_argument("--days", type=int, default=30, help="Janela do detalhamento (padrão: 30)")
    sub.set_defaults(func=cmd_usage)

    sub = subparsers.add_parser(
        "mcp", help="Servidor MCP para o seu agente de código (iniciado por ele, via stdio)")
    sub.add_argument("mcp_action", nargs="?", choices=["install", "uninstall"],
                     help="Adiciona ou remove o servidor na configuração do seu agente de código")
    sub.add_argument("client", nargs="?", choices=["claude", "codex"],
                     help="Qual agente (padrão: só o Claude Code)")
    sub.add_argument("--print", dest="print_config", action="store_true",
                     help="Mostra a configuração para adicionar à mão; não muda nada")
    sub.add_argument("--yes", action="store_true", help="Aplica sem perguntar")
    sub.set_defaults(func=cmd_mcp)

    from sellbird.inbox_cli import register as register_inboxes
    register_inboxes(subparsers)

    from sellbird import desktop_cli
    desktop_cli.register_desktop_commands(subparsers)
    desktop_cli.register(subparsers)

    sub = subparsers.add_parser("suppressions", help="Endereços e domínios para os quais o Sellbird nunca envia")
    sub.add_argument("suppression_action", nargs="?", default="list", choices=["list", "add", "remove"])
    sub.add_argument("value", nargs="?", default="", help="add: um endereço ou domínio; remove: o id dele")
    sub.set_defaults(func=cmd_suppressions)

    # Commands that installed extensions add (sellbird.extensions). A name the
    # built-in CLI already uses is refused, so an extension never hides one.
    from sellbird import extensions
    for name, (help_text, configure) in extensions.registry().cli_commands.items():
        if name in subparsers.choices:
            raise extensions.ExtensionError(
                f"an extension's command {name!r} clashes with a built-in command")
        sub = subparsers.add_parser(name, help=help_text)
        sub.set_defaults(func=configure(sub))

    args = parser.parse_args()
    _carry_over_from_harvey()
    args._project_root = project_root

    # Fill the home folder before any command. Silent: a command's stdout may
    # be a protocol or a file. A failure is one stderr line, and the command
    # still runs where it can.
    from sellbird import home
    from sellbird.paths import PROJECT_ROOT as home_root
    try:
        home.seed_home(home_root, home.bundled_defaults())
    except Exception as e:
        reason = (e.strerror if isinstance(e, OSError) else None) or type(e).__name__
        print(f"  Não deu para preparar a pasta do Sellbird {home_root}: {reason}", file=sys.stderr)

    if args.command is None:
        parser.print_help()
        print("\n  Começo rápido:")
        print("    sellbird install   — Instala as dependências")
        print("    sellbird setup     — Configura o Sellbird (primeira vez)")
        print("    sellbird run       — Começa a prospectar")
        print("    sellbird dashboard — Abre o painel web")
        print()
        sys.exit(0)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n  Interrompido. Até mais.")
        sys.exit(130)
    except Exception as e:
        # ConfigError and friends carry actionable messages — show them
        # cleanly instead of a raw traceback.
        from sellbird.config import ConfigError

        if isinstance(e, ConfigError):
            print(f"\n  Problema na configuração:\n  {e}\n")
        else:
            print(f"\n  Erro ao rodar 'sellbird {args.command}': {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
