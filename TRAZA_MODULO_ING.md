# TRAZA — Módulo ING: Ingreso al Banco de Proyectos

> **Documento de Profundizacion Técnica**
> **Versión:** 1.0 | **Fecha:** 2026-05-12
> **Autor:** FRANCISCO BURGOS S.
> **Estado:** Propuesta técnica para implementación

---

## 1. VISIÓN GENERAL

### 1.1 Qué es el Módulo ING

El **Módulo ING** es la **puerta de entrada** de TRAZA. Es donde Fran recibe una solicitud del Coordinador de Proyectos, registra los documentos, ejecuta las revisiones cruzadas (MDS↔Topografía, EST↔Arquitectura, HAB↔Presupuesto), y genera la respuesta al Coordinador.

**Principio fundamental:** ING no revisa contenido técnico profundo (eso es R01). ING revisa que los documentos **existan**, sean **lo que dicen ser**, y que los **cruces cruzados** de módulos coincidan.

### 1.2 Dónde encaja en TRAZA

```
┌────────────────────────────────────────────────────────────────────┐
│                         PLATAFORMA TRAZA                           │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │ING      │───→│R01      │───→│R02      │───→│REX      │         │
│  │(puerta  │    │(corazon │    │(correc- │    │(excep-  │         │
│  │ entrada)│    │tecnico) │    │ ciones) │    │ cional) │         │
│  │         │    │         │    │         │    │         │         │
│  │ Fran    │    │ TRAZA   │    │ TRAZA   │    │ TRAZA   │         │
│  │ revisa  │    │ opera   │    │ opera   │    │ opera   │         │
│  │ manual  │    │ auto    │    │ select. │    │ variable│         │
│  │ asistido│    │         │    │         │    │         │         │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘         │
│       ↑                                                            │
│  TRAZA gestiona estados, registra revisiones, genera email         │
│  Fran ejecuta las revisiones cruzadas (manual)                     │
└────────────────────────────────────────────────────────────────────┘
```

### 1.3 Principios de diseño

1. **Fran es el revisor, TRAZA es el asistente.** TRAZA nunca decide por Fran.
2. **Todo queda registrado.** Cada revisión cruzada, cada decisión, cada iteración.
3. **La iteración es nativa.** ING #1 → ING #2 → ING #3 es el flujo normal, no la excepción.
4. **No se puede saltar.** R5: No se puede pasar a R01 hasta que ING esté aceptada.
5. **Herencia de aceptados.** R6: Si estaba aceptado en N, sigue aceptado en N+1.

---

## 2. MODELO DE DATOS

### 2.1 Diagrama Entidad-Relación

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   Proyecto      │       │  solicitud_ing   │       │  documento_ing  │
├─────────────────┤       ├──────────────────┤       ├─────────────────┤
│ id UUID PK      │◄──────┤ proyecto_id FK   │◄──────┤ solicitud_ing_id│
│ codigo          │   1:N │ id UUID PK       │   1:N │ id UUID PK      │
│ nombre          │       │ numero_iteracion │       │ nombre_archivo  │
│ empresa         │       │ solicitud_ant_id │       │ tipo_documento  │
│ comuna          │       │ estado           │       │ modulo          │
│ zona_sismica    │       │ modulos JSON     │       │ tipologia       │
│ estado_flujo    │       │ fecha_limite     │       │ estado          │
│ created_at      │       │ link_descarga    │       │ observacion     │
└─────────────────┘       │ email_generado   │       │ hash_sha256     │
                          │ session_id       │       │ ruta_local      │
                          │ created_at       │       │ created_at      │
                          └──────────────────┘       └─────────────────┘
                                   │
                                   ▼ 1:N
                          ┌──────────────────┐
                          │ revision_cruzada │
                          ├──────────────────┤
                          │ id UUID PK       │
                          │ solicitud_ing_id │
                          │ tipo_revision    │
                          │ numero_revision  │
                          │ descripcion      │
                          │ fuente_1         │
                          │ valor_1          │
                          │ fuente_2         │
                          │ valor_2          │
                          │ estado           │
                          │ observacion      │
                          │ fran_marco       │
                          │ session_id       │
                          │ created_at       │
                          └──────────────────┘
