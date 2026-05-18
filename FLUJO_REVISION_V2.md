# FLUJO DE REVISION — Contrato de profundidad y responsabilidades (V2)

> **Version:** 2.0 | **Fecha:** 2026-05-12
> **Correccion aplicada:** CHK e ING son el mismo proceso. Se unifican bajo el nombre **ING**.
> **Integracion TRAZA:** La plataforma TRAZA gestiona y opera todo el pipeline.

---

## Pipeline Macro

```
ING (Ingreso) ──→ R01 (Revision Tecnica) ──→ R02 (Correccion R01) ──→ REX (Excepcion)
   Fran revisa:        TRAZA opera aqui:        TRAZA opera aqui:        TRAZA opera aqui:
   - Llego?            - Contenido tecnico      - Re-ejecucion          - Modo variable
   - Es lo que dice?   - Normativa chilena       selectiva de checks    - Configurable
   - Cruces cruzados   - Cruces con otros docs
   - Completo?         - Acta R01 formal
   - Formato minimo
```

---

## 1. ING (Ingreso al Banco de Proyectos)

### Trigger
Recepcion de email del Coordinador de Proyectos con solicitud formal de ingreso al Banco de Proyectos.

### Actor
Fran (revisor tecnico)

### Que se revisa
- **Existencia fisica:** Llego el documento que dice el correo de envio?
- **Identidad:** El codigo del documento coincide con lo que declara? Es el modulo correcto? Es la tipologia correcta?
- **Formato minimo:** Tiene membrete, firmas, numero de revision, version?
- **Cruces inmediatos:** La tipologia que dice representar la estructura coincide con la que dice la mecanica de suelos?
- **Cruces cruzados (corazon del ING):**
  - MDS ↔ Topografia: calicatas minimas segun superficie
  - EST ↔ Arquitectura: cada tipologia tiene su plano + memoria EST
  - HAB ↔ Presupuesto: cada obra del presupuesto tiene plano + memoria HAB
  - Deteccion de copias: memorias EST no pueden ser contenido copiado renombrado

### Que NO se revisa
- NO se revisa el contenido tecnico profundo (calculos, armaduras, normativa detallada).
- NO se marcan items de acta por vineta.
- NO se verifica cumplimiento normativo detallado (eso es R01).

### Profundidad
| Nivel | Descripcion |
|---|---|
| Documento entero | "Llego" / "No llego" / "Llego pero tiene algo raro" |
| Cruz inmediato | T01 en estructuras = T01 en arquitectura |
| Cruz cruzado | Calicatas vs superficie, tipologias vs memorias, obras vs planos HAB |

### Datos de entrada
El email del Coordinador contiene obligatoriamente:

| Campo | Descripcion | Ejemplo |
|---|---|---|
| `nombre_proyecto` | Nombre completo del proyecto | "Condominio Los Almendros" |
| `empresa` | Empresa desarrolladora | "Constructora del Sur SpA" |
| `modulos` | Modulos que solicita revisar | MDS, EST, HAB, URB |
| `fecha_limite` | Fecha limite de entrega | 2026-06-15 |
| `link_descarga` | Link a ZIP con antecedentes completos | https://drive.google.com/... |

**Datos que NO vienen en el email pero Fran infiere al revisar:**
- `comuna` (del Informe MDS o planos de topografia)
- `zona_sismica` (de la comuna)
- `tipologias` (del plano de loteo de viviendas)
- `superficie_terreno` (del plano de topografia)
- `cantidad_calicatas` (del Informe MDS)

### Acciones del Actor (pasos manuales que TRAZA registra)

#### Paso 1: Descargar factibilidad tecnica
- Descarga ZIP desde `link_descarga`
- Guarda en `/PDP/ING/`
- Solo descarga la factibilidad tecnica, no todo el proyecto

#### Paso 2: Separar por modulos
- Copia documentos a `/PDP/ING/EST/`, `/PDP/ING/MDS/`, `/PDP/ING/HAB/` segun corresponda

#### Paso 3: Revision cruzada (el corazon del ING)

