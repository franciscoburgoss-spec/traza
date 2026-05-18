-- TRAZA Schema SQLite
-- 10 tablas: Proyecto, Documento, Evidencia, Verificacion, Dictamen, LogAuditoria,
--            solicitud_ing, documento_ing, revision_cruzada, tabla_calicatas_minimas

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Funcion helper para generar UUID v4 en SQLite
CREATE TABLE IF NOT EXISTS _sqlite_sequence (_dummy);

CREATE TABLE IF NOT EXISTS Proyecto (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    codigo      TEXT NOT NULL UNIQUE,
    nombre      TEXT NOT NULL,
    tipo_proyecto TEXT,
    ref_comuna  TEXT,
    ref_zona_sismica INTEGER,
    ref_tipo_suelo TEXT,
    ref_Ao      REAL,
    estado      TEXT DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO','CERRADO','ARCHIVADO')),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Documento (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    proyecto_id     TEXT NOT NULL REFERENCES Proyecto(id) ON DELETE CASCADE,
    modulo          TEXT,
    tipo_documento  TEXT,
    nombre_archivo  TEXT NOT NULL,
    ruta_local      TEXT,
    hash_sha256     TEXT,
    extraccion_estado TEXT DEFAULT 'PENDIENTE' CHECK (extraccion_estado IN ('PENDIENTE','EN_PROCESO','COMPLETADO','ERROR')),
    extraccion_json TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Evidencia (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    documento_id    TEXT NOT NULL REFERENCES Documento(id) ON DELETE CASCADE,
    campo           TEXT NOT NULL,
    valor           TEXT,
    valor_tipo      TEXT,
    unidad          TEXT,
    source_page     INTEGER,
    extractor       TEXT,
    confidence      REAL DEFAULT 1.0,
    validada_manual BOOLEAN DEFAULT 0,
    observacion     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Verificacion (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    evidencia_id TEXT REFERENCES Evidencia(id) ON DELETE CASCADE,
    regla_codigo TEXT NOT NULL,
    resultado   TEXT NOT NULL CHECK (resultado IN ('CUMPLE','NO_CUMPLE','NO_APLICA','ERROR')),
    mensaje     TEXT,
    payload_json TEXT,
    session_id  TEXT,
    ejecutada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Dictamen (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    proyecto_id         TEXT NOT NULL UNIQUE REFERENCES Proyecto(id) ON DELETE CASCADE,
    estado              TEXT DEFAULT 'EN_PROCESO' CHECK (estado IN ('EN_PROCESO','COMPLETADO','ERROR')),
    total_verificaciones INTEGER DEFAULT 0,
    total_cumplen       INTEGER DEFAULT 0,
    total_no_cumplen    INTEGER DEFAULT 0,
    justificacion       TEXT,
    score               REAL,
    hab_html            TEXT,
    dictamen_texto      TEXT,
    editable            BOOLEAN DEFAULT 1,
    session_id          TEXT,
    generado_en         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS LogAuditoria (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    entidad_tipo TEXT NOT NULL,
    entidad_id  TEXT NOT NULL,
    accion      TEXT NOT NULL,
    detalle_json TEXT,
    session_id  TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices para lookups frecuentes
CREATE INDEX IF NOT EXISTS idx_doc_proyecto ON Documento(proyecto_id);
CREATE INDEX IF NOT EXISTS idx_evi_documento ON Evidencia(documento_id);
CREATE INDEX IF NOT EXISTS idx_ver_evidencia ON Verificacion(evidencia_id);
CREATE INDEX IF NOT EXISTS idx_ver_regla ON Verificacion(regla_codigo);
CREATE INDEX IF NOT EXISTS idx_ver_session ON Verificacion(session_id);
CREATE INDEX IF NOT EXISTS idx_dic_proyecto ON Dictamen(proyecto_id);
CREATE INDEX IF NOT EXISTS idx_log_entidad ON LogAuditoria(entidad_tipo, entidad_id);
CREATE INDEX IF NOT EXISTS idx_log_session ON LogAuditoria(session_id);

-- ============================================================
-- MODULO ING — Tablas de Ingreso al Banco de Proyectos
-- ============================================================

CREATE TABLE IF NOT EXISTS solicitud_ing (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    proyecto_id         TEXT NOT NULL REFERENCES Proyecto(id) ON DELETE CASCADE,
    numero_iteracion    INTEGER NOT NULL DEFAULT 1 CHECK (numero_iteracion > 0),
    solicitud_anterior_id TEXT REFERENCES solicitud_ing(id) ON DELETE RESTRICT,
    estado              TEXT NOT NULL DEFAULT 'recibida' CHECK (estado IN ('recibida','en_revision','aceptada','observada')),
    nombre_proyecto     TEXT NOT NULL,
    empresa             TEXT NOT NULL,
    modulos             TEXT NOT NULL DEFAULT '[]',
    fecha_limite        TEXT,
    link_descarga       TEXT,
    comuna              TEXT,
    zona_sismica        INTEGER,
    superficie_terreno  REAL,
    cantidad_calicatas  INTEGER,
    tipologias          TEXT,
    email_generado      TEXT,
    fecha_envio_email   TIMESTAMP,
    session_id          TEXT NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(proyecto_id, numero_iteracion)
);

CREATE TABLE IF NOT EXISTS documento_ing (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    solicitud_ing_id    TEXT NOT NULL REFERENCES solicitud_ing(id) ON DELETE CASCADE,
    nombre_archivo      TEXT NOT NULL,
    tipo_documento      TEXT NOT NULL CHECK (tipo_documento IN ('MEMORIA','PLANO','INFORME','PRESUPUESTO','OTRO')),
    modulo              TEXT NOT NULL CHECK (modulo IN ('MDS','EST','HAB','URB')),
    tipologia           TEXT,
    estado              TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','aceptado','observado','faltante','no_aplica')),
    observacion         TEXT,
    hash_sha256         TEXT,
    ruta_local          TEXT,
    iteracion_aceptada_en INTEGER,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(solicitud_ing_id, nombre_archivo, modulo)
);

CREATE TABLE IF NOT EXISTS revision_cruzada (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    solicitud_ing_id    TEXT NOT NULL REFERENCES solicitud_ing(id) ON DELETE CASCADE,
    tipo_revision       TEXT NOT NULL CHECK (tipo_revision IN ('MDS_TOPO','EST_ARQ','HAB_PRES')),
    numero_revision     TEXT NOT NULL,
    descripcion         TEXT NOT NULL,
    fuente_1            TEXT,
    valor_1             TEXT,
    fuente_2            TEXT,
    valor_2             TEXT,
    estado              TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','aceptado','observado','faltante')),
    observacion         TEXT,
    fran_marco          BOOLEAN NOT NULL DEFAULT 0,
    session_id          TEXT NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(solicitud_ing_id, numero_revision)
);

CREATE TABLE IF NOT EXISTS tabla_calicatas_minimas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    superficie_min      INTEGER NOT NULL,
    superficie_max      INTEGER,
    calicatas_minimas   INTEGER NOT NULL,
    observacion         TEXT
);

-- Datos normativos: calicatas minimas segun superficie
INSERT OR IGNORE INTO tabla_calicatas_minimas (superficie_min, superficie_max, calicatas_minimas, observacion)
VALUES
    (0, 2000, 2, 'Superficie menor a 2.000 m2'),
    (2000, 5000, 3, 'Superficie entre 2.000 y 5.000 m2'),
    (5000, 10000, 4, 'Superficie entre 5.000 y 10.000 m2'),
    (10000, NULL, 5, '5 + 1 por cada 5.000 m2 adicional');

-- Indices para Modulo ING
CREATE INDEX IF NOT EXISTS idx_ing_proyecto ON solicitud_ing(proyecto_id);
CREATE INDEX IF NOT EXISTS idx_ing_estado ON solicitud_ing(estado);
CREATE INDEX IF NOT EXISTS idx_ing_iteracion ON solicitud_ing(numero_iteracion);
CREATE INDEX IF NOT EXISTS idx_docing_solicitud ON documento_ing(solicitud_ing_id);
CREATE INDEX IF NOT EXISTS idx_docing_estado ON documento_ing(estado);
CREATE INDEX IF NOT EXISTS idx_rev_solicitud ON revision_cruzada(solicitud_ing_id);
CREATE INDEX IF NOT EXISTS idx_rev_tipo ON revision_cruzada(tipo_revision);
