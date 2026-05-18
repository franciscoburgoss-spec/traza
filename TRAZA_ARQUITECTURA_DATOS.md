# TRAZA — Arquitectura de Datos: Documentos, Evidencias y Observaciones

> **Documento técnico de referencia para Fran**
> **Fecha:** 2026-05-12

---

## 1. Manejo de Documentos: ¿Servidor o Local?

### Respuesta corta
**TRAZA NO almacena documentos.** Solo guarda la **ruta al archivo** en tu disco. Los PDFs nunca se copian a la base de datos.

### ¿Cómo funciona?

```
┌─────────────────────────────────────────────────────────────┐
│                    TU DISCO LOCAL                           │
│                                                             │
│  /PDP/                                                      │
│    /ING/                                                    │
│      /RM-2026-0847/                                         │
│        /EST/                                                │
│          Memoria_EST_T01.pdf  ←── El PDF está aquí         │
│          Plano_EST_Loteo.pdf                                │
│        /MDS/                                                │
│          Informe_MDS.pdf                                    │
│                                                             │
│  traza.db  ←── SQLite (solo guarda la ruta, no el PDF)     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  TABLA Documento en SQLite                   │
│                                                             │
│  id:          "abc-123-..."    ← UUID generado por TRAZA   │
│  proyecto_id: "xyz-789-..."    ← FK al proyecto            │
│  nombre_archivo: "Memoria_EST_T01.pdf"                      │
│  ruta_local:  "/PDP/ING/RM-2026-0847/EST/Memoria_EST_T01.pdf"
│  hash_sha256: "a3f7b2...8e91d4"  ← Hash del archivo        │
│  extraccion_estado: "COMPLETADO"                            │
│  extraccion_json:  NULL  ← Datos extraidos en crudo         │
└─────────────────────────────────────────────────────────────┘
```

### Campo a campo en la tabla Documento

| Campo | ¿Qué guarda? | Ejemplo real |
|-------|-------------|--------------|
| `id` | UUID generado por TRAZA | `"550e8400-e29b-41d4-a716-446655440000"` |
| `proyecto_id` | UUID del proyecto padre | FK a tabla Proyecto |
| `nombre_archivo` | Solo el nombre del archivo | `"Memoria_EST_T01.pdf"` |
| `ruta_local` | **Ruta absoluta en tu disco** | `"/Users/fran/PDP/ING/RM-2026-0847/EST/Memoria_EST_T01.pdf"` |
| `hash_sha256` | Hash criptográfico del archivo | `"a3f7b2d8c4e5f6..."` |
| `extraccion_estado` | Estado del proceso | `PENDIENTE` → `EN_PROCESO` → `COMPLETADO` / `ERROR` |
| `extraccion_json` | Texto crudo extraído (opcional) | `"Memoria de Calculo..."` o NULL |

### Flujo de lectura de un PDF

```
1. Fran hace clic "Extraer" en la UI
   │
   ▼
2. Router llama a POST /api/v1/documentos/{id}/extraer
   │
   ▼
3. ExtractorService recibe documento_id
   │  Lee documento.ruta_local del registro en SQLite
   │
   ▼
4. PDFExtractor abre el archivo DESDE EL DISCO
   │  fitz.open("/Users/fran/PDP/ING/RM-2026-0847/EST/Memoria_EST_T01.pdf")
   │
   ▼
5. Extrae texto pagina por pagina
   │
   ▼
6. SeismicExtractor, NCh3417Extractor, etc.
   │  trabajan sobre el texto extraido (en memoria RAM)
   │
   ▼
7. Evidencias se guardan en SQLite (texto, números, no el PDF)
   │
   ▼
8. PDF se cierra, memoria se libera
   │  El archivo original NUNCA se mueve ni se copia
```

### Implicaciones prácticas

| Situación | ¿Qué pasa? |
|-----------|-----------|
| **Mueves el PDF de carpeta** | TRAZA pierde la referencia. Hay que actualizar `ruta_local` manualmente. |
| **Borras el PDF del disco** | TRAZA tiene el registro pero no puede extraer. Marca error. |
| **Cambias de computador** | Hay que actualizar todas las rutas locales. O usar rutas relativas. |
| **El PDF pesa 50 MB** | No importa. Nunca se guarda en la DB. Solo se lee al extraer. |
| **Hay 200 proyectos** | La base de datos sigue siendo pequeña (solo texto y rutas). |

