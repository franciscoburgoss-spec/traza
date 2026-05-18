"""
Verificadores para caletera HAB (Habitacional).

Modulo de funciones puras que verifican parametros geometricos y
de diseno de caletas (caleteras) segun normativa chilena aplicable
a vivienda social FSEV y manual de carreteras del MOP.

Parametros esperados en datos (dict):
    - longitud_caletera: float - Longitud total en metros
    - ancho_corona: float - Ancho de corona en metros
    - pendiente: float - Pendiente maxima en porcentaje (%)
    - espesor: float - Espesor de capa asfaltica/hormigon en cm
    - tipo_caletera: str - Tipo: "asfaltica", "hormigon", "adoquin", etc.
    - tiene_bermas: bool - Indica si tiene bermas laterales
    - tiene_cunetas: bool - Indica si tiene sistema de cunetas
"""

from typing import Any

from .base import ResultadoVerificacion


# ---------------------------------------------------------------------------
# Verificacion individual: longitud minima
# ---------------------------------------------------------------------------

def verificar_longitud_minima(datos: dict) -> ResultadoVerificacion:
    """Verifica que la longitud de la caletera cumpla el minimo.

    Criterio:
        - longitud >= 20 m: CUMPLE (minimo para considerarse caletera en FSEV)
        - longitud < 20 m: WARNING (podria ser acceso o sendero, no caletera)

    Args:
        datos: Dict con key 'longitud_caletera' (float, en metros).

    Returns:
        ResultadoVerificacion con el estado de la verificacion.
    """
    longitud = datos.get("longitud_caletera")
    datos_usados = {"longitud_caletera": longitud, "longitud_minima": 20.0, "unidad": "m"}

    if longitud is None:
        return ResultadoVerificacion(
            verificador_id="CAL-LON-001",
            nombre="Longitud minima de caletera",
            descripcion="Verifica que la longitud de la caletera sea al menos 20 m.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje="No se especifico la longitud de la caletera. Ingresar manualmente.",
            datos_utilizados=datos_usados,
        )

    try:
        longitud_float = float(longitud)
    except (TypeError, ValueError):
        return ResultadoVerificacion(
            verificador_id="CAL-LON-001",
            nombre="Longitud minima de caletera",
            descripcion="Verifica que la longitud de la caletera sea al menos 20 m.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje=f"La longitud no es un valor numerico valido: {longitud}",
            datos_utilizados=datos_usados,
        )

    datos_usados["longitud_caletera"] = longitud_float

    if longitud_float >= 20.0:
        return ResultadoVerificacion(
            verificador_id="CAL-LON-001",
            nombre="Longitud minima de caletera",
            descripcion="Verifica que la longitud de la caletera sea al menos 20 m.",
            resultado="CUMPLE",
            severidad="INFO",
            mensaje=f"Longitud de caletera: {longitud_float:.1f} m >= 20.0 m minimo. OK.",
            datos_utilizados=datos_usados,
        )
    else:
        return ResultadoVerificacion(
            verificador_id="CAL-LON-001",
            nombre="Longitud minima de caletera",
            descripcion="Verifica que la longitud de la caletera sea al menos 20 m.",
            resultado="NO_CUMPLE",
            severidad="WARNING",
            mensaje=(
                f"Longitud de caletera: {longitud_float:.1f} m < 20.0 m. "
                f"Podria tratarse de un acceso o sendero peatonal mas que de una caletera. "
                f"Verificar clasificacion del elemento en el proyecto."
            ),
            datos_utilizados=datos_usados,
        )


# ---------------------------------------------------------------------------
# Verificacion individual: ancho de corona
# ---------------------------------------------------------------------------

