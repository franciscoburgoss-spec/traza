"""Database engine, session y utilidades de inicializacion."""
import os
import re
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base declarativa para SQLAlchemy 2.0."""
    pass


# Extraer path del SQLite desde DATABASE_URL
def _extract_sqlite_path(url: str) -> str:
    match = re.match(r"sqlite:///(.+)", url)
    if match:
        return match.group(1)
    return "./traza.db"


# Engine SQLite con WAL mode
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# Escuchar conexiones para activar WAL
@event.listens_for(engine, "connect")
def _set_wal_mode(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency para FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea todas las tablas usando SQLAlchemy create_all() + datos normativos."""
    # Importar todos los modelos para que SQLAlchemy los registre
    from app.models import Proyecto, Documento, Evidencia, Verificacion, Dictamen, LogAuditoria  # noqa
    from app.models_ing import SolicitudIng, DocumentoIng, RevisionCruzada, TablaCalicatasMinimas  # noqa

    Base.metadata.create_all(bind=engine)

    # Insertar datos normativos de calicatas si la tabla esta vacia
    with engine.begin() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM tabla_calicatas_minimas"))
        count = result.scalar()
        if count == 0:
            conn.execute(text("""
                INSERT INTO tabla_calicatas_minimas (superficie_min, superficie_max, calicatas_minimas, observacion)
                VALUES
                    (0, 2000, 2, 'Superficie menor a 2.000 m2'),
                    (2000, 5000, 3, 'Superficie entre 2.000 y 5.000 m2'),
                    (5000, 10000, 4, 'Superficie entre 5.000 y 10.000 m2'),
                    (10000, NULL, 5, '5 + 1 por cada 5.000 m2 adicional')
            """))

    # Migracion: agregar columna ruta_carpeta a solicitud_ing si no existe (R7)
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE solicitud_ing ADD COLUMN ruta_carpeta TEXT"))
            print("[DB] Columna ruta_carpeta agregada a solicitud_ing")
    except Exception:
        # Columna ya existe (operacion idempotente)
        pass

    print(f"[DB] Tablas inicializadas en {settings.DATABASE_URL}")
