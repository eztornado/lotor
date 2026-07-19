from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# Incluir routers
app.include_router(predictions.router, prefix=f"{settings.API_V1_STR}/predictions", tags=["predictions"])
app.include_router(history.router, prefix=f"{settings.API_V1_STR}/history", tags=["history"])
app.include_router(stats.router, prefix=f"{settings.API_V1_STR}/stats", tags=["stats"])
app.include_router(multi_combinations.router, prefix=f"{settings.API_V1_STR}/combinations", tags=["combinations"])


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "LoTor API - Sistema de Predicción El Gordo de la Primitiva",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LoTor API"}


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Iniciando {settings.PROJECT_NAME} v{settings.VERSION}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
