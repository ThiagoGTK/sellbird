"""Testes da versão em português (Sellbird PT-BR).

Cobrem: escolha do idioma por país, detector de português, regras de estilo
em português, rodapé de descadastro em português, descadastro e escalada
para humano nas respostas em português, e cargos/nomes brasileiros.
"""

import asyncio
from types import SimpleNamespace

import pytest

from sellbird.agents.handler import _escalates, _flat, _opt_out_reason
from sellbird.collectors.people import is_owner_title, people_from_prose, split_person_name
from sellbird.config import ComplianceConfig, LanguageConfig, compliance_footer_lines
from sellbird.email_style import style_problems, with_sign_off
from sellbird.language import (
    EN, PT_BR, PT_PT, brazil_in_location, country_from_domain, language_for_country,
    language_rule, looks_portuguese, normalize_language, prospect_language,
)


# ── Idioma por país ─────────────────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    ("pt-BR", PT_BR), ("pt", PT_BR), ("Português", PT_BR), ("PT_BR", PT_BR),
    ("pt-PT", PT_PT), ("en", EN), ("english", EN), ("", EN),
])
def test_normaliza_o_idioma(value, expected):
    assert normalize_language(value) == expected


def test_idioma_por_pais():
    assert language_for_country("BR") == PT_BR
    assert language_for_country("PT") == PT_PT
    assert language_for_country("US") == EN
    assert language_for_country("", default=PT_BR) == PT_BR


@pytest.mark.parametrize("location", [
    "Curitiba, PR", "São Paulo - SP", "Recife, Pernambuco", "Porto Alegre, RS, Brasil", "Brazil",
])
def test_localizacoes_brasileiras(location):
    assert brazil_in_location(location, lean_brazil=True)


def test_sigla_ambigua_so_vale_quando_a_operacao_e_no_brasil():
    # "SC" é Santa Catarina ou Carolina do Sul.
    assert not brazil_in_location("Columbia, SC")
    assert brazil_in_location("Florianópolis, SC", lean_brazil=True)


def test_pais_pelo_dominio():
    assert country_from_domain("ana@clinica.com.br") == "BR"
    assert country_from_domain("https://www.exemplo.pt/sobre") == "PT"
    assert country_from_domain("sam@acme.com") == ""


class _State:
    """Banco de mentira: uma empresa com a localização dada."""

    def __init__(self, location=""):
        self.location = location

    async def get_company(self, _id):
        return SimpleNamespace(location=self.location, website="", domain="")

    async def get_setting(self, _key):
        return None


def _config(default="pt-BR", geography=()):
    return SimpleNamespace(
        language=LanguageConfig(default=default),
        icp=SimpleNamespace(geography=list(geography), geo_coordinates={}),
        compliance=SimpleNamespace(precleared=SimpleNamespace(prospect_country="")),
    )


def _prospect(email="ana@exemplo.com", company_id="c1", timezone=""):
    return SimpleNamespace(email=email, company_id=company_id, timezone=timezone)


def _lang(state, prospect, config):
    return asyncio.run(prospect_language(state, prospect, config))


def test_empresa_no_brasil_recebe_portugues():
    assert _lang(_State("Curitiba, PR, Brasil"), _prospect(), _config(default="en")) == PT_BR
    assert _lang(_State("Recife - Pernambuco"), _prospect(), _config(default="en")) == PT_BR
    # Sigla que também é país (PR = Porto Rico): vale como Paraná quando a
    # operação é voltada ao Brasil.
    assert _lang(_State("Curitiba, PR"), _prospect(), _config(default="pt-BR")) == PT_BR
    assert _lang(_State("San Juan, PR"), _prospect(), _config(default="en")) == EN


def test_fuso_de_endereco_brasileiro():
    from sellbird.send_window import recipient_zone, zone_for

    class St(_State):
        async def set_prospect_timezone(self, *_):
            pass

    p = SimpleNamespace(id="p1", company_id="c1", timezone="")
    assert asyncio.run(recipient_zone(St("Curitiba, PR"), p, _config(default="pt-BR"))) == "America/Sao_Paulo"
    p.timezone = ""
    assert asyncio.run(recipient_zone(St("Manaus, AM"), p, _config(default="pt-BR"))) == "America/Manaus"
    assert zone_for("Curitiba, PR, Brasil") == "America/Sao_Paulo"
    assert zone_for("Denver, CO") == "America/Denver"


