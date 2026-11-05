from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat import DocumentChatRequest
from app.services.document_chat import answer_document_question
from app.utils.rate_limit import rate_limit

router = APIRouter()


@router.post(
    "/chat/{document_id}",
    dependencies=[Depends(rate_limit("chat", 60))],
)
def chat_with_document(
    document_id: UUID,
    request: DocumentChatRequest,
):
    try:
        return answer_document_question(
            str(document_id),
            request.question,
            [message.model_dump() for message in request.history],
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
