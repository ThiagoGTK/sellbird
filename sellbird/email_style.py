"""Hard style rules for every email Sellbird writes.

The writer prompt asks for these, and a model still slips. These checks are
code, so a slip never reaches a prospect: the Writer sends a failing draft
back for one rewrite and drops it if the rewrite fails too; the Sender holds
a failing email for review instead of sending it; the dashboard refuses an
edit that breaks them.

Two kinds of rule:

- **Always** (every email Sellbird writes, cold or reply): no em or en
  dashes or a spaced hyphen used as one, no exclamation marks, no
  formatting, none of the phrases that mark an email as AI-written or
  salesy.
- **Cold email shape** (Sellbird's built-in shape only; operator email
  rules replace it): a word cap per step, one question at most, and an
  opening that isn't about the sender.

Curly quotes, ellipsis characters and non-breaking spaces aren't errors a
rewrite should spend a model call on: ``tidy`` straightens them.
"""

import re

from sellbird.language import looks_portuguese

# Word caps for the built-in cold-email shape, by sequence step. Every word
# costs replies, so these are ceilings, not targets: the prompt aims lower.
FIRST_EMAIL_MAX_WORDS = 60
FOLLOW_UP_MAX_WORDS = 50
BREAKUP_MAX_WORDS = 30
REPLY_MAX_WORDS = 120

# Sellbird PT-BR: o português usa mais palavras que o inglês para dizer a
# mesma coisa (artigos, preposições), então os limites são um pouco maiores
# quando o e-mail está em português.
PT_FIRST_EMAIL_MAX_WORDS = 70
PT_FOLLOW_UP_MAX_WORDS = 60
PT_BREAKUP_MAX_WORDS = 35
PT_REPLY_MAX_WORDS = 140


def max_words(step: int, portuguese: bool = False) -> int:
    """The cap for sequence step ``step`` (1-based).

    portuguese: True usa os limites do português (um pouco maiores)."""
    if step <= 1:
        return PT_FIRST_EMAIL_MAX_WORDS if portuguese else FIRST_EMAIL_MAX_WORDS
    if step == 2:
        return PT_FOLLOW_UP_MAX_WORDS if portuguese else FOLLOW_UP_MAX_WORDS
    return PT_BREAKUP_MAX_WORDS if portuguese else BREAKUP_MAX_WORDS


# Dashes: the single most-noticed AI tell. A hyphen inside a word
# ("follow-up", "2-5") is fine; a dash between words is not, whatever
# character makes it.
_DASH_CHARS = "‒–—―−"   # figure, en, em, bar, minus
_SPACED_HYPHEN_RE = re.compile(r"(?<=\S) +-{1,3} +(?=\S)|(?<=\w)--(?=\w)")
_LIST_LINE_RE = re.compile(r"^\s*(?:[-*•●▪]|\d{1,2}[.)])\s+\S", re.MULTILINE)
_MARKDOWN_RE = re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__|^\s*#{1,6}\s", re.MULTILINE)