```

### 2.2 Tabla `solicitud_ing` — Detalle completo

| # | Campo | Tipo | Nullable | Default | Descripción |
|---|-------|------|----------|---------|-------------|
| 1 | `id` | UUID | NO | gen_random_uuid() | PK |
| 2 | `proyecto_id` | UUID | NO | — | FK → Proyecto |
| 3 | `numero_iteracion` | INT | NO | 1 | 1, 2, 3... |
| 4 | `solicitud_anterior_id` | UUID | YES | NULL | FK → solicitud_ing (auto-referencia para cadena) |
| 5 | `estado` | VARCHAR(20) | NO | 'recibida' | recibida / en_revision / aceptada / observada |
| 6 | `nombre_proyecto` | VARCHAR(200) | NO | — | Nombre del proyecto |
| 7 | `empresa` | VARCHAR(200) | NO | — | Empresa desarrolladora |
| 8 | `modulos` | JSON | NO | '[]' | ["MDS","EST","HAB"] |
| 9 | `fecha_limite` | DATE | YES | NULL | Fecha límite |
| 10 | `link_descarga` | VARCHAR(500) | YES | NULL | URL del ZIP |
| 11 | `comuna` | VARCHAR(100) | YES | NULL | Inferida por Fran |
| 12 | `zona_sismica` | INT | YES | NULL | 1, 2 o 3 |
| 13 | `superficie_terreno` | FLOAT | YES | NULL | m², del plano topo |
| 14 | `cantidad_calicatas` | INT | YES | NULL | Del informe MDS |
| 15 | `tipologias` | JSON | YES | NULL | ["T01","T02"] del plano loteo |
| 16 | `email_generado` | TEXT | YES | NULL | Contenido del email |
| 17 | `fecha_envio_email` | DATETIME | YES | NULL | Cuándo se envió |
| 18 | `session_id` | VARCHAR(50) | NO | — | Trazabilidad |
| 19 | `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — |
| 20 | `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP | — |

**Constraints:**
- UNIQUE(proyecto_id, numero_iteracion) — Una iteración por proyecto
- CHECK(estado IN ('recibida', 'en_revision', 'aceptada', 'observada'))
- CHECK(numero_iteracion > 0)
- FK solicitud_anterior_id → solicitud_ing(id) ON DELETE RESTRICT

### 2.3 Tabla `documento_ing` — Detalle completo

| # | Campo | Tipo | Nullable | Default | Descripción |
|---|-------|------|----------|---------|-------------|
| 1 | `id` | UUID | NO | gen_random_uuid() | PK |
| 2 | `solicitud_ing_id` | UUID | NO | — | FK → solicitud_ing |
| 3 | `nombre_archivo` | VARCHAR(255) | NO | — | Nombre original |
| 4 | `tipo_documento` | VARCHAR(30) | NO | — | MEMORIA / PLANO / INFORME / PRESUPUESTO / OTRO |
| 5 | `modulo` | VARCHAR(10) | NO | — | MDS / EST / HAB / URB |
| 6 | `tipologia` | VARCHAR(20) | YES | NULL | T01, T02, etc. |
| 7 | `estado` | VARCHAR(20) | NO | 'pendiente' | pendiente / aceptado / observado / faltante / no_aplica |
| 8 | `observacion` | TEXT | YES | NULL | Motivo del estado |
| 9 | `hash_sha256` | VARCHAR(64) | YES | NULL | Para detección de copias |
| 10 | `ruta_local` | VARCHAR(500) | YES | NULL | /PDP/ING/{codigo}/EST/... |
| 11 | `iteracion_aceptada_en` | INT | YES | NULL | Iteración N donde fue aceptado (R6) |
| 12 | `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — |

**Constraints:**
- CHECK(estado IN ('pendiente', 'aceptado', 'observado', 'faltante', 'no_aplica'))
- UNIQUE(solicitud_ing_id, nombre_archivo, modulo) — No duplicados por iteración

### 2.4 Tabla `revision_cruzada` — Detalle completo

