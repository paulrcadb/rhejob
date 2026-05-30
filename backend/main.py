import logging
import os
import secrets
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

try:
    from .database import (
        create_analise_log,
        create_cargo,
        create_cargo_busca,
        create_usuario,
        delete_all_analise_logs,
        delete_analise_log,
        delete_cargo,
        delete_usuario,
        find_cargo_base,
        get_cargo,
        get_usuario,
        get_usuario_by_email,
        import_cargos_base,
        init_db,
        list_analise_logs,
        list_cargo_buscas,
        list_cargos,
        list_usuarios,
        reset_usuario_senha,
        set_missing_user_passwords,
        touch_cargo,
    )
    from .models import (
        AnaliseLogResponse,
        AnaliseResponse,
        CargoCreate,
        CargoResponse,
        CargoSearch,
        CargoSearchResponse,
        CargoUpdateResponse,
        LoginRequest,
        UsuarioCreate,
        UsuarioResetSenha,
        UsuarioResponse,
    )
    from .services.ai_service import analisar_curriculo_local, gerar_descricao_fallback
    from .services.auth_service import hash_password, verify_password
    from .services.cargo_base import carregar_base_gestao_obras, carregar_base_operacional
    from .services.parser import extrair_texto
    from .services.scraper import buscar_descricao_web
    from .services.source_service import gerar_descricao_por_fontes_publicas
except ImportError:
    from database import (
        create_analise_log,
        create_cargo,
        create_cargo_busca,
        create_usuario,
        delete_all_analise_logs,
        delete_analise_log,
        delete_cargo,
        delete_usuario,
        find_cargo_base,
        get_cargo,
        get_usuario,
        get_usuario_by_email,
        import_cargos_base,
        init_db,
        list_analise_logs,
        list_cargo_buscas,
        list_cargos,
        list_usuarios,
        reset_usuario_senha,
        set_missing_user_passwords,
        touch_cargo,
    )
    from models import (
        AnaliseLogResponse,
        AnaliseResponse,
        CargoCreate,
        CargoResponse,
        CargoSearch,
        CargoSearchResponse,
        CargoUpdateResponse,
        LoginRequest,
        UsuarioCreate,
        UsuarioResetSenha,
        UsuarioResponse,
    )
    from services.ai_service import analisar_curriculo_local, gerar_descricao_fallback
    from services.auth_service import hash_password, verify_password
    from services.cargo_base import carregar_base_gestao_obras, carregar_base_operacional
    from services.parser import extrair_texto
    from services.scraper import buscar_descricao_web
    from services.source_service import gerar_descricao_por_fontes_publicas


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_DIR = BASE_DIR / "frontend"
UPLOADS_DIR = BASE_DIR / "uploads"
LOGS_DIR = BASE_DIR / "logs"
BASE_CARGOS_PATH = BASE_DIR / "data" / "base_operacional_construcao_civil.txt"
BASE_GESTAO_OBRAS_PATH = BASE_DIR / "data" / "base_gestao_obras_projetos_construcao_civil.txt"
UPLOADS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

APP_BASE_PATH = os.getenv("APP_BASE_PATH", "/app").rstrip("/") or "/app"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

