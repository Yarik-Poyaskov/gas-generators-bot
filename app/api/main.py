import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import Config, Server

from app.api.auth import router as auth_router, set_bot_instance
from app.api.data import router as data_router
from app.api.ws import router as ws_router
from app.api.notifications import router as notifications_router
from app.config import config

app = FastAPI(
    title="GPU Checklist API",
    version="1.0.0",
    docs_url="/docs" if config.api_token else None
)

# CORS Setup - allowing origins from config
origins = [origin.strip() for origin in config.cors_origins.split(",")] if config.cors_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {"status": "ok", "message": "GPU Checklist API is running"}

# Include routers with /api prefix for easy routing
app.include_router(auth_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(ws_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")

# Global server instance to allow graceful shutdown
api_server: Server = None

async def start_api_server(bot=None):
    """Starts the FastAPI server concurrently with the Telegram bot."""
    global api_server
    import logging
    logging.info(f"📡 API Server starting on port {config.api_port}...")
    if bot:
        set_bot_instance(bot)
        
    cfg = Config(
        app=app, 
        host="0.0.0.0", 
        port=config.api_port,
        loop="asyncio"
    )
    api_server = Server(cfg)
    await api_server.serve()