| # | Campo | Tipo | Nullable | Default | Descripción |
|---|-------|------|----------|---------|-------------|
| 1 | `id` | UUID | NO | gen_random_uuid() | PK |
| 2 | `solicitud_ing_id` | UUID | NO | — | FK → solicitud_ing |
| 3 | `tipo_revision` | VARCHAR(20) | NO | — | MDS_TOPO / EST_ARQ / HAB_PRES |
| 4 | `numero_revision` | VARCHAR(10) | NO | — | 3.1.1, 3.2.1, etc. |
| 5 | `descripcion` | VARCHAR(200) | NO | — | Texto descriptivo |
| 6 | `fuente_1` | VARCHAR(100) | YES | NULL | Nombre del campo fuente 1 |
| 7 | `valor_1` | TEXT | YES | NULL | Valor extraído |
| 8 | `fuente_2` | VARCHAR(100) | YES | NULL | Nombre del campo fuente 2 |
| 9 | `valor_2` | TEXT | YES | NULL | Valor extraído |
| 10 | `estado` | VARCHAR(20) | NO | 'pendiente' | pendiente / aceptado / observado / faltante |
| 11 | `observacion` | TEXT | YES | NULL | Detalle del resultado |
| 12 | `fran_marco` | BOOLEAN | NO | FALSE | ¿Fran ya revisó? |
| 13 | `session_id` | VARCHAR(50) | NO | — | Trazabilidad |
| 14 | `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | — |

**Constraints:**
- UNIQUE(solicitud_ing_id, numero_revision) — Una revisión por tipo por iteración
- CHECK(tipo_revision IN ('MDS_TOPO', 'EST_ARQ', 'HAB_PRES'))

### 2.5 Tabla normativa: `tabla_calicatas_minimas`

| # | Campo | Tipo | Descripción |
|---|-------|------|-------------|
| 1 | `superficie_min` | INT | m² mínimo del rango |
| 2 | `superficie_max` | INT | m² máximo del rango (NULL = sin límite) |
| 3 | `calicatas_minimas` | INT | Número mínimo de calicatas |
| 4 | `observacion` | VARCHAR(200) | Nota normativa |

**Datos:**
| superficie_min | superficie_max | calicatas_minimas | observacion |
|---|---|---|---|
| 0 | 2000 | 2 | Superficie menor a 2.000 m² |
| 2000 | 5000 | 3 | Superficie entre 2.000 y 5.000 m² |
| 5000 | 10000 | 4 | Superficie entre 5.000 y 10.000 m² |
| 10000 | NULL | 5 | 5 + 1 por cada 5.000 m² adicional |

---

## 3. ESTADOS Y TRANSICIONES

### 3.1 Diagrama de estados — Solicitud ING

```
                         ┌─────────────────────────────────────────┐
                         │                                         │
                         ▼                                         │
┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────┐  │
│ recibida │───→│ en_revision  │───→│aceptada  │    │observada │──┘
└──────────┘    └──────────────┘    └────┬─────┘    └────┬─────┘
                                          │                 │
                                          ▼                 ▼
                                    ┌──────────┐    ┌──────────────┐
                                    │en_r01_   │    │ ING #(N+1)   │
                                    │espera    │    │ se crea con  │
                                    └──────────┘    │ docs NO      │
                                                    │ aceptados    │
                                                    └──────────────┘
```

### 3.2 Diagrama de estados — Documento ING

```
                    ┌──────────────────────────────────────────────┐
                    │                                              │
                    │  R6: Si estaba aceptado en iteración N,      │
                    │      estado = no_aplica en iteración N+1     │
                    │                                              │
┌──────────┐       │    ┌──────────┐      ┌──────────┐           │
│pendiente │───────┼───→│aceptado  │─────→│no_aplica │───────────┘
└──────────┘       │    └──────────┘      └──────────┘
                    │         ▲
                    │         │ (Fran revisa y decide)
                    │    ┌────┴─────┐      ┌──────────┐
                    └───→│observado │      │faltante  │
                         └──────────┘      └──────────┘
```

### 3.3 Diagrama de estados — Revisión cruzada

```
┌──────────┐          ┌──────────┐
│pendiente │─────────→│aceptado  │
└────┬─────┘ Fran     └──────────┘
     │   marca
     │
     ├─────────→┌──────────┐
     │          │observado │
     │          └──────────┘
     │
     └─────────→┌──────────┐
                │faltante  │
                └──────────┘
```

---

## 4. FLUJOS DE USUARIO DETALLADOS

### 4.1 Flujo 1: Crear Solicitud ING #1 (proyecto nuevo)

```
1. Fran accede a Panel TRAZA → "Nueva Solicitud ING"
2. Sistema muestra formulario con campos del email:
   ┌─────────────────────────────────────┐
   │ Solicitud ING #1                    │
   │                                     │
   │ Nombre proyecto: [Condominio Los A] │
   │ Empresa: [Constructora del Sur SpA] │
   │ Módulos: [x] MDS [x] EST [x] HAB  │
   │ Fecha límite: [2026-06-15]         │
   │ Link descarga: [drive.google.com]  │
   │                                     │
   │ [ Crear Solicitud ]                 │
   └─────────────────────────────────────┘

3. TRAZA crea:
   - Proyecto en estado 'en_ing'
   - Solicitud ING #1 en estado 'recibida'
   - Estructura de carpetas /PDP/ING/{codigo}/
   - 0 documentos registrados

