from pydantic import BaseModel, Field


class CargoCreate(BaseModel):
    nome_cargo: str = Field(..., min_length=2, max_length=120)
    descricao: str = Field(..., min_length=20)


class CargoSearch(BaseModel):
    nome_cargo: str = Field(..., min_length=2, max_length=120)


class CargoSearchResponse(BaseModel):
    id: int
    busca_id: int | None = None
    nome_cargo: str
    descricao: str
    origem: str
    data_criacao: str
    data_busca: str | None = None
    categoria: str | None = None
    codigo_base: str | None = None
    cbo_ref: str | None = None
    aliases: str | None = None
    familia: str | None = None
    senioridade: str | None = None
    salario: str | None = None
    variacao_regional: str | None = None
    keywords: str | None = None
    origem_base: str | None = None


class CargoResponse(BaseModel):
    id: int
    nome_cargo: str
    descricao: str
    data_criacao: str
    categoria: str | None = None
    codigo_base: str | None = None
    cbo_ref: str | None = None
    aliases: str | None = None
    familia: str | None = None
    senioridade: str | None = None
    salario: str | None = None
    variacao_regional: str | None = None
    keywords: str | None = None
    origem_base: str | None = None


class CargoUpdateResponse(CargoResponse):
    origem: str


class AnaliseResponse(BaseModel):
    score: int
    pontos_fortes: list[str]
    gaps: list[str]
    sugestoes: list[str]
    resumo: str
    arquivo_nome: str | None = None
    arquivo_tamanho_bytes: int | None = None
    caracteres_extraidos: int | None = None
    preview_curriculo: str | None = None
    termos_encontrados: list[str] = Field(default_factory=list)
    origem_analise: str | None = None
    comparativo: list[dict[str, str]] = Field(default_factory=list)
    conclusao: str | None = None


class UsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=180)
    perfil: str = Field("recrutador", min_length=2, max_length=60)
    senha: str = Field(..., min_length=6, max_length=120)


class UsuarioResetSenha(BaseModel):
    senha: str = Field(..., min_length=6, max_length=120)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=180)
    senha: str = Field(..., min_length=1, max_length=120)


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    perfil: str
    data_criacao: str


class AnaliseLogResponse(BaseModel):
    id: int
    cargo_id: int | None
    nome_cargo: str
    arquivo_nome: str
    arquivo_tamanho_bytes: int
    caracteres_extraidos: int
    score: int
    resumo: str | None
    origem_analise: str | None = None
    data_analise: str