def test_empresa_nos_eua_recebe_ingles_mesmo_com_padrao_portugues():
    assert _lang(_State("Denver, CO"), _prospect(), _config()) == EN


def test_sem_localizacao_usa_o_dominio_e_depois_o_padrao():
    assert _lang(_State(""), _prospect(email="ana@clinica.com.br"), _config(default="en")) == PT_BR
    assert _lang(_State(""), _prospect(), _config(default="pt-BR")) == PT_BR
    assert _lang(_State(""), _prospect(), _config(default="en")) == EN


def test_fuso_horario_do_prospect():
    p = _prospect(timezone="America/Sao_Paulo")
    assert _lang(_State(""), p, _config(default="en")) == PT_BR


def test_by_country_desligado_usa_sempre_o_padrao():
    cfg = _config(default="pt-BR")
    cfg.language.by_country = False
    assert _lang(_State("Denver, CO"), _prospect(), cfg) == PT_BR


def test_regra_de_idioma_no_prompt():
    assert "português do Brasil" in language_rule(PT_BR)
    assert "English" in language_rule(EN)


# ── Detector e estilo ────────────────────────────────────────────────────

def test_detector_de_portugues():
    assert looks_portuguese("Oi Ana, vi que a clínica aparece em 11º no Google. Quer o plano?")
    assert not looks_portuguese("Hi Sam, saw you're hiring a dispatcher. Want a hand?")


GOOD_PT = ("Oi Marcos,\n\nVi que a Hidrotec está contratando alguém para atender ligações. "
           "Até a vaga ser preenchida, um vazamento às 22h vai para o concorrente.\n\n"
           "Atendemos ligações fora do horário. Quer testar grátis por duas semanas?")


def test_um_bom_email_em_portugues_passa():
    assert style_problems("vaga de atendimento", GOOD_PT) == []


def test_clichês_em_portugues_sao_barrados():
    found = style_problems("oi", "Olá Ana,\n\nEspero que esteja bem. Temos uma solução inovadora. Quer ver?")
    assert any("espero que esteja bem" in r for r in found)
    assert any("inovadora" in r for r in found)


def test_abrir_falando_de_si_em_portugues():
    found = style_problems("oi", "Oi Ana,\n\nSomos uma agência de sites em Curitiba. Quer um orçamento?")
    assert any("opens with" in r for r in found)


def test_limite_de_palavras_maior_em_portugues():
    body = "Oi Ana,\n\n" + " ".join(["você"] * 65)
    assert not any("words" in r for r in style_problems("oi", body))      # até 70 em português
    body = "Oi Ana,\n\n" + " ".join(["você"] * 75)
    assert any("words" in r for r in style_problems("oi", body))


def test_despedida_em_portugues_vira_so_o_nome():
    assert with_sign_off("Oi\n\nTexto\n\nAbraço,\nThiago", "Thiago Gaitkoski").endswith("Texto\n\nThiago")


# ── Rodapé de descadastro ────────────────────────────────────────────────

def test_rodape_em_portugues():
    c = SimpleNamespace(compliance=ComplianceConfig(postal_address="Rua X, 100, Curitiba, PR"))
    assert compliance_footer_lines(c, "pt-BR")[1].startswith("Não faz sentido")
    assert compliance_footer_lines(c, "en")[1].startswith("Not interested")


def test_linha_de_descadastro_precisa_dizer_que_para():
    ComplianceConfig(opt_out_line_pt="Sem interesse? Responda SAIR.")
    with pytest.raises(Exception):
        ComplianceConfig(opt_out_line_pt="Abraços e até logo")
    with pytest.raises(Exception):
        ComplianceConfig(opt_out_line_pt="Clique aqui para sair")


# ── Respostas: descadastro e escalada ────────────────────────────────────

@pytest.mark.parametrize("text", [
    "Por favor, me descadastre.", "me tira dessa lista", "Remova meu e-mail da sua lista",
    "Parem de me mandar e-mails", "Não me envie mais e-mails.", "Não tenho interesse.",
    "Não, obrigado.", "sair", "Não quero mais receber isso", "Sem interesse no momento, obrigado.",
])
def test_pedidos_de_saida_em_portugues(text):
    assert _opt_out_reason(text, text) is not None