### ¿Deberíamos cambiar esto?

**No.** Para uso personal offline en tu MacBook Air, el modelo de **referencia por ruta** es correcto:
- La DB es ligera (megabytes, no gigabytes)
- Los PDFs se organizan en carpetas según tu estructura `/PDP/ING/`, `/PDP/APB/`, `/PDP/ACT/`
- Si un día necesitas portabilidad, se puede exportar con las rutas relativas

---

## 2. Formato de Evidencias: Detección, Categorización y Almacenamiento

### 2.1 Pipeline completo: De PDF a Evidencia en DB

```
PDF en disco
    │
    ▼ fitz.open(ruta_local)
Texto crudo (raw_text)
    │
    ▼ SeismicExtractor.extract_from_text(texto)
ExtractionResult {
    raw_text: "La zona sismica es Z=2 con Ao=0.20g...",
    structured_data: {
        "zona_sismica": 2,
        "Ao": 0.20,
        "tipo_suelo": "II"
    },
    confidence: 0.9,
    extractor_name: "SeismicExtractor",
    page_count: 0
}
    │
    ▼ ExtractorService guarda en DB
┌──────────────────────────────────────────────────────────┐
│  TABLA Evidencia (SQLite)                                │
├──────────────────────────────────────────────────────────┤
│  id:           "ev-001-..."                              │
│  documento_id: "doc-001-..."  ← FK al Documento         │
│  campo:        "zona_sismica"  ← Nombre del campo        │
│  valor:        "2"              ← Valor como string      │
│  valor_tipo:   "NUMERIC"       ← Tipo de dato            │
│  unidad:       "adimensional"                           │
│  source_page:  12              ← Página donde apareció   │
│  extractor:    "SeismicExtractor"  ← Quién lo extrajo    │
│  confidence:   0.9             ← 0.0 a 1.0              │
│  validada_manual: FALSE        ← Fran lo revisó?         │
│  observacion:  NULL            ← Nota del revisor        │
│  created_at:   2026-05-12 14:30:00                      │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Formato de salida del extractor: `ExtractionResult`

Es un **dataclass** (objeto Python puro) que todo extractor retorna:

```python
@dataclass
class ExtractionResult:
    raw_text: str          # Texto plano extraido (para debug)
    structured_data: dict  # {"campo": valor, ...} datos estructurados
    confidence: float      # 0.0 = fallo total, 0.5 = parcial, 0.8+ = bueno
    extractor_name: str    # "SeismicExtractor", "NCh3417Extractor", etc.
    page_count: int        # Cuántas páginas procesó
    metadata: dict         # {"error": "..."} o info adicional
```

**Ejemplo real de SeismicExtractor:**
```python
ExtractionResult(
    raw_text="La zona sismica es Z=2 con Ao=0.20g...",
    structured_data={
        "zona_sismica": 2,
        "Ao": 0.20,
        "tipo_suelo": "II"
    },
    confidence=0.9,
    extractor_name="SeismicExtractor",
    page_count=0,
    metadata={"params_encontrados": 3}  # 3 de 3 parámetros encontrados
)
```

### 2.3 Formato de guardado en DB: tabla `Evidencia`

Cada campo del `structured_data` se guarda como **una fila separada**:

| id | documento_id | campo | valor | valor_tipo | unidad | extractor | confidence |
|----|-------------|-------|-------|-----------|--------|-----------|------------|
| ev-001 | doc-001 | zona_sismica | 2 | NUMERIC | adimensional | SeismicExtractor | 0.9 |
| ev-002 | doc-001 | Ao | 0.20 | REAL | g | SeismicExtractor | 0.9 |
| ev-003 | doc-001 | tipo_suelo | II | TEXT | — | SeismicExtractor | 0.9 |

**Un extractor = múltiples evidencias** (una por campo detectado).

### 2.4 Tipos de evidencia (valor_tipo)

| valor_tipo | Significado | Ejemplo |
|-----------|-------------|---------|
| `NUMERIC` | Número entero | "120" (viviendas) |
| `REAL` | Número decimal | "0.20" (Ao en g) |
| `TEXT` | Texto libre | "CNT" (tipología) |
| `STRING` | JSON serializado | '{"altura_m": 3.0, "fc": 25}' |
| `BOOLEAN` | Sí/No | "true", "false" |
| `norma` | Referencia normativa | "NCh 433" |
| `referencia` | Referencia a plano | "Plano E-01" |
| `sismico` | Parámetro sísmico | "Z=2" |

---

## 3. Formato de Verificaciones/Observaciones

### 3.1 Formato de salida del verificador: `ResultadoVerificacion`

Es un **dataclass** que todo verificador retorna:

```python
@dataclass
class ResultadoVerificacion:
    verificador_id: str    # "MURO-ALT-001"
    nombre: str            # "Altura del muro"
    descripcion: str       # "La altura del muro no debe exceder 4.0m"
    resultado: str         # "CUMPLE" / "NO_CUMPLE" / "NO_APLICA" / "SIN_EVIDENCIA"
    severidad: str         # "INFO" / "WARNING" / "ERROR" / "CRITICAL"
    mensaje: str           # "Altura = 3.0m ≤ 4.0m. CUMPLE."
    datos_utilizados: dict # {"altura_muro": 3.0, "altura_max": 4.0}
