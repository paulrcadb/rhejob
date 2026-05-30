import os
import shutil
from pathlib import Path
from typing import Any

import aiosqlite
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _resolve_sqlite_path() -> Path:
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/database.db")
    if database_url.startswith("sqlite:///"):
        database_url = database_url.removeprefix("sqlite:///")

    db_path = Path(database_url)
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)

    legacy_db_path = BASE_DIR / "database.db"
    if not db_path.exists() and legacy_db_path.exists() and legacy_db_path != db_path:
        shutil.copy2(legacy_db_path, db_path)

    return db_path


DB_PATH = _resolve_sqlite_path()


CREATE_CARGOS_TABLE = """
CREATE TABLE IF NOT EXISTS cargos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_cargo TEXT NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    categoria TEXT,
    codigo_base TEXT,
    cbo_ref TEXT,
    aliases TEXT,
    familia TEXT,
    senioridade TEXT,
    salario TEXT,
    variacao_regional TEXT,
    keywords TEXT,
    origem_base TEXT,
    data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_USUARIOS_TABLE = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    perfil TEXT NOT NULL DEFAULT 'recrutador',
    senha_hash TEXT,
    data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ANALISE_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS analise_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cargo_id INTEGER,
    nome_cargo TEXT NOT NULL,
    arquivo_nome TEXT NOT NULL,
    arquivo_tamanho_bytes INTEGER NOT NULL,
    caracteres_extraidos INTEGER NOT NULL,
    score INTEGER NOT NULL,
    resumo TEXT,
    origem_analise TEXT,
    data_analise TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cargo_id) REFERENCES cargos (id)
);
"""

CREATE_CARGOS_EXCLUIDOS_TABLE = """
CREATE TABLE IF NOT EXISTS cargos_excluidos_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_cargo TEXT NOT NULL UNIQUE,
    codigo_base TEXT,
    origem_base TEXT,
    data_exclusao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_CARGO_BUSCAS_TABLE = """
CREATE TABLE IF NOT EXISTS cargo_buscas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cargo_id INTEGER NOT NULL,
    termo_busca TEXT NOT NULL,
    nome_cargo TEXT NOT NULL,
    origem TEXT,
    data_busca TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cargo_id) REFERENCES cargos (id)
);
"""

ADD_ANALISE_LOG_ORIGEM = "ALTER TABLE analise_logs ADD COLUMN origem_analise TEXT"
ADD_USUARIO_SENHA_HASH = "ALTER TABLE usuarios ADD COLUMN senha_hash TEXT"
ADD_CARGO_COLUMNS = [
    ("categoria", "ALTER TABLE cargos ADD COLUMN categoria TEXT"),
    ("codigo_base", "ALTER TABLE cargos ADD COLUMN codigo_base TEXT"),
    ("cbo_ref", "ALTER TABLE cargos ADD COLUMN cbo_ref TEXT"),
    ("aliases", "ALTER TABLE cargos ADD COLUMN aliases TEXT"),
    ("familia", "ALTER TABLE cargos ADD COLUMN familia TEXT"),
    ("senioridade", "ALTER TABLE cargos ADD COLUMN senioridade TEXT"),
    ("salario", "ALTER TABLE cargos ADD COLUMN salario TEXT"),
    ("variacao_regional", "ALTER TABLE cargos ADD COLUMN variacao_regional TEXT"),
    ("keywords", "ALTER TABLE cargos ADD COLUMN keywords TEXT"),
    ("origem_base", "ALTER TABLE cargos ADD COLUMN origem_base TEXT"),
]

CARGO_SELECT = """
SELECT id, nome_cargo, descricao, categoria, codigo_base, cbo_ref, aliases, familia,
       senioridade, salario, variacao_regional, keywords, origem_base, data_criacao
FROM cargos
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_CARGOS_TABLE)
        await db.execute(CREATE_USUARIOS_TABLE)
        await db.execute(CREATE_ANALISE_LOGS_TABLE)
        await db.execute(CREATE_CARGOS_EXCLUIDOS_TABLE)
        await db.execute(CREATE_CARGO_BUSCAS_TABLE)
        for _column, statement in ADD_CARGO_COLUMNS:
            try:
                await db.execute(statement)
            except aiosqlite.OperationalError:
                pass
        try:
            await db.execute(ADD_ANALISE_LOG_ORIGEM)
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute(ADD_USUARIO_SENHA_HASH)
        except aiosqlite.OperationalError:
            pass
        await db.commit()


