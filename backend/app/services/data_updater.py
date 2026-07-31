"""
Servicio de actualización automática de datos para todas las loterías
Actualiza periódicamente los datos históricos desde múltiples fuentes
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
import json

from app.domain.lottery import LotteryType
from app.application.primitiva_predictor import PrimitivaPredictor
from app.application.nacional_predictor import NacionalPredictor


class DataUpdateService:
    """Servicio centralizado de actualización de datos"""

    def __init__(self, update_interval_hours: int = 6):
        self.update_interval = timedelta(hours=update_interval_hours)
        self.last_update_file = "/app/data/last_update.json"
        self.update_log_file = "/app/logs/data_updates.log"
        self.predictors = {
            LotteryType.PRIMITIVA: PrimitivaPredictor(),
            LotteryType.NACIONAL: NacionalPredictor(),
        }

    def update_all_lotteries(self) -> Dict[str, any]:
        """
        Actualizar datos de todas las loterías
        Intenta todas las fuentes con fallback mechanisms
        """
        logger.info("Starting automatic data update for all lotteries")

        results = {
            "timestamp": datetime.now().isoformat(),
            "lotteries": {},
            "overall_status": "success"
        }

        for lottery_type, predictor in self.predictors.items():
            try:
                lottery_result = self._update_lottery(lottery_type, predictor)
                results["lotteries"][lottery_type] = lottery_result

                if lottery_result["status"] == "error":
                    results["overall_status"] = "partial_error"

            except Exception as e:
                logger.error(f"Error updating {lottery_type}: {e}")
                results["lotteries"][lottery_type] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                results["overall_status"] = "error"

        # Guardar estado de actualización
        self._save_update_status(results)

        # Calcular próxima actualización
        next_update = datetime.now() + self.update_interval
        results["next_update"] = next_update.isoformat()

        logger.info(f"Data update completed: {results['overall_status']}")
        return results

    def _update_lottery(self, lottery_type: LotteryType, predictor) -> Dict[str, any]:
        """Actualizar datos para una lotería específica"""
        logger.info(f"Updating {lottery_type}...")

        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "sources_attempted": [],
            "draws_obtained": 0,
            "errors": []
        }

        try:
            # Intentar obtener datos históricos
            # El predictor ya tiene fallback mechanisms implementados
            historical_data = predictor.get_historical_data(count=200)

            if historical_data:
                result["draws_obtained"] = len(historical_data)
                result["status"] = "success"

                # Reentrenar modelo con nuevos datos
                try:
                    predictor.train(historical_data)
                    result["model_trained"] = True
                    logger.info(f"{lottery_type}: {len(historical_data)} draws, model retrained")
                except Exception as e:
                    result["model_trained"] = False
                    result["model_error"] = str(e)
                    logger.warning(f"{lottery_type}: Could not retrain model: {e}")

            else:
                result["status"] = "error"
                result["errors"].append("No data obtained from any source")
                logger.error(f"{lottery_type}: No data obtained")

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
            logger.error(f"{lottery_type}: {e}")

        return result

    def force_update(self, lottery_type: Optional[LotteryType] = None) -> Dict[str, any]:
        """
        Forzar actualización inmediata de datos

        Args:
            lottery_type: Tipo específico de lotería, o None para todas
        """
        logger.info(f"Force update requested for {lottery_type or 'all lotteries'}")

        if lottery_type:
            predictor = self.predictors.get(lottery_type)
            if not predictor:
                return {"error": f"Unknown lottery type: {lottery_type}"}

            result = self._update_lottery(lottery_type, predictor)
            return result
        else:
            return self.update_all_lotteries()

    def get_update_status(self) -> Dict[str, any]:
        """Obtener estado de actualizaciones"""
        try:
            if Path(self.last_update_file).exists():
                with open(self.last_update_file, 'r') as f:
                    return json.load(f)
            else:
                return {"status": "never_updated", "timestamp": None}
        except Exception as e:
            logger.error(f"Error reading update status: {e}")
            return {"error": str(e)}

    def _save_update_status(self, results: Dict[str, any]):
        """Guardar estado de actualización"""
        try:
            Path(self.last_update_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.last_update_file, 'w') as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving update status: {e}")

    def should_update(self) -> bool:
        """Verificar si es momento de actualizar"""
        status = self.get_update_status()

        if status.get("status") == "never_updated":
            return True

        last_update_str = status.get("timestamp")
        if not last_update_str:
            return True

        try:
            last_update = datetime.fromisoformat(last_update_str)
            time_since_update = datetime.now() - last_update
            return time_since_update >= self.update_interval
        except:
            return True

    def get_next_update_time(self) -> datetime:
        """Calcular próxima hora de actualización"""
        status = self.get_update_status()

        if status.get("status") == "never_updated":
            return datetime.now()

        last_update_str = status.get("timestamp")
        if last_update_str:
            try:
                last_update = datetime.fromisoformat(last_update_str)
                return last_update + self.update_interval
            except:
                pass

        return datetime.now() + self.update_interval


# Singleton instance
_updater_instance = None


def get_data_updater() -> DataUpdateService:
    """Obtener instancia singleton del actualizador"""
    global _updater_instance

    if _updater_instance is None:
        _updater_instance = DataUpdateService(update_interval_hours=6)

    return _updater_instance