# Phrases that tell the reader a model or a marketer wrote it. Lowercase,
# matched on word boundaries. Spam-trigger words live in gate.BANNED_PHRASES.
AI_TELLS = (
    # openers and filler
    "hope this finds you", "hope this email finds you", "hope you're doing well",
    "hope you are doing well", "hope you're well", "hope all is well",
    "i know you're busy", "i know you are busy", "reaching out because",
    "i'm reaching out", "i am reaching out", "just wanted to", "wanted to reach out",
    "just following up", "just checking in", "following up on my", "circling back",
    "circle back", "touch base", "i'd love to", "i would love to",
    "in today's", "fast-paced", "picture this", "imagine if", "imagine a world",
    "what if i told you", "here's the thing", "here is the thing", "the truth is",
    "funny enough", "let that sink in",
    # weak asks
    "worth a quick", "quick question", "no pressure", "no obligation", "no strings",
    "would you be open to", "let me know if you're interested",
    "let me know if you are interested", "are you the right person",
    # inflated words
    "game-changer", "game changer", "gamechanger", "revolutionize", "revolutionise",
    "cutting-edge", "cutting edge", "next-level", "next level", "supercharge",
    "unlock", "unleash", "elevate", "empower", "seamless", "seamlessly",
    "leverage", "leveraging", "synergy", "synergies", "delve", "tapestry",
    "testament to", "robust", "crucial", "pivotal", "transformative",
    "transform your", "streamline", "pain point", "pain points",
    "best-in-class", "world-class", "low-hanging fruit", "move the needle",
    "at the end of the day", "a whole new level",
    # staged contrasts
    "it's not about", "it is not about", "isn't about", "this isn't just",
    "it's not just", "it isn't just", "not just a",
    # ── Português (Sellbird PT-BR) ──
    # aberturas e enrolação
    "espero que esteja bem", "espero que estejam bem", "espero que voce esteja bem",
    "espero que você esteja bem", "espero que este e-mail", "espero que este email",
    "espero que tudo esteja bem", "espero encontra-lo bem", "espero encontrá-lo bem",
    "venho por meio deste", "venho por meio desta", "gostaria de me apresentar",
    "me chamo", "meu nome é", "sei que você é ocupado", "sei que você está ocupado",
    "sei que sua agenda", "estou entrando em contato", "entrando em contato para",
    "só passando para", "so passando para", "só queria", "só gostaria de",
    "dando um follow", "fazendo um follow", "retomando o contato", "voltando a falar",
    "imagine só", "imagine se", "e se eu te dissesse", "a verdade é que",
    "nos dias de hoje", "no mundo de hoje", "mundo acelerado",
    # pedidos fracos
    "uma pergunta rápida", "pergunta rápida", "sem compromisso", "sem pressão",
    "você estaria aberto", "você estaria aberta", "estaria disponível para um bate-papo",
    "um bate-papo rápido", "um papo rápido", "você é a pessoa certa",
    "me avise se tiver interesse", "caso tenha interesse",
    # palavras infladas
    "revolucionar", "revolucionário", "revolucionária", "inovador", "inovadora",
    "solução inovadora", "de ponta", "próximo nível", "outro nível",
    "potencializar", "alavancar", "alavanque", "sinergia", "sinergias",
    "agregar valor", "transformar o seu", "transformar seu", "transformar sua",
    "transformador", "transformadora", "disruptivo", "disruptiva",
    "robusto", "robusta", "crucial", "fundamental para o seu", "de classe mundial",
    "dor do cliente", "dores do cliente", "sem complicação", "descomplicar",
    "no fim do dia", "game changer",
    # contrastes encenados
    "não se trata de", "não é só sobre", "não é apenas sobre", "não é apenas um",
    "não é só um",
)
_TELL_RES = tuple(
    (phrase, re.compile(r"(?<![\w-])" + re.escape(phrase).replace("'", "['’]") + r"(?![\w-])"))
    for phrase in AI_TELLS
)
_NOT_ONLY_BUT_RE = re.compile(r"\bnot (?:only|just|merely) [^.?!\n]{1,60}?\bbut\b", re.IGNORECASE)
# "não só X, mas (também) Y" / "não apenas X, mas Y": o mesmo vício em português.
_NOT_ONLY_BUT_PT_RE = re.compile(r"\bn[ãa]o (?:s[óo]|apenas|somente) [^.?!\n]{1,60}?\bmas\b", re.IGNORECASE)

# Saudações também em português: "Oi Ana,", "Olá, equipe,", "Bom dia, Marcos,".
_GREETING_RE = re.compile(r"^(?:hi|hey|hello|dear|good (?:morning|afternoon)"
                          r"|oi|ol[áa]|e a[íi]|prezad[oa]s?|caro|cara|bom dia|boa tarde|boa noite)\b[^\n]{0,40}$"
                          r"|^\w[\w .'-]{0,30},$",
                          re.IGNORECASE)
# Abrir falando de si: "Eu...", "Nós...", "Sou...", "Somos...", "Meu nome...".
_SELF_OPENING_RE = re.compile(r"^(?:i|we|i'm|we're|i've|we've|i'd|we'd|my|our"
                              r"|eu|n[óo]s|sou|somos|meu|minha|nosso|nossa|aqui [ée]|trabalho|trabalhamos)\b",
                              re.IGNORECASE)

_TIDY = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "″": '"',
    " ": " ", " ": " ", " ": " ", " ": " ",
    "​": "", "⁠": "", "﻿": "",
})


def tidy(text: str) -> str:
    """Straight quotes, plain spaces and "..." for what a model types fancy.

    Changes nothing a reader would call a different word, so it never needs
    a model call or a review."""
    text = (text or "").translate(_TIDY).replace("…", "...")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def words(text: str) -> int:
    return len((text or "").split())


def _blank(text: str, names) -> str:
    """``text`` with each known name (company, person) blanked out, so a
    company called "Elevate Fitness" isn't an AI tell."""
    for name in names or ():
        name = (name or "").strip()
        if len(name) >= 3:
            text = re.sub(re.escape(name), " ", text, flags=re.IGNORECASE)
    return text


def _first_line(body: str) -> str:
    """The first line after any greeting ("Hi Sam," / "Sam,")."""
    lines = [line.strip() for line in body.split("\n") if line.strip()]
    for line in lines:
        if _GREETING_RE.match(line):
            continue
        return line
    return ""


def _fold(text: str) -> str:
    """Minúsculas e sem acento, para comparar palavras ("Negócios" = "negocios")."""
    import unicodedata
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def avoided_words(text: str, avoid=()) -> list[str]:
    """As palavras de ``avoid`` (writer.avoid_words) que aparecem em ``text``.

    Compara sem maiúsculas e sem acento, sempre palavra inteira, para que
    "pequeno" pegue "Pequeno" e "pequenó" mas não "pequenez".
    """
    folded = _fold(text or "")
    found = []
    for word in avoid or ():
        w = _fold(str(word).strip())
        if w and re.search(rf"(?<!\w){re.escape(w)}(?!\w)", folded):
            found.append(str(word).strip())
    return found