def verificar_ancho_corona(datos: dict) -> ResultadoVerificacion:
    """Verifica que el ancho de corona cumpla el minimo.

    Criterio:
        - ancho >= 3.0 m: CUMPLE (minimo para caletera vehicular FSEV)
        - 2.5 m <= ancho < 3.0 m: WARNING (justificar si es caletera peatonal)
        - ancho < 2.5 m: ERROR (insuficiente)

    Args:
        datos: Dict con key 'ancho_corona' (float, en metros).

    Returns:
        ResultadoVerificacion con el estado de la verificacion.
    """
    ancho = datos.get("ancho_corona")
    datos_usados = {"ancho_corona": ancho, "ancho_minimo": 3.0, "ancho_warning": 2.5, "unidad": "m"}

    if ancho is None:
        return ResultadoVerificacion(
            verificador_id="CAL-ANC-001",
            nombre="Ancho de corona",
            descripcion="Verifica que el ancho de corona de la caletera sea al menos 3.0 m.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje="No se especifico el ancho de corona. Ingresar manualmente.",
            datos_utilizados=datos_usados,
        )

    try:
        ancho_float = float(ancho)
    except (TypeError, ValueError):
        return ResultadoVerificacion(
            verificador_id="CAL-ANC-001",
            nombre="Ancho de corona",
            descripcion="Verifica que el ancho de corona de la caletera sea al menos 3.0 m.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje=f"Ancho de corona no es numerico: {ancho}",
            datos_utilizados=datos_usados,
        )

    datos_usados["ancho_corona"] = ancho_float

    if ancho_float >= 3.0:
        return ResultadoVerificacion(
            verificador_id="CAL-ANC-001",
            nombre="Ancho de corona",
            descripcion="Verifica que el ancho de corona de la caletera sea al menos 3.0 m.",
            resultado="CUMPLE",
            severidad="INFO",
            mensaje=f"Ancho de corona: {ancho_float:.2f} m >= 3.0 m minimo. OK.",
            datos_utilizados=datos_usados,
        )
    elif ancho_float >= 2.5:
        return ResultadoVerificacion(
            verificador_id="CAL-ANC-001",
            nombre="Ancho de corona",
            descripcion="Verifica que el ancho de corona de la caletera sea al menos 3.0 m.",
            resultado="NO_CUMPLE",
            severidad="WARNING",
            mensaje=(
                f"Ancho de corona: {ancho_float:.2f} m < 3.0 m pero >= 2.5 m. "
                f"Verificar si la caletera es de uso peatonal o vehicular. "
                f"Si es vehicular, requiere justificacion tecnica."
            ),
            datos_utilizados=datos_usados,
        )
    else:
        return ResultadoVerificacion(
            verificador_id="CAL-ANC-001",
            nombre="Ancho de corona",
            descripcion="Verifica que el ancho de corona de la caletera sea al menos 3.0 m.",
            resultado="NO_CUMPLE",
            severidad="ERROR",
            mensaje=(
                f"Ancho de corona: {ancho_float:.2f} m < 2.5 m. INSUFICIENTE. "
                f"El ancho minimo para caletera vehicular es 3.0 m segun manual de carreteras MOP. "
                f"Levantar observacion."
            ),
            datos_utilizados=datos_usados,
        )


# ---------------------------------------------------------------------------
# Verificacion individual: pendiente maxima
# ---------------------------------------------------------------------------

def verificar_pendiente_maxima(datos: dict) -> ResultadoVerificacion:
    """Verifica que la pendiente maxima de la caletera este dentro del limite.

    Criterio:
        - pendiente <= 8%: CUMPLE (maximo recomendado para caletas FSEV)
        - 8% < pendiente <= 12%: WARNING (excesiva, revisar drenaje)
        - pendiente > 12%: ERROR (requiere estudios especiales)

    Args:
        datos: Dict con key 'pendiente' (float, en porcentaje %).

    Returns:
        ResultadoVerificacion con el estado de la verificacion.
    """
    pendiente = datos.get("pendiente")
    datos_usados = {"pendiente": pendiente, "pendiente_maxima": 8.0, "pendiente_error": 12.0, "unidad": "%"}

    if pendiente is None:
        return ResultadoVerificacion(
            verificador_id="CAL-PEN-001",
            nombre="Pendiente maxima",
            descripcion="Verifica que la pendiente maxima de la caletera no exceda 8%.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje="No se especifico la pendiente maxima. Ingresar manualmente.",
            datos_utilizados=datos_usados,
        )

    try:
        pendiente_float = float(pendiente)
    except (TypeError, ValueError):
        return ResultadoVerificacion(
            verificador_id="CAL-PEN-001",
            nombre="Pendiente maxima",
            descripcion="Verifica que la pendiente maxima de la caletera no exceda 8%.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje=f"Pendiente no es numerica: {pendiente}",
            datos_utilizados=datos_usados,
        )

    datos_usados["pendiente"] = pendiente_float

    if pendiente_float <= 8.0:
        return ResultadoVerificacion(
            verificador_id="CAL-PEN-001",
            nombre="Pendiente maxima",
            descripcion="Verifica que la pendiente maxima de la caletera no exceda 8%.",
            resultado="CUMPLE",
            severidad="INFO",
            mensaje=f"Pendiente maxima: {pendiente_float:.1f}% <= 8.0%. OK.",
            datos_utilizados=datos_usados,
        )
    elif pendiente_float <= 12.0:
        return ResultadoVerificacion(
            verificador_id="CAL-PEN-001",
            nombre="Pendiente maxima",
            descripcion="Verifica que la pendiente maxima de la caletera no exceda 8%.",
            resultado="NO_CUMPLE",
            severidad="WARNING",
            mensaje=(
                f"Pendiente maxima: {pendiente_float:.1f}% > 8.0%. "
                f"Pendiente excesiva para caletera FSEV. Verificar: "
                f"(1) sistema de drenaje, (2) tipo de pavimento, (3) necesidad de muros de contencion. "
                f"Maximo aceptable sin estudios especiales: 12.0%."
            ),
            datos_utilizados=datos_usados,
        )
    else:
        return ResultadoVerificacion(
            verificador_id="CAL-PEN-001",
            nombre="Pendiente maxima",
            descripcion="Verifica que la pendiente maxima de la caletera no exceda 8%.",
            resultado="NO_CUMPLE",
            severidad="ERROR",
            mensaje=(
                f"Pendiente maxima: {pendiente_float:.1f}% > 12.0%. "
                f"Pendiente excesiva que requiere estudios geotecnicos especiales "
                f"y justificacion de estabilidad de taludes. Levantar observacion critica."
            ),
            datos_utilizados=datos_usados,
        )