4. Estado cambia: recibida → en_revision
```

### 4.2 Flujo 2: Registrar documentos

```
5. Fran carga archivos arrastrando al panel:
   ┌─────────────────────────────────────┐
   │ Documentos del proyecto             │
   │                                     │
   │ Arrastra archivos aquí              │
   │ o selecciona desde carpeta          │
   │                                     │
   │ ┌─────────────┐ ┌─────────────┐    │
   │ │Memoria_EST_ │ │Plano_EST_   │    │
   │ │T01.pdf      │ │Loteo.pdf    │    │
   │ │[EST] [T01]  │ │[EST]        │    │
   │ │PENDIENTE    │ │PENDIENTE    │    │
   │ └─────────────┘ └─────────────┘    │
   │                                     │
   │ [ + Agregar más ]                 │
   └─────────────────────────────────────┘

6. Por cada documento, TRAZA pregunta:
   - Módulo: MDS / EST / HAB / URB
   - Tipo: MEMORIA / PLANO / INFORME / PRESUPUESTO
   - Tipología: (solo si EST) T01 / T02 / ...
   - Ruta local: (auto-detectada)

7. TRAZA calcula hash SHA256 para cada archivo
```

### 4.3 Flujo 3: Revisión cruzada (checklist interactivo)

```
8. TRAZA presenta el checklist de revisiones cruzadas:
   ┌──────────────────────────────────────────────────────┐
   │ Revisiones Cruzadas — ING #1                        │
   │                                                      │
   │ 3.1 MDS ↔ Topografía                                 │
   │                                                      │
   │ [x] 3.1.1 Calicatas mínimas                         │
   │     Superficie terreno: 8.500 m²                     │
   │     Calicatas informadas: 4                          │
   │     Mínimo normativo: 4 ← Tabla                      │
   │     Resultado: [ ACEPTADO ] [ OBSERVADO ]            │
   │                                                      │
   │ 3.2 EST ↔ Arquitectura                               │
   │                                                      │
   │ [ ] 3.2.1 Planos por tipología                      │
   │     Tipologías detectadas: T01, T02, T03             │
   │     Planos EST registrados: T01, T02                 │
   │     Resultado: [ ACEPTADO ] [ OBSERVADO ]            │
   │     Observación: [Falta plano EST T03]              │
   │                                                      │
   │ [ ] 3.2.2 Memorias por tipología                     │
   │     Tipologías: T01, T02, T03                        │
   │     Memorias EST registradas: T01, T02               │
   │     Resultado: [ ACEPTADO ] [ OBSERVADO ]            │
   │                                                      │
   │ [ ] 3.2.3 Detección de copias                       │
   │     Memoria T01: hash a3f7b2...8e91d4              │
   │     Memoria T02: hash c8d1e4...2f56a7              │
   │     Son diferentes ✓                                │
   │     Resultado: [ ACEPTADO ] [ OBSERVADO ]            │
   │                                                      │
   │ 3.3 HAB ↔ Presupuesto                                │
   │                                                      │
   │ [ ] 3.3.1 Obras con plano HAB                       │
   │     Obras en presupuesto: 8                          │
   │     Planos HAB registrados: 7                        │
   │     Resultado: [ ACEPTADO ] [ OBSERVADO ]            │
   │     Observación: [Falta plano HAB planta elevadora] │
   │                                                      │
   │ [ ] 3.3.2 Obras con memoria HAB                     │
   │     ...                                              │
   │                                                      │
   │ [ Guardar Revisiones ] [ Generar Email ]             │
   └──────────────────────────────────────────────────────┘
```

### 4.4 Flujo 4: Generar email al Coordinador

```
9. Fran hace clic en "Generar Email"
10. TRAZA redacta automáticamente:

    ─────────────────────────────────────────
    Destinatario: coordinador@serviu.gob.cl
    Asunto: Resultado ING — Condominio Los Almendros
    
    Estimado Coordinador,
    
    Resultado verificación ING — Proyecto Condominio Los Almendros:
    
    ACEPTADOS:
    • Informe MDS — 4 calicatas (cumple mínimo para 8.500 m²)
    • Planos EST T01, T02 — coinciden con arquitectura
    • Memorias EST T01, T02 — no son copias
    • Memoria HAB — describe 7 de 8 obras
    
    OBSERVADOS:
    • Plano EST T03 — FALTA (no viene en antecedentes)
    • Memoria EST T03 — FALTA
    • Plano HAB planta elevadora — FALTA en antecedentes
    
    FALTANTES:
    • Planos y memorias EST T03
    • Plano HAB sistema de planta elevadora
    
    Quedo atento.
    
    ---
    Generado por TRAZA | Fran | 2026-05-12 14:30:00
    Solicitud ING #1 | Session: local-1715503200-8472
    ─────────────────────────────────────────

