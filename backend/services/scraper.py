import logging
import re
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


async def buscar_descricao_web(nome_cargo: str) -> str | None:
    query = quote_plus(f"{nome_cargo} descricao cargo responsabilidades requisitos")
    url = f"https://duckduckgo.com/html/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0 job-analyzer-local/1.0"}

    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception as exc:
        logger.info("Busca web falhou: %s", exc)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    snippets = [
        re.sub(r"\s+", " ", item.get_text(" ", strip=True))
        for item in soup.select(".result__snippet")
    ]
    text = " ".join(snippets[:6]).strip()
    if len(text) < 160:
        return None

    return (
        f"Responsabilidades:\n{text[:900]}\n\n"
        f"Requisitos:\nConhecimentos e experiencias citados nas fontes encontradas para {nome_cargo}.\n\n"
        f"Habilidades desejadas:\nComunicacao, organizacao, colaboracao, capacidade analitica e aprendizado continuo."
    )


async def buscar_descricao_web_profunda(nome_cargo: str) -> str | None:
    queries = [
        f"{nome_cargo} descricao cargo responsabilidades requisitos habilidades",
        f"{nome_cargo} atividades competencias experiencia formacao",
        f"vaga {nome_cargo} responsabilidades requisitos senioridade",
        f"job description {nome_cargo} responsibilities requirements skills",
    ]
    headers = {"User-Agent": "Mozilla/5.0 job-analyzer-local/1.0"}
    snippets: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=headers) as client:
            for query in queries:
                url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
                response = await client.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                snippets.extend(
                    re.sub(r"\s+", " ", item.get_text(" ", strip=True))
                    for item in soup.select(".result__snippet")
                )
    except Exception as exc:
        logger.info("Busca web profunda falhou: %s", exc)

    unique_snippets = list(dict.fromkeys(snippets))
    text = " ".join(unique_snippets[:18]).strip()
    if len(text) < 220:
        return None

    return (
        f"Responsabilidades:\n{text[:1400]}\n\n"
        f"Requisitos:\n"
        f"- Experiencia relacionada a {nome_cargo}.\n"
        f"- Conhecimento tecnico e capacidade de coordenar entregas, processos e indicadores.\n"
        f"- Vivencia com ferramentas, rotinas e stakeholders citados nas fontes encontradas.\n\n"
        f"Habilidades desejadas:\n"
        f"- Lideranca, comunicacao, organizacao e capacidade analitica.\n"
        f"- Resolucao de problemas, visao sistemica e orientacao a resultados.\n"
        f"- Capacidade de priorizar demandas e documentar decisoes tecnicas."
    )
