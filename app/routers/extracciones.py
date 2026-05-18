"""Router para orquestar extracciones de documentos."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas import EvidenciaRead
from app.services.extractor_service import run_extraction

router = APIRouter(prefix="/extracciones", tags=["Extracciones"])


@router.post("/{documento_id}", response_model=list[EvidenciaRead])
def extraer(documento_id: str, session_id: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        evidencias = run_extraction(db, documento_id, session_id)
        return evidencias
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en extraccion: {str(e)}")