@pytest.mark.parametrize("text", [
    "Pode me tirar uma dúvida? Quanto custa?",
    "Não temos interesse no plano anual, mas o mensal pode ser.",
    "Se não tiver interesse eu te aviso",
    "Não me envie a proposta ainda, preciso falar com meu sócio",
    "Pode me mandar mais detalhes?",
    "Sim ou não, obrigado pela atenção",
    "Não me escreva até março, estamos fechando o trimestre",
])
def test_respostas_que_nao_sao_pedido_de_saida(text):
    assert _opt_out_reason(text, text) is None


@pytest.mark.parametrize("text,expected", [
    ("Vou acionar meu advogado", True), ("Vou reclamar no Procon", True),
    ("Isso é spam", True), ("Vocês estão descumprindo a LGPD", True),
    ("Quero entender o processo de vocês", False), ("Pode me ligar amanhã?", False),
])
def test_escalada_para_humano(text, expected):
    assert _escalates(_flat(text)) is expected


# ── Decisores em sites brasileiros ───────────────────────────────────────

@pytest.mark.parametrize("title,expected", [
    ("Sócia-fundadora", True), ("Proprietário", True), ("Diretor Geral", True), ("Sócio", True),
    ("Vice-presidente", False), ("Assistente da diretoria", False), ("Ex-proprietário", False),
])
def test_cargos_de_dono_em_portugues(title, expected):
    assert is_owner_title(title) is expected


def test_nomes_brasileiros():
    assert split_person_name("Dra. Ana Paula Souza") == ("Ana", "Souza")
    assert split_person_name("Pedro do Carmo") == ("Pedro", "do Carmo")
    assert split_person_name("Maria da Silva Oliveira") == ("Maria", "Oliveira")


def test_dono_citado_em_frase_em_portugues():
    html = ("<p>A Clínica Sorriso Pleno foi fundada em 2004 pela Dra. Ana Souza.</p>"
            "<p>Fernanda Alves é a proprietária da loja.</p>")
    found = {(p["first_name"], p["last_name"]) for p in people_from_prose(html, "sorrisopleno.com.br",
                                                                         "Sorriso Pleno")}
    assert ("Ana", "Souza") in found and ("Fernanda", "Alves") in found


# ── Writer: uma campanha por idioma ──────────────────────────────────────

class _RecordingBrain:
    """Brain de mentira que guarda os prompts e devolve uma sequência válida."""

    def __init__(self):
        self.prompts = []

    def load_skills_for_agent(self, name):
        return ""

    def load_prompt(self, name, **kw):
        return "prompt"

    async def think_json(self, prompt, **kw):
        self.prompts.append(prompt)
        return [{"step": 1, "subject": "uma ideia", "body": "Oi {{first_name}}, quem atende na {{company}}?",
                 "delay_days": 0}]


@pytest.mark.asyncio
async def test_writer_separa_campanhas_por_idioma(tmp_path):
    from sellbird.agents.writer import Writer
    from sellbird.models.company import Company
    from sellbird.models.prospect import Prospect
    from sellbird.state import StateManager

    state = StateManager(str(tmp_path / "pt.db"))
    await state.init_db()
    br = await state.add_company(Company(name="Sorriso", domain="sorriso.com.br", location="Curitiba, PR"))
    us = await state.add_company(Company(name="Smile", domain="smile.example", location="Denver, CO"))
    for n, cid in ((1, br), (2, us)):
        await state.add_prospect(Prospect(
            first_name=f"P{n}", last_name="Silva", title="Owner", company=f"Co{n}", industry="Dental",
            email=f"p{n}@co{n}.example", email_status="verified", company_id=cid))
    config = SimpleNamespace(
        channels=SimpleNamespace(email=SimpleNamespace(provider="instantly", require_approval=False)),
        product=SimpleNamespace(name="P", description="D", key_benefits=[], pricing=""),
        persona=SimpleNamespace(name="S", company="C", role="R", tone="t"),
        writer=SimpleNamespace(humanizer=False, email_rules=""),
        language=LanguageConfig(default="pt-BR"),
        icp=SimpleNamespace(geography=[], geo_coordinates={}),
        compliance=SimpleNamespace(precleared=SimpleNamespace(prospect_country="")),
    )
    brain = _RecordingBrain()
    await Writer(brain, state, config, None).run()

    names = sorted(c.name for c in await state.get_campaigns_by_status("draft"))
    assert names == ["Dental-outreach", "Dental-outreach-pt-BR"]
    assert sum("IDIOMA DO E-MAIL: português do Brasil" in p for p in brain.prompts) == 1
    assert sum("EMAIL LANGUAGE: English" in p for p in brain.prompts) == 1


