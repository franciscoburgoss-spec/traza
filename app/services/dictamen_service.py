"""Servicio de generacion de dictamen para TRAZA.

Build dictamen: ejecuta verificadores, cuenta resultados, calcula score 0-100,
genera hab_html a partir de plantillas Jinja2, genera justificacion.
"""
import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import Dictamen, Evidencia, Verificacion, Proyecto, Documento
from app.services.auditoria_service import log_action


# Reglas de verificacion hardcodeadas (100% offline)
REGLAS = [
    {"codigo": "R001", "nombre": "Zona sismica definida", "campo": "zona_sismica", "tipo": "exists"},
    {"codigo": "R002", "nombre": "Ao definido", "campo": "Ao", "tipo": "exists"},
    {"codigo": "R003", "nombre": "Tipo de suelo definido", "campo": "tipo_suelo", "tipo": "exists"},
    {"codigo": "R004", "nombre": "Altura del edificio", "campo": "altura_edificio", "tipo": "exists"},
    {"codigo": "R005", "nombre": "Numero de pisos", "campo": "numero_pisos", "tipo": "exists"},
    {"codigo": "R006", "nombre": "Uso de edificacion", "campo": "uso_edificacion", "tipo": "exists"},
    {"codigo": "R007", "nombre": "Superficie construida", "campo": "superficie_construida", "tipo": "exists"},
    {"codigo": "R008", "nombre": "Norma NCh433 referenciada", "campo": "norma_NCh433", "tipo": "exists"},
    {"codigo": "R009", "nombre": "Numero de pisos coherente con altura", "campo": "numero_pisos", "tipo": "custom", "check": "coherencia_pisos_altura"},
    {"codigo": "R010", "nombre": "Zona sismica entre 1 y 3", "campo": "zona_sismica", "tipo": "range", "min": 1, "max": 3},
]


def _run_verificadores(db: Session, proyecto_id: str, session_id: str = None) -> List[Verificacion]:
    """Ejecuta todas las reglas de verificacion sobre las evidencias del proyecto."""
    verificaciones = []

    # Obtener todas las evidencias del proyecto
    stmt = (
        select(Evidencia)
        .join(Documento, Evidencia.documento_id == Documento.id)
        .where(Documento.proyecto_id == proyecto_id)
    )
    evidencias = list(db.execute(stmt).scalars().all())

    # Indexar evidencias por campo
    evi_por_campo = {e.campo: e for e in evidencias}

    for regla in REGLAS:
        campo = regla["campo"]
        evidencia = evi_por_campo.get(campo)

        if evidencia is None:
            verificacion = Verificacion(
                evidencia_id=None,
                regla_codigo=regla["codigo"],
                resultado="NO_CUMPLE",
                mensaje=f"No se encontro evidencia para '{campo}'",
                session_id=session_id,
            )
        elif regla["tipo"] == "exists":
            verificacion = Verificacion(
                evidencia_id=evidencia.id,
                regla_codigo=regla["codigo"],
                resultado="CUMPLE",
                mensaje=f"Campo '{campo}' encontrado: {evidencia.valor}",
                payload_json=json.dumps({"valor": evidencia.valor, "unidad": evidencia.unidad}),
                session_id=session_id,
            )
        elif regla["tipo"] == "range":
            try:
                val = float(evidencia.valor)
                if regla.get("min", float("-inf")) <= val <= regla.get("max", float("inf")):
                    resultado = "CUMPLE"
                    mensaje = f"Valor {val} dentro del rango [{regla.get('min')}, {regla.get('max')}]"
                else:
                    resultado = "NO_CUMPLE"
                    mensaje = f"Valor {val} fuera del rango [{regla.get('min')}, {regla.get('max')}]"
            except (ValueError, TypeError):
                resultado = "ERROR"
                mensaje = f"Valor '{evidencia.valor}' no es numerico"
            verificacion = Verificacion(
                evidencia_id=evidencia.id,
                regla_codigo=regla["codigo"],
                resultado=resultado,
                mensaje=mensaje,
                payload_json=json.dumps({"valor": evidencia.valor}),
                session_id=session_id,
            )
        elif regla["tipo"] == "custom" and regla.get("check") == "coherencia_pisos_altura":
            # Verificar coherencia: altura / pisos ~= 3m por piso
            altura_evi = evi_por_campo.get("altura_edificio")
            pisos_evi = evi_por_campo.get("numero_pisos")
            if altura_evi and pisos_evi:
                try:
                    altura = float(altura_evi.valor)
                    pisos = int(float(pisos_evi.valor))
                    if pisos > 0:
                        altura_por_piso = altura / pisos
                        if 2.5 <= altura_por_piso <= 4.0:
                            resultado = "CUMPLE"
                            mensaje = f"Altura/piso = {altura_por_piso:.2f}m (coherente)"
                        else:
                            resultado = "NO_CUMPLE"
                            mensaje = f"Altura/piso = {altura_por_piso:.2f}m (incoherente, esperado 2.5-4.0m)"
                    else:
                        resultado = "ERROR"
                        mensaje = "Numero de pisos es 0"
                except (ValueError, TypeError):
                    resultado = "ERROR"
                    mensaje = "Error en conversion numerica"
            else:
                resultado = "NO_CUMPLE"
                mensaje = "Faltan evidencias de altura o numero de pisos"
            verificacion = Verificacion(
                evidencia_id=evidencia.id,
                regla_codigo=regla["codigo"],
                resultado=resultado,
                mensaje=mensaje,
                session_id=session_id,
            )
        else:
            verificacion = Verificacion(
                evidencia_id=evidencia.id if evidencia else None,
                regla_codigo=regla["codigo"],
                resultado="NO_APLICA",
                mensaje=f"Tipo de regla '{regla['tipo']}' no implementado",
                session_id=session_id,
            )

        db.add(verificacion)
        verificaciones.append(verificacion)

    db.commit()
    for v in verificaciones:
        db.refresh(v)

    return verificaciones