##### 3.1 Cruz MDS ↔ Topografia
| Revision | Fuente 1 | Fuente 2 | Regla |
|---|---|---|---|
| Calicatas vs superficie | Plano topografia → `superficie_terreno` | Informe MDS → `cantidad_calicatas` | Tabla normativa: segun superficie, minimo X calicatas segun profundidad |
| Estado | Si cumple → aceptado | Si no cumple → observado | "No cumple minimo normativo de calicatas" |

##### 3.2 Cruz EST ↔ Arquitectura
| Revision | Fuente 1 | Fuente 2 | Regla |
|---|---|---|---|
| Tipologias estructurales | Plano loteo → tipologias con estructura diferente | Planos EST + memorias EST | Debe haber plano y memoria por cada tipologia estructural diferente |
| Copia detectada | Memoria EST T01 | Memoria EST T02 | Abrir y verificar que no sea contenido copiado renombrado |
| Estado | Si coincide todo → aceptado | Si falta tipologia o es copia → observado | "Falta memoria de calculo T03" / "Memorias T01 y T02 son identicas" |

##### 3.3 Cruz HAB ↔ Presupuesto
| Revision | Fuente 1 | Fuente 2 | Regla |
|---|---|---|---|
| Obras declaradas | Presupuesto detallado → lista de obras/infraestructura | Planos HAB + Memoria HAB | Toda obra del presupuesto debe tener plano y memoria |
| Memoria de habilitacion | Memoria HAB | Presupuesto | La memoria debe describir y explicar todas las obras del presupuesto |
| Estado | Si coincide todo → aceptado | Si falta obra o no se describe → observado | "Falta memoria de habilitacion para planta elevadora" |

#### Paso 4: Responder email al Coordinador
**Formato:** Email de texto libre, sin acta formal.

**Contenido:**
- Documentos **aceptados** (listado)
- Documentos **observados** (listado + motivo)
- Documentos **faltantes** (listado)

**Ejemplo:**
```
Estimado Coordinador,

Resultado verificacion ING — Proyecto Condominio Los Almendros:

ACEPTADOS:
- Informe MDS — cumple calicatas minimas
- Planos EST T01, T02 — coinciden con arquitectura

OBSERVADOS:
- Memoria EST T03 — FALTA (no viene en los antecedentes)
- Memoria HAB — No describe la planta elevadora declarada en presupuesto

FALTANTES:
- Planos HAB de sistema alcantarillado

Quedo atento.
```

### Resultado posible
| Estado | Significado |
|---|---|
| `aceptado` | Documento correcto, es lo que dice ser, cruces OK |
| `observado` | Llego pero hay algo mal (codigo erroneo, tipologia no coincide, falta membrete, copia detectada) |
| `faltante` | No llego, deberia estar |
| `no_aplica` | El modulo no solicita este documento |