```

**Ejemplo real — Verificador de altura de muro:**
```python
ResultadoVerificacion(
    verificador_id="MURO-ALT-001",
    nombre="Altura del muro de contención",
    descripcion="Verifica que la altura no excede 4.0m (WARNING) o 6.0m (ERROR)",
    resultado="CUMPLE",
    severidad="INFO",
    mensaje="Altura = 3.0m ≤ 4.0m. CUMPLE con margen de 1.0m.",
    datos_utilizados={"altura_muro": 3.0, "altura_max_warning": 4.0}
)
```

### 3.2 Formato de guardado en DB: tabla `Verificacion`

Cada verificación se guarda como **una fila**:

| id | evidencia_id | regla_codigo | resultado | mensaje | payload_json | session_id |
|----|-------------|--------------|-----------|---------|-------------|------------|
| ver-001 | ev-001 | MURO-ALT-001 | CUMPLE | "Altura = 3.0m ≤ 4.0m" | `{"altura_muro": 3.0}` | local-1715503200-8472 |
| ver-002 | ev-001 | MURO-DRE-001 | CUMPLE | "Altura 1.5m, no requiere drenaje" | `{"altura_m": 1.5}` | local-1715503200-8472 |

### 3.3 Estados de verificación (resultado)

| Estado | Significado | Color en UI |
|--------|-------------|-------------|
| `CUMPLE` | La norma se cumple | Verde |
| `NO_CUMPLE` | La norma NO se cumple | Rojo |
| `NO_APLICA` | Esta verificación no aplica a este proyecto | Gris |
| `SIN_EVIDENCIA` | No se encontró el dato necesario | Amarillo |

### 3.4 Niveles de severidad

| Severidad | Significado | Requiere acción | Ejemplo |
|-----------|-------------|-----------------|---------|
| `INFO` | Información, no es observación | No | "Altura = 3.0m. OK." |
| `WARNING` | Advertencia, recomendación | Sí, pero no bloqueante | "Altura = 4.5m. Supera 4.0m. Revisar estabilidad." |
| `ERROR` | Observación que debe corregirse | Sí, bloqueante para aprobación | "Altura = 7.0m > 6.0m máximo. INCUMPLE." |
| `CRITICAL` | Observación crítica | Sí, dictamen rechazado | "FOS vuelco = 1.2 < 1.3. Riesgo de colapso." |

---

## 4. Formato del Dictamen (resultado agregado)

### 4.1 Tabla `Dictamen`

| Campo | Valor ejemplo | Descripción |
|-------|---------------|-------------|
| `id` | "dic-001" | UUID |
| `proyecto_id` | "proj-001" | FK a Proyecto (único) |
| `estado` | "COMPLETADO" | EN_PROCESO / COMPLETADO / ERROR |
| `total_verificaciones` | 37 | Total de checks ejecutados |
| `total_cumplen` | 28 | Checks que CUMPLEN |
| `total_no_cumplen` | 9 | Checks que NO CUMPLEN |
| `score` | 75.68 | Score 0-100 calculado |
| `hab_html` | "`<html>...`" | HTML renderizable del HAB |
| `dictamen_texto` | "DICTAMEN TÉCNICO..." | Texto plano editable por Fran |
| `justificacion` | "El proyecto presenta..." | Justificación generada |
| `editable` | TRUE | Fran puede editar el texto |
| `session_id` | "local-1715..." | Trazabilidad |

### 4.2 Cálculo del Score

```python
score = (cumplen / aplicables) * 100
# donde: aplicables = total - no_aplican

