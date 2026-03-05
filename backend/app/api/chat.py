from fastapi import APIRouter
from app.rag.pipeline import run_rag

router = APIRouter()

@router.post("/chat")
def chat(payload: dict):
    query = payload.get("query")
    answer = run_rag(query)
    return {"answer": answer}