# ---------------------------------------------------------------------------
# Verificacion individual: espesor minimo
# ---------------------------------------------------------------------------

def verificar_espesor_minimo(datos: dict) -> ResultadoVerificacion:
    """Verifica que el espesor de la capa de rodadura cumpla el minimo.

    Criterio:
        - espesor >= 15 cm: CUMPLE (minimo para pavimento estructural FSEV)
        - 10 cm <= espesor < 15 cm: WARNING (solo para pavimento no estructural)
        - espesor < 10 cm: ERROR (insuficiente)

    Args:
        datos: Dict con key 'espesor' (float, en cm).

    Returns:
        ResultadoVerificacion con el estado de la verificacion.
    """
    espesor = datos.get("espesor")
    datos_usados = {"espesor": espesor, "espesor_minimo": 15.0, "espesor_warning": 10.0, "unidad": "cm"}

    if espesor is None:
        return ResultadoVerificacion(
            verificador_id="CAL-ESP-001",
            nombre="Espesor minimo de capa",
            descripcion="Verifica que el espesor de la capa de rodadura sea al menos 15 cm.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje="No se especifico el espesor de la capa de rodadura. Ingresar manualmente.",
            datos_utilizados=datos_usados,
        )

    try:
        espesor_float = float(espesor)
    except (TypeError, ValueError):
        return ResultadoVerificacion(
            verificador_id="CAL-ESP-001",
            nombre="Espesor minimo de capa",
            descripcion="Verifica que el espesor de la capa de rodadura sea al menos 15 cm.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje=f"Espesor no es numerico: {espesor}",
            datos_utilizados=datos_usados,
        )

    datos_usados["espesor"] = espesor_float

    if espesor_float >= 15.0:
        return ResultadoVerificacion(
            verificador_id="CAL-ESP-001",
            nombre="Espesor minimo de capa",
            descripcion="Verifica que el espesor de la capa de rodadura sea al menos 15 cm.",
            resultado="CUMPLE",
            severidad="INFO",
            mensaje=f"Espesor de capa: {espesor_float:.1f} cm >= 15.0 cm minimo. OK.",
            datos_utilizados=datos_usados,
        )
    elif espesor_float >= 10.0:
        return ResultadoVerificacion(
            verificador_id="CAL-ESP-001",
            nombre="Espesor minimo de capa",
            descripcion="Verifica que el espesor de la capa de rodadura sea al menos 15 cm.",
            resultado="NO_CUMPLE",
            severidad="WARNING",
            mensaje=(
                f"Espesor de capa: {espesor_float:.1f} cm < 15.0 cm pero >= 10.0 cm. "
                f"Verificar si el pavimento es estructural o de uso peatonal/leve. "
                f"Para pavimento estructural vehicular se requieren 15 cm minimos."
            ),
            datos_utilizados=datos_usados,
        )
    else:
        return ResultadoVerificacion(
            verificador_id="CAL-ESP-001",
            nombre="Espesor minimo de capa",
            descripcion="Verifica que el espesor de la capa de rodadura sea al menos 15 cm.",
            resultado="NO_CUMPLE",
            severidad="ERROR",
            mensaje=(
                f"Espesor de capa: {espesor_float:.1f} cm < 10.0 cm. INSUFICIENTE. "
                f"El espesor minimo para cualquier tipo de pavimento es 10 cm (adoquin/hormigon). "
                f"Para pavimento asfaltico estructural: 15 cm minimos. Levantar observacion."
            ),
            datos_utilizados=datos_usados,
        )


# ---------------------------------------------------------------------------
# Verificacion completa de la caletera: ejecuta todas las verificaciones
# ---------------------------------------------------------------------------

def verificar_caletera_completo(datos: dict) -> list[ResultadoVerificacion]:
    """Ejecuta TODAS las verificaciones de la caletera.

    Esta funcion agrupa las 4 verificaciones individuales y retorna
    la lista completa de resultados. Es la entrada principal para
    el dictamen builder.

    Args:
        datos: Dict con los parametros de la caletera:
            - longitud_caletera: float (m)
            - ancho_corona: float (m)
            - pendiente: float (%)
            - espesor: float (cm)

    Returns:
        Lista de ResultadoVerificacion con todas las verificaciones.

    Ejemplo:
        >>> datos = {
        ...     "longitud_caletera": 45.0,
        ...     "ancho_corona": 3.5,
        ...     "pendiente": 6.0,
        ...     "espesor": 18.0,
        ... }
        >>> resultados = verificar_caletera_completo(datos)
        >>> len(resultados)
        4
    """
    return [
        verificar_longitud_minima(datos),
        verificar_ancho_corona(datos),
        verificar_pendiente_maxima(datos),
        verificar_espesor_minimo(datos),
    ]
