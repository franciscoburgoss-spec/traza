"""
Plantillas y datos para HAB (Habitacional) - muros y caletas.

Define las plantillas de datos con valores por defecto y la funcion de
renderizado HTML para presentar los resultados de verificacion HAB en
la interfaz del revisor.

Las plantillas contienen todos los campos necesarios para que el revisor
complete la revision de un proyecto HAB tipico de vivienda social FSEV.
"""

from typing import Any, Optional

# ---------------------------------------------------------------------------
# Jinja2 es opcional - si no esta disponible, se usa un renderizado basico
# ---------------------------------------------------------------------------
try:
    from jinja2 import Template
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


# ---------------------------------------------------------------------------
# Plantilla de datos: Muro de contencion HAB
# ---------------------------------------------------------------------------

PLANTILLA_MURO: dict[str, Any] = {
    # Identificacion
    "tipo_elemento": "muro_contencion",
    "nombre": "Muro de contencion",
    "descripcion": "",

    # Geometria
    "altura_muro": None,         # float, metros
    "longitud_muro": None,       # float, metros
    "espesor_muro": None,        # float, metros
    "ancho_base": None,          # float, metros
    "espesor_base": None,        # float, metros
    "inclinacion": 0.0,          # float, grados de inclinacion (0 = vertical)

    # Materiales
    "fc": None,                  # float, MPa - resistencia hormigon
    "fy": None,                  # float, MPa - resistencia acero
    "tipo_hormigon": "H-20",     # str - H-20, H-25, H-30
    "tipo_acero": "A63-42H",     # str - A63-42H, A44-28H
    "recubrimiento": 0.05,       # float, metros

    # Drenaje
    "tiene_drenaje": None,       # bool
    "tipo_drenaje": "",          # str - tubular, geodren, etc.
    "tiene_impermeabilizacion": False,  # bool

    # Estabilidad
    "fos_vuelco": None,          # float, factor de seguridad
    "fos_deslizamiento": None,   # float
    "fos_hundimiento": None,     # float
    "presion_tierra_activa": None,  # float, kPa
    "presion_tierra_pasiva": None,  # float, kPa
    "peso_especifico_relleno": 18.0,  # float, kN/m3

    # Cimentacion
    "tipo_cimentacion": "zapata",  # str - zapata, losa, pilotes
    "profundidad_cimentacion": None,  # float, metros
    "capacidad_portante_suelo": None,  # float, kPa

    # Observaciones del revisor
    "observaciones_revisor": "",
    "cumple_global": None,       # bool - decision final del revisor
}


# ---------------------------------------------------------------------------
# Plantilla de datos: Caletera HAB
# ---------------------------------------------------------------------------

PLANTILLA_CALETERA: dict[str, Any] = {
    # Identificacion
    "tipo_elemento": "caletera",
    "nombre": "Caletera",
    "descripcion": "",

    # Geometria
    "longitud_caletera": None,   # float, metros
    "ancho_corona": None,        # float, metros
    "pendiente": None,           # float, porcentaje (%)
    "espesor": None,             # float, cm
    "ancho_berma_izq": None,     # float, metros
    "ancho_berma_der": None,     # float, metros

    # Tipo de pavimento
    "tipo_caletera": "asfaltica",  # str - asfaltica, hormigon, adoquin, ripio
    "tipo_subbase": "",          # str
    "espesor_subbase": None,     # float, cm
    "tipo_base": "",             # str
    "espesor_base": None,        # float, cm
    "tipo_carpeta": "",          # str
    "espesor_carpeta": None,     # float, cm

    # Drenaje
    "tiene_cunetas": None,       # bool
    "tipo_cuneta": "",           # str - hormigon, tierra
    "tiene_drenaje": False,      # bool
    "tiene_impermeabilizacion": False,  # bool

    # Sistema estructural
    "tiene_muro_sostenimiento": False,  # bool
    "tipo_muro_sostenimiento": "",      # str
    "tiene_entibado": False,     # bool

    # Señalizacion
    "tiene_senalizacion": False,  # bool
    "tipo_senalizacion": "",      # str

    # Observaciones del revisor
    "observaciones_revisor": "",
    "cumple_global": None,       # bool - decision final del revisor
}


# ---------------------------------------------------------------------------
# Template HTML para muro (Jinja2)
# ---------------------------------------------------------------------------

