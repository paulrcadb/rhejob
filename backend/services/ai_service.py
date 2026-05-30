import logging
import re
import unicodedata
from difflib import SequenceMatcher


logger = logging.getLogger(__name__)


def gerar_descricao_fallback(nome_cargo: str) -> str:
    cargo = nome_cargo.strip().title()
    return (
        f"Responsabilidades:\n"
        f"- Executar atividades relacionadas ao cargo de {cargo} com foco em qualidade, prazos e resultados.\n"
        f"- Colaborar com equipes internas, documentar processos e acompanhar indicadores da area.\n"
        f"- Identificar oportunidades de melhoria e apoiar a tomada de decisao.\n\n"
        f"Requisitos:\n"
        f"- Experiencia previa ou conhecimentos praticos relacionados a {cargo}.\n"
        f"- Boa comunicacao, organizacao e capacidade de resolver problemas.\n"
        f"- Familiaridade com ferramentas digitais e rotinas corporativas.\n\n"
        f"Habilidades desejadas:\n"
        f"- Pensamento analitico, autonomia e aprendizado continuo.\n"
        f"- Trabalho em equipe, adaptabilidade e orientacao a resultados.\n"
        f"- Capacidade de transformar necessidades do negocio em entregas concretas."
    )


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _keywords(text: str) -> set[str]:
    stopwords = {
        "para",
        "com",
        "uma",
        "das",
        "dos",
        "que",
        "por",
        "como",
        "mais",
        "de",
        "da",
        "do",
        "em",
        "e",
        "a",
        "o",
        "as",
        "os",
        "ao",
        "aos",
        "nas",
        "nos",
        "pela",
        "pelo",
        "ser",
        "ter",
        "sua",
        "seu",
        "suas",
        "seus",
        "entre",
        "sobre",
        "area",
        "cargo",
        "descricao",
        "responsabilidades",
        "requisitos",
        "habilidades",
        "desejadas",
    }
    words = re.findall(r"[a-z]{4,}", _normalize(text))
    cleaned = set()
    for word in words:
        if word in stopwords:
            continue
        if len(word) > 5 and word.endswith(("oes", "ais", "eis")):
            word = word[:-3]
        elif len(word) > 5 and word.endswith(("os", "as", "es")):
            word = word[:-2]
        elif len(word) > 5 and word.endswith("s"):
            word = word[:-1]
        cleaned.add(word)
    return cleaned


def _expand_terms(terms: set[str]) -> set[str]:
    groups = [
        {"infraestrutura", "infra", "servidor", "servidores", "rede", "redes", "datacenter", "cloud", "nuvem", "backup", "seguranca", "firewall", "windows", "linux", "virtualizacao", "vmware", "azure", "aws"},
        {"coordenador", "coordenacao", "coordena", "lideranca", "gestao", "equipe", "supervisao", "planejamento", "indicadores", "fornecedores"},
        {"dados", "data", "sql", "python", "bi", "dashboard", "power", "analytics", "relatorio", "indicadores"},
        {"projeto", "projetos", "cronograma", "escopo", "stakeholders", "riscos", "orcamento", "entregas"},
    ]
    expanded = set(terms)
    for group in groups:
        normalized_group = {_normalize(item) for item in group}
        if expanded & normalized_group:
            expanded |= normalized_group
    return expanded


DOMAIN_GROUPS = {
    "infraestrutura_ti": {
        "infraestrutura",
        "infra",
        "servidor",
        "servidores",
        "rede",
        "redes",
        "datacenter",
        "cloud",
        "nuvem",
        "backup",
        "seguranca",
        "firewall",
        "windows",
        "linux",
        "virtualizacao",
        "vmware",
        "azure",
        "aws",
        "storage",
        "switch",
        "roteador",
        "roteadores",
        "active",
        "directory",
        "suporte",
    },
    "rh": {
        "rh",
        "humanos",
        "recursos",
        "recrutamento",
        "selecao",
        "talent",
        "acquisition",
        "headhunting",
        "entrevistas",
        "beneficios",
        "admissional",
        "rescisorio",
        "folha",
        "departamento",
        "pessoal",
    },
    "obras": {
        "obra",
        "obras",
        "engenharia",
        "cronograma",
        "medicao",
        "orcamento",
        "suprimentos",
        "insumos",
        "canteiro",
        "construcao",
    },
    "dados": {
        "dados",
        "data",
        "sql",
        "python",
        "bi",
        "dashboard",
        "analytics",
        "relatorio",
        "indicadores",
    },
}


