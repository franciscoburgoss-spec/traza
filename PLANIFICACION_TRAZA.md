# PLANIFICACION TRAZA — Hacia Produccion

> **Autor:** Francisco Burgos S.  
> **Enfoque:** Calidad sobre velocidad. Producto util para trabajo profesional personal.  
> **Metodologia:** Iteraciones cortas con testing manual y automatico.

---

## ESTADO ACTUAL (Snapshot)

### Lo que FUNCIONA hoy

| Modulo | Estado | Tests |
|--------|--------|-------|
| Infraestructura (DB, config, models) | Estable | 15 tests |
| Core (extractores PDF, verificadores, scoring) | Estable | 25 tests |
| Proyectos (CRUD basico) | Estable | 18 tests |
| Documentos/Evidencias/Verificaciones | Estable | 16 tests |
| Dictamenes/Auditoria | Estable | 12 tests |
| HAB (Muro/Caletera) | Estable | 10 tests |
| **ING (MVP completo)** | **Estable** | **34 tests** |
| **TOTAL** | | **127 tests pasando** |

### Lo que NO funciona bien (deuda tecnica)

1. **UI/UX**: Las paginas HTML existen pero no tienen polish visual. El sidebar no marca activo, los estados vacios no se manejan bien.
2. **R01 Workflow**: La extraccion de PDFs funciona via API pero no hay UI de flujo guiado.
3. **Data real**: No hay carga masiva ni importacion desde Excel/email.
4. **R02/REX**: Solo esqueleto, sin logica de negocio implementada.
5. **Offline 100%**: Tailwind y HTMX ya funcionan offline. PyMuPDF falta como dependencia para extraccion real de PDFs.

---

## FASE 1: ING — Pulido y Produccion (2-3 semanas)

### Objetivo
El Modulo ING funciona perfectamente en tu workflow diario. Puedes crear solicitudes, registrar documentos, ejecutar revisiones cruzadas, generar emails, y pasar a R01 sin errores.

### Tareas

#### 1.1 Pulido UI Lista ING
- [x] Arreglar JSON crudo en dashboard (FIXED)
- [x] Renderizar cards directamente desde servidor
- [ ] Ordenar solicitudes por fecha limite (mas urgentes primero)
- [ ] Paginacion si hay mas de 20 solicitudes
- [ ] Estado vacio: mensaje amigable cuando no hay solicitudes

#### 1.2 Formulario Nueva Solicitud ING
- [x] 33 comunas con acentos correctos (FIXED)
- [x] Zona sismica automatica (FIXED)
- [x] Preview de acronimo en vivo (FIXED)
- [x] Sacar superficie/calicatas del formulario (FIXED)
- [ ] Validacion: no permitir fecha limite anterior a fecha solicitud
- [ ] Validacion: empresa no puede estar vacia
- [ ] Autocomplete: sugerir empresas ya registradas

#### 1.3 Panel de Detalle ING
- [ ] Mejorar layout visual (mas compacto)
- [ ] Mostrar acronimo prominente con badge de color
- [ ] Timeline visual de la iteracion (recibida -> en_revision -> aceptada/observada)
- [ ] Comparacion visual ING #N vs ING #(N+1)

#### 1.4 Revisiones Cruzadas (Checklist)
- [ ] Mejorar UX: botones mas grandes para tablet
- [ ] Estado visual claro (circulo verde/rojo/gris)
- [ ] Validar MDS_TOPO 3.1.1 con datos reales (superficie vs calicatas)
- [ ] Guardar observaciones con formato enriquecido (negrita, listas)

#### 1.5 Generacion de Email
- [ ] Template HTML mas profesional (no solo texto plano)
- [ ] Copiar al portapapeles con un click
- [ ] Preview del email antes de marcar como enviado
- [ ] Historial de emails enviados

