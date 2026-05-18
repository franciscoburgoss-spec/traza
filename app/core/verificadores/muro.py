"""
Verificadores para muro de contencion HAB (Habitacional).

Modulo de funciones puras que verifican parametros geometricos,
materiales y estabilidad de muros de contencion segun normativa
chilena aplicable a vivienda social FSEV.

Cada funcion recibe un dict con los datos del muro y retorna un
ResultadoVerificacion. No tienen side effects.

Parametros esperados en datos (dict):
    - altura_muro: float - Altura del muro en metros
    - tiene_drenaje: bool - Indica si el muro tiene sistema de drenaje
    - fc: float - Resistencia a compresion del hormigon en MPa
    - fos_vuelco: float - Factor de seguridad contra vuelco
    - espesor_muro: float - Espesor del muro en metros (opcional)
    - longitud_muro: float - Longitud del muro en metros (opcional)
    - tipo_cimentacion: str - Tipo de cimentacion (opcional)
"""

from typing import Any

from .base import ResultadoVerificacion


# ---------------------------------------------------------------------------
# Verificacion individual: altura del muro
# ---------------------------------------------------------------------------

def verificar_altura_muro(datos: dict) -> ResultadoVerificacion:
    """Verifica que la altura del muro este dentro de limites razonables.

    Criterios:
        - altura <= 4.0 m: OK (CUMPLE)
        - 4.0 m < altura <= 6.0 m: WARNING (excede lo comun en FSEV)
        - altura > 6.0 m: ERROR (requiere justificacion especial)

    Args:
        datos: Dict con key 'altura_muro' (float, en metros).

    Returns:
        ResultadoVerificacion con el estado de la verificacion.
    """
    altura = datos.get("altura_muro")
    datos_usados = {"altura_muro": altura, "limite_warning": 4.0, "limite_error": 6.0}

    if altura is None:
        return ResultadoVerificacion(
            verificador_id="MURO-ALT-001",
            nombre="Altura de muro",
            descripcion="Verifica que la altura del muro de contencion este dentro de limites aceptables para vivienda social FSEV.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje="No se especifico la altura del muro en los datos. Ingresar manualmente.",
            datos_utilizados=datos_usados,
        )

    try:
        altura_float = float(altura)
    except (TypeError, ValueError):
        return ResultadoVerificacion(
            verificador_id="MURO-ALT-001",
            nombre="Altura de muro",
            descripcion="Verifica que la altura del muro de contencion este dentro de limites aceptables para vivienda social FSEV.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje=f"La altura del muro no es un valor numerico valido: {altura}",
            datos_utilizados=datos_usados,
        )

    datos_usados["altura_muro"] = altura_float

    if altura_float <= 4.0:
        return ResultadoVerificacion(
            verificador_id="MURO-ALT-001",
            nombre="Altura de muro",
            descripcion="Verifica que la altura del muro de contencion este dentro de limites aceptables para vivienda social FSEV.",
            resultado="CUMPLE",
            severidad="INFO",
            mensaje=f"Altura de muro {altura_float:.2f} m dentro del limite recomendado (<= 4.0 m).",
            datos_utilizados=datos_usados,
        )
    elif altura_float <= 6.0:
        return ResultadoVerificacion(
            verificador_id="MURO-ALT-001",
            nombre="Altura de muro",
            descripcion="Verifica que la altura del muro de contencion este dentro de limites aceptables para vivienda social FSEV.",
            resultado="NO_CUMPLE",
            severidad="WARNING",
            mensaje=(
                f"Altura de muro {altura_float:.2f} m excede el limite comun "
                f"para FSEV (4.0 m). Verificar si esta justificado tecnicamente "
                f"y cuenta con aprobacion de Excmo. Consejo Regional. "
                f"Maximo aceptable sin justificacion especial: 6.0 m."
            ),
            datos_utilizados=datos_usados,
        )
    else:
        return ResultadoVerificacion(
            verificador_id="MURO-ALT-001",
            nombre="Altura de muro",
            descripcion="Verifica que la altura del muro de contencion este dentro de limites aceptables para vivienda social FSEV.",
            resultado="NO_CUMPLE",
            severidad="ERROR",
            mensaje=(
                f"Altura de muro {altura_float:.2f} m excede el maximo permitido (6.0 m). "
                f"Requiere justificacion especial y aprobacion del Excmo. Consejo Regional. "
                f"Revisar DS 60 articulo 2.3."
            ),
            datos_utilizados=datos_usados,
        )


