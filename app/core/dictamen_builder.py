"""
Constructor de dictamen para revision estructural de vivienda social FSEV.

Este modulo es el ORQUESTADOR del proceso de dictamen:
  1. Recibe los resultados de todas las verificaciones (muro, caletera, NCh 3417, RE 7713)
  2. Cuenta resultados (cumplen / no cumplen / no aplican / sin evidencia)
  3. Calcula score 0-100 con pesos configurables
  4. Genera justificacion en texto natural
  5. Genera hab_html usando Jinja2 templates
  6. Genera dictamen_texto editable para el revisor

IMPORTANTE: El dictamen generado por este modulo es PRELIMINAR. El revisor
SIEMPRE debe revisar y editar antes de firmar. Nunca es automatico al 100%.

Workflow real:
    recibir expediente -> revisar documentos -> verificaciones automaticas
    -> generar dictamen preliminar -> REVISOR EDITA -> dictamen final firmado
"""

from typing import Any, Optional
from datetime import datetime

from .scoring import compute_score, get_categoria, PESOS_MVP
from .hab_templates import render_hab_html


# ---------------------------------------------------------------------------
# Configuracion de pesos por defecto
# ---------------------------------------------------------------------------

PESOS_DICTAMEN: dict[str, float] = {
    "muro": 0.40,
    "caletera": 0.30,
    "nch3417": 0.20,
    "re7713": 0.10,
}


# ---------------------------------------------------------------------------
# Constructor principal de dictamen
# ---------------------------------------------------------------------------