# ── E-mail montado a partir de nome com acento ──

def test_nome_com_acento_vira_email_sem_acento():
    """"João" precisa virar "joao@", não "joo@" (bug visto em produção)."""
    from sellbird.integrations.email_finder import _clean_name_part, build_email

    assert _clean_name_part("João") == "joao"
    assert _clean_name_part("Conceição") == "conceicao"
    assert _clean_name_part("Müller") == "muller"
    assert build_email("{f}", "João", "Heckert", "hec.adv.br") == "joao@hec.adv.br"


# ── Ferramentas brasileiras no detector de plataformas e de agendamento ──

def test_detecta_ferramentas_brasileiras():
    from sellbird.integrations.tech_detect import detect_tech
    html = ('<script src="https://d335luupugsy2.cloudfront.net/js/x.js"></script>'
            '<a href="https://wa.me/5500000000000">WhatsApp</a>'
            '<img src="https://www.doctoralia.com.br/widget.png">'
            '<link href="https://cdn.lojaintegrada.com.br/x.css">')
    found = detect_tech(html)
    for tool in ("RD Station", "WhatsApp", "Doctoralia", "Loja Integrada"):
        assert tool in found


def test_botao_de_whatsapp_conta_como_agendamento():
    """Quem agenda pelo WhatsApp não é "sem agendamento online"."""
    from sellbird.collectors.profile import BOOKING_HINTS, ProfileCollector
    assert ProfileCollector._any('<a href="https://wa.me/5500000000000">Agende</a>', BOOKING_HINTS)
    assert ProfileCollector._any('<a href="https://api.whatsapp.com/send?phone=55">x</a>', BOOKING_HINTS)
    assert ProfileCollector._any('<iframe src="https://app.simplesdental.com/agenda">', BOOKING_HINTS)
    assert not ProfileCollector._any('<p>Ligue para marcar.</p>', BOOKING_HINTS)


# ── Agência creditada no rodapé ("Desenvolvido por") ──

def _agencia(html):
    from sellbird.collectors.profile import ProfileCollector
    return ProfileCollector.__new__(ProfileCollector).detect_agency(html, "clinica.example.com.br")


def test_rodape_desenvolvido_por_vira_agencia():
    found = _agencia('<footer>© Clínica. Desenvolvido por <a href="https://agencia.example.com">Agência X</a></footer>')
    assert found and found[0] == "Agência X" and found[1] >= 0.75
    found = _agencia('<footer>Desenvolvimento: <a href="https://web.example.com">Web Y</a></footer>')
    assert found and found[0] == "Web Y"
    found = _agencia('<footer>Feito com ♥ por <a href="https://estudio.example.com">Estúdio Z</a></footer>')
    assert found and found[0] == "Estúdio Z"


def test_link_solto_ou_whatsapp_no_rodape_nao_e_agencia():
    assert _agencia('<footer><a href="https://parceiro.example.com">Parceiro</a></footer>') is None
    assert _agencia('<footer>Fale por <a href="https://api.whatsapp.com/send?phone=55">WhatsApp</a></footer>') is None


# ── Guias e diretórios brasileiros não viram empresa ──

def test_guias_brasileiros_sao_descartados():
    from sellbird.collectors.discover import is_junk
    for domain in ("listamais.com.br", "www.guiamais.com.br", "apontador.com.br",
                   "telelistas.net", "encontrabalneariocamboriu.com.br", "casadosdados.com.br",
                   "doctoralia.com.br", "jusbrasil.com.br", "booking.com"):
        assert is_junk(domain), domain
    # Uma empresa de verdade passa.
    assert not is_junk("clinicaexemplo.com.br")
    assert not is_junk("escritorio-exemplo.adv.br")


def test_scout_usa_os_mesmos_padroes():
    from sellbird.agents.scout import Scout
    scout = Scout.__new__(Scout)
    assert scout._is_noise_domain("listamais.com.br")
    assert not scout._is_noise_domain("clinicaexemplo.com.br")


# ── Planilha de empresas sem site (WhatsApp) ──

