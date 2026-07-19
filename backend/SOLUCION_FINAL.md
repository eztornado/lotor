# Solución FINAL - Instalación en Raspberry Pi 3 (ARM)

## Problema
NumPy 1.26.4 requiere compiladores C (gcc/cc) que no están instalados por defecto en RPi.

## Solución

### Opción 1: Script completo (RECOMENDADO)
```bash
cd /root/LoTor/backend
./install-rpi-final.sh
```

Este script:
1. Instala gcc y build-essential si no están
2. Crea el entorno virtual
3. Instala NumPy 1.24.4 (última versión con wheel precompilada para ARM)
4. Instala scikit-learn 1.3.2 y XGBoost 1.7.6 (versiones estables para ARM)

### Opción 2: Instalación manual
```bash
# 1. Instalar compiladores
sudo apt-get update
sudo apt-get install -y build-essential python3-dev

# 2. Crear venv e instalar
cd /root/LoTor/backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements-arm-final.txt
```

## Verificar instalación
```bash
cd /root/LoTor/backend
./test-rpi-final.sh
```

## Cambios clave de requisitos

| Paquete | Versión anterior | Versión ARM |
|---------|------------------|-------------|
| numpy | 1.26.4 | 1.24.4 (wheel ARM) |
| scikit-learn | 1.5.2 | 1.3.2 (wheel ARM) |
| xgboost | 2.1.2 | 1.7.6 (wheel ARM) |
| pandas | 2.2.3 | 2.0.3 (wheel ARM) |

Estas versiones son **completamente funcionales** y tienen wheels precompiladas en piwheels.org para ARM64.

## Funcionalidad mantenida
- ✅ 7 combinaciones semanales con estrategias diversificadas
- ✅ Ensemble ML (scikit-learn + XGBoost)
- ✅ Predictores estadísticos
- ✅ Multi-source data fetching
- ✅ API FastAPI completa
- ❌ SIN PyTorch (no disponible para ARM)

## Ejecutar el sistema
```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Verificar en producción
```bash
source venv/bin/activate
python -c "import numpy, sklearn, xgboost, pandas; print('✓ Todo OK')"
```