def _calcular_score(verificaciones: List[Verificacion]) -> float:
    """Calcula score 0-100 basado en verificaciones."""
    if not verificaciones:
        return 0.0
    total = len(verificaciones)
    cumplen = sum(1 for v in verificaciones if v.resultado == "CUMPLE")
    no_aplican = sum(1 for v in verificaciones if v.resultado == "NO_APLICA")
    # Score: (cumplen / aplicables) * 100
    aplicables = total - no_aplican
    if aplicables == 0:
        return 0.0
    return round((cumplen / aplicables) * 100, 2)


def _generar_hab_html(verificaciones: List[Verificacion], proyecto: Proyecto) -> str:
    """Genera HTML de Hoja de Acuerdo de Base (HAB) a partir de las verificaciones."""
    total = len(verificaciones)
    cumplen = sum(1 for v in verificaciones if v.resultado == "CUMPLE")
    no_cumplen = sum(1 for v in verificaciones if v.resultado == "NO_CUMPLE")
    errores = sum(1 for v in verificaciones if v.resultado == "ERROR")
    no_aplican = sum(1 for v in verificaciones if v.resultado == "NO_APLICA")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>HAB - {proyecto.codigo}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
        h1 {{ color: #2c5282; border-bottom: 3px solid #2c5282; padding-bottom: 10px; }}
        .meta {{ background: #f7fafc; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .resumen {{ display: flex; gap: 20px; margin: 20px 0; }}
        .badge {{ padding: 10px 20px; border-radius: 8px; font-weight: bold; }}
        .cumple {{ background: #c6f6d5; color: #22543d; }}
        .no-cumple {{ background: #fed7d7; color: #742a2a; }}
        .error {{ background: #feebc8; color: #744210; }}
        .no-aplica {{ background: #e2e8f0; color: #2d3748; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #2c5282; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
        tr:hover {{ background: #f7fafc; }}
        .result-cumple {{ color: #22543d; font-weight: bold; }}
        .result-no-cumple {{ color: #742a2a; font-weight: bold; }}
        .result-error {{ color: #744210; font-weight: bold; }}
        .footer {{ margin-top: 40px; font-size: 0.85em; color: #718096; border-top: 1px solid #e2e8f0; padding-top: 20px; }}
    </style>
</head>
<body>
    <h1>Hoja de Acuerdo de Base (HAB)</h1>
    <div class="meta">
        <strong>Proyecto:</strong> {proyecto.nombre} ({proyecto.codigo})<br>
        <strong>Tipo:</strong> {proyecto.tipo_proyecto or 'N/A'}<br>
        <strong>Comuna:</strong> {proyecto.ref_comuna or 'N/A'}<br>
        <strong>Zona Sismica:</strong> {proyecto.ref_zona_sismica or 'N/A'}<br>
        <strong>Tipo Suelo:</strong> {proyecto.ref_tipo_suelo or 'N/A'}<br>
        <strong>Ao:</strong> {proyecto.ref_Ao or 'N/A'}<br>
    </div>

    <h2>Resumen de Verificaciones</h2>
    <div class="resumen">
        <div class="badge cumple">CUMPLE: {cumplen}</div>
        <div class="badge no-cumple">NO CUMPLE: {no_cumplen}</div>
        <div class="badge error">ERROR: {errores}</div>
        <div class="badge no-aplica">NO APLICA: {no_aplican}</div>
    </div>

    <h2>Detalle de Verificaciones</h2>
    <table>
        <tr>
            <th>Regla</th>
            <th>Resultado</th>
            <th>Mensaje</th>
            <th>Payload</th>
        </tr>
"""

    for v in verificaciones:
        css_class = {
            "CUMPLE": "result-cumple",
            "NO_CUMPLE": "result-no-cumple",
            "ERROR": "result-error",
        }.get(v.resultado, "")
        html += f"""        <tr>
            <td>{v.regla_codigo}</td>
            <td class="{css_class}">{v.resultado}</td>
            <td>{v.mensaje or ''}</td>
            <td><pre>{v.payload_json or ''}</pre></td>
        </tr>
"""

    html += """    </table>

    <div class="footer">
        Generado por TRAZA | 100% offline | Sin APIs externas
    </div>
</body>
</html>"""

    return html


def _generar_justificacion(verificaciones: List[Verificacion], score: float) -> str:
    """Genera texto de justificacion del dictamen."""
    total = len(verificaciones)
    cumplen = sum(1 for v in verificaciones if v.resultado == "CUMPLE")
    no_cumplen = sum(1 for v in verificaciones if v.resultado == "NO_CUMPLE")

    just = f"""DICTAMEN TECNICO TRAZA

El proyecto ha sido evaluado bajo {total} reglas de verificacion normativa.

RESULTADO GLOBAL:
- Score de cumplimiento: {score}/100
- Reglas que CUMPLEN: {cumplen}
- Reglas que NO CUMPLEN: {no_cumplen}

VERIFICACIONES QUE NO CUMPLEN:
"""

    for v in verificaciones:
        if v.resultado == "NO_CUMPLE":
            just += f"\n- {v.regla_codigo}: {v.mensaje}"

    just += f"""

CONCLUSION:
"""
    if score >= 80:
        just += "El proyecto presenta un nivel de cumplimiento SATISFACTORIO. Se recomienda continuar con la revision detallada."
    elif score >= 50:
        just += "El proyecto presenta un nivel de cumplimiento PARCIAL. Se requieren ajustes antes de continuar."
    else:
        just += "El proyecto presenta un nivel de cumplimiento INSUFICIENTE. Se requiere revision completa de la documentacion."

    return just


def build_dictamen(db: Session, proyecto_id: str, session_id: str = None) -> Dictamen:
    """
    Construye o actualiza el dictamen de un proyecto.
    Ejecuta verificadores, cuenta resultados, calcula score, genera HTML y justificacion.
    """
    proyecto = db.get(Proyecto, proyecto_id)
    if not proyecto:
        raise ValueError(f"Proyecto {proyecto_id} no encontrado")

    # 1. Ejecutar verificadores
    verificaciones = _run_verificadores(db, proyecto_id, session_id)

    # 2. Contar resultados
    total = len(verificaciones)
    cumplen = sum(1 for v in verificaciones if v.resultado == "CUMPLE")
    no_cumplen = sum(1 for v in verificaciones if v.resultado == "NO_CUMPLE")

    # 3. Calcular score
    score = _calcular_score(verificaciones)

    # 4. Generar HTML y justificacion
    hab_html = _generar_hab_html(verificaciones, proyecto)
    justificacion = _generar_justificacion(verificaciones, score)

    # 5. Crear o actualizar dictamen
    stmt = select(Dictamen).where(Dictamen.proyecto_id == proyecto_id)
    existing = db.execute(stmt).scalar_one_or_none()

    if existing:
        existing.total_verificaciones = total
        existing.total_cumplen = cumplen
        existing.total_no_cumplen = no_cumplen
        existing.score = score
        existing.justificacion = justificacion
        existing.hab_html = hab_html
        existing.dictamen_texto = justificacion
        existing.estado = "COMPLETADO"
        existing.session_id = session_id
        existing.generado_en = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        dictamen = existing
    else:
        dictamen = Dictamen(
            proyecto_id=proyecto_id,
            estado="COMPLETADO",
            total_verificaciones=total,
            total_cumplen=cumplen,
            total_no_cumplen=no_cumplen,
            justificacion=justificacion,
            score=score,
            hab_html=hab_html,
            dictamen_texto=justificacion,
            editable=True,
            session_id=session_id,
        )
        db.add(dictamen)
        db.commit()
        db.refresh(dictamen)

    log_action(
        db,
        "Dictamen",
        dictamen.id,
        "DICTAMEN_GENERADO",
        {"proyecto_id": proyecto_id, "score": score, "total_verificaciones": total},
        session_id,
    )

    return dictamen
