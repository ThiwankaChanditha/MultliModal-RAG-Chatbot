from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.api.chat import router as chat_router
from app.api.upload import router as upload_router
from app.api.debug import router as debug_router

os.makedirs("temp_uploads", exist_ok=True)

app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/temp_uploads", StaticFiles(directory="temp_uploads"), name="temp_uploads")
app.include_router(debug_router)
app.include_router(chat_router)
app.include_router(upload_router)