11. Fran edita si es necesario, copia y envía (manual por ahora)
12. TRAZA registra: fecha_envio_email, estado → 'observada'
```

### 4.5 Flujo 5: Crear ING #2 (siguiente iteración)

```
13. Coordinador reenvía documentos subsanados
14. Fran accede a la Solicitud ING #1 → "Crear Siguiente Iteración"
15. TRAZA crea ING #2 con:
    - mismo proyecto_id
    - numero_iteracion = 2
    - solicitud_anterior_id = ING #1
    
16. TRAZA aplica R6 (herencia):
    - Documentos 'aceptado' en ING #1 → estado 'no_aplica' en ING #2
    - Documentos 'observado' o 'faltante' → estado 'pendiente' en ING #2
    
17. Fran solo carga los documentos nuevos/corregidos
18. Revisa solo las revisiones que estaban observadas
19. Repite Flujo 4 hasta que estado = 'aceptada'
```

### 4.6 Flujo 6: ING aceptada → pasar a R01

```
20. Cuando TODOS los documentos están 'aceptado' (o 'no_aplica'):
    - Estado ING → 'aceptada'
    - TRAZA muestra: "✓ Listo para R01"
    
21. Fran hace clic en "Iniciar R01"
22. TRAZA:
    - Cambia proyecto.estado_flujo → 'en_r01'
    - Copia documentos de /ING/ a /R01/
    - Habilita extractores y verificadores
    - Crea Solicitud R01 vinculada
    
23. Fran pasa al Módulo R01 de TRAZA
```

---

## 5. WIREFRAMES CONCEPTUALES

### 5.1 Panel Principal de ING

```
┌─────────────────────────────────────────────────────────────────────┐
│ TRAZA > ING — Solicitudes de Ingreso                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ [ + Nueva Solicitud ING ]   │  Filtro: [Todas ▼]  Buscar: [    ] │
│                              │                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  EN REVISIÓN (2)        ACEPTADAS (5)       OBSERVADAS (3)        │
│  ┌──────────────┐       ┌──────────────┐     ┌──────────────┐      │
│  │ Los Almendros│       │ Puerto Viejo │     │ Centro Ortega│      │
│  │ ING #1       │       │ ING #2 ✓     │     │ ING #2       │      │
│  │ MDS EST HAB  │       │ ING #1 ✓     │     │ MDS EST      │      │
│  │ 2026-06-15 ⚠│       │ Cerrado      │     │ 2026-05-20   │      │
│  │ [ Revisar ]  │       │              │     │ [ Revisar ]  │      │
│  └──────────────┘       └──────────────┘     └──────────────┘      │
│  ┌──────────────┐                                                  │
│  │ Pto Varas    │                                                  │
│  │ ING #1       │                                                  │
│  │ EST HAB      │                                                  │
│  │ 2026-06-01 🔥│                                                  │
│  │ [ Revisar ]  │                                                  │
│  └──────────────┘                                                  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  RESUMEN ESTADÍSTICAS                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ 8        │ │ 4        │ │ 12       │ │ 3        │              │
│  │ Solicitud│ │ Aceptadas│ │ Total    │ │ En revis.│              │
│  │ es ING   │ │ ING      │ │ Iterac.  │ │ ion      │              │
│  │ #1-#8    │ │ esta mes │ │ este mes │ │ urgente  │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Detalle de Solicitud ING (3 columnas)

