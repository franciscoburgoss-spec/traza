# SPEC-001-V2: ING — Ingreso al Banco de Proyectos (integrado con TRAZA)

> **Version:** 2.0 | **Fecha:** 2026-05-12
> **Correccion:** CHK e ING son el mismo proceso. Se unifican bajo ING.
> **Integracion TRAZA:** Este SPEC se integra como Modulo ING dentro de la plataforma TRAZA.

---

## 1. Trigger

Recepcion de **email del Coordinador de Proyectos** con solicitud formal de ingreso al Banco de Proyectos.

---

## 2. Actor

**Fran** (revisor tecnico de la oficina). TRAZA actua como **asistente de registro y gestion**, no como revisor automatico.

---

## 3. Datos de Entrada

### 3.1 Datos del email del Coordinador (obligatorios)

| Campo | Descripcion | Ejemplo | Tipo |
|---|---|---|---|
| `nombre_proyecto` | Nombre completo del proyecto | "Condominio Los Almendros" | string |
| `empresa` | Empresa desarrolladora | "Constructora del Sur SpA" | string |
| `modulos` | Modulos que solicita revisar | MDS, EST, HAB, URB | array[string] |
| `fecha_limite` | Fecha limite de entrega | 2026-06-15 | date |
| `link_descarga` | Link a ZIP con antecedentes completos | https://drive.google.com/... | url |

### 3.2 Datos que NO vienen en el email pero Fran infiere al revisar

| Campo | Fuente | Tipo |
|---|---|---|
| `comuna` | Informe MDS o planos de topografia | string |
| `zona_sismica` | Tabla por comuna (NCh 433 Of.96) | int (1,2,3) |
| `tipologias` | Plano de loteo de viviendas | array[string] |
| `superficie_terreno` | Plano de topografia | float (m2) |
| `cantidad_calicatas` | Informe MDS | int |

---

## 4. Acciones del Actor (pasos manuales asistidos por TRAZA)

### Paso 1: Recibir solicitud en TRAZA
- Fran accede al Panel de ING de TRAZA
- Crea una nueva **Solicitud de Ingreso** con los datos del email del Coordinador
- TRAZA genera automaticamente la estructura de carpetas:
  ```
  /PDP/ING/{proyecto_codigo}/
    /EST/
    /MDS/
    /HAB/
    /URB/ (si aplica)
  ```

### Paso 2: Descargar y cargar factibilidad tecnica
- Fran descarga el ZIP desde `link_descarga` (manual)
- Carga los documentos en TRAZA arrastrando los archivos
- TRAZA **registra cada documento** con: nombre, tipo, modulo, version, estado inicial `pendiente`

### Paso 3: Revision cruzada asistida

TRAZA presenta a Fran los **cruces cruzados** como checklist interactivo. Fran responde cada item y TRAZA registra el resultado.

#### 3.1 Cruz MDS ↔ Topografia
| # | Revisión | Fuente 1 | Fuente 2 | Estado en TRAZA |
|---|---------|----------|----------|-----------------|
| 3.1.1 | Calicatas minimas | `superficie_terreno` | `cantidad_calicatas` | Fran marca aceptado/observado |

**Regla normativa (tabla):**
| Superficie terreno (m2) | Min. calicatas segun profundidad |
|---|---|
| < 2.000 | 2 calicatas |
| 2.000 - 5.000 | 3 calicatas |
| 5.000 - 10.000 | 4 calicatas |
| > 10.000 | 5 + 1 por cada 5.000 m2 adicional |

#### 3.2 Cruz EST ↔ Arquitectura
| # | Revision | Fuente 1 | Fuente 2 | Estado en TRAZA |
|---|---------|----------|----------|-----------------|
| 3.2.1 | Planos por tipologia | Plano loteo → tipologias | Planos EST | Fran marca aceptado/observado/faltante |
| 3.2.2 | Memorias por tipologia | Tipologias detectadas | Memorias EST | Fran marca aceptado/observado/faltante |
| 3.2.3 | Deteccion de copias | Memoria EST T01 (hash) | Memoria EST T02 (hash) | TRAZA calcula hash, Fran decide si son copia |