# Ejemplo:
# total = 37, cumplen = 28, no_aplican = 5, no_cumplen = 4
# aplicables = 37 - 5 = 32
# score = (28 / 32) * 100 = 87.5
```

### 4.3 Categorías de Score

| Score | Categoría | Color | Significado |
|-------|-----------|-------|-------------|
| 90-100 | Excelente | Verde oscuro | Cumple holgadamente |
| 75-89 | Bueno | Verde | Cumple con márgenes aceptables |
| 60-74 | Regular | Amarillo | Cumple pero con observaciones importantes |
| 0-59 | Deficiente | Rojo | No cumple, requiere revisión completa |

---

## 5. Trazabilidad completa: De PDF a Dictamen

```
PDF en disco (/PDP/ING/.../Memoria.pdf)
    │
    ├── fitz.open() ──→ raw_text (en memoria RAM)
    │                       │
    │   SeismicExtractor ──→ structured_data: {zona_sismica: 2, Ao: 0.20, tipo_suelo: "II"}
    │                       │
    │   NCh3417Extractor ──→ structured_data: {portada: true, indice: true, ... 22 checks}
    │                       │
    │   RE7713Extractor  ──→ structured_data: {itemizacion: true, antecedentes: true, ... 15 checks}
    │                       │
    ▼                       ▼
┌────────────────────────────────────────────────────────────────────┐
│  TABLA Evidencia (SQLite) — Datos extraídos                       │
│  - 3 evidencias sísmicas (zona, Ao, suelo)                        │
│  - 22+ evidencias NCh3417 (checks de memoria)                     │
│  - 15 evidencias RE7713 (itemización)                             │
│  - 4 evidencias HAB muro (altura, drenaje, fc, estabilidad)       │
│  - 4 evidencias HAB caletera (longitud, ancho, pendiente, espesor)│
└────────────────────────────────────────────────────────────────────┘
    │
    ▼ Verificadores ejecutan sobre evidencias
┌────────────────────────────────────────────────────────────────────┐
│  TABLA Verificacion (SQLite) — Resultados de norma                │
│  - MURO-ALT-001: CUMPLE (altura = 3.0m)                          │
│  - MURO-DRE-001: CUMPLE (drenaje OK)                              │
│  - MURO-FC-001:  CUMPLE (fc = 25 ≥ 20)                           │
│  - CAL-LON-001:  CUMPLE (longitud = 50m ≥ 20)                    │
│  - ... 37 verificaciones en total                                  │
└────────────────────────────────────────────────────────────────────┘
    │
    ▼ Scoring + Generación
┌────────────────────────────────────────────────────────────────────┐
│  TABLA Dictamen (SQLite) — Resultado final                        │
│  - Score: 87.5 / 100 (Bueno)                                      │
│  - hab_html: "<html>..." (renderizable en navegador)              │
│  - dictamen_texto: "DICTAMEN TÉCNICO TRAZA..." (editable por Fran)│
└────────────────────────────────────────────────────────────────────┘
    │
    ▼ Log de auditoría
┌────────────────────────────────────────────────────────────────────┐
│  TABLA LogAuditoria — Todo queda registrado                       │
│  - Documento creado                                               │
│  - Extracción completada (12 evidencias)                          │
│  - Dictamen generado (score: 87.5)                                │
│  - Dictamen editado por Fran (cambio en justificación)            │
│  - Estado cambiado a APROBADO                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 6. Resumen visual: ¿Qué guarda TRAZA vs qué NO guarda?

| Elemento | ¿Se guarda en SQLite? | ¿Dónde está? |
|----------|----------------------|--------------|
| PDF original (50 MB) | **NO** | En tu disco, ruta referenciada |
| Texto extraído del PDF | Parcialmente (`extraccion_json`) | En la tabla Documento (opcional) |
| Datos estructurados (zona, Ao, etc.) | **SÍ** | En tabla Evidencia |
| Resultados de verificación | **SÍ** | En tabla Verificacion |
| Dictamen HTML | **SÍ** | En tabla Dictamen (`hab_html`) |
| Dictamen texto editable | **SÍ** | En tabla Dictamen (`dictamen_texto`) |
| Score 0-100 | **SÍ** | En tabla Dictamen (`score`) |
| Fotos del proyecto | **NO** | Solo si se referencian por ruta |
| Planos DWG | **NO** | Solo ruta local |
| Logs de auditoría | **SÍ** | En tabla LogAuditoria |
