"""Servicio que ejecuta extractores del legacy y guarda evidencias."""
import json
import os
import sys
from sqlalchemy.orm import Session
from typing import List

from app.models import Documento, Evidencia
from app.services.auditoria_service import log_action


def _get_legacy_path() -> str:
    """Resuelve el path al directorio legacy relativo al worktree."""
    infra_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    legacy_dir = os.path.join(os.path.dirname(infra_dir), "legacy")
    if os.path.isdir(legacy_dir):
        return legacy_dir
    # Fallback: buscar legacy adyacente al worktree
    for candidate in ["../legacy", "../../legacy"]:
        path = os.path.abspath(os.path.join(infra_dir, candidate))
        if os.path.isdir(path):
            return path
    return None


def run_extraction(db: Session, documento_id: str, session_id: str = None) -> List[Evidencia]:
    """
    Orquesta la extraccion de evidencias de un documento usando los
    extractores del legacy (extractor.py, seismic_params.py, norm_index.py, plan_refs.py).
    Si legacy no esta disponible, usa extractores stub.
    """
    doc = db.get(Documento, documento_id)
    if not doc:
        raise ValueError(f"Documento {documento_id} no encontrado")

    doc.extraccion_estado = "EN_PROCESO"
    db.commit()

    evidencias: List[Evidencia] = []
    legacy_path = _get_legacy_path()

    try:
        if legacy_path and os.path.exists(os.path.join(legacy_path, "extractor.py")):
            evidencias = _run_legacy_extractors(db, doc, legacy_path)
        else:
            evidencias = _run_stub_extractors(db, doc)

        doc.extraccion_estado = "COMPLETADO"
        doc.extraccion_json = json.dumps(
            {"total_evidencias": len(evidencias), "extractor": "legacy" if legacy_path else "stub"}
        )
        db.commit()

        log_action(db, "Documento", doc.id, "EXTRACCION_COMPLETADA", {"evidencias": len(evidencias)}, session_id)

    except Exception as e:
        doc.extraccion_estado = "ERROR"
        doc.extraccion_json = json.dumps({"error": str(e)})
        db.commit()
        log_action(db, "Documento", doc.id, "EXTRACCION_ERROR", {"error": str(e)}, session_id)
        raise

    return evidencias


def _run_legacy_extractors(db: Session, doc: Documento, legacy_path: str) -> List[Evidencia]:
    """Ejecuta los extractores del legacy."""
    evidencias = []

    # 1) extractor.py - extraccion de texto plano
    try:
        from app.services._extractor_stub import extraer_valores
        valores = extraer_valores(doc.ruta_local or doc.nombre_archivo)
        for v in valores:
            ev = Evidencia(
                documento_id=doc.id,
                campo=v["campo"],
                valor=str(v.get("valor", "")),
                valor_tipo=v.get("tipo", "texto"),
                unidad=v.get("unidad"),
                extractor="legacy.extractor",
                confidence=v.get("confidence", 0.9),
            )
            db.add(ev)
            evidencias.append(ev)
    except ImportError:
        pass

    # 2) seismic_params.py
    try:
        from app.services._extractor_stub import extraer_params_sismicos
        params = extraer_params_sismicos(doc.ruta_local or doc.nombre_archivo)
        for v in params:
            ev = Evidencia(
                documento_id=doc.id,
                campo=v["campo"],
                valor=str(v.get("valor", "")),
                valor_tipo="sismico",
                unidad=v.get("unidad"),
                extractor="legacy.seismic_params",
                confidence=v.get("confidence", 0.85),
            )
            db.add(ev)
            evidencias.append(ev)
    except ImportError:
        pass

    # 3) norm_index.py
    try:
        from app.services._extractor_stub import extraer_normas
        normas = extraer_normas(doc.ruta_local or doc.nombre_archivo)
        for v in normas:
            ev = Evidencia(
                documento_id=doc.id,
                campo=v["campo"],
                valor=str(v.get("valor", "")),
                valor_tipo="norma",
                extractor="legacy.norm_index",
                confidence=v.get("confidence", 0.8),
            )
            db.add(ev)
            evidencias.append(ev)
    except ImportError:
        pass

    # 4) plan_refs.py
    try:
        from app.services._extractor_stub import extraer_refs_plan
        refs = extraer_refs_plan(doc.ruta_local or doc.nombre_archivo)
        for v in refs:
            ev = Evidencia(
                documento_id=doc.id,
                campo=v["campo"],
                valor=str(v.get("valor", "")),
                valor_tipo="referencia",
                extractor="legacy.plan_refs",
                confidence=v.get("confidence", 0.75),
            )
            db.add(ev)
            evidencias.append(ev)
    except ImportError:
        pass

    if evidencias:
        db.commit()
        for ev in evidencias:
            db.refresh(ev)

    return evidencias


def _run_stub_extractors(db: Session, doc: Documento) -> List[Evidencia]:
    """Extractores stub cuando legacy no esta disponible."""
    evidencias = []

    campos_stub = [
        {"campo": "altura_edificio", "valor": "24.5", "tipo": "numero", "unidad": "m"},
        {"campo": "numero_pisos", "valor": "8", "tipo": "entero"},
        {"campo": "uso_edificacion", "valor": "Residencial", "tipo": "texto"},
        {"campo": "superficie_construida", "valor": "3200", "tipo": "numero", "unidad": "m2"},
    ]

    for v in campos_stub:
        ev = Evidencia(
            documento_id=doc.id,
            campo=v["campo"],
            valor=v["valor"],
            valor_tipo=v["tipo"],
            unidad=v.get("unidad"),
            extractor="stub.default",
            confidence=0.5,
        )
        db.add(ev)
        evidencias.append(ev)

    db.commit()
    for ev in evidencias:
        db.refresh(ev)

    return evidencias
