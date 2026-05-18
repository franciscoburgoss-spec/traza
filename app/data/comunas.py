"""
Catalogo de 33 comunas de la Region de O'Higgins (VI Region) con codigos
de 3 letras y zona sismica asignada.

Fuentes:
  - JSON comunas_zona_sismica.json (datos oficiales SERVIU O'Higgins)
  - SUBDERE: 33 comunas de la VI Region

La zona sismica es INMUTABLE — depende unicamente de la ubicacion geografica
de la comuna y no puede ser modificada manualmente.
"""

# ═══════════════════════════════════════════════════════════
# 33 Comunas de O'Higgins con codigo de 3 letras y zona sismica
# ═══════════════════════════════════════════════════════════

COMUNAS_OHIGGINS = [
    # Provincia de Cachapoal
    {"nombre": "Chépica",              "codigo": "CHP", "zona_sismica": 2, "provincia": "Colchagua"},
    {"nombre": "Chimbarongo",          "codigo": "CHB", "zona_sismica": 2, "provincia": "Colchagua"},
    {"nombre": "Codegua",              "codigo": "COD", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Coinco",               "codigo": "COI", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Coltauco",             "codigo": "COL", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Doñihue",              "codigo": "DON", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Graneros",             "codigo": "GRA", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "La Estrella",          "codigo": "LES", "zona_sismica": 3, "provincia": "Cardenal Caro"},
    {"nombre": "Las Cabras",           "codigo": "LCB", "zona_sismica": 3, "provincia": "Cachapoal"},
    {"nombre": "Litueche",             "codigo": "LIT", "zona_sismica": 3, "provincia": "Cardenal Caro"},
    {"nombre": "Lolol",                "codigo": "LOL", "zona_sismica": 3, "provincia": "Colchagua"},
    {"nombre": "Machalí",              "codigo": "MCH", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Malloa",               "codigo": "MLL", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Marchihue",            "codigo": "MRG", "zona_sismica": 3, "provincia": "Cardenal Caro"},
    {"nombre": "Mostazal",             "codigo": "MST", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Nancagua",             "codigo": "NCG", "zona_sismica": 2, "provincia": "Colchagua"},
    {"nombre": "Navidad",              "codigo": "NAV", "zona_sismica": 3, "provincia": "Cardenal Caro"},
    {"nombre": "Olivar",               "codigo": "OLI", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Palmilla",             "codigo": "PLM", "zona_sismica": 3, "provincia": "Colchagua"},
    {"nombre": "Paredones",            "codigo": "PAR", "zona_sismica": 3, "provincia": "Cardenal Caro"},
    {"nombre": "Peralillo",            "codigo": "PER", "zona_sismica": 3, "provincia": "Colchagua"},
    {"nombre": "Peumo",                "codigo": "PEU", "zona_sismica": 3, "provincia": "Cachapoal"},
    {"nombre": "Pichidegua",           "codigo": "PCH", "zona_sismica": 3, "provincia": "Cachapoal"},
    {"nombre": "Pichilemu",            "codigo": "PIC", "zona_sismica": 3, "provincia": "Cardenal Caro"},
    {"nombre": "Placilla",             "codigo": "PLC", "zona_sismica": 2, "provincia": "Colchagua"},
    {"nombre": "Pumanque",             "codigo": "PMQ", "zona_sismica": 3, "provincia": "Colchagua"},
    {"nombre": "Quinta de Tilcoco",    "codigo": "QTC", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Rancagua",             "codigo": "RAN", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Rengo",                "codigo": "RNG", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Requínoa",             "codigo": "REQ", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "San Fernando",         "codigo": "SFE", "zona_sismica": 2, "provincia": "Colchagua"},
    {"nombre": "San Vicente",          "codigo": "SVT", "zona_sismica": 2, "provincia": "Cachapoal"},
    {"nombre": "Santa Cruz",           "codigo": "SCZ", "zona_sismica": 3, "provincia": "Colchagua"},
]

# Index rapido por nombre
_COMUNAS_BY_NOMBRE = {c["nombre"].lower(): c for c in COMUNAS_OHIGGINS}


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def get_comuna(nombre: str) -> dict | None:
    """Retorna la comuna completa (dict) dado su nombre. Case-insensitive."""
    return _COMUNAS_BY_NOMBRE.get(nombre.lower())


def get_zona_sismica(nombre_comuna: str) -> int:
    """Retorna la zona sismica (1, 2 o 3) para una comuna dada.

    La zona sismica es INMUTABLE — depende unicamente de la ubicacion
    geografica de la comuna. No puede ser modificada manualmente.
    """
    comuna = get_comuna(nombre_comuna)
    if comuna:
        return comuna["zona_sismica"]
    return 0  # Desconocida


def get_comuna_codigo(nombre_comuna: str) -> str:
    """Retorna el codigo de 3 letras para una comuna dada."""
    comuna = get_comuna(nombre_comuna)
    if comuna:
        return comuna["codigo"]
    return "XXX"


def get_comuna_nombre(codigo: str) -> str:
    """Retorna el nombre de la comuna dado su codigo de 3 letras."""
    for c in COMUNAS_OHIGGINS:
        if c["codigo"].upper() == codigo.upper():
            return c["nombre"]
    return "Desconocida"


def listar_comunas() -> list[dict]:
    """Retorna las 33 comunas ordenadas alfabeticamente por nombre."""
    return sorted(COMUNAS_OHIGGINS, key=lambda x: x["nombre"])


# ═══════════════════════════════════════════════════════════
# Tipos de proyecto y sus letras para el acronimo
# ═══════════════════════════════════════════════════════════

TIPOS_PROYECTO = [
    {"codigo": "HAB", "nombre": "Habitacional",    "letra": "H"},
    {"codigo": "TEC", "nombre": "Tecnico",         "letra": "T"},
    {"codigo": "DOS", "nombre": "Dos Fases",       "letra": "D"},
    {"codigo": "OTR", "nombre": "Otros",           "letra": "O"},
]


def get_tipo_proyecto_letra(tipo_codigo: str) -> str:
    """Retorna la letra del tipo de proyecto para el acronimo."""
    for t in TIPOS_PROYECTO:
        if t["codigo"].upper() == tipo_codigo.upper():
            return t["letra"]
    return "X"


def listar_tipos_proyecto() -> list[dict]:
    """Retorna la lista de tipos de proyecto."""
    return TIPOS_PROYECTO


# ═══════════════════════════════════════════════════════════
# Generador de acronimo [T][YY][CCC][NN]
# ═══════════════════════════════════════════════════════════

def generar_acronimo(tipo_proyecto: str, comuna: str, nombre_proyecto: str,
                     anio: int | None = None) -> str:
    """
    Genera el acronimo de 8 caracteres segun la regla [T][YY][CCC][NN].

    Parametros:
        tipo_proyecto: codigo del tipo (HAB, TEC, DOS, OTR)
        comuna: nombre de la comuna
        nombre_proyecto: nombre del proyecto
        anio: ano de creacion (default: ano actual)

    Retorna:
        String de 8 caracteres, ej: 'H26RANLA'
    """
    import re
    from datetime import datetime

    # [T] — Letra del tipo de proyecto
    letra_tipo = get_tipo_proyecto_letra(tipo_proyecto)

    # [YY] — Ultimos dos digitos del ano
    if anio is None:
        anio = datetime.now().year
    yy = str(anio)[-2:]

    # [CCC] — Codigo de 3 letras de la comuna
    codigo_comuna = get_comuna_codigo(comuna).upper()

    # [NN] — 2 letras representativas del nombre del proyecto
    stop_words = {"el", "la", "los", "las", "de", "del", "en", "un", "una",
                  "los", "con", "para", "por", "al", "su", "sus", "lo"}

    palabras = re.findall(r'[A-Za-z\u00C0-\u00FF]+', nombre_proyecto)
    palabras_filtradas = [p for p in palabras if p.lower() not in stop_words]

    if len(palabras_filtradas) >= 2:
        nn = (palabras_filtradas[0][0] + palabras_filtradas[1][0]).upper()
    elif len(palabras_filtradas) == 1:
        nn = palabras_filtradas[0][:2].upper()
    else:
        nn = "XX"

    return f"{letra_tipo}{yy}{codigo_comuna}{nn}"