#### 3.3 Cruz HAB ↔ Presupuesto
| # | Revision | Fuente 1 | Fuente 2 | Estado en TRAZA |
|---|---------|----------|----------|-----------------|
| 3.3.1 | Obras con plano HAB | Presupuesto → lista de obras | Planos HAB registrados | Fran marca aceptado/faltante |
| 3.3.2 | Obras con memoria HAB | Presupuesto → lista de obras | Memorias HAB registradas | Fran marca aceptado/faltante |
| 3.3.3 | Memoria describe todas las obras | Memoria HAB (texto) | Lista de obras del presupuesto | Fran marca aceptado/observado |

### Paso 4: Generar respuesta al Coordinador (TRAZA la redacta)
- TRAZA genera automaticamente el **borrador de email** con:
  - Documentos aceptados (listado)
  - Documentos observados (listado + motivo registrado en cada revision)
  - Documentos faltantes (listado)
- Fran revisa y edita si es necesario
- Envia al Coordinador (manual, fuera de TRAZA por ahora)

---

## 5. Datos de Salida

### 5.1 Email al Coordinador (generado por TRAZA)
- Destino: Coordinador de Proyectos
- Formato: Texto plano, cuerpo del email
- Contenido: Aceptados / Observados / Faltantes

**Ejemplo generado por TRAZA:**
```
Estimado Coordinador,

Resultado verificacion ING — Proyecto {nombre_proyecto}:

ACEPTADOS:
{lista auto-generada de documentos con estado 'aceptado'}

OBSERVADOS:
{lista auto-generada de documentos con estado 'observado' + motivo}

FALTANTES:
{lista auto-generada de documentos con estado 'faltante'}

Quedo atento.

---
Generado por TRAZA — Solicitud ING #{numero} | Fran | {fecha_hora}
```

### 5.2 Acta
**NO.** En ING no hay acta formal. Solo email de respuesta.