def test_numero_brasileiro_para_whatsapp():
    from sellbird.sem_site import brazil_number, phone_kind, whatsapp_link
    assert brazil_number("+55 (47) 99999-0000") == "5547999990000"
    assert brazil_number("(47) 3333-0000") == "554733330000"
    assert brazil_number("047 99999-0000") == "5547999990000"
    assert brazil_number("0xx41 99999-0000".replace("xx", "15")) == "5541999990000"
    assert brazil_number("+55 47 99999-0000; +55 47 3333-0000") == "5547999990000"
    assert brazil_number("123") == ""
    assert brazil_number("") == ""
    assert phone_kind("5547999990000") == "celular"
    assert phone_kind("554733330000") == "fixo"
    assert whatsapp_link("5547999990000") == "https://wa.me/5547999990000"
    assert whatsapp_link("") == ""


def test_planilha_sem_site_so_traz_quem_nao_tem_site():
    import asyncio
    from sellbird.sem_site import build_rows, to_csv

    empresas = [
        {"name": "Clínica Sem Site", "phone": "(47) 3333-0000", "industry": "Clínica odontológica",
         "location": "Itajaí, SC", "source_url": "https://www.openstreetmap.org/node/1",
         "created_at": "2026-01-02 10:00:00", "domain": "", "website": ""},
        {"name": "Contabilidade Celular", "phone": "+55 47 99999-0000", "industry": "Contabilidade",
         "location": "Itajaí, SC", "source_url": "", "created_at": "2026-01-03 10:00:00",
         "domain": "", "website": ""},
    ]

    async def fake_query(sql, params=()):
        assert "domain" in sql and "website" in sql   # filtro de "sem site" vai no SQL
        return empresas

    rows = asyncio.run(build_rows(fake_query))
    assert [r["empresa"] for r in rows] == ["Contabilidade Celular", "Clínica Sem Site"]  # celular primeiro
    assert rows[0]["link_whatsapp"] == "https://wa.me/5547999990000"
    text = to_csv(rows)
    assert text.splitlines()[0].startswith("empresa;telefone;tipo;link_whatsapp")


# ── Avisos do analista em português ──

def test_aviso_travado_em_portugues_e_sem_instantly():
    from sellbird.agents.analyst import Analyst
    a = Analyst.__new__(Analyst)
    report = {"pipeline": {"queued": 2, "contacted": 0, "new": 0}, "intents": {},
              "stages": {}, "campaigns": []}
    text = " ".join(a._generate_insights(report))
    assert "TRAVADO" in text and "Instantly" not in text


# ── Nomes de serviço e de cidade não viram pessoa ──

def test_servico_e_cidade_nao_sao_nome_de_pessoa():
    from sellbird.collectors.people import split_person_name
    for texto in ("Tratamentos Camboriú", "Preenchimento BC", "Harmonização Facial",
                  "Clareamento Dental", "Odontologia Avançada"):
        assert split_person_name(texto) is None, texto
    assert split_person_name("João Exemplo") == ("João", "Exemplo")
    assert split_person_name("Maria da Silva Exemplo") == ("Maria", "Exemplo")


# ── Endereços de setor em português (contato@, secretaria@...) ──

def test_endereco_de_setor_nao_ensina_padrao_de_nome():
    """secretaria@ não pode fazer o Sellbird achar que o escritório usa {primeiro nome}@."""
    from sellbird.integrations.email_finder import ROLE_LOCALS, pattern_from_local
    for local in ("contato", "secretaria", "atendimento", "comercial", "financeiro", "faleconosco"):
        assert local in ROLE_LOCALS
        assert pattern_from_local(local) is None


# ── Funil: e-mail inválido não conta como "Para escrever" ──

def test_email_invalido_sai_do_para_escrever():
    from sellbird.dashboard import _pipeline_bucket
    assert _pipeline_bucket("new", None, None, "invalid") == "closed_out"
    assert _pipeline_bucket("new", None, None, "verified") == "to_write"
    assert _pipeline_bucket("queued", None, None, "risky") == "to_write"


# ── Índice de sitemaps (WordPress/Yoast): conta páginas, não sitemaps ──

