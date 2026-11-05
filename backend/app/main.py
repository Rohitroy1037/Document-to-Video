
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.upload import router as upload_router
from app.api.analyze import router as analyze_router
from app.api.script import router as script_router
from app.api.translate import router as translate_router
from app.api.audio import router as audio_router
from app.api.scenes import router as scenes_router
from app.api.video import router as video_router
from app.api.chat import router as chat_router


# Initialize FastAPI application
app = FastAPI(
    title="Document to Video AI",
    description="Convert PDF and PowerPoint documents into narrated videos.",
    version="1.0.0",
)


configured_origins = os.getenv("FRONTEND_ORIGINS")
allowed_origins = (
    [
        origin.strip().rstrip("/")
        for origin in configured_origins.split(",")
        if origin.strip()
    ]
    if configured_origins
    else [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Storage directories
VIDEO_DIR = Path("storage/videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
SUBTITLE_DIR = Path("storage/subtitles")
SUBTITLE_DIR.mkdir(parents=True, exist_ok=True)


# Health check
@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "Document to Video AI backend is running",
    }


# Serve generated MP4 videos
# Example: /videos/<document_id>_hinglish.mp4
app.mount(
    "/videos",
    StaticFiles(directory=str(VIDEO_DIR)),
    name="videos",
)

app.mount(
    "/subtitles",
    StaticFiles(directory=str(SUBTITLE_DIR)),
    name="subtitles",
)


# Register API routers
app.include_router(upload_router)
app.include_router(analyze_router)
app.include_router(script_router)
app.include_router(translate_router)
app.include_router(audio_router)
app.include_router(scenes_router)
app.include_router(video_router)
app.include_router(chat_router)