def build_dictamen(
    proyecto_id: str,
    verificaciones: list[dict],
    datos_hab: dict[str, dict],
    session_id: str,
    revisor_nombre: str = "",
    pesos: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """Construye un dictamen preliminar a partir de las verificaciones ejecutadas.

    Este es el metodo principal del modulo. Recibe los resultados de todas
    las verificaciones y construye un dictamen completo que el revisor
    puede editar antes de firmar.

    Args:
        proyecto_id: ID del proyecto en la base de datos.
        verificaciones: Lista de ResultadoVerificacion serializados (dicts).
            Cada dict debe tener: verificador_id, nombre, resultado, severidad,
            mensaje, datos_utilizados.
        datos_hab: Dict con datos HAB:
            {"muro": {...}, "caletera": {...}}
        session_id: ID de la sesion de revision (para trazabilidad).
        revisor_nombre: Nombre del revisor (opcional, para el dictamen).
        pesos: Pesos por modulo. Si None, usa PESOS_DICTAMEN.

    Returns:
        Dict con todos los campos para insertar en tabla Dictamen:
        {
            "proyecto_id": str,
            "session_id": str,
            "fecha_dictamen": str,
            "score": float,
            "categoria": str,
            "resumen_verificaciones": dict,
            "observaciones_encontradas": list[dict],
            "hab_html": str,
            "dictamen_texto": str,
            "dictamen_preliminar": str,
            "estado": str,
            "revisor_nombre": str,
            "metadata": dict,
        }

    Ejemplo:
        >>> verifs = [
        ...     {"verificador_id": "MURO-ALT-001", "nombre": "Altura muro",
        ...      "resultado": "CUMPLE", "severidad": "INFO", "mensaje": "OK",
        ...      "datos_utilizados": {"altura_muro": 3.0}, "modulo": "muro"},
        ... ]
        >>> datos_hab = {
        ...     "muro": {"altura_muro": 3.0, "tiene_drenaje": True, "fc": 25.0, "fos_vuelco": 1.8},
        ...     "caletera": {"longitud_caletera": 45.0, "ancho_corona": 3.5, "pendiente": 5.0, "espesor": 18.0},
        ... }
        >>> dictamen = build_dictamen("PROY-001", verifs, datos_hab, "SES-001")
    """
    if pesos is None:
        pesos = PESOS_DICTAMEN.copy()

    fecha = datetime.now().isoformat()

    # 1. Contar resultados
    resumen = _contar_resultados(verificaciones)

    # 2. Extraer observaciones (solo las que NO cumplen)
    observaciones = _extraer_observaciones(verificaciones)

    # 3. Calcular score
    score = compute_score(verificaciones, pesos=pesos)
    categoria = get_categoria(score)

    # 4. Generar HAB HTML
    hab_html_parts: list[str] = []
    if "muro" in datos_hab and datos_hab["muro"]:
        try:
            hab_html_parts.append(render_hab_html("muro", datos_hab["muro"]))
        except Exception:
            hab_html_parts.append("<p>Error renderizando muro</p>")
    if "caletera" in datos_hab and datos_hab["caletera"]:
        try:
            hab_html_parts.append(render_hab_html("caletera", datos_hab["caletera"]))
        except Exception:
            hab_html_parts.append("<p>Error renderizando caletera</p>")
    hab_html = "\n".join(hab_html_parts)

    # 5. Generar texto de dictamen
    dictamen_texto = _generar_dictamen_texto(
        proyecto_id=proyecto_id,
        resumen=resumen,
        score=score,
        categoria=categoria,
        observaciones=observaciones,
        revisor_nombre=revisor_nombre,
    )

    # 6. Estado del dictamen
    estado = _determinar_estado(score, observaciones)

    return {
        "proyecto_id": proyecto_id,
        "session_id": session_id,
        "fecha_dictamen": fecha,
        "score": score,
        "categoria": categoria["nombre"],
        "categoria_descripcion": categoria["descripcion"],
        "resumen_verificaciones": resumen,
        "observaciones_encontradas": observaciones,
        "hab_html": hab_html,
        "dictamen_texto": dictamen_texto,
        "dictamen_preliminar": dictamen_texto,  # El revisor edita este campo
        "estado": estado,
        "revisor_nombre": revisor_nombre,
        "metadata": {
            "pesos_usados": pesos,
            "total_verificaciones": len(verificaciones),
            "version_builder": "1.0.0",
        },
    }


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------

def _contar_resultados(verificaciones: list[dict]) -> dict[str, int]:
    """Cuenta verificaciones por resultado.

    Args:
        verificaciones: Lista de verificaciones (dicts).

    Returns:
        Dict con conteo por tipo de resultado y severidad.
    """
    conteo: dict[str, int] = {
        "total": len(verificaciones),
        "cumplen": 0,
        "no_cumplen": 0,
        "no_aplican": 0,
        "sin_evidencia": 0,
        "info": 0,
        "warning": 0,
        "error": 0,
        "critical": 0,
    }

    for v in verificaciones:
        resultado = v.get("resultado", "")
        severidad = v.get("severidad", "INFO").lower()

        if resultado == "CUMPLE":
            conteo["cumplen"] += 1
        elif resultado == "NO_CUMPLE":
            conteo["no_cumplen"] += 1
        elif resultado == "NO_APLICA":
            conteo["no_aplican"] += 1
        elif resultado == "SIN_EVIDENCIA":
            conteo["sin_evidencia"] += 1

        if severidad in conteo:
            conteo[severidad] += 1

    return conteo


def _extraer_observaciones(verificaciones: list[dict]) -> list[dict]:
    """Extrae observaciones (verificaciones que NO cumplen).

    Args:
        verificaciones: Lista de verificaciones.

    Returns:
        Lista de observaciones para levantar.
    """
    observaciones: list[dict] = []
    for v in verificaciones:
        resultado = v.get("resultado", "")
        if resultado in ("NO_CUMPLE", "SIN_EVIDENCIA"):
            observaciones.append({
                "verificador_id": v.get("verificador_id", ""),
                "nombre": v.get("nombre", ""),
                "descripcion": v.get("descripcion", ""),
                "resultado": resultado,
                "severidad": v.get("severidad", "WARNING"),
                "mensaje": v.get("mensaje", ""),
                "datos_utilizados": v.get("datos_utilizados", {}),
            })
    return observaciones


def _generar_dictamen_texto(
    proyecto_id: str,
    resumen: dict[str, int],
    score: float,
    categoria: dict[str, str],
    observaciones: list[dict],
    revisor_nombre: str,
) -> str:
    """Genera el texto del dictamen preliminar.

    Este texto es EDITABLE por el revisor antes de firmar.
    Genera un parrafo estructurado con toda la informacion relevante.

    Args:
        proyecto_id: ID del proyecto.
        resumen: Conteo de resultados.
        score: Score numerico 0-100.
        categoria: Dict con nombre y descripcion de la categoria.
        observaciones: Lista de observaciones.
        revisor_nombre: Nombre del revisor.

    Returns:
        Texto del dictamen preliminar.
    """
    lineas: list[str] = []

    # Encabezado
    lineas.append("=" * 72)
    lineas.append("DICTAMEN PRELIMINAR DE REVISION ESTRUCTURAL")
    lineas.append("=" * 72)
    lineas.append("")
    lineas.append(f"Proyecto ID: {proyecto_id}")
    lineas.append(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    if revisor_nombre:
        lineas.append(f"Revisor: {revisor_nombre}")
    lineas.append("")

    # Resumen ejecutivo
    lineas.append("-" * 72)
    lineas.append("1. RESUMEN EJECUTIVO")
    lineas.append("-" * 72)
    lineas.append("")
    lineas.append(f"Score global: {score:.1f}/100")
    lineas.append(f"Categoria: {categoria['nombre']}")
    lineas.append(f"  {categoria['descripcion']}")
    lineas.append("")
    lineas.append(f"Verificaciones ejecutadas: {resumen['total']}")
    lineas.append(f"  - Cumplen: {resumen['cumplen']}")
    lineas.append(f"  - No cumplen: {resumen['no_cumplen']}")
    lineas.append(f"  - No aplican: {resumen['no_aplican']}")
    lineas.append(f"  - Sin evidencia: {resumen['sin_evidencia']}")
    lineas.append("")

    # Observaciones
    if observaciones:
        lineas.append("-" * 72)
        lineas.append(f"2. OBSERVACIONES A LEVANTAR ({len(observaciones)})")
        lineas.append("-" * 72)
        lineas.append("")

        for i, obs in enumerate(observaciones, start=1):
            lineas.append(f"2.{i} [{obs['severidad']}] {obs['nombre']}")
            lineas.append(f"    ID: {obs['verificador_id']}")
            lineas.append(f"    Resultado: {obs['resultado']}")
            lineas.append(f"    {obs['mensaje']}")
            lineas.append("")
    else:
        lineas.append("-" * 72)
        lineas.append("2. OBSERVACIONES")
        lineas.append("-" * 72)
        lineas.append("")
        lineas.append("No se detectaron observaciones automaticas.")
        lineas.append("El revisor debe validar que la documentacion esta completa.")
        lineas.append("")

    # Recomendacion
    lineas.append("-" * 72)
    lineas.append("3. RECOMENDACION PRELIMINAR")
    lineas.append("-" * 72)
    lineas.append("")
    if score >= 90:
        lineas.append("El proyecto presenta documentacion completa y cumple con")
        lineas.append("los requisitos normativos principales. Se recomienda DICTAMEN")
        lineas.append("FAVORABLE con observaciones menores si las hubiere.")
    elif score >= 75:
        lineas.append("El proyecto presenta documentacion adecuada con observaciones")
        lineas.append("menores que deben ser corregidas. Se recomienda DICTAMEN")
        lineas.append("FAVORABLE condicionado a correccion de observaciones.")
    elif score >= 60:
        lineas.append("El proyecto requiere correcciones significativas antes de")
        lineas.append("emitir dictamen. Se recomienda DEVOLVER para complementacion.")
    else:
        lineas.append("El proyecto presenta falencias graves en la documentacion.")
        lineas.append("Se recomienda DICTAMEN DESFAVORABLE o devolver para")
        lineas.append("completa revision del proyecto.")
    lineas.append("")

    # Nota legal
    lineas.append("-" * 72)
    lineas.append("NOTA IMPORTANTE")
    lineas.append("-" * 72)
    lineas.append("")
    lineas.append("Este dictamen es PRELIMINAR y fue generado asistido por sistema.")
    lineas.append("El revisor estructural debe revisar, editar y validar toda la")
    lineas.append("informacion antes de firmar el dictamen final. Las observaciones")
    lineas.append("automaticas son una guia pero no reemplazan el criterio profesional")
    lineas.append("del revisor.")
    lineas.append("")
    lineas.append("=" * 72)
    lineas.append("[ESPACIO PARA EDICION DEL REVISOR]")
    lineas.append("=" * 72)
    lineas.append("")
    lineas.append("El revisor puede editar este texto antes de emitir el dictamen final.")
    lineas.append("")

    return "\n".join(lineas)


def _determinar_estado(score: float, observaciones: list[dict]) -> str:
    """Determina el estado preliminar del dictamen.

    Args:
        score: Score numerico.
        observaciones: Lista de observaciones.

    Returns:
        Estado preliminar: "PRELIMINAR_FAVORABLE", "PRELIMINAR_CONDICIONADO",
        "PRELIMINAR_DESFAVORABLE", o "REVISION_PENDIENTE".
    """
    if score >= 90 and not any(
        o["severidad"] in ("ERROR", "CRITICAL") for o in observaciones
    ):
        return "PRELIMINAR_FAVORABLE"
    elif score >= 75:
        return "PRELIMINAR_CONDICIONADO"
    elif score >= 60:
        return "REVISION_PENDIENTE"
    else:
        return "PRELIMINAR_DESFAVORABLE"
