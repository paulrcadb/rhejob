import csv
from pathlib import Path
from typing import Any


CATEGORIA_OPERACIONAL = "Operacional Construção Civil"
CATEGORIA_GESTAO = "Gestão de Obras e Projetos Construção Civil"


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def _table_lines(text: str) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    header_index = next((index for index, line in enumerate(lines) if line.startswith("ID|")), None)
    if header_index is None:
        return lines
    return lines[header_index:]


def montar_descricao_base(row: dict[str, str], categoria: str) -> str:
    nome = (row.get("Cargo_Padrao") or row.get("Cargo") or "").strip()
    partes = [
        f"Categoria: {categoria}",
        f"Cargo padrao: {nome}",
        f"CBO: {row.get('CBO_Ref', '').strip()}",
        f"Familia: {row.get('Familia', '').strip()}",
        f"Senioridade: {row.get('Senioridade', '').strip()}",
        "",
        "Descricao:",
        row.get("Descricao", "").strip(),
        "",
        "Responsabilidades:",
        row.get("Responsabilidades", "").strip(),
        "",
        "Requisitos:",
        row.get("Requisitos", "").strip(),
        "",
        "NRs recomendadas:",
        row.get("NRs_Recomendadas", "").strip(),
        "",
        "Ferramentas:",
        row.get("Ferramentas", "").strip(),
        "",
        "Faixa salarial CLT mensal:",
        row.get("Faixa_CLT_BR_Mensal", "").strip(),
        "",
        "PJ referencia:",
        row.get("PJ_Referencia", "").strip(),
        "",
        "Variacao regional:",
        row.get("Variacao_Regional", "").strip(),
        "",
        "Mercado premium:",
        row.get("Mercado_Premium", "").strip(),
        "",
        "Aliases:",
        row.get("Aliases", "").strip(),
        "",
        "Palavras-chave:",
        row.get("Keywords", "").strip(),
    ]
    return "\n".join(part for part in partes if part is not None).strip()


def carregar_base_cargos(path: Path, categoria: str, origem_base: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    text = _read_text(path)
    rows = csv.DictReader(_table_lines(text), delimiter="|")
    cargos = []
    for row in rows:
        nome = (row.get("Cargo_Padrao") or row.get("Cargo") or "").strip()
        if not nome:
            continue
        variacao_regional = (row.get("Variacao_Regional") or row.get("Mercado_Premium") or "").strip()
        cargos.append(
            {
                "codigo_base": (row.get("ID") or "").strip(),
                "nome_cargo": nome,
                "descricao": montar_descricao_base(row, categoria),
                "categoria": categoria,
                "cbo_ref": (row.get("CBO_Ref") or "").strip(),
                "aliases": (row.get("Aliases") or "").strip(),
                "familia": (row.get("Familia") or "").strip(),
                "senioridade": (row.get("Senioridade") or "").strip(),
                "salario": (row.get("Faixa_CLT_BR_Mensal") or "").strip(),
                "variacao_regional": variacao_regional,
                "keywords": (row.get("Keywords") or "").strip(),
                "origem_base": origem_base,
            }
        )
    return cargos


def carregar_base_operacional(path: Path) -> list[dict[str, Any]]:
    return carregar_base_cargos(path, CATEGORIA_OPERACIONAL, "base_operacional_construcao_civil")


def carregar_base_gestao_obras(path: Path) -> list[dict[str, Any]]:
    return carregar_base_cargos(path, CATEGORIA_GESTAO, "base_gestao_obras_projetos_construcao_civil")