# ---------------------------------------------------------------------------
# Verificacion individual: drenaje del muro
# ---------------------------------------------------------------------------

def verificar_drenaje_muro(datos: dict) -> ResultadoVerificacion:
    """Verifica que el muro tenga sistema de drenaje si la altura lo requiere.

    Criterio:
        - Si altura > 2.0 m: drenaje obligatorio
        - Si altura <= 2.0 m: drenaje recomendado pero no obligatorio

    Args:
        datos: Dict con keys 'altura_muro' (float) y 'tiene_drenaje' (bool).

    Returns:
        ResultadoVerificacion con el estado del drenaje.
    """
    altura = datos.get("altura_muro")
    tiene_drenaje = datos.get("tiene_drenaje")
    datos_usados = {"altura_muro": altura, "tiene_drenaje": tiene_drenaje, "umbral_drenaje": 2.0}

    if altura is None:
        return ResultadoVerificacion(
            verificador_id="MURO-DRE-001",
            nombre="Drenaje de muro",
            descripcion="Verifica la existencia de sistema de drenaje para muros de altura superior a 2.0 m.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje="No se especifico la altura del muro. No se puede verificar el requisito de drenaje.",
            datos_utilizados=datos_usados,
        )

    try:
        altura_float = float(altura)
    except (TypeError, ValueError):
        return ResultadoVerificacion(
            verificador_id="MURO-DRE-001",
            nombre="Drenaje de muro",
            descripcion="Verifica la existencia de sistema de drenaje para muros de altura superior a 2.0 m.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje=f"Altura del muro no es numerica: {altura}",
            datos_utilizados=datos_usados,
        )

    datos_usados["altura_muro"] = altura_float

    # Muro bajo: drenaje recomendado pero no obligatorio
    if altura_float <= 2.0:
        if tiene_drenaje is True:
            return ResultadoVerificacion(
                verificador_id="MURO-DRE-001",
                nombre="Drenaje de muro",
                descripcion="Verifica la existencia de sistema de drenaje para muros de altura superior a 2.0 m.",
                resultado="CUMPLE",
                severidad="INFO",
                mensaje=f"Muro de {altura_float:.2f} m (<= 2.0 m). Drenaje presente (recomendado, no obligatorio).",
                datos_utilizados=datos_usados,
            )
        else:
            return ResultadoVerificacion(
                verificador_id="MURO-DRE-001",
                nombre="Drenaje de muro",
                descripcion="Verifica la existencia de sistema de drenaje para muros de altura superior a 2.0 m.",
                resultado="CUMPLE",
                severidad="INFO",
                mensaje=f"Muro de {altura_float:.2f} m (<= 2.0 m). Drenaje no requerido, aunque es recomendable.",
                datos_utilizados=datos_usados,
            )

    # Muro alto: drenaje obligatorio
    if altura_float > 2.0:
        if tiene_drenaje is True:
            return ResultadoVerificacion(
                verificador_id="MURO-DRE-001",
                nombre="Drenaje de muro",
                descripcion="Verifica la existencia de sistema de drenaje para muros de altura superior a 2.0 m.",
                resultado="CUMPLE",
                severidad="INFO",
                mensaje=f"Muro de {altura_float:.2f} m (> 2.0 m) cuenta con sistema de drenaje. OK.",
                datos_utilizados=datos_usados,
            )
        elif tiene_drenaje is False:
            return ResultadoVerificacion(
                verificador_id="MURO-DRE-001",
                nombre="Drenaje de muro",
                descripcion="Verifica la existencia de sistema de drenaje para muros de altura superior a 2.0 m.",
                resultado="NO_CUMPLE",
                severidad="ERROR",
                mensaje=(
                    f"Muro de {altura_float:.2f} m (> 2.0 m) NO cuenta con sistema de drenaje. "
                    f"El drenaje es obligatorio para muros mayores a 2.0 m segun buenas practicas "
                    f"y manual de carreteras del MOP. Levantar observacion."
                ),
                datos_utilizados=datos_usados,
            )
        else:
            return ResultadoVerificacion(
                verificador_id="MURO-DRE-001",
                nombre="Drenaje de muro",
                descripcion="Verifica la existencia de sistema de drenaje para muros de altura superior a 2.0 m.",
                resultado="SIN_EVIDENCIA",
                severidad="ERROR",
                mensaje=(
                    f"Muro de {altura_float:.2f} m (> 2.0 m). No se especifica si tiene drenaje. "
                    f"Revisar planos y memoria de calculo. Levantar observacion si no se acredita."
                ),
                datos_utilizados=datos_usados,
            )

    # Fallback (nunca deberia llegar aqui)
    return ResultadoVerificacion(
        verificador_id="MURO-DRE-001",
        nombre="Drenaje de muro",
        descripcion="Verifica la existencia de sistema de drenaje para muros de altura superior a 2.0 m.",
        resultado="SIN_EVIDENCIA",
        severidad="WARNING",
        mensaje="No se pudo determinar el estado del drenaje. Revisar manualmente.",
        datos_utilizados=datos_usados,
    )


