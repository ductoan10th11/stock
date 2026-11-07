from fastapi import APIRouter, HTTPException, Response, status

from app.schemas.paper import PaperCreateRequest, PaperState, RefreshResult
from app.services import paper_service

router = APIRouter(prefix="/paper", tags=["paper"])


@router.get("")
def get_state() -> PaperState:
    return paper_service.read_state()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_account(request: PaperCreateRequest) -> PaperState:
    paper_service.create_account(request)
    return paper_service.read_state()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_account() -> Response:
    paper_service.delete_account()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/refresh")
def refresh() -> RefreshResult:
    try:
        return RefreshResult(sessions=paper_service.refresh())
    except Exception as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"refresh_failed: {error}") from error
