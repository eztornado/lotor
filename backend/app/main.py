import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import settings
from app.api import predictions, history, stats, multi_combinations, bonoloto, gordo

# Configurar logger (sink explícito a stdout para evitar recursión/bloqueos)
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API de predicción para El Gordo de la Primitiva y generación de Bonoloto",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar assets del frontend si están presentes (build de producción).
# En Docker el build se copia a ./frontend; en local puede estar en
# ./frontend/dist (raíz del repo) o ../frontend/dist (ejecutando desde backend).
def _find_frontend_dir() -> str:
    for candidate in (
        "./frontend/dist",
        "../frontend/dist",
        "./frontend",
        "../frontend",
        "./dist",
    ):
        if os.path.isfile(os.path.join(candidate, "index.html")):
            return os.path.abspath(candidate)
    return os.path.abspath("./frontend")


FRONTEND_DIR = _find_frontend_dir()
if os.path.isdir(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

# Incluir routers
app.include_router(predictions.router, prefix=f"{settings.API_V1_STR}/predictions", tags=["predictions"])
app.include_router(history.router, prefix=f"{settings.API_V1_STR}/history", tags=["history"])
app.include_router(stats.router, prefix=f"{settings.API_V1_STR}/stats", tags=["stats"])
app.include_router(multi_combinations.router, prefix=f"{settings.API_V1_STR}/combinations", tags=["combinations"])
app.include_router(bonoloto.router, prefix=f"{settings.API_V1_STR}/bonoloto", tags=["bonoloto"])
app.include_router(gordo.router, prefix=f"{settings.API_V1_STR}/gordo", tags=["gordo"])


@app.get("/")
async def root():
    """Endpoint raíz: sirve el frontend si está construido; si no, info de la API."""
    frontend_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path, media_type="text/html")
    return {
        "message": "LoTor API - Predicciones y generación de loterías",
        "version": settings.VERSION,
        "games": ["El Gordo de la Primitiva", "Bonoloto"],
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LoTor API"}


# Catch-all para SPA routing (debe ir al final)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Sirve el frontend para todas las rutas que no sean de la API."""
    if full_path.startswith("api/") or full_path in {"api", "health"}:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    static_path = os.path.abspath(os.path.join(FRONTEND_DIR, full_path))
    if not static_path.startswith(FRONTEND_DIR + os.sep):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    if os.path.isfile(static_path):
        return FileResponse(static_path)

    frontend_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path, media_type="text/html")

    return JSONResponse(
        status_code=404,
        content={
            "message": "LoTor API - Predicciones y generación de loterías",
            "version": settings.VERSION,
            "docs": "/docs",
        },
    )


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Iniciando {settings.PROJECT_NAME} v{settings.VERSION}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
