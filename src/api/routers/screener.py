from fastapi import APIRouter

router = APIRouter()

@router.get("")
def endpoint():
    return {"status": "ok"}