GENERIC_MATCH_TERMS = {
    "atividade",
    "atividad",
    "carreira",
    "comunicacao",
    "conhecimento",
    "demand",
    "equipe",
    "experiencia",
    "gestao",
    "habilidade",
    "indicadores",
    "lideranca",
    "mercado",
    "necessidad",
    "organizacao",
    "orientacao",
    "pesso",
    "planejamento",
    "process",
    "profissional",
    "projet",
    "relacionad",
    "resultad",
    "rotin",
    "tecnic",
    "tecnico",
    "trabalho",
}


def _group_matches(terms: set[str]) -> dict[str, set[str]]:
    return {name: sorted_terms for name, group in DOMAIN_GROUPS.items() if (sorted_terms := terms & group)}


def _primary_domain(job_terms: set[str]) -> str | None:
    matches = _group_matches(job_terms)
    if not matches:
        return None
    return max(matches.items(), key=lambda item: len(item[1]))[0]


def _extract_requirements(descricao: str, nome_cargo: str) -> list[str]:
    lines = [line.strip(" -•\t") for line in descricao.splitlines()]
    requirements = [
        line
        for line in lines
        if 18 <= len(line) <= 180
        and not line.lower().startswith(("fontes", "palavras-chave", "resumo do cargo"))
    ]
    if requirements:
        return requirements[:8]
    terms = sorted(_keywords(f"{nome_cargo} {descricao}") - GENERIC_MATCH_TERMS)
    return [f"Evidencia relacionada a {term}" for term in terms[:8]]


