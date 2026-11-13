"""Empresas sem site, para prospecção por WhatsApp (Sellbird PT-BR).

O Sellbird só consegue mandar e-mail para quem tem site: é do domínio que ele
tira o endereço. As empresas que a busca encontra sem site nenhum ficavam
paradas no banco, e no Brasil elas são justamente o melhor público para quem
vende sites. Este módulo monta uma planilha (CSV) com essas empresas, o
telefone e um link pronto para abrir a conversa no WhatsApp.

O Sellbird NÃO manda WhatsApp sozinho: mensagem automática em massa leva o
número a ser banido. A planilha é para a pessoa abrir cada conversa e mandar a
própria mensagem.
"""

import csv
import io
import re

# Colunas do CSV, na ordem em que aparecem na planilha.
COLUMNS = ("empresa", "telefone", "tipo", "link_whatsapp", "segmento", "cidade",
           "mapa", "encontrada_em")


def _digits(phone: str) -> str:
    """Só os números do telefone: "+55 (47) 3367-0000" → "554733670000"."""
    return re.sub(r"\D", "", phone or "")


def brazil_number(phone: str) -> str:
    """Número no formato internacional do WhatsApp (55 + DDD + número), ou "".

    Aceita o que vem dos mapas: com ou sem +55, com ou sem o 0 de longa
    distância e o código da operadora (0xx41...). Um número que não tem cara de
    telefone brasileiro (DDD + 8 ou 9 dígitos) volta vazio: um link errado é
    pior que nenhum. Quando o campo traz dois números ("...; ..."), usa o primeiro.
    """
    first = re.split(r"[;,/]|\bou\b", phone or "")[0]
    d = _digits(first)
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    elif d.startswith("0") and len(d) in (13, 14):   # 0 + operadora (2 díg.) + DDD + número
        d = d[3:]
    elif d.startswith("0") and len(d) in (11, 12):   # 0 + DDD + número
        d = d[1:]
    # Aqui sobra DDD (2 dígitos, sem zero) + 8 ou 9 dígitos.
    if len(d) not in (10, 11) or d[0] == "0":
        return ""
    return "55" + d


def phone_kind(number: str) -> str:
    """"celular" quando o número (55 + DDD + 9 dígitos começando com 9) é móvel.

    Fixo também pode ter WhatsApp Business, por isso o link sai para os dois;
    a coluna só ajuda a decidir por onde começar.
    """
    if len(number) == 13 and number[4] == "9":
        return "celular"
    return "fixo" if number else ""


def whatsapp_link(number: str) -> str:
    """Link que abre a conversa no WhatsApp (app ou web), sem mensagem pronta."""
    return f"https://wa.me/{number}" if number else ""


async def build_rows(query_db) -> list[dict]:
    """Empresas sem site, com telefone primeiro (celular antes de fixo).

    ``query_db`` é a função do painel que roda SQL e devolve uma lista de dicts.
    """
    companies = await query_db(
        "SELECT name, phone, industry, location, source_url, created_at FROM companies "
        "WHERE COALESCE(domain, '') = '' AND COALESCE(website, '') = '' "
        "ORDER BY created_at")
    rows = []
    for c in companies:
        number = brazil_number(c.get("phone") or "")
        rows.append({
            "empresa": c.get("name") or "",
            "telefone": (c.get("phone") or "").strip(),
            "tipo": phone_kind(number),
            "link_whatsapp": whatsapp_link(number),
            "segmento": c.get("industry") or "",
            "cidade": c.get("location") or "",
            "mapa": c.get("source_url") or "",
            "encontrada_em": (c.get("created_at") or "")[:10],
        })
    # Ordem de trabalho: celular, depois fixo, por último quem não tem telefone.
    order = {"celular": 0, "fixo": 1, "": 2}
    rows.sort(key=lambda r: order.get(r["tipo"], 2))
    return rows


def to_csv(rows: list[dict]) -> str:
    """CSV com ";" como separador, que o Excel em português abre em colunas."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, delimiter=";", lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()