### Iteraciones
ING puede tener **multiples iteraciones** (ING #1, ING #2, ING #3...) hasta que todo este aceptado.

### Acta
**NO.** En ING no hay acta formal. Solo email de respuesta.

---

## 2. R01 (Revision 01)

### Que se revisa
- **Contenido tecnico del documento:** Cada item de la pauta de revision tecnica.
- **Normativa:** Verificacion contra normas chilenas (Decreto 49, Resolucion 7713, NCh 3417, etc.).
- **Requerimientos del itemizado tecnico:** Lo que el programa de vivienda exige para ese tipo de documento.
- **Cruces con otros documentos:** La mecanica de suelos refleja lo que pide estructuras?

### Que NO se revisa
- NO se revisa si el documento llego (eso fue ING).
- NO se revisa formato administrativo (eso fue ING).

### Profundidad
| Nivel | Descripcion |
|---|---|
| Item por item | Cada vineta de la pauta de revision tecnica |
| Observacion normativa | Con fundamento, severidad, accion correctiva |
| Referencia cruzada | Lamina X del plano Y, pagina Z de la memoria |

### Resultado posible por item
| Estado | Significado |
|---|---|
| `aprobado` | Cumple normativa y requerimientos |
| `observado` | No conforme, requiere corregir |
| `no_aplica` | No aplica para este documento/tipologia |

### Resultado posible por documento
- Si todos los items aprobados/no_aplica → Documento aprobado.
- Si hay items observados → Documento observado (con lista de observaciones).
- Si hay items criticos → Documento rechazado (raro, pero posible).

### Quien lo hace
Fran revisando plano por plano, memoria por memoria. TRAZA **opera aqui** (extractores, verificadores, scoring).

### Que produce
- **Acta de Revision 01** con observaciones detalladas por item (viñeta × viñeta).
- Email al Coordinador con resumen de observaciones y plazo para correcciones.

---

## 3. R02 (Revision 02)

### Que se revisa
- **Correcciones de R01:** Se atendieron todas las observaciones?
- **Nuevos items:** Si R01 genero cambios mayores, se revisan los items afectados.
- **Revision parcial:** No se revisa todo de nuevo, solo lo que cambio.

### Profundidad
| Nivel | Descripcion |
|---|---|
| Item observado en R01 | Se corrigio? Como? |
| Nuevos items | Solo si R01 genero cambios mayores |

### Resultado
| Estado | Significado |
|---|---|
| `aprobado` | Todas las observaciones atendidas |
| `observado` | Quedaron observaciones sin atender |
| `rechazado` | No se atendieron observaciones criticas |

### TRAZA en R02
- Carga el Acta R01 anterior
- Identifica checks con resultado `observado`
- **Re-ejecuta SOLO esos checks** (no todo de nuevo)
- Compara: cambio el resultado?
- Genera **Acta R02** con solo las diferencias

### Que produce
- Acta de Revision 02.
- Email con resumen.

---

## 4. REX (Revision Excepcional)

### Que se revisa
- **Documentos que llegaron fuera de flujo normal:** Por ejemplo, una REX para un documento que llego despues de cerrado.
- **Documentos con cambios mayores post-R02:** Una reestructuracion completa.
- **Documentos especiales:** Planos de emergencia, modificaciones de obra.

### Profundidad
- Variable. Puede ser tan profunda como R01 o tan simple como ING.
- Depende del motivo de la excepcion.

### TRAZA en REX
- Modo variable: se configura la profundidad segun el caso.
- Puede usar extractores selectivamente, o verificadores completos, o solo scoring.

### Resultado
- Variable segun el caso.

---

## 5. TRAZA — Integracion en el flujo

### TRAZA NO opera en ING (pero lo gestiona)
ING es proceso manual de Fran. TRAZA **registra y gestiona** el proceso (solicitudes, iteraciones, estados de documentos, respuestas al Coordinador) pero **no realiza las revisiones cruzadas** (eso lo hace Fran manualmente).

### TRAZA opera en R01 (el corazon)
| Componente TRAZA | Uso en R01 |
|---|---|
| `PDFExtractor` | Extrae texto de memorias y planos |
| `SeismicExtractor` | Verifica Z, Ao, tipo suelo en MDS |
| `NCh3417Extractor` | 22+ checks de contenido de memoria de calculo |
| `RE7713Extractor` | 15 checks de itemizacion tecnica |
| `VerificadorMuro` | Verificacion estructural de muros de contencion |
| `VerificadorCaletera` | Verificacion estructural de caletas |
| `Scoring 0-100` | Priorizacion y categorizacion del dictamen |
| `Dictamen editable` | Acta R01 con observaciones fundadas |

### TRAZA opera en R02 (re-ejecucion selectiva)
- Carga checks `observados` del Acta R01
- Re-ejecuta solo esos checks
- Genera Acta R02 con diferencias

### TRAZA opera en REX (modo variable)
- Configuracion ad-hoc segun el caso
- Extractores y verificadores selectivos

---

## 6. Modulos faltantes en TRAZA (roadmap)

| Modulo | Descripcion | Prioridad | Etapa pipeline |
|---|---|---|---|
| **Modulo ING** | Gestion de solicitudes de ingreso, iteraciones, estados de documentos, generacion de email al Coordinador | **Alta** | ING |
| **Modulo R01-Acta** | Generacion formal del Acta de Revision 01 (vineta × vineta) en formato entregable | **Alta** | R01 |
| **Modulo R02** | Re-ejecucion selectiva de checks observados, comparacion con R01, Acta R02 | **Media** | R02 |
| **Modulo REX** | Revision excepcional configurable, profundidad variable | **Baja** | REX |
| **Panel de Fran** | Dashboard unificado con todo el pipeline: proyectos en ING, R01, R02, cerrados | **Alta** | Global |