app = FastAPI(title="Job Analyzer", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

SESSIONS: dict[str, dict] = {}
PUBLIC_PATHS = {
    "/",
    f"{APP_BASE_PATH}",
    f"{APP_BASE_PATH}/",
    f"{APP_BASE_PATH}/index.html",
    f"{APP_BASE_PATH}/login.html",
    "/login.html",
    "/login",
    "/config/ia",
    "/docs",
    "/openapi.json",
    "/redoc",
}
FRONTEND_ASSET_SUFFIXES = {
    ".css",
    ".js",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
}


def _is_frontend_asset(path: str) -> bool:
    return path.startswith(f"{APP_BASE_PATH}/") and Path(path).suffix.lower() in FRONTEND_ASSET_SUFFIXES


def _auth_required(request: Request) -> bool:
    server = request.scope.get("server") or ("", 0)
    port = server[1] if len(server) > 1 else 0
    if port == 8001:
        return False
    path = request.url.path
    if path.startswith("/static") or _is_frontend_asset(path) or path in PUBLIC_PATHS:
        return False
    return os.getenv("AUTH_REQUIRED", "true").lower() != "false"


def _current_user(request: Request) -> dict | None:
    token = request.cookies.get("rh_session")
    return SESSIONS.get(token or "")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if _auth_required(request) and not _current_user(request):
        path = request.url.path
        wants_html = path.endswith(".html") or path in {"/", f"{APP_BASE_PATH}", f"{APP_BASE_PATH}/"}
        if wants_html:
            login_path = f"{APP_BASE_PATH}/login.html" if path.startswith(APP_BASE_PATH) else "/login.html"
            return RedirectResponse(login_path, status_code=302)
        return JSONResponse({"detail": "Autenticacao obrigatoria."}, status_code=401)
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    await init_db()
    cargos_base = carregar_base_operacional(BASE_CARGOS_PATH)
    if cargos_base:
        total_base = await import_cargos_base(cargos_base)
        logger.info("Base Operacional Construcao Civil importada: %s cargo(s).", total_base)
    cargos_gestao_obras = carregar_base_gestao_obras(BASE_GESTAO_OBRAS_PATH)
    if cargos_gestao_obras:
        total_gestao_obras = await import_cargos_base(cargos_gestao_obras)
        logger.info("Base Gestao de Obras e Projetos importada: %s cargo(s).", total_gestao_obras)
    existing_users = await list_usuarios()
    if not existing_users:
        await create_usuario("Administrador RH", "admin@rhjob.local", "administrador", hash_password("admin123"))
        logger.info("Usuario administrador inicial criado.")
    updated_users = await set_missing_user_passwords(hash_password("admin123"))
    if updated_users:
        logger.info("Senha temporaria definida para %s usuario(s) sem senha.", updated_users)
    logger.info("Banco SQLite inicializado via DATABASE_URL=%s", os.getenv("DATABASE_URL", "sqlite:///data/database.db"))


@app.get("/")
async def healthcheck() -> dict:
    return {
        "status": "online",
        "service": "job-analyzer",
    }


@app.get(f"{APP_BASE_PATH}")
@app.get(f"{APP_BASE_PATH}/")
@app.get(f"{APP_BASE_PATH}/index.html")
async def app_home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/login.html")
@app.get(f"{APP_BASE_PATH}/login.html")
async def login_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/cargos.html")
@app.get(f"{APP_BASE_PATH}/cargos.html")
async def cargos_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "cargos.html")


@app.get("/analise.html")
@app.get(f"{APP_BASE_PATH}/analise.html")
async def analise_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "analise.html")


@app.get("/admin.html")
@app.get(f"{APP_BASE_PATH}/admin.html")
async def admin_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "admin.html")


app.mount(APP_BASE_PATH, StaticFiles(directory=FRONTEND_DIR), name="app")


async def _gerar_descricao_cargo(nome: str) -> tuple[str, str]:
    contexto_web = await buscar_descricao_web(nome)
    if contexto_web:
        return contexto_web, "web"
    descricao = gerar_descricao_fallback(nome)
    origem = "fallback_local"
    return descricao, origem


async def _gerar_descricao_profunda(nome: str) -> tuple[str, str]:
    descricao, _fontes = await gerar_descricao_por_fontes_publicas(nome)
    return descricao, "fontes_publicas"


@app.get("/config/ia")
async def status_ia() -> dict:
    return {
        "integracao_externa": False,
        "modelo": "local_heuristico",
        "modo": "local_fontes_publicas",
    }