# ---------------------------------------------------------------------------
# Verificacion individual: resistencia del hormigon (f'c)
# ---------------------------------------------------------------------------

def verificar_fc_muro(datos: dict) -> ResultadoVerificacion:
    """Verifica que la resistencia a compresion del hormigon cumpla el minimo.

    Criterio:
        - f'c >= 20 MPa: CUMPLE (minimo para hormigon armado en estructuras)
        - f'c < 20 MPa: NO_CUMPLE
        - Si no se especifica: SIN_EVIDENCIA

    Args:
        datos: Dict con key 'fc' (float, en MPa).

    Returns:
        ResultadoVerificacion con el estado de f'c.
    """
    fc = datos.get("fc")
    datos_usados = {"fc": fc, "fc_minimo": 20.0, "unidad": "MPa"}

    if fc is None:
        return ResultadoVerificacion(
            verificador_id="MURO-FC-001",
            nombre="Resistencia del hormigon (f'c)",
            descripcion="Verifica que la resistencia a compresion del hormigon del muro sea al menos 20 MPa.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje="No se especifico f'c del hormigon. Valor requerido segun NCh 430 y DS 60.",
            datos_utilizados=datos_usados,
        )

    try:
        fc_float = float(fc)
    except (TypeError, ValueError):
        return ResultadoVerificacion(
            verificador_id="MURO-FC-001",
            nombre="Resistencia del hormigon (f'c)",
            descripcion="Verifica que la resistencia a compresion del hormigon del muro sea al menos 20 MPa.",
            resultado="SIN_EVIDENCIA",
            severidad="ERROR",
            mensaje=f"f'c no es un valor numerico valido: {fc}",
            datos_utilizados=datos_usados,
        )

    datos_usados["fc"] = fc_float

    if fc_float >= 20.0:
        return ResultadoVerificacion(
            verificador_id="MURO-FC-001",
            nombre="Resistencia del hormigon (f'c)",
            descripcion="Verifica que la resistencia a compresion del hormigon del muro sea al menos 20 MPa.",
            resultado="CUMPLE",
            severidad="INFO",
            mensaje=f"f'c = {fc_float:.1f} MPa >= 20.0 MPa minimo requerido. OK.",
            datos_utilizados=datos_usados,
        )
    else:
        return ResultadoVerificacion(
            verificador_id="MURO-FC-001",
            nombre="Resistencia del hormigon (f'c)",
            descripcion="Verifica que la resistencia a compresion del hormigon del muro sea al menos 20 MPa.",
            resultado="NO_CUMPLE",
            severidad="ERROR",
            mensaje=(
                f"f'c = {fc_float:.1f} MPa < 20.0 MPa minimo requerido por NCh 430 y DS 60. "
                f"El hormigon para elementos estructurales en vivienda social "
                f"debe ser H-20 como minimo. Levantar observacion."
            ),
            datos_utilizados=datos_usados,
        )


# ---------------------------------------------------------------------------
# Verificacion individual: estabilidad contra vuelco (FOS)
# ---------------------------------------------------------------------------