HTML_TEMPLATE_MURO: str = """
<div class="hab-elemento hab-muro">
    <h3>{{ datos.nombre or 'Muro de contencion' }}</h3>
    <p class="descripcion">{{ datos.descripcion or '' }}</p>

    <table class="hab-tabla">
        <thead>
            <tr><th colspan="2">Geometria</th></tr>
        </thead>
        <tbody>
            <tr><td>Altura (m)</td><td>{{ datos.altura_muro | default('N/A') }}</td></tr>
            <tr><td>Longitud (m)</td><td>{{ datos.longitud_muro | default('N/A') }}</td></tr>
            <tr><td>Espesor (m)</td><td>{{ datos.espesor_muro | default('N/A') }}</td></tr>
            <tr><td>Ancho base (m)</td><td>{{ datos.ancho_base | default('N/A') }}</td></tr>
            <tr><td>Inclinacion (grados)</td><td>{{ datos.inclinacion | default('N/A') }}</td></tr>
        </tbody>
    </table>

    <table class="hab-tabla">
        <thead>
            <tr><th colspan="2">Materiales</th></tr>
        </thead>
        <tbody>
            <tr><td>f'c (MPa)</td><td>{{ datos.fc | default('N/A') }}</td></tr>
            <tr><td>fy (MPa)</td><td>{{ datos.fy | default('N/A') }}</td></tr>
            <tr><td>Tipo hormigon</td><td>{{ datos.tipo_hormigon | default('N/A') }}</td></tr>
            <tr><td>Tipo acero</td><td>{{ datos.tipo_acero | default('N/A') }}</td></tr>
            <tr><td>Recubrimiento (m)</td><td>{{ datos.recubrimiento | default('N/A') }}</td></tr>
        </tbody>
    </table>

    <table class="hab-tabla">
        <thead>
            <tr><th colspan="2">Drenaje</th></tr>
        </thead>
        <tbody>
            <tr><td>Tiene drenaje</td><td>{{ 'Si' if datos.tiene_drenaje else ('No' if datos.tiene_drenaje == False else 'N/A') }}</td></tr>
            <tr><td>Tipo drenaje</td><td>{{ datos.tipo_drenaje | default('N/A') }}</td></tr>
            <tr><td>Impermeabilizacion</td><td>{{ 'Si' if datos.tiene_impermeabilizacion else 'No' }}</td></tr>
        </tbody>
    </table>

    <table class="hab-tabla">
        <thead>
            <tr><th colspan="2">Estabilidad</th></tr>
        </thead>
        <tbody>
            <tr><td>FOS Vuelco</td><td>{{ datos.fos_vuelco | default('N/A') }}</td></tr>
            <tr><td>FOS Deslizamiento</td><td>{{ datos.fos_deslizamiento | default('N/A') }}</td></tr>
            <tr><td>FOS Hundimiento</td><td>{{ datos.fos_hundimiento | default('N/A') }}</td></tr>
        </tbody>
    </table>
</div>
"""


# ---------------------------------------------------------------------------
# Template HTML para caletera (Jinja2)
# ---------------------------------------------------------------------------

HTML_TEMPLATE_CALETERA: str = """
<div class="hab-elemento hab-caletera">
    <h3>{{ datos.nombre or 'Caletera' }}</h3>
    <p class="descripcion">{{ datos.descripcion or '' }}</p>

    <table class="hab-tabla">
        <thead>
            <tr><th colspan="2">Geometria</th></tr>
        </thead>
        <tbody>
            <tr><td>Longitud (m)</td><td>{{ datos.longitud_caletera | default('N/A') }}</td></tr>
            <tr><td>Ancho corona (m)</td><td>{{ datos.ancho_corona | default('N/A') }}</td></tr>
            <tr><td>Pendiente (%)</td><td>{{ datos.pendiente | default('N/A') }}</td></tr>
            <tr><td>Espesor capa (cm)</td><td>{{ datos.espesor | default('N/A') }}</td></tr>
        </tbody>
    </table>

    <table class="hab-tabla">
        <thead>
            <tr><th colspan="2">Tipo de pavimento</th></tr>
        </thead>
        <tbody>
            <tr><td>Tipo</td><td>{{ datos.tipo_caletera | default('N/A') }}</td></tr>
            <tr><td>Subbase (cm)</td><td>{{ datos.espesor_subbase | default('N/A') }}</td></tr>
            <tr><td>Base (cm)</td><td>{{ datos.espesor_base | default('N/A') }}</td></tr>
            <tr><td>Carpeta (cm)</td><td>{{ datos.espesor_carpeta | default('N/A') }}</td></tr>
        </tbody>
    </table>

    <table class="hab-tabla">
        <thead>
            <tr><th colspan="2">Drenaje y complementos</th></tr>
        </thead>
        <tbody>
            <tr><td>Cunetas</td><td>{{ 'Si' if datos.tiene_cunetas else ('No' if datos.tiene_cunetas == False else 'N/A') }}</td></tr>
            <tr><td>Muro sostenimiento</td><td>{{ 'Si' if datos.tiene_muro_sostenimiento else 'No' }}</td></tr>
            <tr><td>Senalizacion</td><td>{{ 'Si' if datos.tiene_senalizacion else 'No' }}</td></tr>
        </tbody>
    </table>
</div>
"""