```
┌─────────────────────────────────────────────────────────────────────┐
│ TRAZA > ING > Condominio Los Almendros > ING #1                   │
├──────────────────┬──────────────────────────────┬──────────────────┤
│ INFO DEL PROYECTO│ DOCUMENTOS (8)               │ REVISIONES (7)   │
│                  │                              │                  │
│ Nombre: Cond.    │ [+] Agregar documento        │ 3.1 MDS↔TOPO    │
│ Los Almendros    │                              │ [✓] 3.1.1 Calic.│
│ Empresa: Const.  │ MDS (2)                      │     ACEPTADO     │
│ del Sur SpA      │ • Informe_MDS.pdf            │                  │
│ Módulos: MDS,    │   [ACEPTADO]                 │ 3.2 EST↔ARQ     │
│ EST, HAB         │ • Plano_Topografia.pdf       │ [✗] 3.2.1 Planos│
│                  │   [ACEPTADO]                 │     OBSERVADO    │
│ Fecha límite:    │                              │ [✗] 3.2.2 Memor.│
│ 2026-06-15 ⚠    │ EST (4)                      │     OBSERVADO    │
│                  │ • Memoria_EST_T01.pdf        │ [✓] 3.2.3 Copias│
│ Estado:          │   [ACEPTADO]                 │     ACEPTADO     │
│ en_revision 🔵   │ • Memoria_EST_T02.pdf        │                  │
│                  │   [ACEPTADO]                 │ 3.3 HAB↔PRES    │
│ Iteración: #1    │ • Plano_EST_T01.pdf          │ [✗] 3.3.1 Planos│
│                  │   [ACEPTADO]                 │     OBSERVADO    │
│ [ Iniciar R01 ]  │ • Plano_EST_T02.pdf          │ [✓] 3.3.2 Memor.│
│ (deshabilitado)  │   [ACEPTADO]                 │     ACEPTADO     │
│                  │                              │                  │
│                  │ HAB (2)                      │                  │
│                  │ • Memoria_HAB.pdf            │                  │
│                  │   [ACEPTADO]                 │                  │
│                  │ • Planta_Elevadora_HAB.pdf   │                  │
│                  │   [FALTANTE] 🔴              │                  │
│                  │                              │                  │
├──────────────────┴──────────────────────────────┴──────────────────┤
│                                                                     │
│ [ Guardar ]  [ Generar Email ]  [ Crear ING #2 ]                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.3 Comparación de iteraciones (ING #1 vs ING #2)

```
┌─────────────────────────────────────────────────────────────────────┐
│ TRAZA > ING > Centro Ortega > Comparar Iteraciones                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│         ING #1 (2026-05-01)          vs       ING #2 (2026-05-12) │
│                                                                     │
│ Documento          │ Estado #1 │ Estado #2 │ Cambio                │
│ ───────────────────┼───────────┼───────────┼────────────────────── │
│ Informe_MDS.pdf    │ ✓ ACEPT.  │ —         │ Heredado (R6)         │
│ Plano_EST_T01.pdf  │ ✓ ACEPT.  │ —         │ Heredado (R6)         │
│ Memoria_EST_T03.pdf│ ✗ FALT.   │ ✓ ACEPT.  │ ← CORREGIDO           │
│ Memoria_HAB.pdf    │ ⚠ OBSERV. │ ✓ ACEPT.  │ ← CORREGIDO           │
│                                                                     │
│ Resultado: ING #2 = ACEPTADA ✓                                     │
│ Listo para R01 → [ Iniciar R01 ]                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. REGLAS DE NEGOCIO (completo)

### 6.1 Reglas de creación

| Regla | Descripción | Validación |
|---|---|---|
| R1 | ING es la **primera y única** forma de conocer un proyecto | No se puede crear R01 sin ING aceptada |
| R2 | ING puede tener **múltiples iteraciones** | numero_iteracion >= 1 |
| R3 | Cada iteración revisa **solo** documentos observados/faltantes | R6 aplica automáticamente |
| R7 | La estructura de carpetas se crea automáticamente | Al crear Solicitud ING #1 |
| R8 | Fran solo descarga **factibilidad técnica** | Registro manual en observación si descarga todo |

### 6.2 Reglas de estado

| Regla | Descripción | Implementación |
|---|---|---|
| R4 | ING aceptada = **todos** los documentos aceptados | COUNT(documento WHERE estado!='aceptado' AND estado!='no_aplica') = 0 |
| R5 | **No se puede pasar a R01** hasta ING aceptada | Botón "Iniciar R01" deshabilitado si estado != 'aceptada' |
| R6 | Si aceptado en N → **sigue aceptado** en N+1 | Al crear ING #(N+1), copiar docs aceptados con estado='no_aplica' |
| R9 | Las revisiones cruzadas se registran **siempre** | Incluso si resultado = 'aceptado' |
| R10 | Documento observado puede ser: mal nombrado, copiado, incompleto | Campo observacion es obligatorio si estado='observado' |

### 6.3 Reglas de integridad

| Regla | Descripción |
|---|---|
| R11 | Una solicitud ING no se puede eliminar si tiene documentos registrados |
| R12 | Una iteración ING no se puede modificar si estado = 'aceptada' (inmutable) |
| R13 | El email generado se guarda tal cual fue enviado (version final) |
| R14 | El hash SHA256 se calcula al registrar el documento, no al revisar |
| R15 | Toda transición de estado queda en LogAuditoria (tabla existente de TRAZA) |