### 5.3 Registro en TRAZA
Cada Solicitud ING queda registrada en TRAZA con:
- Datos completos de la solicitud (proyecto, empresa, modulos, fecha limite)
- Todos los documentos registrados con su estado por iteracion
- Resultado de cada revision cruzada (3.1, 3.2, 3.3)
- Historial de iteraciones (ING #1 → ING #2 → ...)
- Email generado (version final enviada)

---

## 6. Reglas de Negocio (ING)

| Regla | Descripcion |
|---|---|
| R1 | ING es la **primera y unica** forma de conocer un proyecto. No existe proyecto antes de ING. |
| R2 | ING puede tener **multiples iteraciones** (1, 2, 3...) hasta que todo este aceptado. |
| R3 | En cada iteracion, el Coordinador reenvia **solo** documentos observados o faltantes. |
| R4 | Una iteracion ING se da por **aceptada** cuando todos los documentos estan en estado `aceptado`. |
| R5 | **No se puede pasar a R01** hasta que la ultima iteracion ING este aceptada. |
| R6 | Si un documento estaba `aceptado` en iteracion N, **sigue aceptado** en iteracion N+1 (no se revisa de nuevo). |
| R7 | La estructura de carpetas `/ING/`, `/APB/`, `/ACT/` se crea automaticamente al iniciar ING. |
| R8 | Fran solo descarga **factibilidad tecnica**, no todo el ZIP. |
| R9 | Las revisiones cruzadas se registran **siempre**, aunque el resultado sea `aceptado`. |
| R10 | Un documento `observado` en ING puede ser: mal nombrado, copiado, incompleto, o no cumple normativa minima. |

---

## 7. Estados de ING

### 7.1 Estados de la Solicitud ING
```
recibida → en_revision → [aceptada | observada]
                          ↑___________________|
                           (nueva iteracion)
```

| Estado | Significado |
|---|---|
| `recibida` | Email recibido, proyecto creado en TRAZA, aun no se empieza a revisar |
| `en_revision` | Fran esta revisando cruzado los documentos en TRAZA |
| `aceptada` | Todos los documentos aceptados. Listo para R01. |
| `observada` | Hay documentos observados o faltantes. Se requiere nueva iteracion. |

### 7.2 Estados de un Documento en ING

| Estado | Significado |
|---|---|
| `pendiente` | Aun no revisado en esta iteracion |
| `aceptado` | Paso la revision cruzada |
| `observado` | No paso la revision cruzada (detalle en observacion) |
| `faltante` | Declarado en presupuesto o modulo pero no viene en antecedentes |
| `no_aplica` | El modulo no solicita este documento (ej: URB no tiene EST) |

---

## 8. Transiciones

### 8.1 Cuando ING esta `aceptada`
```
Solicitud ING #N → estado 'aceptada'
  → Proyecto estado_flujo cambia a 'en_r01_espera'
  → Fran puede recibir Solicitud R01
  → TRAZA habilita el modulo R01 para este proyecto
```

### 8.2 Cuando ING esta `observada`
```
Solicitud ING #N → estado 'observada'
  → TRAZA genera email al Coordinador
  → Fran envia email al Coordinador
  → Coordinador envia a empresa desarrolladora
  → Empresa subsana
  → Coordinador reenvia nuevos antecedentes
  → Fran crea Solicitud ING #(N+1) en TRAZA
  → TRAZA marca como 'no_aplica' los documentos aceptados en N (R6)
  → Solo revisar documentos que estaban 'observado' o 'faltante'
```

---

## 9. Integracion con TRAZA

### 9.1 TRAZA como plataforma principal

```
Panel Principal (Fran)
  ├── Modulo ING  ← Este SPEC
  │     ├── Solicitudes activas
  │     ├── Historial
  │     ├── Cruces cruzados (checklist)
  │     └── Generador de email
  ├── Modulo R01  ← TRAZA existente (extractores, verificadores)
  │     ├── Documentos en revision
  │     ├── Verificadores HAB
  │     ├── Scoring
  │     └── Dictamen / Acta R01
  ├── Modulo R02  ← Nuevo (re-ejecucion selectiva)
  │     ├── Comparacion R01 vs R02
  │     └── Acta R02
  └── Modulo REX  ← Nuevo (revision excepcional)
```

### 9.2 Flujo de datos entre modulos

```
ING #N aceptada
  → TRAZA crea "Solicitud R01" para el proyecto
  → Copia documentos de /ING/ a /R01/
  → Habilita extractores y verificadores
  → Fran ejecuta revision tecnica
  → TRAZA genera Acta R01

R01 con observaciones
  → Espera correcciones del Coordinador
  → Cuando llegan, TRAZA crea "Solicitud R02"
  → Re-ejecuta solo checks observados
  → TRAZA genera Acta R02
```

---

## 10. Modelo de Datos ING (tablas en TRAZA)

### 10.1 Tabla: `solicitud_ing`

| Campo | Tipo | Descripcion |
|---|---|---|
| `id` | UUID PK | Identificador unico |
| `proyecto_id` | UUID FK → Proyecto | Proyecto asociado |
| `numero_iteracion` | INT | 1, 2, 3... |
| `solicitud_anterior_id` | UUID FK → solicitud_ing | Para R6 (cadena de iteraciones) |
| `nombre_proyecto` | STRING | Nombre del proyecto |
| `empresa` | STRING | Empresa desarrolladora |
| `modulos` | JSON | ["MDS", "EST", "HAB"] |
| `fecha_limite` | DATE | Fecha limite |
| `link_descarga` | STRING | URL del ZIP |
| `estado` | ENUM | recibida / en_revision / aceptada / observada |
| `fecha_envio_email` | DATETIME | Cuando se envio la respuesta |
| `email_generado` | TEXT | Contenido del email enviado |
| `session_id` | STRING | Trazabilidad |
| `created_at` | DATETIME | Fecha de creacion |
| `updated_at` | DATETIME | Fecha de actualizacion |

### 10.2 Tabla: `documento_ing`

| Campo | Tipo | Descripcion |
|---|---|---|
| `id` | UUID PK | Identificador unico |
| `solicitud_ing_id` | UUID FK → solicitud_ing | Iteracion ING |
| `nombre_archivo` | STRING | Nombre del archivo |
| `tipo_documento` | ENUM | MEMORIA / PLANO / INFORME / PRESUPUESTO |
| `modulo` | ENUM | MDS / EST / HAB / URB |
| `tipologia` | STRING | T01, T02, etc. (si aplica) |
| `estado` | ENUM | pendiente / aceptado / observado / faltante / no_aplica |
| `observacion` | TEXT | Motivo del estado (si observado) |
| `hash_sha256` | STRING | Hash para deteccion de copias |
| `ruta_local` | STRING | Path en /PDP/ING/ |
| `fecha_registro` | DATETIME | Cuando se cargo en TRAZA |
| `created_at` | DATETIME | Fecha de creacion |

### 10.3 Tabla: `revision_cruzada`

| Campo | Tipo | Descripcion |
|---|---|---|
| `id` | UUID PK | Identificador unico |
| `solicitud_ing_id` | UUID FK → solicitud_ing | Iteracion ING |
| `tipo_revision` | ENUM | MDS_TOPO / EST_ARQ / HAB_PRES |
| `numero_revision` | INT | 3.1.1, 3.2.1, etc. |
| `descripcion` | STRING | Descripcion de la revision |
| `fuente_1` | STRING | Fuente 1 (nombre campo) |
| `valor_1` | STRING | Valor extraido fuente 1 |
| `fuente_2` | STRING | Fuente 2 (nombre campo) |
| `valor_2` | STRING | Valor extraido fuente 2 |
| `estado` | ENUM | pendiente / aceptado / observado / faltante |
| `observacion` | TEXT | Detalle del resultado |
| `fran_marco` | BOOLEAN | Fran ya reviso este item |
| `session_id` | STRING | Trazabilidad |
| `created_at` | DATETIME | Fecha de creacion |

---

## 11. API Endpoints ING (propuestos)

### Solicitudes ING
| Metodo | Endpoint | Descripcion |
|---|---|---|
| POST | `/api/v1/ing/solicitudes` | Crear nueva solicitud ING |
| GET | `/api/v1/ing/solicitudes` | Listar solicitudes (filtrar por estado) |
| GET | `/api/v1/ing/solicitudes/{id}` | Ver solicitud con documentos y revisiones |
| PUT | `/api/v1/ing/solicitudes/{id}` | Actualizar solicitud |
| POST | `/api/v1/ing/solicitudes/{id}/siguiente-iteracion` | Crear ING #(N+1) |

### Documentos ING
| Metodo | Endpoint | Descripcion |
|---|---|---|
| POST | `/api/v1/ing/solicitudes/{id}/documentos` | Registrar documento |
| GET | `/api/v1/ing/solicitudes/{id}/documentos` | Listar documentos |
| PATCH | `/api/v1/ing/documentos/{id}/estado` | Cambiar estado (aceptado/observado/faltante) |
| POST | `/api/v1/ing/documentos/{id}/hash` | Calcular hash SHA256 (deteccion de copias) |

### Revisiones cruzadas
| Metodo | Endpoint | Descripcion |
|---|---|---|
| POST | `/api/v1/ing/solicitudes/{id}/revisiones` | Crear revision cruzada |
| GET | `/api/v1/ing/solicitudes/{id}/revisiones` | Listar revisiones (checklist) |
| PATCH | `/api/v1/ing/revisiones/{id}/estado` | Fran marca resultado |

### Email
| Metodo | Endpoint | Descripcion |
|---|---|---|
| POST | `/api/v1/ing/solicitudes/{id}/generar-email` | Generar borrador de email |
| GET | `/api/v1/ing/solicitudes/{id}/email` | Ver email generado |
| POST | `/api/v1/ing/solicitudes/{id}/enviar-email` | Registrar envio de email |

---

## 12. Panel de Fran (vista global)

```
┌─────────────────────────────────────────────────────────────┐
│  PANEL DE FRAN — TRAZA                                      │
├─────────────────────────────────────────────────────────────┤
│  En ING (3)   |   En R01 (2)   |   En R02 (1)   |   Cerrados │
│  ┌───────┐    |   ┌───────┐     |   ┌───────┐     |   ┌─────┐   │
│  │Los Al │    |   │Pto Vie│     |   │Condo  │     |   │...  │   │
│  │Pto Vie│    |   │Centro │     |   │Ortega │     |   │     │   │
│  │Centro │    |   └───────┘     |   └───────┘     |   └─────┘   │
│  └───────┘    |                  |                  |              │
│  + Nueva Solicitud ING                                      │
└─────────────────────────────────────────────────────────────┘
```