def style_problems(subject: str, body: str, *, kind: str = "cold", step: int = 1,
                   names=(), shape: bool = True, avoid=()) -> list[str]:
    """Why this email breaks Sellbird's writing rules, or [] when it doesn't.

    kind: "cold" for a sequence email, "reply" for an answer to someone.
    step: the sequence step, for the word cap.
    names: the prospect's name, company and similar: text that is theirs, so
        it is never read as a tell.
    avoid: words the operator never wants in an email (writer.avoid_words).
    shape: False when the operator's own email rules set length and
        structure; the always-rules still apply.

    Each reason says what to change, in words a person editing the draft can
    act on.
    """
    subject = subject or ""
    body = body or ""
    text = _blank(f"{subject}\n{body}", names)
    lowered = tidy(text).lower()
    reasons: list[str] = []

    dashes = sorted({c for c in text if c in _DASH_CHARS})
    if dashes or _SPACED_HYPHEN_RE.search(text):
        reasons.append("uses a dash between words; use a period or a comma instead")
    if "!" in text:
        reasons.append("has an exclamation mark")
    if _LIST_LINE_RE.search(body) or _MARKDOWN_RE.search(text):
        reasons.append("has formatting (a list, bold or a heading); write plain sentences")

    hits = [phrase for phrase, rx in _TELL_RES if rx.search(lowered)]
    if _NOT_ONLY_BUT_RE.search(lowered):
        hits.append("not just X but Y")
    if _NOT_ONLY_BUT_PT_RE.search(lowered):
        hits.append("não só X, mas Y")
    # Sellbird PT-BR: e-mail em português usa os limites de palavras do português.
    portuguese = looks_portuguese(f"{subject}\n{body}")
    if hits:
        shown = ", ".join(f'"{h}"' for h in hits[:4])
        reasons.append(f"sounds AI-written or salesy: {shown}")
    # Sellbird PT-BR: palavras que o remetente pediu para nunca usar
    # (writer.avoid_words). O nome do prospect e da empresa não contam.
    banned = avoided_words(text, avoid)
    if banned:
        shown = ", ".join(f'"{w}"' for w in banned[:4])
        reasons.append(f"uses words the sender asked never to use: {shown}; "
                       "rephrase without them (never describe the prospect's size)")

    if kind == "cold" and shape:
        cap = max_words(step, portuguese)
        count = words(body)
        if count > cap:
            reasons.append(f"is {count} words; email {step} must be {cap} or fewer")
        if body.count("?") > 1:
            reasons.append("asks more than one question; keep the one that matters")
        if _SELF_OPENING_RE.match(_first_line(body)):
            reasons.append('opens with "I" or "we"; open with them, not you')
        if words(subject) > 6:
            reasons.append(f"subject is {words(subject)} words; keep it to 2-5")
    elif kind == "reply":
        reply_cap = PT_REPLY_MAX_WORDS if portuguese else REPLY_MAX_WORDS
        if words(body) > reply_cap:
            reasons.append(f"is {words(body)} words; a reply must be {reply_cap} or fewer")
    return reasons


_SIGN_OFF_RE = re.compile(
    r"^(?:best|best wishes|thanks|thank you|thanks again|many thanks|cheers|regards|best regards|"
    r"kind regards|warm regards|warmly|talk soon|speak soon|all the best|sincerely|take care"
    # Despedidas em português: "Abraço,", "Abs", "Atenciosamente,", "Att.", "Obrigado,"
    r"|abra[çc]os?|um abra[çc]o|grande abra[çc]o|abs|att|atenciosamente|cordialmente|sauda[çc][õo]es"
    r"|obrigad[oa]|muito obrigad[oa]|grat[oa]|valeu|at[ée] mais|at[ée] breve|um forte abra[çc]o)[,.]?$",
    re.IGNORECASE)


def with_sign_off(body: str, name: str) -> str:
    """``body`` ending in the sender's first name on its own line, and no
    other sign-off.

    Models sign off three different ways in ten emails ("Best,", "Thanks,",
    none at all); one plain name under every email reads like a person who
    writes a lot of email. An empty ``name`` leaves the body as it is."""
    first = (name or "").strip().split(" ")[0] if (name or "").strip() else ""
    if not first:
        return body
    full = (name or "").strip().lower()
    lines = (body or "").rstrip().split("\n")
    while lines:
        last = lines[-1].strip().lstrip("-~ ").strip()
        low = last.lower().rstrip(",.")
        if not last or _SIGN_OFF_RE.match(last) or low in (first.lower(), full):
            lines.pop()
            continue
        m = re.match(r"^(.*?)[,.]?\s+(?:-\s*)?" + re.escape(first) + r"\.?$", last, re.IGNORECASE)
        if m and _SIGN_OFF_RE.match(m.group(1).strip() + ","):
            lines.pop()
            continue
        break
    return "\n".join(lines).rstrip() + "\n\n" + first
