"""Idioma de cada e-mail: português (Brasil/Portugal) ou inglês.

Adicionado na versão em português do Sellbird. A regra é simples:

- Empresa no Brasil  -> e-mail em português do Brasil ("pt-BR").
- Empresa em Portugal, Angola, Moçambique etc. -> português europeu ("pt-PT").
- Empresa em qualquer outro país -> inglês ("en").
- Não deu para saber o país -> o idioma padrão do sellbird.yaml
  (``language.default``; a versão PT-BR vem com "pt-BR").

Como o país é descoberto, do sinal mais forte para o mais fraco:
1. a localização da empresa (o mesmo cálculo que o envio usa para o fuso
   horário: "Curitiba, PR, Brasil", um estado brasileiro, coordenadas);
2. o fuso horário já guardado no prospect ("America/Sao_Paulo");
3. o final do domínio do e-mail ou do site (".br", ".pt");
4. o país das buscas configuradas (icp.geography) ou
   compliance.precleared.prospect_country.

Também há ``looks_portuguese``: um detector simples (sem chamar modelo) que
diz se um texto está em português. Ele é usado onde só temos o texto do
e-mail em mãos, como nos limites de palavras e na escolha do rodapé.
"""

import re
import unicodedata

# Códigos de idioma que o Sellbird entende.
PT_BR = "pt-BR"
PT_PT = "pt-PT"
EN = "en"
LANGUAGES = (PT_BR, PT_PT, EN)

# País (código ISO de duas letras) -> idioma do e-mail.
# Só o Brasil usa pt-BR; os demais países lusófonos usam o português europeu.
_PORTUGUESE_COUNTRIES = {
    "BR": PT_BR,
    "PT": PT_PT, "AO": PT_PT, "MZ": PT_PT, "CV": PT_PT,
    "GW": PT_PT, "ST": PT_PT, "TL": PT_PT,
}

# Final do domínio -> país. Só os que importam para escolher português.
_TLD_COUNTRY = {"br": "BR", "pt": "PT", "ao": "AO", "mz": "MZ", "cv": "CV"}

# Os 26 estados + DF, por sigla e por nome (sem acento, minúsculo). Uma
# localização como "Londrina, PR" ou "Belo Horizonte - Minas Gerais" é do
# Brasil mesmo sem a palavra "Brasil". Algumas siglas também são estados
# dos EUA ou províncias (PA = Pensilvânia, MA = Massachusetts...), então
# só contam quando a localização não nomeia outro país.
BR_STATE_CODES = frozenset("""AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN
RS RO RR SC SP SE TO""".split())
# Nomes dos estados sem acento (inclusive os compostos, como "mato grosso do sul").
BR_STATE_NAMES = frozenset({
    "acre", "alagoas", "amapa", "amazonas", "bahia", "ceara", "distrito federal",
    "espirito santo", "goias", "maranhao", "mato grosso", "mato grosso do sul",
    "minas gerais", "para", "paraiba", "parana", "pernambuco", "piaui",
    "rio de janeiro", "rio grande do norte", "rio grande do sul", "rondonia",
    "roraima", "santa catarina", "sao paulo", "sergipe", "tocantins",
})
# Siglas que também são estados americanos/canadenses/australianos: só
# valem como Brasil quando nada mais na localização aponta outro país.
_AMBIGUOUS_STATE_CODES = frozenset({"AL", "MA", "PA", "SC", "ES", "MT", "SE", "PE", "CE",
                                    "RS", "AC", "TO", "MS", "GO", "DF", "MG", "RO", "RR"})


