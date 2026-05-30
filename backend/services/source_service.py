import logging
import re
from collections import Counter
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)

SOURCE_QUERIES = [
    (
        "CBO / Ministerio do Trabalho",
        "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/cbo",
        "site:gov.br/trabalho-e-emprego CBO {cargo} atividades competencias ocupacao",
    ),
    (
        "Consulta CBO",
        "https://consulta.trabalho.gov.br/empregador/cbo/procuracbo/",
        "site:consulta.trabalho.gov.br/empregador/cbo/procuracbo {cargo}",
    ),
    (
        "Guia Brasileiro de Ocupacoes",
        "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/guia-brasileiro-de-ocupacoes",
        "site:gov.br/trabalho-e-emprego guia brasileiro ocupacoes {cargo}",
    ),
    (
        "O*NET",
        "https://www.onetonline.org/",
        "site:onetonline.org {cargo} tasks skills knowledge",
    ),
    (
        "ESCO",
        "https://esco.ec.europa.eu/",
        "site:esco.ec.europa.eu {cargo} occupation skills competences",
    ),
    (
        "Vagas reais publicas",
        "https://duckduckgo.com/",
        "vaga {cargo} responsabilidades requisitos ferramentas conhecimentos",
    ),
]

STOPWORDS = {
    "para",
    "com",
    "uma",
    "das",
    "dos",
    "que",
    "por",
    "como",
    "mais",
    "cargo",
    "vaga",
    "sobre",
    "este",
    "esta",
    "sao",
    "ser",
    "ter",
    "area",
    "profissional",
    "trabalho",
    "emprego",
}

GENERIC_SKILLS = [
    "comunicacao",
    "organizacao",
    "lideranca",
    "colaboracao",
    "visao sistemica",
    "resolucao de problemas",
    "analise critica",
    "orientacao a resultados",
]

BAD_SNIPPET_MARKERS = {
    "apresentacao",
    "apresentação",
    "apresenta",
    "por meio desta publicacao",
    "por meio desta publicação",
    "portaria ministerial",
    "classificacao brasileira de ocupacoes",
    "classificação brasileira de ocupações",
    "cbo atualizada",
    "pagina inicial",
    "você está aqui",
    "voce esta aqui",
    "acesso a informacao",
}

GOOD_SNIPPET_MARKERS = {
    "responsavel",
    "responsável",
    "atividades",
    "funcoes",
    "funções",
    "tarefas",
    "habilidades",
    "competencias",
    "competências",
    "requisitos",
    "conhecimentos",
    "ferramentas",
    "experiencia",
    "experiência",
    "planejar",
    "gerenciar",
    "coordenar",
    "supervisionar",
    "implementar",
    "monitorar",
}


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-zÀ-ÿ0-9#+.]{4,}", text.lower())
    counts = Counter(word for word in words if word not in STOPWORDS)
    return [word for word, _count in counts.most_common(35)]


def _bullets_from_snippets(snippets: list[str], terms: list[str], limit: int = 6) -> list[str]:
    selected: list[str] = []
    ranked = sorted(snippets, key=_snippet_score, reverse=True)
    for snippet in ranked:
        if len(selected) >= limit:
            break
        if any(term in snippet.lower() for term in terms[:18]):
            sentence = snippet.split(". ")[0].strip(" .")
            if 45 <= len(sentence) <= 220 and sentence not in selected:
                selected.append(sentence)
    return selected


def _snippet_score(snippet: str) -> int:
    lowered = snippet.lower()
    if any(marker in lowered for marker in BAD_SNIPPET_MARKERS):
        return -10
    score = sum(2 for marker in GOOD_SNIPPET_MARKERS if marker in lowered)
    score += min(len(snippet) // 120, 4)
    return score


async def _duckduckgo_snippets(query: str) -> list[str]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"User-Agent": "Mozilla/5.0 rh-job-local/1.0"}
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception as exc:
        logger.info("Fonte publica falhou para query '%s': %s", query, exc)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    snippets = [
        _clean_text(item.get_text(" ", strip=True))
        for item in soup.select(".result__snippet")
    ]
    return [
        snippet
        for snippet in snippets
        if len(snippet) > 40 and _snippet_score(snippet) >= 0
    ]


