"""
Servicio de generacion de emails HTML para TRAZA.

Renderiza templates Jinja2 con estilo profesional SERVIU para los
correos de resultado de verificacion ING.
"""
import os
from datetime import datetime
from typing import Dict, Any, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Configurar Jinja2 para cargar templates desde app/templates/email
_template_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "email")
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(["html", "xml"]),
)


def _serialize_doc(doc) -> Dict[str, Any]:
    """Convierte un DocumentoIng a dict serializable para el template."""
    return {
        "nombre": doc.nombre_archivo,
        "modulo": doc.modulo,
        "tipo": doc.tipo_documento,
        "tipologia": doc.tipologia,
        "estado": doc.estado,
        "observacion": doc.observacion,
    }


def renderizar_email_resultado_ing(solicitud, aceptados, observados, faltantes) -> str:
    """
    Renderiza el template HTML de resultado ING con los datos de la solicitud.

    Args:
        solicitud: Objeto SolicitudIng
        aceptados: Lista de DocumentoIng aceptados
        observados: Lista de DocumentoIng observados
        faltantes: Lista de DocumentoIng faltantes

    Returns:
        String con HTML completo del email
    """
    template = _jinja_env.get_template("resultado_ing.html")

    proyecto = {
        "nombre": solicitud.nombre_proyecto,
        "empresa": solicitud.empresa,
        "acronimo": solicitud.acronimo_proyecto or "—",
        "comuna": solicitud.comuna or "—",
        "tipo": solicitud.tipo_proyecto or "—",
        "modulos": ", ".join(solicitud.get_modulos()) if solicitud.get_modulos() else "—",
        "iteracion": solicitud.numero_iteracion,
        "session_id": solicitud.session_id or "—",
    }

    stats = {
        "aceptados": len(aceptados),
        "observados": len(observados),
        "faltantes": len(faltantes),
        "total": len(aceptados) + len(observados) + len(faltantes),
    }

    contexto = {
        "proyecto": proyecto,
        "stats": stats,
        "aceptados": [_serialize_doc(d) for d in aceptados],
        "observados": [_serialize_doc(d) for d in observados],
        "faltantes": [_serialize_doc(d) for d in faltantes],
        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }

    return template.render(**contexto)


def generar_email_texto_plano(solicitud, aceptados, observados, faltantes) -> str:
    """
    Genera version texto plano del email como fallback.

    Args:
        solicitud: Objeto SolicitudIng
        aceptados: Lista de DocumentoIng aceptados
        observados: Lista de DocumentoIng observados
        faltantes: Lista de DocumentoIng faltantes

    Returns:
        String con texto plano
    """
    lineas = [
        f"Estimado Coordinador,",
        "",
        f"Resultado verificacion ING — Proyecto {solicitud.nombre_proyecto}:",
        "",
        f"ACEPTADOS ({len(aceptados)}):",
    ]
    for doc in aceptados:
        linea = f"  • {doc.nombre_archivo} — {doc.modulo}"
        if doc.tipologia:
            linea += f" ({doc.tipologia})"
        lineas.append(linea)

    lineas.append("")
    lineas.append(f"OBSERVADOS ({len(observados)}):")
    for doc in observados:
        lineas.append(f"  • {doc.nombre_archivo} — {doc.modulo}")
        if doc.observacion:
            lineas.append(f"    Motivo: {doc.observacion}")

    if faltantes:
        lineas.append("")
        lineas.append(f"FALTANTES ({len(faltantes)}):")
        for doc in faltantes:
            lineas.append(f"  • {doc.nombre_archivo} — {doc.modulo}")
            if doc.observacion:
                lineas.append(f"    Nota: {doc.observacion}")

    lineas.extend([
        "",
        "Quedo atento.",
        "",
        "---",
        f"Generado por TRAZA — Solicitud ING #{solicitud.numero_iteracion} | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    ])

    return "\n".join(lineas)