def verificar_estabilidad_vuelco(datos: dict) -> ResultadoVerificacion:
    """Verifica el factor de seguridad contra vuelco del muro.

    Criterio:
        - FOS >= 1.5: CUMPLE (minimo aceptable para estado limite de servicio)
        - 1.3 <= FOS < 1.5: WARNING (bajo, revisar)
        - FOS < 1.3: ERROR (inestable, NO_CUMPLE)

    Args:
        datos: Dict con key 'fos_vuelco' (float, factor de seguridad).

    Returns:
        ResultadoVerificacion con el estado de estabilidad.
    """
    fos = datos.get("fos_vuelco")
    datos_usados = {
        "fos_vuelco": fos,
        "fos_minimo_cumple": 1.5,
        "fos_minimo_warning": 1.3,
    }

    if fos is None:
        return ResultadoVerificacion(
            verificador_id="MURO-VOL-001",
            nombre="Estabilidad contra vuelco",
            descripcion="Verifica que el factor de seguridad contra vuelco del muro sea al menos 1.5.",
            resultado="SIN_EVIDENCIA",
            severidad="CRITICAL",
            mensaje=(
                "No se especifico el factor de seguridad contra vuelco. "
                "Este es un parametro critico para la estabilidad del muro. "
                "Revisar memoria de calculo y levantar observacion."
            ),
            datos_utilizados=datos_usados,
        )

    try:
        fos_float = float(fos)
    except (TypeError, ValueError):
        return ResultadoVerificacion(
            verificador_id="MURO-VOL-001",
            nombre="Estabilidad contra vuelco",
            descripcion="Verifica que el factor de seguridad contra vuelco del muro sea al menos 1.5.",
            resultado="SIN_EVIDENCIA",
            severidad="CRITICAL",
            mensaje=f"FOS contra vuelco no es numerico: {fos}",
            datos_utilizados=datos_usados,
        )

    datos_usados["fos_vuelco"] = fos_float

    if fos_float >= 1.5:
        return ResultadoVerificacion(
            verificador_id="MURO-VOL-001",
            nombre="Estabilidad contra vuelco",
            descripcion="Verifica que el factor de seguridad contra vuelco del muro sea al menos 1.5.",
            resultado="CUMPLE",
            severidad="INFO",
            mensaje=f"FOS contra vuelco = {fos_float:.2f} >= 1.50. OK.",
            datos_utilizados=datos_usados,
        )
    elif fos_float >= 1.3:
        return ResultadoVerificacion(
            verificador_id="MURO-VOL-001",
            nombre="Estabilidad contra vuelco",
            descripcion="Verifica que el factor de seguridad contra vuelco del muro sea al menos 1.5.",
            resultado="NO_CUMPLE",
            severidad="WARNING",
            mensaje=(
                f"FOS contra vuelco = {fos_float:.2f}. Valor bajo (minimo recomendado: 1.50). "
                f"Se acepta provisionalmente pero se recomienda revisar el calculo. "
                f"Verificar cargas y presiones de tierra consideradas."
            ),
            datos_utilizados=datos_usados,
        )
    else:
        return ResultadoVerificacion(
            verificador_id="MURO-VOL-001",
            nombre="Estabilidad contra vuelco",
            descripcion="Verifica que el factor de seguridad contra vuelco del muro sea al menos 1.5.",
            resultado="NO_CUMPLE",
            severidad="CRITICAL",
            mensaje=(
                f"FOS contra vuelco = {fos_float:.2f} < 1.30. INESTABLE. "
                f"El muro NO cumple con el minimo de estabilidad. "
                f"Se requiere rediseno urgente. Verificar: "
                f"(1) peso del muro, (2) presion de tierra activa, "
                f"(3) sobrecargas, (4) dimensiones de la base."
            ),
            datos_utilizados=datos_usados,
        )


# ---------------------------------------------------------------------------
# Verificacion completa del muro: ejecuta todas las verificaciones
# ---------------------------------------------------------------------------

def verificar_muro_completo(datos: dict) -> list[ResultadoVerificacion]:
    """Ejecuta TODAS las verificaciones del muro de contencion.

    Esta funcion agrupa las 4 verificaciones individuales y retorna
    la lista completa de resultados. Es la entrada principal para
    el dictamen builder.

    Args:
        datos: Dict con los parametros del muro:
            - altura_muro: float (m)
            - tiene_drenaje: bool
            - fc: float (MPa)
            - fos_vuelco: float

    Returns:
        Lista de ResultadoVerificacion con todas las verificaciones.

    Ejemplo:
        >>> datos = {
        ...     "altura_muro": 3.5,
        ...     "tiene_drenaje": True,
        ...     "fc": 25.0,
        ...     "fos_vuelco": 1.8,
        ... }
        >>> resultados = verificar_muro_completo(datos)
        >>> len(resultados)
        4
    """
    return [
        verificar_altura_muro(datos),
        verificar_drenaje_muro(datos),
        verificar_fc_muro(datos),
        verificar_estabilidad_vuelco(datos),
    ]