@app.post("/login")
async def login(payload: LoginRequest) -> dict:
    usuario = await get_usuario_by_email(payload.email)
    if not usuario or not verify_password(payload.senha, usuario.get("senha_hash")):
        raise HTTPException(status_code=401, detail="E-mail ou senha invalidos.")

    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "perfil": usuario["perfil"],
    }
    response = JSONResponse({"ok": True, "usuario": SESSIONS[token]})
    response.set_cookie(
        "rh_session",
        token,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )
    return response


@app.post("/logout")
async def logout(request: Request) -> dict:
    token = request.cookies.get("rh_session")
    if token:
        SESSIONS.pop(token, None)
    response = JSONResponse({"ok": True})
    response.delete_cookie("rh_session")
    return response


@app.get("/me")
async def me(request: Request) -> dict:
    return {"usuario": _current_user(request)}


@app.post("/cargo/buscar", response_model=CargoSearchResponse)
async def buscar_cargo(payload: CargoSearch) -> dict:
    nome = payload.nome_cargo.strip()
    cargo_base = await find_cargo_base(nome)
    if cargo_base:
        cargo = await touch_cargo(cargo_base["id"]) or cargo_base
        cargo["origem"] = cargo.get("origem_base") or "base_local"
        busca = await create_cargo_busca(cargo["id"], nome, cargo["nome_cargo"], cargo["origem"])
        cargo["busca_id"] = busca["id"]
        cargo["data_busca"] = busca["data_busca"]
        logger.info("Cargo encontrado na base local: %s", cargo["nome_cargo"])
        return cargo

    descricao, origem = await _gerar_descricao_cargo(nome)
    cargo = await create_cargo(nome, descricao)
    busca = await create_cargo_busca(cargo["id"], nome, cargo["nome_cargo"], origem)
    logger.info("Descricao buscada para cargo: %s origem=%s", nome, origem)
    cargo["origem"] = origem
    cargo["busca_id"] = busca["id"]
    cargo["data_busca"] = busca["data_busca"]
    return cargo


@app.post("/cargo", response_model=CargoResponse)
async def cadastrar_cargo(payload: CargoCreate) -> dict:
    nome = payload.nome_cargo.strip()
    descricao = payload.descricao.strip()
    cargo = await create_cargo(nome, descricao)
    logger.info("Cargo salvo/atualizado: %s", nome)
    return cargo


@app.post("/cargo/gerar-e-salvar", response_model=CargoResponse)
async def gerar_e_salvar_cargo(payload: CargoSearch) -> dict:
    nome = payload.nome_cargo.strip()
    descricao, _origem = await _gerar_descricao_cargo(nome)

    cargo = await create_cargo(nome, descricao)
    logger.info("Busca de cargo salva/atualizada: %s", nome)
    return cargo