async def create_cargo(
    nome_cargo: str,
    descricao: str,
    categoria: str | None = None,
    codigo_base: str | None = None,
    cbo_ref: str | None = None,
    aliases: str | None = None,
    familia: str | None = None,
    senioridade: str | None = None,
    salario: str | None = None,
    variacao_regional: str | None = None,
    keywords: str | None = None,
    origem_base: str | None = None,
    atualizar_data: bool = True,
) -> dict[str, Any]:
    data_update = "data_criacao = CURRENT_TIMESTAMP," if atualizar_data else ""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""
            INSERT INTO cargos (
                nome_cargo, descricao, categoria, codigo_base, cbo_ref, aliases,
                familia, senioridade, salario, variacao_regional, keywords, origem_base
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(nome_cargo) DO UPDATE SET
                descricao = excluded.descricao,
                {data_update}
                categoria = COALESCE(excluded.categoria, cargos.categoria),
                codigo_base = COALESCE(excluded.codigo_base, cargos.codigo_base),
                cbo_ref = COALESCE(excluded.cbo_ref, cargos.cbo_ref),
                aliases = COALESCE(excluded.aliases, cargos.aliases),
                familia = COALESCE(excluded.familia, cargos.familia),
                senioridade = COALESCE(excluded.senioridade, cargos.senioridade),
                salario = COALESCE(excluded.salario, cargos.salario),
                variacao_regional = COALESCE(excluded.variacao_regional, cargos.variacao_regional),
                keywords = COALESCE(excluded.keywords, cargos.keywords),
                origem_base = COALESCE(excluded.origem_base, cargos.origem_base)
            RETURNING id, nome_cargo, descricao, categoria, codigo_base, cbo_ref, aliases,
                      familia, senioridade, salario, variacao_regional, keywords, origem_base,
                      data_criacao
            """,
            (
                nome_cargo.strip(),
                descricao.strip(),
                categoria,
                codigo_base,
                cbo_ref,
                aliases,
                familia,
                senioridade,
                salario,
                variacao_regional,
                keywords,
                origem_base,
            ),
        )
        row = await cursor.fetchone()
        await db.commit()
        return dict(row)


async def upsert_cargo_base(cargo: dict[str, Any], atualizar_data: bool = False) -> dict[str, Any]:
    return await create_cargo(
        cargo["nome_cargo"],
        cargo["descricao"],
        categoria=cargo.get("categoria"),
        codigo_base=cargo.get("codigo_base"),
        cbo_ref=cargo.get("cbo_ref"),
        aliases=cargo.get("aliases"),
        familia=cargo.get("familia"),
        senioridade=cargo.get("senioridade"),
        salario=cargo.get("salario"),
        variacao_regional=cargo.get("variacao_regional"),
        keywords=cargo.get("keywords"),
        origem_base=cargo.get("origem_base"),
        atualizar_data=atualizar_data,
    )


async def import_cargos_base(cargos: list[dict[str, Any]]) -> int:
    total = 0
    excluidos = await list_cargos_excluidos_base()
    for cargo in cargos:
        if cargo["nome_cargo"].strip().lower() in excluidos:
            continue
        await upsert_cargo_base(cargo, atualizar_data=False)
        total += 1
    return total


async def list_cargos_excluidos_base() -> set[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT lower(nome_cargo) FROM cargos_excluidos_base")
        rows = await cursor.fetchall()
        return {row[0] for row in rows}


async def list_cargos() -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""
            {CARGO_SELECT}
            ORDER BY
                CASE WHEN categoria IN ('Operacional Construção Civil', 'Operacional Construcao Civil') THEN 0 ELSE 1 END,
                familia COLLATE NOCASE,
                nome_cargo COLLATE NOCASE
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_cargo(cargo_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"{CARGO_SELECT} WHERE id = ?",
            (cargo_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def find_cargo_base(query: str) -> dict[str, Any] | None:
    termo = f"%{query.strip().lower()}%"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""
            {CARGO_SELECT}
            WHERE origem_base IS NOT NULL
              AND (
                lower(nome_cargo) LIKE ?
                OR lower(COALESCE(aliases, '')) LIKE ?
                OR lower(COALESCE(keywords, '')) LIKE ?
                OR lower(COALESCE(familia, '')) LIKE ?
              )
            ORDER BY
                CASE WHEN lower(nome_cargo) = lower(?) THEN 0 ELSE 1 END,
                nome_cargo COLLATE NOCASE
            LIMIT 1
            """,
            (termo, termo, termo, termo, query.strip()),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def touch_cargo(cargo_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""
            UPDATE cargos
            SET data_criacao = CURRENT_TIMESTAMP
            WHERE id = ?
            RETURNING id, nome_cargo, descricao, categoria, codigo_base, cbo_ref, aliases,
                      familia, senioridade, salario, variacao_regional, keywords, origem_base,
                      data_criacao
            """,
            (cargo_id,),
        )
        row = await cursor.fetchone()
        await db.commit()
        return dict(row) if row else None


async def create_cargo_busca(cargo_id: int, termo_busca: str, nome_cargo: str, origem: str) -> dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            INSERT INTO cargo_buscas (cargo_id, termo_busca, nome_cargo, origem)
            VALUES (?, ?, ?, ?)
            RETURNING id, cargo_id, termo_busca, nome_cargo, origem, data_busca
            """,
            (cargo_id, termo_busca.strip(), nome_cargo.strip(), origem),
        )
        row = await cursor.fetchone()
        await db.commit()
        return dict(row)


async def list_cargo_buscas(limit: int = 10) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""
            SELECT
                cb.id AS busca_id,
                cb.termo_busca,
                cb.origem AS origem_busca,
                cb.data_busca,
                c.id,
                c.nome_cargo,
                c.descricao,
                c.categoria,
                c.codigo_base,
                c.cbo_ref,
                c.aliases,
                c.familia,
                c.senioridade,
                c.salario,
                c.variacao_regional,
                c.keywords,
                c.origem_base,
                c.data_criacao
            FROM cargo_buscas cb
            JOIN cargos c ON c.id = cb.cargo_id
            ORDER BY cb.data_busca DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_cargo(cargo_id: int) -> dict[str, Any] | None:
    cargo = await get_cargo(cargo_id)
    if not cargo:
        return None

    async with aiosqlite.connect(DB_PATH) as db:
        if cargo.get("origem_base"):
            await db.execute(
                """
                INSERT INTO cargos_excluidos_base (nome_cargo, codigo_base, origem_base)
                VALUES (?, ?, ?)
                ON CONFLICT(nome_cargo) DO UPDATE SET
                    codigo_base = excluded.codigo_base,
                    origem_base = excluded.origem_base,
                    data_exclusao = CURRENT_TIMESTAMP
                """,
                (cargo["nome_cargo"], cargo.get("codigo_base"), cargo.get("origem_base")),
            )
        await db.execute("DELETE FROM cargo_buscas WHERE cargo_id = ?", (cargo_id,))
        await db.execute("DELETE FROM cargos WHERE id = ?", (cargo_id,))
        await db.commit()
    return cargo


async def create_usuario(nome: str, email: str, perfil: str, senha_hash: str) -> dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            INSERT INTO usuarios (nome, email, perfil, senha_hash)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                nome = excluded.nome,
                perfil = excluded.perfil,
                senha_hash = excluded.senha_hash
            RETURNING id, nome, email, perfil, data_criacao
            """,
            (nome.strip(), email.strip().lower(), perfil.strip() or "recrutador", senha_hash),
        )
        row = await cursor.fetchone()
        await db.commit()
        return dict(row)


async def list_usuarios() -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, nome, email, perfil, data_criacao FROM usuarios ORDER BY data_criacao DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_usuario_by_email(email: str) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, nome, email, perfil, senha_hash, data_criacao FROM usuarios WHERE email = ?",
            (email.strip().lower(),),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_usuario(usuario_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, nome, email, perfil, senha_hash, data_criacao FROM usuarios WHERE id = ?",
            (usuario_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def reset_usuario_senha(usuario_id: int, senha_hash: str) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?
            WHERE id = ?
            RETURNING id, nome, email, perfil, data_criacao
            """,
            (senha_hash, usuario_id),
        )
        row = await cursor.fetchone()
        await db.commit()
        return dict(row) if row else None


