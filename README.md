# TRAZA

Sistema personal de trazabilidad normativa para revision estructural de proyectos FSEV.

> **Autor:** Francisco Burgos S.  
> **Ambiente:** 100% offline, laptop personal  
> **Institucion:** SERVIU O'Higgins

---

## Que es TRAZA

TRAZA es una herramienta de escritorio (corre en el navegador) que te ayuda a:

1. **ING** — Revisar documentos de ingreso al Banco de Proyectos (MDS, EST, HAB)
2. **R01** — Extraer evidencias de PDFs y verificarlas contra normativa
3. **R02** — Corregir observaciones y re-verificar selectivamente
4. **REX** — Dictaminar excepciones con justificacion tecnica

Todo queda guardado en tu laptop, sin conexion a internet, sin servidores externos.

---

## Requisitos

- Python 3.10 o superior
- Navegador web (Chrome, Firefox, Edge)
- ~200 MB de disco

---

## Instalacion (primera vez)

Descomprimir el ZIP en cualquier carpeta, por ejemplo `C:\TRAZA` (Windows) o `~/TRAZA` (Linux/Mac).

```bash
# 1. Entrar a la carpeta
cd TRAZA

# 2. Crear entorno virtual (recomendado)
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Verificar que todo funciona
pytest
# Debe mostrar: 126 passed
```

---

## Uso

### Iniciar TRAZA

```bash
# Con el entorno virtual activado:
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Abrir el navegador en: **http://127.0.0.1:8000**

### Flujo de trabajo

```
ING → R01 → R02 → REX
```

| Paso | Donde | Que haces |
|------|-------|-----------|
| **ING** | `/ing` | Revisas documentos del Coordinador, marcas aceptados/observados, generas email de respuesta |
| **R01** | `/proyectos` | Subes PDFs, extraes evidencias, verificas contra normativa (NCh3417, RE7713, etc.) |
| **R02** | `/proyectos/{id}` | Corriges observaciones, re-verificas solo lo que cambio |
| **REX** | `/dictamenes` | Dictaminas excepciones cuando aplica |

---

## Estructura del proyecto

```
TRAZA/
├── requirements.txt          # Dependencias Python
├── schema.sql                # Base de datos SQLite
├── .env.example              # Configuracion de ejemplo
├── README.md                 # Este archivo
├── app/
│   ├── main.py               # Aplicacion FastAPI
│   ├── config.py             # Configuracion
│   ├── database.py           # Conexion SQLite
│   ├── models.py             # Tablas core (Proyecto, Documento, etc.)
│   ├── models_ing.py         # Tablas ING (SolicitudIng, DocumentoIng, etc.)
│   ├── schemas.py            # Validacion de datos
│   ├── schemas_ing.py        # Validacion ING
│   ├── routers/
│   │   ├── ing.py            # API del Modulo ING
│   │   ├── proyectos.py      # API de proyectos
│   │   ├── documentos.py     # API de documentos
│   │   ├── evidencias.py     # API de evidencias
│   │   ├── verificaciones.py # API de verificaciones
│   │   ├── dictamenes.py     # API de dictamenes
│   │   ├── auditoria.py      # API de logs
│   │   └── extracciones.py   # API de extraccion PDF
│   ├── services/
│   │   ├── ing_service.py    # Logica de negocio ING
│   │   ├── proyecto_service.py
│   │   ├── extractor_service.py
│   │   └── dictamen_service.py
│   ├── core/
│   │   ├── extractors/       # Extractores de PDF
│   │   ├── verificadores/    # Verificadores normativos
│   │   ├── scoring.py        # Calculo de puntajes
│   │   └── hab_templates.py  # Plantillas HAB
│   ├── templates/
│   │   ├── base.html         # Layout principal
│   │   └── ing/              # Paginas del Modulo ING
│   │       ├── lista.html    # Lista de solicitudes
│   │       ├── detalle.html  # Detalle de solicitud
│   │       └── nueva.html    # Nueva solicitud
│   └── static/
│       └── style.css         # Estilos
└── tests/
    ├── integration/
    │   ├── test_ing.py       # 34 tests del Modulo ING
    │   ├── test_api_basic.py
    │   └── test_db.py
    ├── unit/
    │   ├── test_verificadores_muro.py
    │   ├── test_verificadores_caletera.py
    │   └── ...
    └── conftest.py