---

## 7. API ENDPOINTS

### 7.1 Solicitudes ING

```
POST   /api/v1/ing/solicitudes
       → Crear nueva Solicitud ING #1
       ← 201 Created { solicitud_ing completa + proyecto creado }

GET    /api/v1/ing/solicitudes
       → Listar con filtros: ?estado=en_revision&proyecto_id=xxx
       ← 200 OK [ lista de solicitudes con conteo de docs por estado ]

GET    /api/v1/ing/solicitudes/{id}
       → Ver detalle completo con documentos y revisiones anidadas
       ← 200 OK { solicitud + documentos[] + revisiones[] + historial_iteraciones }

PUT    /api/v1/ing/solicitudes/{id}
       → Actualizar datos (nombre, empresa, fecha_limite, etc.)
       ← 200 OK

POST   /api/v1/ing/solicitudes/{id}/siguiente-iteracion
       → Crear ING #(N+1) aplicando R6
       ← 201 Created { nueva_solicitud con docs heredados }
```

### 7.2 Documentos ING

```
POST   /api/v1/ing/solicitudes/{id}/documentos
       → Registrar documento (nombre, tipo, modulo, tipologia, ruta)
       ← 201 Created { documento con hash_sha256 calculado }

GET    /api/v1/ing/solicitudes/{id}/documentos
       → Listar documentos agrupados por modulo
       ← 200 OK { MDS: [...], EST: [...], HAB: [...] }

PATCH  /api/v1/ing/documentos/{doc_id}/estado
       → Cambiar estado + observacion
       ← 200 OK

POST   /api/v1/ing/documentos/{doc_id}/hash
       → (Re)calcular hash SHA256 para detección de copias
       ← 200 OK { hash_sha256 }

GET    /api/v1/ing/documentos/{doc_id}/comparar/{doc2_id}
       → Comparar dos documentos (detección de copias)
       ← 200 OK { son_identicos: bool, hash_1, hash_2 }
```

### 7.3 Revisiones cruzadas

```
POST   /api/v1/ing/solicitudes/{id}/revisiones
       → Crear revisiones cruzadas automáticas (pre-poblar checklist)
       ← 201 Created [ lista de 7 revisiones creadas ]

GET    /api/v1/ing/solicitudes/{id}/revisiones
       → Listar checklist agrupado por tipo (3.1, 3.2, 3.3)
       ← 200 OK { MDS_TOPO: [...], EST_ARQ: [...], HAB_PRES: [...] }

PATCH  /api/v1/ing/revisiones/{rev_id}/estado
       → Fran marca resultado: estado + observacion + fran_marco=true
       ← 200 OK

GET    /api/v1/ing/solicitudes/{id}/progreso
       → Ver progreso del checklist (X/7 revisadas, Y/7 aceptadas)
       ← 200 OK { total: 7, revisadas: 4, aceptadas: 3, observadas: 1 }
```

### 7.4 Email

```
POST   /api/v1/ing/solicitudes/{id}/generar-email
       → Generar borrador de email con aceptados/observados/faltantes
       ← 200 OK { asunto, cuerpo, estadisticas }

GET    /api/v1/ing/solicitudes/{id}/email
       → Ver último email generado/enviado
       ← 200 OK { email_generado, fecha_envio }

POST   /api/v1/ing/solicitudes/{id}/enviar-email
       → Registrar que el email fue enviado (actualiza fecha_envio_email)
       ← 200 OK
```

### 7.5 Dashboard / Estadísticas

```
GET    /api/v1/ing/dashboard
       → Panel de Fran: conteos por estado, próximos vencimientos, urgencias
       ← 200 OK {
           en_revision: 2, aceptadas: 5, observadas: 3,
           vencimiento_proximo: [...],
           iteraciones_mes: 12
         }

GET    /api/v1/ing/proyectos/{proyecto_id}/historial
       → Ver todas las iteraciones ING de un proyecto
       ← 200 OK [ ING #1, ING #2, ... ] con resumen de cada una
```

---

## 8. CRITERIOS DE ACEPTACIÓN

### 8.1 Must Have (MVP del Módulo ING)

