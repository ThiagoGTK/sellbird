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
    assert _lang(_State("Curitiba, PR"), _prospect(), _config(default="en")) == PT_BR


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