def _fold(text: str) -> str:
    """Minúsculo e sem acentos: "São Paulo" -> "sao paulo"."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def normalize_language(value, fallback: str = EN) -> str:
    """Aceita o jeito que a pessoa escrever ("pt", "PT_BR", "português",
    "english") e devolve um dos códigos de LANGUAGES."""
    raw = _fold(value).strip().replace("_", "-")
    if not raw:
        return fallback
    if raw in ("pt-br", "pt", "br", "portugues", "portugues do brasil", "brasileiro", "portuguese"):
        return PT_BR
    if raw in ("pt-pt", "portugues europeu", "portugues de portugal"):
        return PT_PT
    if raw in ("en", "en-us", "en-gb", "ingles", "english"):
        return EN
    return fallback


def language_for_country(country: str, default: str = EN) -> str:
    """O idioma de um país; ``default`` quando o país não é conhecido."""
    code = str(country or "").strip().upper()
    if not code:
        return default
    return _PORTUGUESE_COUNTRIES.get(code, EN)


def is_portuguese(language: str) -> bool:
    return str(language or "").startswith("pt")


def brazil_in_location(location: str, lean_brazil: bool = False) -> bool:
    """A localização é claramente no Brasil? ("Curitiba, PR", "Recife -
    Pernambuco", "Brasil", "Brazil").

    lean_brazil: True quando a operação é voltada ao Brasil (idioma padrão
    pt-BR ou buscas no Brasil). Aí uma sigla ambígua como "SC" conta como
    Santa Catarina, não Carolina do Sul."""
    folded = _fold(location)
    if not folded.strip():
        return False
    if re.search(r"\b(?:brasil|brazil)\b", folded):
        return True
    # Nome de estado escrito por extenso.
    parts = [p.strip() for p in re.split(r"[,\-/|]", folded) if p.strip()]
    if any(p in BR_STATE_NAMES for p in parts[1:]):
        return True
    # Sigla de estado ("Londrina, PR"). As ambíguas só valem quando a
    # operação é voltada ao Brasil; senão o send_window decide o país.
    raw_parts = [p.strip() for p in re.split(r"[,\-/|]", str(location or "")) if p.strip()]
    for p in raw_parts[1:]:
        code = p.upper()
        if code in BR_STATE_CODES and (lean_brazil or code not in _AMBIGUOUS_STATE_CODES):
            return True
    return False


def country_from_domain(value: str) -> str:
    """País pelo final do domínio de um e-mail ou site ("ana@clinica.com.br"
    -> "BR"), ou "" quando o final não diz nada (.com, .net...)."""
    host = str(value or "").strip().lower().rsplit("@", 1)[-1]
    host = re.sub(r"^[a-z]+://", "", host).split("/", 1)[0].strip(".")
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    return _TLD_COUNTRY.get(tld, "")


def default_language(config) -> str:
    """O idioma padrão configurado (``language.default``); "en" se não houver."""
    section = getattr(config, "language", None)
    return normalize_language(getattr(section, "default", ""), EN)


def _by_country(config) -> bool:
    """Se o idioma deve seguir o país do prospect (padrão: sim)."""
    section = getattr(config, "language", None)
    return bool(getattr(section, "by_country", True))


async def prospect_language(state, prospect, config) -> str:
    """O idioma em que o Sellbird deve escrever para este prospect.

    Nunca chama API nem modelo: usa só o que já está no banco local.
    Qualquer falha numa etapa apenas passa para a próxima.
    """
    fallback = default_language(config)
    if prospect is None or not _by_country(config):
        return fallback

    # Importado aqui para não criar importação circular com send_window.
    from sellbird.send_window import country_for, icp_country, zone_country

    # 1. Localização da empresa.
    location, point = "", ""
    try:
        if getattr(prospect, "company_id", "") and state is not None:
            company = await state.get_company(prospect.company_id)
            location = (getattr(company, "location", "") or "") if company else ""
            website = (getattr(company, "website", "") or getattr(company, "domain", "")
                       or "") if company else ""
            if location.strip():
                cached = await state.get_setting("geo:" + location.strip().lower())
                point = "" if not cached or cached == "-" else cached
        else:
            website = ""
    except Exception:
        website = ""
    try:
        icp_code = icp_country(config)
    except Exception:
        icp_code = ""
    lean_brazil = fallback == PT_BR or icp_code == "BR"
    if brazil_in_location(location, lean_brazil):
        return PT_BR
    try:
        country, _certain = country_for(location, point)
    except Exception:
        country = ""
    if country:
        return language_for_country(country, fallback)

    # 2. Fuso horário já descoberto para o prospect.
    zone_code = zone_country(getattr(prospect, "timezone", "") or "")
    if zone_code:
        return language_for_country(zone_code, fallback)

    # 3. Domínio do e-mail ou do site.
    for value in (getattr(prospect, "email", ""), website):
        code = country_from_domain(value)
        if code:
            return language_for_country(code, fallback)

    # 4. País das buscas configuradas.
    code = icp_code
    if not code:
        compliance = getattr(config, "compliance", None)
        precleared = getattr(compliance, "precleared", None)
        code = str(getattr(precleared, "prospect_country", "") or "").upper()
    if code:
        return language_for_country(code, fallback)
    return fallback


# ── Instruções de idioma para o modelo ───────────────────────────────────

_PT_BR_RULE = """
IDIOMA DO E-MAIL: português do Brasil.
- Escreva TODO o e-mail (assunto e corpo) em português do Brasil, natural,
  como um brasileiro ocupado escreveria no celular. Nada de tradução literal
  do inglês, nada de português de Portugal.
- Trate a pessoa por "você". Saudação curta: "Oi Ana," ou "Olá, Ana,". Para a
  caixa geral da empresa: "Olá, equipe da {empresa}," ou "Olá,".
- Evite clichês: "espero que esteja bem", "venho por meio deste", "gostaria
  de me apresentar", "solução inovadora", "alavancar", "agregar valor".
- Assunto em minúsculas, 2 a 5 palavras.
- Em português, os limites de palavras ficam um pouco maiores que os citados
  acima: e-mail 1 até 70 palavras (ideal 35 a 55), e-mail 2 até 60, e-mail 3
  até 35, resposta até 140. Mesmo assim, quanto mais curto, melhor.
- Exemplos do nível esperado (os fatos mudam sempre, nunca copie as palavras):
  > Oi Ana,
  >
  > Pesquisando "dentista família curitiba", a Sorriso Pleno aparece em 11º, na
  > segunda página. A maioria dos pacientes escolhe na primeira e nem rola a tela.
  >
  > Posso te mandar um plano para colocar a clínica entre as três primeiras. Quer?

  > Marcos,
  >
  > Vi que a Hidrotec está contratando alguém para atender ligações e agendar
  > serviços. Até a vaga ser preenchida, um vazamento às 22h cai na caixa
  > postal e vai para o concorrente.
  >
  > Atendemos ligações fora do horário para empresas de hidráulica. Quer testar
  > grátis por duas semanas enquanto contrata?
"""

_PT_PT_RULE = """
IDIOMA DO E-MAIL: português europeu (de Portugal).
- Escreva TODO o e-mail (assunto e corpo) em português europeu natural.
  Trate a pessoa de forma educada e direta. Assunto em minúsculas, 2 a 5 palavras.
"""

_EN_RULE = """
EMAIL LANGUAGE: English.
- Write the whole email (subject and body) in natural English, even though some
  of these instructions are in Portuguese.
"""


def language_rule(language: str) -> str:
    """O bloco de instruções de idioma que vai no fim do prompt do Writer."""
    if language == PT_BR:
        return _PT_BR_RULE
    if language == PT_PT:
        return _PT_PT_RULE
    return _EN_RULE


REPLY_LANGUAGE_RULE = """
IDIOMA DA RESPOSTA: responda no MESMO idioma da última mensagem do prospect.
Se ele escreveu em português, responda em português do Brasil natural (ou
português europeu, se ele escreveu assim); se escreveu em inglês, responda em
inglês. Nunca misture idiomas na mesma resposta."""


def language_name(language: str) -> str:
    """Nome do idioma para mostrar na tela ("português (Brasil)")."""
    return {PT_BR: "português (Brasil)", PT_PT: "português (Portugal)",
            EN: "inglês"}.get(language, language)


# ── Detector simples de português ────────────────────────────────────────

# Palavras muito comuns em português e raras em inglês. Contamos quantas
# aparecem: duas ou mais num texto curto já indicam português.
_PT_WORDS = frozenset("""
voce voces nao sim para com que uma um uns umas dos das nos nas pelo pela pelos
pelas esta este isso isto essa esse seu sua seus suas meu minha nosso nossa
muito mais mas quando como onde porque obrigado obrigada oi ola bom boa dia
tarde noite quer posso pode podemos vamos tem temos ser sao foi vou vai ainda
tambem entao aqui agora hoje amanha semana mes ano empresa equipe clinica
gratis plano vi vejo sobre ate depois antes
""".split())
# Terminações típicas do português ("-ção", "-ções", "-ão").
_PT_ENDINGS = re.compile(r"\w(?:cao|coes|oes|ao)\b")


def looks_portuguese(text: str) -> bool:
    """True quando o texto parece estar em português.

    Não precisa acertar 100%: serve para escolher limites de palavras e o
    rodapé certo. Acentos típicos (ã, õ, ç) já bastam; senão, contamos
    palavras comuns do português."""
    raw = str(text or "")
    if re.search(r"[ãõçÃÕÇ]", raw):
        return True
    words = re.findall(r"[a-z]+", _fold(raw))
    if not words:
        return False
    hits = sum(1 for w in words if w in _PT_WORDS) + len(_PT_ENDINGS.findall(_fold(raw)))
    return hits >= 2 and hits >= len(words) * 0.12
