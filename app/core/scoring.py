"""
Sistema de scoring para dictamen de revision estructural.

Calcula un puntaje ponderado 0-100 basado en los resultados de las
verificaciones normativas. El score sirve para PRIORIZAR la revision
pero NUNCA reemplaza la decision del revisor estructural.

Pesos por defecto del MVP:
    - muro: 40% (es el elemento mas critico y comun en HAB)
    - caletera: 30% (segundo elemento mas frecuente)
    - nch3417: 20% (cumplimiento normativo general)
    - re7713: 10% (itemizacion FRANCISCO BURGOS S.)

Categorias:
    90-100: Excelente - Proyecto bien documentado
    75-89:  Bueno - Observaciones menores
    60-74:  Regular - Requiere observaciones que deben corregirse
    0-59:   Deficiente - Proyecto con falencias graves
"""

from typing import Optional


# ---------------------------------------------------------------------------
# Pesos por defecto para el MVP
# ---------------------------------------------------------------------------

PESOS_MVP: dict[str, float] = {
    "muro": 0.40,
    "caletera": 0.30,
    "nch3417": 0.20,
    "re7713": 0.10,
}

# ---------------------------------------------------------------------------
# Categorias de calificacion
# ---------------------------------------------------------------------------

CATEGORIAS: list[tuple[float, str, str]] = [
    (90.0, "Excelente", "Proyecto bien documentado, cumple con la mayoria de los requisitos normativos."),
    (75.0, "Bueno", "Observaciones menores que deben ser corregidas antes del dictamen favorable."),
    (60.0, "Regular", "Requiere observaciones significativas que deben ser corregidas y re-revisadas."),
    (0.0, "Deficiente", "Proyecto con falencias graves. Se recomienda devolver para completa revision."),
]


def compute_score(
    verificaciones: list[dict],
    pesos: Optional[dict[str, float]] = None,
) -> float:
    """Calcula el score ponderado 0-100 del proyecto.

    El score se calcula como promedio ponderado del porcentaje de cumplimiento
    de cada modulo de verificacion. Cada verificacion en la lista debe tener
    los campos 'modulo' y 'score_porcentaje' en sus datos.

    Si una verificacion no tiene score_porcentaje, se calcula a partir del
    ratio de CUMPLE vs total.

    Args:
        verificaciones: Lista de ResultadoVerificacion o dicts con:
            - modulo: str - Identificador del modulo (muro, caletera, nch3417, re7713)
            - resultado: str - CUMPLE/NO_CUMPLE/NO_APLICA/SIN_EVIDENCIA
            - score_porcentaje: float (opcional) - Score del modulo
        pesos: Dict con pesos por modulo. Si es None, usa PESOS_MVP.

    Returns:
        Score float entre 0.0 y 100.0.

    Ejemplo:
        >>> verifs = [
        ...     {"modulo": "muro", "resultado": "CUMPLE", "score_porcentaje": 100.0},
        ...     {"modulo": "caletera", "resultado": "CUMPLE", "score_porcentaje": 100.0},
        ...     {"modulo": "nch3417", "resultado": "CUMPLE", "score_porcentaje": 80.0},
        ...     {"modulo": "re7713", "resultado": "NO_CUMPLE", "score_porcentaje": 50.0},
        ... ]
        >>> compute_score(verifs)
        90.0
    """
    if pesos is None:
        pesos = PESOS_MVP.copy()

    if not verificaciones:
        return 0.0

    # Agrupar verificaciones por modulo y calcular score de cada uno
    scores_por_modulo: dict[str, float] = {}
    cuenta_por_modulo: dict[str, int] = {}

    for v in verificaciones:
        # Extraer modulo
        modulo = v.get("modulo", "")
        if not modulo:
            # Intentar extraer del verificador_id
            vid = v.get("verificador_id", "")
            if vid.startswith("MURO"):
                modulo = "muro"
            elif vid.startswith("CAL"):
                modulo = "caletera"
            elif vid.startswith("NCh3417"):
                modulo = "nch3417"
            elif vid.startswith("RE7713"):
                modulo = "re7713"
            else:
                continue  # No sabemos de que modulo es

        # Si ya tenemos score_porcentaje, usarlo
        score_porcentaje = v.get("score_porcentaje")
        if score_porcentaje is not None:
            if modulo not in scores_por_modulo:
                scores_por_modulo[modulo] = 0.0
                cuenta_por_modulo[modulo] = 0
            scores_por_modulo[modulo] += float(score_porcentaje)
            cuenta_por_modulo[modulo] += 1
        else:
            # Calcular score a partir del resultado
            resultado = v.get("resultado", "SIN_EVIDENCIA")
            if modulo not in scores_por_modulo:
                scores_por_modulo[modulo] = 0.0
                cuenta_por_modulo[modulo] = 0
            if resultado == "CUMPLE":
                scores_por_modulo[modulo] += 100.0
            elif resultado == "NO_CUMPLE":
                scores_por_modulo[modulo] += 0.0
            elif resultado == "NO_APLICA":
                scores_por_modulo[modulo] += 100.0  # No aplica = no penaliza
            elif resultado == "SIN_EVIDENCIA":
                scores_por_modulo[modulo] += 0.0
            cuenta_por_modulo[modulo] += 1

    # Promediar scores por modulo
    for modulo in scores_por_modulo:
        if cuenta_por_modulo[modulo] > 0:
            scores_por_modulo[modulo] /= cuenta_por_modulo[modulo]

    # Calcular score ponderado global (solo sobre modulos con verificaciones)
    score_total = 0.0
    peso_total = 0.0

    for modulo, peso in pesos.items():
        if modulo in scores_por_modulo:
            score_total += scores_por_modulo[modulo] * peso
            peso_total += peso
        # Si no hay verificaciones de este modulo, no se incluye (no penaliza)

    # Normalizar si no todos los pesos suman 1.0
    if peso_total > 0:
        score_final = score_total / peso_total
    else:
        score_final = 0.0

    return round(min(100.0, max(0.0, score_final)), 1)