#### 1.6 Testing con Data Real
- [ ] Crear 5-10 proyectos ficticios pero realistas
- [ ] Probar flujo completo: ING #1 observada -> ING #2 herencia R6
- [ ] Verificar que acronimos son unicos (no colisiones)
- [ ] Probar todas 33 comunas (una por cada zona sismica)

### Criterio de Aceptacion
> "Puedo recibir un email del Coordinador, crear la Solicitud ING en menos de 2 minutos, registrar los documentos, ejecutar las revisiones cruzadas, generar el email de respuesta, y el proyecto queda listo para R01. Todo funciona sin errores y los datos persisten correctamente."

### Testing
- **Automatizado**: 34 tests existentes + 10 nuevos (validaciones, edge cases)
- **Manual**: Lista de verificacion de 20 pasos (ver abajo)

---

## FASE 2: Extraccion de PDFs — R01 Fundacion (2-3 semanas)

### Objetivo
Puedes subir un PDF de Memoria EST o Plano HAB y TRAZA extrae automaticamente las evidencias (texto, tablas, referencias normativas). No mas copiar datos a mano.

### Tareas

#### 2.1 Integrar PyMuPDF (fitz)
- [ ] Agregar `PyMuPDF>=1.23` a requirements.txt
- [ ] Implementar extractor basico: texto + tablas
- [ ] Manejo de errores: PDF corrupto, protegido, escaneado (sin texto)

#### 2.2 Extractor de Memorias EST
- [ ] Detectar tipologia estructural (T01, T02, etc.)
- [ ] Extraer dimensiones principales (luz, altura, base)
- [ ] Detectar normas citadas (NCh2361, NCh433, etc.)
- [ ] Comparar hash para deteccion de copias entre tipologias

#### 2.3 Extractor de Planos HAB
- [ ] Extraer lista de obras desde presupuesto/plano
- [ ] Detectar sistema constructivo
- [ ] Contar niveles, superficies, unidades

#### 2.4 Extractor de MDS/Topografia
- [ ] Extraer superficie del terreno
- [ ] Contar calicatas mencionadas
- [ ] Detectar zona sismica del estudio de suelos

#### 2.5 UI de Extraccion
- [ ] Arrastrar y soltar PDF
- [ ] Barra de progreso de extraccion
- [ ] Preview de evidencias extraidas antes de guardar
- [ ] Editar evidencias extraidas (correccion manual)

### Testing
- **Automatizado**: Tests con PDFs de ejemplo (generar fixtures)
- **Manual**: Subir 10 PDFs reales y verificar extraccion

---

## FASE 3: Verificacion Normativa — R01 Inteligente (3-4 semanas)

### Objetivo
TRAZA verifica automaticamente las evidencias contra la normativa y genera un score. Fran revisa solo las observaciones, no todo.

### Tareas

#### 3.1 Motor de Reglas
- [ ] Implementar RE7713Extractor completo (15 checks)
- [ ] Implementar NCh3417Extractor (verificacion sismica)
- [ ] Sistema de pesos configurable por norma
- [ ] Umbrales de aprobacion/rechazo

#### 3.2 Verificador Muro HAB
- [ ] 4 checks completos con scoring
- [ ] Categoria: Aceptado/Observado/Rechazado
- [ ] Colores visuales por categoria

#### 3.3 Verificador Caletera HAB
- [ ] 4 checks completos con scoring
- [ ] Comparacion con muro (consistencia)

#### 3.4 Reporte R01
- [ ] Score global del proyecto
- [ ] Detalle check por check con evidencias
- [ ] Exportar a PDF
- [ ] Firma digital del revisor

### Testing
- **Automatizado**: 30+ tests con casos de borde
- **Manual**: Verificar 5 proyectos reales contra revision manual

---

## FASE 4: Iteraciones y Correcciones — R02 (2 semanas)

### Objetivo
Cuando hay observaciones, TRAZA gestiona la iteracion: nuevos documentos, re-verificacion selectiva, tracking de cambios.

