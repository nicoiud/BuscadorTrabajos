from fastapi import APIRouter

from app.schemas.autofill import FieldAnswerOut, FieldAnswerRequest
from app.services.enrichment.field_answer import generate_field_answer

router = APIRouter(prefix="/autofill", tags=["autofill"])


@router.post("/answer", response_model=FieldAnswerOut)
async def answer_form_field(body: FieldAnswerRequest) -> FieldAnswerOut:
    """Usado por la extensión de navegador para completar campos de texto libre.

    No persiste nada — no hay job_id ni base de datos involucrada, solo el campo del
    formulario (visto en cualquier sitio de terceros) y el perfil del usuario.
    """
    answer = await generate_field_answer(body.field_label, body.profile_text)
    return FieldAnswerOut(answer=answer)