def get_categoria(score: float) -> dict[str, str]:
    """Obtiene la categoria y descripcion para un score dado.

    Args:
        score: Score numerico 0-100.

    Returns:
        Dict con 'nombre' y 'descripcion' de la categoria.

    Ejemplo:
        >>> get_categoria(92.5)
        {'nombre': 'Excelente', 'descripcion': 'Proyecto bien documentado...'}
        >>> get_categoria(45.0)
        {'nombre': 'Deficiente', 'descripcion': 'Proyecto con falencias graves...'}
    """
    for umbral, nombre, descripcion in CATEGORIAS:
        if score >= umbral:
            return {"nombre": nombre, "descripcion": descripcion}
    return {"nombre": "Deficiente", "descripcion": CATEGORIAS[-1][2]}


def compute_score_from_extractors(
    resultados_extractor: dict[str, dict],
    pesos: Optional[dict[str, float]] = None,
) -> float:
    """Calcula score directamente desde resultados de extractores.

    Este metodo es util cuando se tienen los resultados de NCh3417Extractor
    y RE7713Extractor que ya incluyen score_porcentaje en sus structured_data.

    Args:
        resultados_extractor: Dict con resultados de cada extractor:
            {"nch3417": {"score_porcentaje": 85.0}, "re7713": {...}}
        pesos: Pesos por modulo (usa PESOS_MVP por defecto).

    Returns:
        Score float 0-100.
    """
    if pesos is None:
        pesos = PESOS_MVP.copy()

    score_total = 0.0
    peso_total = 0.0

    for modulo, peso in pesos.items():
        resultado = resultados_extractor.get(modulo, {})
        score_modulo = resultado.get("score_porcentaje", 0.0)
        score_total += score_modulo * peso
        peso_total += peso

    if peso_total > 0:
        return round(min(100.0, max(0.0, score_total / peso_total)), 1)
    return 0.0