- [ ] **CA-ING-01**: Fran puede crear una Solicitud ING #1 con datos del email del Coordinador
- [ ] **CA-ING-02**: TRAZA crea la estructura de carpetas /PDP/ING/{codigo}/ automáticamente
- [ ] **CA-ING-03**: Fran puede registrar documentos (nombre, tipo, módulo, tipología)
- [ ] **CA-ING-04**: TRAZA calcula hash SHA256 de cada documento para detección de copias
- [ ] **CA-ING-05**: TRAZA presenta el checklist de revisiones cruzadas (3.1, 3.2, 3.3)
- [ ] **CA-ING-06**: Fran puede marcar cada revisión como aceptado/observado/faltante con observación
- [ ] **CA-ING-07**: TRAZA valida que campo observación es obligatorio si estado = 'observado'
- [ ] **CA-ING-08**: TRAZA genera automáticamente el email con aceptados/observados/faltantes
- [ ] **CA-ING-09**: TRAZA registra fecha de envío del email
- [ ] **CA-ING-10**: Si hay documentos observados/faltantes, estado = 'observada'
- [ ] **CA-ING-11**: Si todos aceptados, estado = 'aceptada'
- [ ] **CA-ING-12**: Botón "Iniciar R01" está deshabilitado si ING no está aceptada (R5)
- [ ] **CA-ING-13**: Fran puede crear ING #(N+1) que hereda aceptados como 'no_aplica' (R6)
- [ ] **CA-ING-14**: Panel de Fran muestra solicitudes agrupadas por estado
- [ ] **CA-ING-15**: Toda transición queda en LogAuditoria (trazabilidad)

### 8.2 Should Have

- [ ] **CA-ING-16**: Validación automática de calicatas mínimas con tabla normativa
- [ ] **CA-ING-17**: Detección automática de copias (comparación de hashes)
- [ ] **CA-ING-18**: Vista de comparación entre iteraciones (ING #1 vs ING #2)
- [ ] **CA-ING-19**: Alerta de fecha límite próxima (días restantes)
- [ ] **CA-ING-20**: Exportar resumen de ING en PDF

### 8.3 Could Have

- [ ] **CA-ING-21**: Integración con email (enviar directamente desde TRAZA)
- [ ] **CA-ING-22**: Drag & drop de archivos para carga
- [ ] **CA-ING-23**: Preview de PDF dentro de TRAZA
- [ ] **CA-ING-24**: Notificaciones push de nuevas solicitudes

---

## 9. INTEGRACIÓN CON TRAZA EXISTENTE

### 9.1 Tablas existentes que se reutilizan

| Tabla TRAZA existente | Uso en ING |
|---|---|
| `Proyecto` | Se crea al iniciar ING #1 |
| `LogAuditoria` | Toda transición de estado de ING se registra aquí |
| `Documento` | (R01) Los documentos de ING se migran a Documento cuando pasa a R01 |

### 9.2 Tablas nuevas (este módulo)

| Tabla nueva | Descripción |
|---|---|
| `solicitud_ing` | Gestión de solicitudes y iteraciones ING |
| `documento_ing` | Documentos registrados en ING (separado de R01) |
| `revision_cruzada` | Checklist de revisiones cruzadas |
| `tabla_calicatas_minimas` | Tabla normativa para validación MDS↔Topo |

### 9.3 Flujo de datos ING → R01

```
ING aceptada
  │
  ├→ solicitud_ing.estado = 'aceptada'
  ├→ proyecto.estado_flujo = 'en_r01'
  │
  ├→ Por cada documento_ing con estado='aceptado':
  │     Crear Documento (tabla existente) en /R01/
  │     Copiar: nombre_archivo, modulo, tipologia, hash, ruta_local
  │
  ├→ Crear Solicitud R01 (tabla futura)
  │     Vincular todos los Documentos creados
  │
  └→ Fran accede a Módulo R01
```

---

## 10. GLOSARIO

| Término | Significado |
|---|---|
| **ING** | Ingreso al Banco de Proyectos — recepción y revisión cruzada de documentos |
| **R01** | Revisión Técnica 01 — revisión de contenido técnico profundo |
| **R02** | Revisión 02 — corrección de observaciones de R01 |
| **REX** | Revisión Excepcional — caso especial fuera de flujo normal |
| **PDP** | Programa de Proyectos — estructura de carpetas |
| **Cruce cruzado** | Comparación entre documentos de módulos diferentes |
| **Iteración** | Repetición de ING (ING #1, #2, #3...) hasta aceptación |
| **MDS** | Mecánica de Suelos |
| **EST** | Estructural |
| **HAB** | Habilitación |
| **URB** | Urbanización |
| **FRANCISCO BURGOS S.** | Autor de TRAZA, revisor estructural |
