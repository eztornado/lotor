#!/bin/bash
# Install LoTor en Raspberry Pi - Version FINAL
# Soluciona problema de compiladores de C

set -e

echo "=== LoTor - Instalación Raspberry Pi (ARM) ==="
echo "Detectando arquitectura..."
ARCH=$(uname -m)
echo "Arquitectura: $ARCH"

if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" ]]; then
    echo "⚠️  Advertencia: Esto está optimizado para ARM (Raspberry Pi)"
fi

echo ""
echo "1/5 Verificando e instalando dependencias del sistema..."
if ! command -v gcc &> /dev/null; then
    echo "   gcc no encontrado - instalando..."
    sudo apt-get update
    sudo apt-get install -y build-essential python3-dev
else
    echo "   ✓ gcc ya instalado"
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: python3 no encontrado"
    exit 1
fi

echo ""
echo "2/5 Limpiando instalación anterior..."
cd /root/LoTor/backend
rm -rf venv

echo ""
echo "3/5 Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "4/5 Actualizando pip..."
pip install --upgrade pip setuptools wheel

echo ""
echo "5/5 Instalando dependencias Python (SIN PyTorch)..."
pip install -r requirements-arm-final.txt

echo ""
echo "=== Instalación completada ==="
echo ""
echo "Para verificar:"
echo "  source venv/bin/activate"
echo "  python -c 'import numpy, sklearn, xgboost; print(\"✓ Todo OK\")'"
echo ""
echo "Para ejecutar:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
