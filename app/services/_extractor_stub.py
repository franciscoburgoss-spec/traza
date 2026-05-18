"""Stub de extractores cuando el legacy no esta disponible.
Estas funciones simulan la interfaz de los extractores legacy."""
import json
import re
from typing import List, Dict, Any


def extraer_valores(ruta_archivo: str) -> List[Dict[str, Any]]:
    """Stub: extrae valores numericos y textuales basicos."""
    return [
        {"campo": "altura_edificio", "valor": "24.5", "tipo": "numero", "unidad": "m", "confidence": 0.9},
        {"campo": "numero_pisos", "valor": "8", "tipo": "entero", "confidence": 0.95},
        {"campo": "uso_edificacion", "valor": "Residencial", "tipo": "texto", "confidence": 0.85},
        {"campo": "superficie_construida", "valor": "3200", "tipo": "numero", "unidad": "m2", "confidence": 0.8},
        {"campo": "zona_sismica", "valor": "2", "tipo": "entero", "confidence": 0.88},
        {"campo": "Ao", "valor": "0.30", "tipo": "numero", "unidad": "g", "confidence": 0.82},
        {"campo": "tipo_suelo", "valor": "II", "tipo": "texto", "confidence": 0.78},
    ]


def extraer_params_sismicos(ruta_archivo: str) -> List[Dict[str, Any]]:
    """Stub: extrae parametros sismicos de referencia."""
    return [
        {"campo": "zona_sismica", "valor": "2", "tipo": "entero", "unidad": None, "confidence": 0.85},
        {"campo": "Ao", "valor": "0.30", "tipo": "numero", "unidad": "g", "confidence": 0.8},
        {"campo": "tipo_suelo", "valor": "II", "tipo": "texto", "confidence": 0.75},
    ]


def extraer_normas(ruta_archivo: str) -> List[Dict[str, Any]]:
    """Stub: extrae referencias normativas mencionadas."""
    return [
        {"campo": "norma_NCh433", "valor": "NCh433 Of.96 Mod.2012", "tipo": "norma", "confidence": 0.9},
        {"campo": "norma_NCh2361", "valor": "NCh2361", "tipo": "norma", "confidence": 0.7},
        {"campo": "norma_NCh3171", "valor": "NCh3171 Of.2010", "tipo": "norma", "confidence": 0.65},
    ]


def extraer_refs_plan(ruta_archivo: str) -> List[Dict[str, Any]]:
    """Stub: extrae referencias a planos."""
    return [
        {"campo": "ref_plano_arquitectura", "valor": "A-101", "tipo": "referencia", "confidence": 0.75},
        {"campo": "ref_plano_estructura", "valor": "E-201", "tipo": "referencia", "confidence": 0.7},
    ]
