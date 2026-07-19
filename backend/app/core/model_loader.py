"""
Loader dinámico de modelos según arquitectura y disponibilidad
"""

import platform
import os
from loguru import logger


class ModelLoader:
    """Loader dinámico de modelos según el hardware"""

    @staticmethod
    def detect_architecture() -> str:
        """Detectar arquitectura del sistema"""
        machine = platform.machine().lower()
        processor = platform.processor().lower()

        # Detectar ARM
        if 'arm' in machine or 'aarch64' in machine:
            return 'arm'

        # Detectar x86_64
        if 'x86_64' in machine or 'amd64' in machine:
            return 'x86_64'

        return 'unknown'

    @staticmethod
    def check_pytorch_available() -> bool:
        """Verificar si PyTorch está disponible"""
        try:
            import torch
            logger.info(f"PyTorch disponible: {torch.__version__}")
            return True
        except ImportError:
            logger.info("PyTorch no disponible (normal en ARM, usando modelos ligeros)")
            return False

    @staticmethod
    def check_sklearn_available() -> bool:
        """Verificar si scikit-learn está disponible"""
        try:
            import sklearn
            logger.info(f"Scikit-learn disponible: {sklearn.__version__}")
            return True
        except ImportError:
            logger.warning("Scikit-learn no disponible")
            return False

    @staticmethod
    def get_best_model_type() -> str:
        """Determinar el mejor tipo de modelo para el sistema"""
        architecture = ModelLoader.detect_architecture()

        logger.info(f"Arquitectura detectada: {architecture}")

        # En ARM, siempre usar modelos ligeros (PyTorch no disponible)
        if architecture == 'arm':
            if ModelLoader.check_sklearn_available():
                logger.info("Usando modelos ligeros (scikit-learn) para ARM")
                return 'lightweight'
            else:
                logger.info("Usando modelos estadísticos para ARM")
                return 'statistical'

        # En x86_64, usar PyTorch si está disponible
        elif architecture == 'x86_64':
            if ModelLoader.check_pytorch_available():
                logger.info("Usando PyTorch para x86_64")
                return 'pytorch'
            elif ModelLoader.check_sklearn_available():
                logger.info("PyTorch no disponible, usando modelos ligeros")
                return 'lightweight'
            else:
                logger.info("Usando modelos estadísticos")
                return 'statistical'

        # Para otras arquitecturas, usar lo que esté disponible
        if ModelLoader.check_sklearn_available():
            return 'lightweight'
        else:
            return 'statistical'

    @staticmethod
    def create_predictor():
        """Crear predictor según el mejor tipo disponible"""
        model_type = ModelLoader.get_best_model_type()

        logger.info(f"Creando predictor de tipo: {model_type}")

        if model_type == 'pytorch':
            try:
                from app.ml.models import create_models
                return create_models()
            except Exception as e:
                logger.error(f"Error creando modelos PyTorch: {e}")
                logger.info("Fallback a modelos ligeros")
                return ModelLoader._create_lightweight()

        elif model_type == 'lightweight':
            return ModelLoader._create_lightweight()

        else:  # statistical
            return ModelLoader._create_statistical()

    @staticmethod
    def _create_lightweight():
        """Crear predictor ligero"""
        try:
            from app.ml.lightweight_models import create_lightweight_models
            return create_lightweight_models()
        except Exception as e:
            logger.error(f"Error creando modelos ligeros: {e}")
            logger.info("Fallback a modelo estadístico")
            return ModelLoader._create_statistical()

    @staticmethod
    def _create_statistical():
        """Crear predictor estadístico"""
        from app.ml.lightweight_models import create_statistical_model
        return create_statistical_model()


# Singleton instance
_model_instance = None


def get_predictor():
    """Obtener predictor (singleton)"""
    global _model_instance

    if _model_instance is None:
        _model_instance = ModelLoader.create_predictor()

    return _model_instance


def get_model_info() -> dict:
    """Obtener información sobre el modelo actual"""
    return {
        'architecture': ModelLoader.detect_architecture(),
        'model_type': ModelLoader.get_best_model_type(),
        'pytorch_available': ModelLoader.check_pytorch_available(),
        'sklearn_available': ModelLoader.check_sklearn_available(),
        'platform': platform.platform(),
        'python_version': platform.python_version()
    }