async def coletar_fontes_publicas(nome_cargo: str) -> tuple[list[dict], list[str]]:
    fontes: list[dict] = []
    all_snippets: list[str] = []

    for nome, url, template in SOURCE_QUERIES:
        snippets = await _duckduckgo_snippets(template.format(cargo=nome_cargo))
        if snippets:
            fontes.append({"nome": nome, "url": url, "trechos": snippets[:4]})
            all_snippets.extend(snippets)

    unique_snippets = list(dict.fromkeys(all_snippets))
    return fontes, unique_snippets


async def gerar_descricao_por_fontes_publicas(nome_cargo: str) -> tuple[str, list[dict]]:
    fontes, snippets = await coletar_fontes_publicas(nome_cargo)
    if not snippets:
        raise RuntimeError("Nenhuma fonte publica retornou informacoes suficientes.")

    corpus = " ".join(snippets)
    terms = _keywords(f"{nome_cargo} {corpus}")
    bullets = _bullets_from_snippets(snippets, terms)
    ferramentas = [
        term
        for term in terms
        if any(marker in term for marker in ["sql", "sap", "excel", "power", "python", "linux", "windows", "aws", "azure", "vmware", "cbo", "pmp"])
    ][:10]
    habilidades = [term for term in terms if term not in ferramentas][:12]

    responsabilidades = bullets[:5] or [
        f"Planejar, executar e acompanhar atividades relacionadas a {nome_cargo}.",
        "Atuar com indicadores, processos, documentacao e melhoria continua.",
        "Interagir com equipes, liderancas, fornecedores e demais stakeholders.",
    ]
    requisitos = [
        f"Experiencia pratica em atividades associadas ao cargo de {nome_cargo}.",
        "Conhecimento dos processos, ferramentas e indicadores citados nas fontes consultadas.",
        "Capacidade de documentar rotinas, analisar problemas e propor melhorias.",
    ]
    habilidades_desejadas = list(dict.fromkeys(habilidades[:8] + GENERIC_SKILLS[:4]))

    fontes_texto = "\n".join(f"- {fonte['nome']}: {fonte['url']}" for fonte in fontes)
    palavras_chave = ", ".join(terms[:25])
    ferramentas_texto = ", ".join(ferramentas) if ferramentas else "Ferramentas especificas nao identificadas nas fontes; revisar conforme contexto da empresa."

    descricao = (
        f"Resumo do cargo:\n"
        f"{nome_cargo} e uma ocupacao estruturada a partir de fontes publicas de ocupacoes, competencias e vagas reais. "
        f"A descricao abaixo combina atividades recorrentes, requisitos observados e palavras-chave uteis para triagem.\n\n"
        f"Responsabilidades:\n"
        + "\n".join(f"- {item}" for item in responsabilidades)
        + "\n\nRequisitos obrigatorios:\n"
        + "\n".join(f"- {item}" for item in requisitos)
        + "\n\nHabilidades desejadas:\n"
        + "\n".join(f"- {item}" for item in habilidades_desejadas)
        + f"\n\nFerramentas e conhecimentos:\n- {ferramentas_texto}\n\n"
        f"Indicadores de sucesso:\n"
        f"- Qualidade e prazo das entregas associadas ao cargo.\n"
        f"- Aderencia a processos, documentacao e requisitos tecnicos/operacionais.\n"
        f"- Satisfacao de clientes internos, gestores ou stakeholders.\n"
        f"- Evolucao de indicadores de produtividade, estabilidade, custo ou eficiencia.\n\n"
        f"Palavras-chave para triagem:\n{palavras_chave}\n\n"
        f"Fontes consultadas:\n{fontes_texto}"
    )
    return descricao, fontes