def _evidence_for_requirement(requirement: str, curriculo: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+|\n+", curriculo)
    req_terms = _keywords(requirement) - GENERIC_MATCH_TERMS
    best_sentence = ""
    best_score = 0
    for sentence in sentences:
        if len(sentence.strip()) < 30:
            continue
        score = len(req_terms & _keywords(sentence))
        if score > best_score:
            best_sentence = sentence.strip()
            best_score = score
    if best_score == 0:
        return "Nao encontrada evidencia direta no curriculo."
    return best_sentence[:260]


def _fit_label(requirement: str, evidence: str) -> str:
    if evidence.startswith("Nao encontrada"):
        return "Nao evidenciado"
    overlap = len((_keywords(requirement) - GENERIC_MATCH_TERMS) & _keywords(evidence))
    if overlap >= 3:
        return "Aderente"
    if overlap >= 1:
        return "Parcial"
    return "Nao evidenciado"


def gerar_comparativo_local(curriculo: str, descricao: str, nome_cargo: str) -> list[dict[str, str]]:
    rows = []
    for requirement in _extract_requirements(descricao, nome_cargo)[:6]:
        evidence = _evidence_for_requirement(requirement, curriculo)
        rows.append(
            {
                "requisito_vaga": requirement,
                "evidencia_curriculo": evidence,
                "leitura": _fit_label(requirement, evidence),
            }
        )
    return rows


def gerar_conclusao_local(
    nome_cargo: str,
    score: int,
    comparativo: list[dict[str, str]],
    pontos_fortes: list[str],
    gaps: list[str],
    termos_encontrados: list[str],
) -> str:
    aderentes = [item for item in comparativo if item.get("leitura") == "Aderente"]
    parciais = [item for item in comparativo if item.get("leitura") == "Parcial"]
    nao_evidenciados = [item for item in comparativo if item.get("leitura") == "Nao evidenciado"]
    termos = ", ".join(termos_encontrados[:8]) if termos_encontrados else "poucos termos especificos"

    if score >= 75:
        avaliacao = "O curriculo apresenta boa aderencia geral"
    elif score >= 45:
        avaliacao = "O curriculo apresenta aderencia parcial"
    else:
        avaliacao = "O curriculo apresenta baixa aderencia"

    destaque = pontos_fortes[0] if pontos_fortes else "Foram avaliadas as evidencias textuais do curriculo frente aos requisitos da vaga."
    gap = gaps[0] if gaps else "Nao foram identificados gaps criticos pelo avaliador local."

    return (
        f"{avaliacao} para a vaga de {nome_cargo}, com score de {score}%. "
        f"A leitura do de/para encontrou {len(aderentes)} requisito(s) aderente(s), "
        f"{len(parciais)} parcialmente atendido(s) e {len(nao_evidenciados)} sem evidencia direta no curriculo. "
        f"Entre os principais sinais encontrados estao: {termos}. {destaque} "
        f"Como ponto de atencao, {gap} "
        f"Em conclusao, a recomendacao e usar esta analise como apoio inicial de triagem, validando manualmente "
        f"as experiencias mais relevantes e pedindo exemplos praticos em entrevista quando houver aderencia parcial."
    )


def analisar_fallback(curriculo: str, descricao: str, nome_cargo: str = "") -> dict:
    vaga_kw = _keywords(f"{nome_cargo} {descricao}") - GENERIC_MATCH_TERMS
    cv_kw = _keywords(curriculo)
    intersecao = sorted(vaga_kw & cv_kw)
    faltantes = sorted(vaga_kw - cv_kw)
    cobertura = len(intersecao) / max(len(vaga_kw), 1)
    titulo_kw = _keywords(nome_cargo)
    titulo_match = min(1, len(titulo_kw & cv_kw) / max(len(titulo_kw), 1))
    dominio = _primary_domain(_keywords(f"{nome_cargo} {descricao}"))
    dominio_vaga = DOMAIN_GROUPS.get(dominio or "", set())
    dominio_cv = cv_kw & dominio_vaga
    dominio_match = len(dominio_cv) / max(min(len(dominio_vaga), 8), 1) if dominio_vaga else 0
    cv_domains = _group_matches(cv_kw)
    conflito_rh = dominio == "infraestrutura_ti" and len(cv_domains.get("rh", set())) >= 4 and len(dominio_cv) < 4
    similaridade = SequenceMatcher(None, _normalize(curriculo[:6000]), _normalize(descricao[:6000])).ratio()
    score = round((cobertura * 35) + (titulo_match * 20) + (dominio_match * 35) + (similaridade * 10))
    if dominio and len(dominio_cv) < 2:
        score = min(score, 35)
    if conflito_rh:
        score = min(score, 25)
    score = max(0, min(100, score))

    pontos_fortes = [
        f"Evidencia termos importantes da vaga: {', '.join(intersecao[:8]) or 'poucos termos diretos encontrados'}",
        f"Evidencia tecnica do dominio: {', '.join(sorted(dominio_cv)[:8]) or 'nao encontrada'}",
        "Curriculo processado localmente e comparado com a descricao cadastrada.",
    ]
    gaps = [
        f"Pouca evidencia para: {', '.join(faltantes[:8]) or 'nenhum gap critico identificado automaticamente'}",
        "Termos genericos de gestao, comunicacao e processos nao sao suficientes para alta aderencia.",
        "A analise local agora exige evidencias diretas do dominio da vaga.",
    ]
    sugestoes = [
        "Adicionar resultados mensuraveis e exemplos praticos ligados ao cargo.",
        "Destacar ferramentas, metodologias e responsabilidades citadas na vaga.",
        "Reorganizar o resumo profissional para refletir os requisitos principais.",
    ]
    termos_encontrados = intersecao[:20]
    comparativo = gerar_comparativo_local(curriculo, descricao, nome_cargo)

    return {
        "score": score,
        "pontos_fortes": pontos_fortes,
        "gaps": gaps,
        "sugestoes": sugestoes,
        "resumo": (
            "Analise local gerada por cobertura de termos especificos, afinidade com o titulo, "
            "evidencia direta do dominio da vaga e similaridade textual."
        ),
        "termos_encontrados": termos_encontrados,
        "origem_analise": "fallback_local",
        "comparativo": comparativo,
        "conclusao": gerar_conclusao_local(
            nome_cargo,
            score,
            comparativo,
            pontos_fortes,
            gaps,
            termos_encontrados,
        ),
    }


async def analisar_curriculo_local(curriculo: str, descricao: str, nome_cargo: str) -> dict:
    return analisar_fallback(curriculo, descricao, nome_cargo)
