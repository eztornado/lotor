"""
Sistema de actualización automática al inicio de la aplicación
Verifica si es necesario actualizar y lo hace automáticamente
"""

from loguru import logger
from app.services.data_updater import get_data_updater


async def check_and_update_on_startup():
    """
    Verificar y actualizar datos al inicio de la aplicación
    Se ejecuta automáticamente al arrancar el servidor
    """
    try:
        updater = get_data_updater()

        logger.info("Checking if data update is needed on startup...")

        if updater.should_update():
            logger.info("Data update needed, running automatic update...")
            result = updater.update_all_lotteries()

            if result["overall_status"] == "success":
                logger.info(f"✅ Automatic data update successful: {result['lotteries']}")
            else:
                logger.warning(f"⚠️ Partial data update: {result.get('overall_status')}")
                # No fallar el inicio si hay actualización parcial
        else:
            next_update = updater.get_next_update_time()
            logger.info(f"✅ Data is up to date. Next update: {next_update}")

    except Exception as e:
        logger.error(f"Error in startup data update check: {e}")
        # No fallar el inicio si hay error en actualización
        logger.info("⚠️ Continuing startup despite data update error")


def get_startup_tasks():
    """Retornar lista de tareas a ejecutar al inicio"""
    return [
        ("Data update check", check_and_update_on_startup),
    ]