async def set_missing_user_passwords(senha_hash: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE usuarios SET senha_hash = ? WHERE senha_hash IS NULL OR senha_hash = ''",
            (senha_hash,),
        )
        await db.commit()
        return cursor.rowcount or 0


async def delete_usuario(usuario_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        await db.commit()


async def create_analise_log(
    cargo_id: int,
    nome_cargo: str,
    arquivo_nome: str,
    arquivo_tamanho_bytes: int,
    caracteres_extraidos: int,
    score: int,
    resumo: str,
    origem_analise: str,
) -> dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            INSERT INTO analise_logs (
                cargo_id, nome_cargo, arquivo_nome, arquivo_tamanho_bytes,
                caracteres_extraidos, score, resumo, origem_analise
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id, cargo_id, nome_cargo, arquivo_nome, arquivo_tamanho_bytes,
                      caracteres_extraidos, score, resumo, origem_analise, data_analise
            """,
            (
                cargo_id,
                nome_cargo,
                arquivo_nome,
                arquivo_tamanho_bytes,
                caracteres_extraidos,
                score,
                resumo,
                origem_analise,
            ),
        )
        row = await cursor.fetchone()
        await db.commit()
        return dict(row)


async def list_analise_logs() -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, cargo_id, nome_cargo, arquivo_nome, arquivo_tamanho_bytes,
                   caracteres_extraidos, score, resumo, origem_analise, data_analise
            FROM analise_logs
            ORDER BY data_analise DESC
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_analise_log(log_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM analise_logs WHERE id = ?", (log_id,))
        await db.commit()


async def delete_all_analise_logs() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM analise_logs")
        await db.commit()
