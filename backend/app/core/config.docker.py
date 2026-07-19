# Configuración Docker para LoTor - Force lightweight models
from .config import *

# Forzar uso de modelos ligeros sin PyTorch en Docker
FORCE_LIGHTWEIGHT_MODELS = True
ML_MODEL_TYPE = "lightweight"  # Opciones: "pytorch", "lightweight"