```

---

## Modulo ING (nuevo)

El Modulo ING es la entrada principal de TRAZA. Ahi revisas los documentos que te envia el Coordinador de Proyectos antes de pasar a la revision tecnica (R01).

### Funcionalidades

- **Solicitudes ING #1, #2, #3...** — Cada iteracion cuando hay observaciones
- **Documentos por modulo** — MDS, EST, HAB, URB agrupados
- **Hash SHA256** — Deteccion automatica de copias entre memorias
- **7 Revisiones cruzadas**:
  - 3.1 MDS-TOPO: Calicatas minimas segun superficie
  - 3.2 EST-ARQ: Planos y memorias por tipologia, deteccion de copias
  - 3.3 HAB-PRES: Obras con plano/memoria HAB, coherencia con presupuesto
- **Email al Coordinador** — Genera borrador con aceptados, observados y faltantes
- **Herencia R6** — Documentos aceptados en ING #N se heredan como `no_aplica` en ING #(N+1)
- **Dashboard** — Conteos por estado, vencimientos proximos

### Reglas de negocio

| Regla | Descripcion |
|-------|-------------|
| **R4** | ING aceptada = todos los documentos aceptados o no_aplica |
| **R5** | No se puede pasar a R01 sin ING aceptada |
| **R6** | Si aceptado en N → no_aplica en N+1 (herencia entre iteraciones) |
| **R10** | Observacion obligatoria al marcar documento como `observado` |
| **R12** | Iteracion aceptada es inmutable (no se puede modificar) |

---

## API Endpoints

### Modulo ING

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | `/api/v1/ing/solicitudes` | Crear Solicitud ING #1 |
| GET | `/api/v1/ing/solicitudes` | Listar solicitudes |
| GET | `/api/v1/ing/solicitudes/{id}` | Ver solicitud con documentos y revisiones |
| PATCH | `/api/v1/ing/solicitudes/{id}/estado` | Cambiar estado |
| POST | `/api/v1/ing/solicitudes/{id}/siguiente-iteracion` | Crear ING #(N+1) |
| POST | `/api/v1/ing/solicitudes/{id}/documentos` | Registrar documento |
| PATCH | `/api/v1/ing/documentos/{id}/estado` | Cambiar estado documento |
| POST | `/api/v1/ing/solicitudes/{id}/revisiones` | Crear checklist 7 revisiones |
| PATCH | `/api/v1/ing/revisiones/{id}/estado` | Marcar revision cruzada |
| POST | `/api/v1/ing/solicitudes/{id}/generar-email` | Generar borrador email |
| POST | `/api/v1/ing/solicitudes/{id}/enviar-email` | Registrar envio |
| GET | `/api/v1/ing/dashboard` | Panel de estadisticas |
| POST | `/api/v1/ing/validar-calicatas` | Validar calicatas normativa |

### Paginas HTML

| URL | Descripcion |
|-----|-------------|
| `/` | Panel principal |
| `/ing` | Lista de solicitudes ING |
| `/ing/nueva` | Formulario nueva solicitud |
| `/ing/{id}` | Detalle de solicitud |
| `/proyectos` | Lista de proyectos |
| `/dashboard` | Dashboard general |
| `/auditoria` | Logs de auditoria |

---

## Testing

```bash
# Todos los tests
pytest

# Solo tests del Modulo ING
pytest tests/integration/test_ing.py -v

# Con coverage
pytest --cov=app --cov-report=html
```

---

## Configuracion

Copiar `.env.example` a `.env` y ajustar:

```env
DATABASE_URL=sqlite:///./traza.db
DEBUG=false
SESSION_PREFIX=local
```

---

## Notas

- **100% offline:** No requiere internet. Los PDFs se leen desde tu disco local.
- **No almacena PDFs:** Solo guarda la ruta del archivo (`ruta_local`). Los PDFs deben estar accesibles en tu sistema de archivos.
- **Base de datos:** SQLite en archivo local (`traza.db`). Puedes copiarlo como respaldo.
- **Windows/Linux/Mac:** Funciona en cualquier sistema con Python 3.10+