@app.post("/cargo/{cargo_id}/atualizar-profundo", response_model=CargoUpdateResponse)
async def atualizar_cargo_profundo(cargo_id: int) -> dict:
    cargo_atual = await get_cargo(cargo_id)
    if not cargo_atual:
        raise HTTPException(status_code=404, detail="Cargo nao encontrado.")

    try:
        descricao, origem = await _gerar_descricao_profunda(cargo_atual["nome_cargo"])
    except RuntimeError as exc:
        logger.warning("Atualizacao profunda abortada: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    cargo = await create_cargo(cargo_atual["nome_cargo"], descricao)
    logger.info("Cargo atualizado com busca profunda: id=%s origem=%s", cargo_id, origem)
    cargo["origem"] = origem
    return cargo


@app.get("/cargos", response_model=list[CargoResponse])
async def listar_cargos() -> list[dict]:
    return await list_cargos()


@app.get("/cargos/buscas")
async def listar_buscas_cargos() -> list[dict]:
    return await list_cargo_buscas()


@app.delete("/cargo/{cargo_id}")
async def excluir_cargo(cargo_id: int) -> dict:
    cargo = await delete_cargo(cargo_id)
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo nao encontrado.")
    logger.info("Cargo excluido da base de consulta: id=%s nome=%s", cargo_id, cargo["nome_cargo"])
    return {"ok": True, "cargo": cargo}


@app.post("/usuarios", response_model=UsuarioResponse)
async def cadastrar_usuario(payload: UsuarioCreate) -> dict:
    usuario = await create_usuario(payload.nome, payload.email, payload.perfil, hash_password(payload.senha))
    logger.info("Usuario cadastrado/atualizado: %s", payload.email)
    return usuario


@app.get("/usuarios", response_model=list[UsuarioResponse])
async def listar_usuarios() -> list[dict]:
    return await list_usuarios()


@app.delete("/usuarios/{usuario_id}")
async def excluir_usuario(usuario_id: int) -> dict:
    await delete_usuario(usuario_id)
    logger.info("Usuario excluido: id=%s", usuario_id)
    return {"ok": True}


@app.post("/usuarios/{usuario_id}/reset-senha", response_model=UsuarioResponse)
async def resetar_senha_usuario(usuario_id: int, payload: UsuarioResetSenha) -> dict:
    usuario = await get_usuario(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    atualizado = await reset_usuario_senha(usuario_id, hash_password(payload.senha))
    logger.info("Senha resetada para usuario id=%s", usuario_id)
    return atualizado


@app.get("/logs/analises", response_model=list[AnaliseLogResponse])
async def listar_logs_analise() -> list[dict]:
    return await list_analise_logs()


@app.delete("/logs/analises/{log_id}")
async def excluir_log_analise(log_id: int) -> dict:
    await delete_analise_log(log_id)
    logger.info("Log de analise excluido: id=%s", log_id)
    return {"ok": True}


@app.delete("/logs/analises")
async def excluir_todos_logs_analise() -> dict:
    await delete_all_analise_logs()
    logger.info("Todos os logs de analise foram excluidos")
    return {"ok": True}


@app.post("/analyze", response_model=AnaliseResponse)
@app.post("/analisar", response_model=AnaliseResponse)
async def analisar(cargo_id: int = Form(...), arquivo: UploadFile = File(...)) -> dict:
    cargo = await get_cargo(cargo_id)
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo nao encontrado.")

    suffix = Path(arquivo.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF ou DOCX.")

    destination = UPLOADS_DIR / f"{uuid4().hex}{suffix}"
    try:
        content = await arquivo.read()
        destination.write_bytes(content)
        texto_curriculo = extrair_texto(destination)
    except Exception as exc:
        logger.exception("Falha ao processar curriculo")
        raise HTTPException(status_code=400, detail=f"Nao foi possivel ler o arquivo: {exc}") from exc

    if not texto_curriculo:
        raise HTTPException(
            status_code=400,
            detail=(
                "O arquivo foi carregado, mas nao possui texto extraivel. "
                "Isso costuma acontecer com PDF escaneado ou salvo como imagem. "
                "Envie um PDF com texto selecionavel ou um DOCX."
            ),
        )

    resultado = await analisar_curriculo_local(
        texto_curriculo,
        cargo["descricao"],
        cargo["nome_cargo"],
    )
    resultado["arquivo_nome"] = arquivo.filename
    resultado["arquivo_tamanho_bytes"] = len(content)
    resultado["caracteres_extraidos"] = len(texto_curriculo)
    resultado["preview_curriculo"] = texto_curriculo[:700]
    resultado["origem_analise"] = resultado.get("origem_analise", "fallback_local")
    await create_analise_log(
        cargo_id=cargo_id,
        nome_cargo=cargo["nome_cargo"],
        arquivo_nome=arquivo.filename or "curriculo",
        arquivo_tamanho_bytes=len(content),
        caracteres_extraidos=len(texto_curriculo),
        score=int(resultado.get("score", 0)),
        resumo=str(resultado.get("resumo", ""))[:1200],
        origem_analise=str(resultado.get("origem_analise", "")),
    )
    logger.info("Analise concluida para cargo_id=%s arquivo=%s", cargo_id, arquivo.filename)
    return resultado