# ---------------------------------------------------------------------------
# Renderizado HTML
# ---------------------------------------------------------------------------

def render_hab_html(tipo: str, datos: dict) -> str:
    """Renderiza HTML para un elemento HAB usando Jinja2 o fallback.

    Args:
        tipo: "muro" o "caletera".
        datos: Dict con los datos del elemento (usar PLANTILLA_MURO o
               PLANTILLA_CALETERA como base).

    Returns:
        String con HTML renderizado.

    Raises:
        ValueError: Si el tipo no es "muro" ni "caletera".

    Ejemplo:
        >>> datos = PLANTILLA_MURO.copy()
        >>> datos["altura_muro"] = 3.5
        >>> datos["fc"] = 25.0
        >>> html = render_hab_html("muro", datos)
    """
    if tipo not in ("muro", "caletera"):
        raise ValueError(f"Tipo '{tipo}' no valido. Usar 'muro' o 'caletera'.")

    if tipo == "muro":
        template_str = HTML_TEMPLATE_MURO
    else:
        template_str = HTML_TEMPLATE_CALETERA

    if HAS_JINJA2:
        template = Template(template_str)
        return template.render(datos=datos)
    else:
        # Fallback sin Jinja2: renderizado basico con str.replace
        return _render_fallback(template_str, datos)


def _render_fallback(template_str: str, datos: dict) -> str:
    """Renderizado fallback sin Jinja2.

    Reemplaza las expresiones {{ datos.xxx | default('N/A') }} y
    {{ datos.xxx }} por los valores correspondientes.
    """
    import re

    def replacer(match):
        full_expr = match.group(1).strip()
        # Extraer nombre de campo
        if "| default" in full_expr:
            field_match = re.search(r"datos\.(\w+)", full_expr)
            if field_match:
                field_name = field_match.group(1)
                val = datos.get(field_name)
                return str(val) if val is not None else "N/A"
        elif full_expr.startswith("datos."):
            field_name = full_expr.replace("datos.", "")
            val = datos.get(field_name)
            return str(val) if val is not None else ""
        elif "'Si' if datos." in full_expr:
            # Booleanos
            field_match = re.search(r"datos\.(\w+)", full_expr)
            if field_match:
                field_name = field_match.group(1)
                val = datos.get(field_name)
                if val is True:
                    return "Si"
                elif val is False:
                    return "No"
                else:
                    return "N/A"
        return match.group(0)

    return re.sub(r"\{\{\s*(.+?)\s*\}\}", replacer, template_str)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def crear_datos_muro(**kwargs) -> dict[str, Any]:
    """Crea un dict de datos de muro a partir de la plantilla.

    Args:
        **kwargs: Valores a sobrescribir en la plantilla.

    Returns:
        Dict con los datos del muro listos para verificar.

    Ejemplo:
        >>> datos = crear_datos_muro(altura_muro=3.5, fc=25.0, tiene_drenaje=True)
    """
    datos = PLANTILLA_MURO.copy()
    datos.update(kwargs)
    return datos


def crear_datos_caletera(**kwargs) -> dict[str, Any]:
    """Crea un dict de datos de caletera a partir de la plantilla.

    Args:
        **kwargs: Valores a sobrescribir en la plantilla.

    Returns:
        Dict con los datos de la caletera listos para verificar.

    Ejemplo:
        >>> datos = crear_datos_caletera(longitud=45.0, ancho_corona=3.5)
    """
    datos = PLANTILLA_CALETERA.copy()
    datos.update(kwargs)
    return datos
