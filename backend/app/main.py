from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from loguru import logger
from app.core.config import settings
from app.api import predictions, history, stats, multi_combinations

# Configurar logger
logger.remove()
logger.add(
    logger.info,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API de predicción para El Gordo de la Primitiva",
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

# Montar archivos estáticos del frontend
if os.path.exists("./frontend"):
    app.mount("/assets", StaticFiles(directory="./frontend/assets"), name="assets")

# Incluir routers
app.include_router(predictions.router, prefix=f"{settings.API_V1_STR}/predictions", tags=["predictions"])
app.include_router(history.router, prefix=f"{settings.API_V1_STR}/history", tags=["history"])
app.include_router(stats.router, prefix=f"{settings.API_V1_STR}/stats", tags=["stats"])
app.include_router(multi_combinations.router, prefix=f"{settings.API_V1_STR}/combinations", tags=["combinations"])


@app.get("/")
async def root():
    """Endpoint raíz - sirve el frontend"""
    frontend_path = "./frontend/index.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path, media_type="text/html")
    else:
        return {
            "message": "LoTor API - Sistema de Predicción El Gordo de la Primitiva",
            "version": settings.VERSION,
            "docs": "/docs",
        }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LoTor API"}


@app.get("/api")
async def api_info():
    """Endpoint info API"""
    return {
        "message": "LoTor API - Sistema de Predicción El Gordo de la Primitiva",
        "version": settings.VERSION,
        "docs": "/docs",
        "endpoints": {
            "predictions": "/api/v1/predictions",
            "history": "/api/v1/history",
            "stats": "/api/v1/stats",
            "combinations": "/api/v1/combinations"
        }
    }


# Catch-all para SPA routing
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Sirve el frontend para todas las rutas no-API"""
    # Si es una ruta de API, devolver 404
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path == "health":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={"detail": "Not Found"}
        )

    # Si es un archivo estático, intentar servirlo
    static_path = f"./frontend/{full_path}"
    if os.path.exists(static_path) and os.path.isfile(static_path):
        return FileResponse(static_path)

    # Si no existe, servir el index.html para SPA routing
    frontend_path = "./frontend/index.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path, media_type="text/html")

    # Fallback a JSON si no hay frontend
    return {
        "message": "LoTor API - Sistema de Predicción El Gordo de la Primitiva",
        "version": settings.VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Iniciando {settings.PROJECT_NAME} v{settings.VERSION}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