def test_indice_de_sitemaps_conta_as_paginas_de_verdade():
    import asyncio
    import re
    from sellbird.collectors.profile import ProfileCollector

    site = "https://escritorio.example.com.br"
    paginas = {
        f"{site}/sitemap.xml": (
            "<sitemapindex>"
            f"<sitemap><loc>{site}/page-sitemap.xml</loc></sitemap>"
            f"<sitemap><loc>{site}/post-sitemap.xml</loc></sitemap>"
            f"<sitemap><loc>{site}/video-sitemap.xml</loc></sitemap>"
            "<sitemap><loc>https://outro.example.com/sitemap.xml</loc></sitemap>"
            "</sitemapindex>"),
        f"{site}/page-sitemap.xml": "<urlset>" + "".join(
            f"<url><loc>{site}/p{i}/</loc></url>" for i in range(12)) + "</urlset>",
        f"{site}/post-sitemap.xml": "<urlset>" + "".join(
            f"<url><loc>{site}/post{i}/</loc></url>" for i in range(30)) + "</urlset>",
    }
    pedidos = []

    async def fake_get(url):
        pedidos.append(url)
        return paginas.get(url, "")

    p = ProfileCollector.__new__(ProfileCollector)
    p._get = fake_get
    texto = asyncio.run(p._sitemap_text(site))
    assert len(re.findall(r"<loc>", texto)) == 42          # 12 páginas + 30 posts, não "4"
    assert f"{site}/video-sitemap.xml" not in pedidos       # vídeo repete páginas
    assert "https://outro.example.com/sitemap.xml" not in pedidos   # outro site: ignorado


def test_sitemap_simples_continua_igual():
    import asyncio
    from sellbird.collectors.profile import ProfileCollector
    site = "https://clinica.example.com.br"
    simples = f"<urlset><url><loc>{site}/</loc></url><url><loc>{site}/artigos/</loc></url></urlset>"

    async def fake_get(url):
        return simples if url.endswith("/sitemap.xml") else ""

    p = ProfileCollector.__new__(ProfileCollector)
    p._get = fake_get
    assert asyncio.run(p._sitemap_text(site)) == simples


# ── Palavras proibidas pelo remetente (writer.avoid_words) ──

def test_palavra_proibida_vira_problema_de_estilo():
    from sellbird.email_style import avoided_words, style_problems
    corpo = "Oi Ana,\n\nFaço sites para pequenos negócios. Quer ver uma prévia?\n\nThiago"
    avoid = ["pequeno", "pequenos", "pequena", "pequenas"]
    assert avoided_words(corpo, avoid) == ["pequenos"]
    assert avoided_words("Faço sites para PEQUENOS negócios", avoid) == ["pequenos"]
    assert avoided_words("Não é pequenez nenhuma", avoid) == []   # palavra inteira
    problemas = style_problems("site", corpo, avoid=avoid)
    assert any("never to use" in p for p in problemas)
    # Sem lista, nada muda.
    assert not any("never to use" in p for p in style_problems("site", corpo))


def test_nome_do_prospect_com_palavra_proibida_nao_conta():
    from sellbird.email_style import style_problems
    corpo = "Oi Ana,\n\nVi o site da Pequena Padaria Exemplo. Quer ver uma prévia?\n\nThiago"
    problemas = style_problems("site", corpo, names=["Pequena Padaria Exemplo"], avoid=["pequena"])
    assert not any("never to use" in p for p in problemas)


def test_config_aceita_avoid_words():
    from sellbird.config import WriterConfig
    assert WriterConfig(avoid_words="pequeno").avoid_words == ["pequeno"]
    assert WriterConfig(avoid_words=[" pequenos negócios ", ""]).avoid_words == ["pequenos negócios"]
    assert WriterConfig().avoid_words == []


# ── Chaves das fontes de busca pelo painel ──

def test_painel_salva_e_mostra_chaves_de_busca(tmp_path, monkeypatch):
    """Scavio, Serper, TinyFish e DataForSEO entram pelo painel como o Reoon."""
    import asyncio
    import json
    from sellbird import dashboard

    env = tmp_path / ".env"
    env.write_text("SMTP_HOST=smtp.example.com\n", encoding="utf-8")
    monkeypatch.setattr(dashboard, "ENV_FILE", env)
    for k in ("SCAVIO_API_KEY", "DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"):
        monkeypatch.delenv(k, raising=False)

    class Req:
        async def json(self):
            return {"SCAVIO_API_KEY": "chave-de-teste", "DATAFORSEO_LOGIN": "conta@example.com"}

    r = asyncio.run(dashboard.save_env_settings(Req()))
    r = r if isinstance(r, dict) else json.loads(r.body)
    assert r["success"]
    texto = env.read_text(encoding="utf-8")
    assert "SCAVIO_API_KEY=chave-de-teste" in texto and "SMTP_HOST=smtp.example.com" in texto
    s = asyncio.run(dashboard.get_settings())
    assert s["scavio_api_key_set"] is True and "chave-de-teste" not in json.dumps(s)
    assert s["dataforseo_login"] == "conta@example.com" and s["dataforseo_password_set"] is False
