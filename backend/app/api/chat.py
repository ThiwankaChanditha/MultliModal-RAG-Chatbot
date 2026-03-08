from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.rag.pipeline import run_rag
from app.core.auth import verify_token

router = APIRouter()


@router.post("/chat")
def chat(payload: dict, user=Depends(verify_token)):
    query = payload.get("query", "").strip()
    if not query:
        return JSONResponse(status_code=400, content={"detail": "Query cannot be empty"})

    answer = run_rag(query)

    return {
        "answer": answer,
        "usage": {
            "queries_used": user.get("queries_used"),
            "queries_remaining": user.get("queries_remaining"),
            "is_owner": user.get("is_owner", False),
        },
    }