### Tareas

#### 4.1 Gestion de Observaciones
- [ ] Listar observaciones pendientes por proyecto
- [ ] Marcar observaciones como corregidas
- [ ] Upload de nuevo PDF corregido

#### 4.2 Re-verificacion Selectiva
- [ ] Detectar que cambio entre versiones
- [ ] Re-verificar SOLO lo que cambio (no todo de nuevo)
- [ ] Comparar evidencias viejas vs nuevas

#### 4.3 Historial de Iteraciones
- [ ] Timeline completo del proyecto
- [ ] Quien hizo que cambio y cuando
- [ ] Versionado de documentos

### Testing
- **Automatizado**: 15 tests
- **Manual**: Flujo completo con 3 iteraciones

---

## FASE 5: Dictamenes y Excepciones — REX (1-2 semanas)

### Objetivo
Cuando un proyecto no cumple la normativa pero tiene justificacion tecnica, TRAZA genera el dictamen de excepcion.

### Tareas
- [ ] Formulario de justificacion tecnica
- [ ] Template de dictamen oficial
- [ ] Firma digital
- [ ] Exportar PDF del dictamen
- [ ] Tracking de excepciones aprobadas/rechazadas

---

## FASE 6: Polish y Produccion (2 semanas)

### Tareas
- [ ] Diseno visual profesional (colores, tipografia, espaciado)
- [ ] Responsive (funciona en tablet para campo)
- [ ] Dark mode
- [ ] Backup automatico de la base de datos
- [ ] Guia de usuario (documentacion)
- [ ] Script de instalacion one-click

---

## CRONOGRAMA ESTIMADO

```
Semana  1-3:  FASE 1 — ING Pulido (PRIMERA PRIORIDAD)
Semana  4-6:  FASE 2 — Extraccion PDFs
Semana  7-10: FASE 3 — Verificacion Normativa
Semana 11-12: FASE 4 — R02 Iteraciones
Semana 13-14: FASE 5 — REX Dictamenes
Semana 15-16: FASE 6 — Polish y Produccion
```

**Total estimado: 16 semanas (4 meses)** — trabajando a ritmo comodo, sin apuro.

---

## LISTA DE VERIFICACION MANUAL — ING (FASE 1)

Copiar y marcar con [x] despues de probar:

### Crear Solicitud
- [ ] Crear solicitud ING #1 — "Condominio Los Almendros", Rancagua, Habitacional
- [ ] Verificar acronimo generado: H26RANLA (8 caracteres)
- [ ] Verificar zona sismica: Zona 2 (automatica)
- [ ] Verificar que el proyecto se creo automaticamente
- [ ] Verificar fecha de creacion

### Comunas con caracteres especiales
- [ ] Probar Chépica
- [ ] Probar Doñihue
- [ ] Probar Machalí
- [ ] Probar Requínoa

### Documentos
- [ ] Registrar documento MEMORIA EST T01
- [ ] Registrar documento PLANO HAB
- [ ] Marcar documento como aceptado
- [ ] Marcar documento como observado con observacion obligatoria

### Revisiones Cruzadas
- [ ] Crear checklist (7 revisiones)
- [ ] Marcar 3.1.1 MDS_TOPO como aceptado
- [ ] Marcar 3.2.1 EST_ARQ como observado con nota
- [ ] Ver progreso: X/7 revisadas

### Email
- [ ] Generar email al Coordinador
- [ ] Verificar que tiene aceptados/observados/faltantes
- [ ] Marcar como enviado

### Ciclo completo
- [ ] Crear ING #1, observarla
- [ ] Crear ING #2 (herencia R6)
- [ ] Verificar documentos aceptados en #1 son no_aplica en #2
- [ ] Aceptar ING #2
- [ ] Verificar boton R01 se habilita
- [ ] Verificar que ING aceptada es inmutable (R12)
