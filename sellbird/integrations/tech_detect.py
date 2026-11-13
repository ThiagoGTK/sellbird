"""Tech-stack detection — what tools a company's website reveals.

A curated subset of Wappalyzer-style fingerprints matched against HTML
Sellbird already downloads while researching a company. Zero extra network
requests, zero dependencies. Knowing a prospect runs Shopify / HubSpot /
Intercom (or conspicuously lacks something) is a concrete, verifiable
personalization hook — the kind that actually earns replies.

Patterns are intentionally conservative: match distinctive script hosts,
cookie names, or generator tags — not generic words — so false positives
stay rare.
"""

import re

# name -> list of regexes; any match counts. Compiled lazily, matched
# case-insensitively against the raw HTML.
FINGERPRINTS: dict[str, list[str]] = {
    # CMS / site builders
    "WordPress": [r"wp-content/", r"wp-includes/", r'<meta name="generator" content="WordPress'],
    "Shopify": [r"cdn\.shopify\.com", r"myshopify\.com"],
    "Wix": [r"static\.parastorage\.com", r"wix\.com/website-builder"],
    "Squarespace": [r"static1\.squarespace\.com", r'<!-- This is Squarespace'],
    "Webflow": [r"assets\.website-files\.com", r'data-wf-domain'],
    "Framer": [r"framerusercontent\.com"],
    "Drupal": [r'<meta name="generator" content="Drupal', r"sites/default/files"],
    "Ghost": [r'<meta name="generator" content="Ghost'],
    "Next.js": [r"/_next/static/"],
    "Gatsby": [r"/page-data/app-data\.json", r"id=\"___gatsby\""],

    # Analytics / tracking
    "Google Analytics": [r"googletagmanager\.com/gtag", r"google-analytics\.com/analytics\.js"],
    "Google Tag Manager": [r"googletagmanager\.com/gtm\.js"],
    "Segment": [r"cdn\.segment\.com/analytics\.js"],
    "Mixpanel": [r"cdn\.mxpnl\.com"],
    "Hotjar": [r"static\.hotjar\.com"],
    "Plausible": [r"plausible\.io/js"],
    "Meta Pixel": [r"connect\.facebook\.net/[^\"']*fbevents\.js"],

    # Marketing / CRM
    "HubSpot": [r"js\.hs-scripts\.com", r"js\.hsforms\.net", r"hubspot\.com/api"],
    "Marketo": [r"munchkin\.marketo\.net"],
    "Mailchimp": [r"chimpstatic\.com", r"list-manage\.com/subscribe"],
    "Klaviyo": [r"static\.klaviyo\.com"],
    "ActiveCampaign": [r"trackcmp\.net"],
    "Salesforce": [r"force\.com", r"salesforce\.com/embeddedservice"],

    # Chat / support
    "Intercom": [r"widget\.intercom\.io", r"js\.intercomcdn\.com"],
    "Drift": [r"js\.driftt\.com"],
    "Zendesk": [r"static\.zdassets\.com", r"zendesk\.com/embeddable"],
    "Crisp": [r"client\.crisp\.chat"],
    "Tidio": [r"code\.tidio\.co"],
    "LiveChat": [r"cdn\.livechatinc\.com"],

    # Scheduling / payments
    "Calendly": [r"assets\.calendly\.com", r"calendly\.com/[\w\-]+/"],
    "Stripe": [r"js\.stripe\.com"],
    "Typeform": [r"embed\.typeform\.com"],

    # E-commerce (non-Shopify)
    "WooCommerce": [r"woocommerce", r"wc-ajax"],
    "BigCommerce": [r"cdn\d*\.bigcommerce\.com"],

    # ── Brasil (Sellbird PT-BR): ferramentas comuns em sites brasileiros ──
    # Criadores de site e lojas virtuais
    "Nuvemshop": [r"nuvemshop", r"lojanuvem\.com\.br", r"tiendanube"],
    "Tray": [r"tray\.com\.br", r"traycorp"],
    "Loja Integrada": [r"lojaintegrada\.com\.br"],
    "VTEX": [r"vteximg\.com\.br", r"vtexassets\.com", r"vtex\.com\.br"],
    "Hostinger Website Builder": [r"zyrosite\.com", r"zyro\.com", r"assets\.zyrosite"],
    # Marketing / CRM
    "RD Station": [r"rdstation\.com\.br", r"d335luupugsy2\.cloudfront\.net", r"rdstation-static"],
    "Kommo": [r"kommo\.com", r"amocrm\.(?:com|ru)"],
    "Leadster": [r"leadster\.com\.br"],
    # Atendimento
    "WhatsApp": [r"wa\.me/", r"api\.whatsapp\.com/send", r"web\.whatsapp\.com/send"],
    "JivoChat": [r"jivosite\.com", r"jivochat"],
    "Blip": [r"blip\.ai", r"take\.net/blip"],
    # Agenda (clínicas, salões, serviços)
    "Doctoralia": [r"doctoralia\.com\.br"],
    "iClinic": [r"iclinic\.com\.br"],
    "Simples Dental": [r"simplesdental\.com"],
    "Feegow": [r"feegow\.com"],
    "Clinicorp": [r"clinicorp\.com"],
    "Trinks": [r"trinks\.com"],
    # Pagamentos e infoprodutos
    "PagSeguro": [r"pagseguro\.uol\.com\.br", r"stc\.pagseguro"],
    "Mercado Pago": [r"mercadopago\.com", r"sdk\.mercadopago"],
    "Hotmart": [r"hotmart\.com"],

    # Hosting/infra hints
    "Cloudflare": [r"/cdn-cgi/"],
    "Vercel": [r"vercel\.app", r"x-vercel"],
}

_compiled: dict[str, list[re.Pattern]] | None = None


def _get_compiled() -> dict[str, list[re.Pattern]]:
    global _compiled
    if _compiled is None:
        _compiled = {
            name: [re.compile(p, re.IGNORECASE) for p in patterns]
            for name, patterns in FINGERPRINTS.items()
        }
    return _compiled


def detect_tech(html: str, max_bytes: int = 300_000) -> list[str]:
    """Return the tools detectable in a page's HTML, alphabetized."""
    if not html:
        return []
    sample = html[:max_bytes]
    found = []
    for name, patterns in _get_compiled().items():
        if any(p.search(sample) for p in patterns):
            found.append(name)
    return sorted(found)
