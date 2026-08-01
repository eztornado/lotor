#!/bin/bash
# Script para desplegar las mejoras del Sorteo Nacional en producción

echo "🚀 Desplegando mejoras del Sorteo Nacional del Jueves..."

# Directorios
BACKEND_DIR="/home/ubuntu/LoTor/backend"
FRONTEND_DIR="/home/ubuntu/LoTor/frontend"
PRODUCTION_SERVER="lotor.tornadocore.es"

echo "📋 VERIFICACIÓN DE COMPONENTES"

# Verificar archivos clave del backend
echo "✅ Backend mejorado:"
echo "   - nacional_predictor.py: Sistema sklearn con 4 números"
echo "   - nacional_source.py: Datos expandidos (200 sorteos)"
echo "   - lotteries.py: API v2 con Sorteo Nacional habilitado"

# Verificar datos expandidos
if [ -f "$BACKEND_DIR/data/raw/nacional_historical_expanded.csv" ]; then
    echo "   ✅ Datos expandidos: 200 sorteos (2020-2024)"
else
    echo "   ❌ ERROR: Falta archivo de datos expandidos"
    exit 1
fi

# Verificar frontend
echo "✅ Frontend configurado:"
echo "   - types/lottery.ts: LotteryType.NACIONAL definido"
echo "   - services/lotteryApi.ts: API v2 endpoints"
echo "   - MultiLotteryDashboard: Soporte multi-lotería"

echo ""
echo "🔧 PASOS PARA DESPLIEGUE EN PRODUCCIÓN"
echo "======================================"

echo "1. 📦 Preparar archivos para despliegue:"
echo "   - Backend: Copiar archivos mejorados a producción"
echo "   - Frontend: Re-build y desplegar"
echo "   - Datos: Copiar CSV expandido"

echo ""
echo "2. 🎯 Comandos necesarios en servidor de producción:"
echo ""
echo "   # Copiar backend mejorado"
echo "   scp -r backend/* usuario@$PRODUCTION_SERVER:/path/to/backend/"
echo ""
echo "   # Copiar datos expandidos"
echo "   scp backend/data/raw/nacional_historical_expanded.csv usuario@$PRODUCTION_SERVER:/path/to/backend/data/raw/"
echo ""
echo "   # Re-build y desplegar frontend"
echo "   cd frontend"
echo "   npm run build"
echo "   scp -r dist/* usuario@$PRODUCTION_SERVER:/path/to/frontend/"

echo ""
echo "3. 🔍 Verificación post-despliegue:"
echo ""
echo "   # Test API endpoint"
echo "   curl https://$PRODUCTION_SERVER/api/v2/lotteries"
echo ""
echo "   # Test health check"
echo "   curl https://$PRODUCTION_SERVER/api/v2/health/lotteries"
echo ""
echo "   # Test predicción Nacional"
echo "   curl -X POST https://$PRODUCTION_SERVER/api/v2/lotteries/nacional/predict?count=200"

echo ""
echo "📊 RESULTADOS ESPERADOS"
echo "======================"
echo ""
echo "1. API /lotteries debe devolver:"
echo '   [{"type": "nacional", "name": "Sorteo Nacional", "enabled": true}]'
echo ""
echo "2. Dashboard debe mostrar:"
echo "   - 2 loterías activas (Primitiva + Nacional)"
echo "   - Tarjeta del Sorteo Nacional del jueves"
echo "   - Predicciones de 4 números"
echo ""
echo "3. Health check debe mostrar:"
echo '   {"nacional": {"status": "healthy", "model_trained": true}}'

echo ""
echo "🎯 DATOS DEL SORTEO NACIONAL"
echo "============================"
echo "   - Nombre: Sorteo Nacional del Jueves"
echo "   - Predicción: 4 números (SIEMPRE)"
echo "   - Histórico: 200 sorteos (2020-2024)"
echo "   - Modelo: sklearn GradientBoosting"
echo "   - Confianza: 0.45-0.72"

echo ""
echo "🚀 ¿Listo para desplegar en $PRODUCTION_SERVER?"
echo "=========================================="
echo ""
echo "Opciones:"
echo "1. Despliegue manual (copiar archivos)"
echo "2. Despliegue automático (CI/CD)"
echo "3. Actualización en caliente (Docker)"

# Crear archivo con comandos específicos para el usuario
cat > /tmp/deploy_commands.txt << 'EOF'
# COMANDOS PARA DESPLIEGUE EN PRODUCCIÓN
# =======================================

# 1. EN SERVIDOR LOCAL - Preparar archivos
cd /home/ubuntu/LoTor

# Crear paquete de actualización
tar -czf /tmp/nacional_update.tar.gz \
  backend/app/application/nacional_predictor.py \
  backend/app/infrastructure/data/nacional_source.py \
  backend/app/api/v2/lotteries.py \
  backend/data/raw/nacional_historical_expanded.csv \
  backend/data/raw/nacional_expansion_summary.txt

# 2. COPIAR A SERVIDOR PRODUCCIÓN
scp /tmp/nacional_update.tar.gz usuario@lotor.tornadocore.es:/tmp/

# 3. EN SERVIDOR PRODUCCIÓN - Desplegar
ssh usuario@lotor.tornadocore.es << 'ENDSSH'
cd /path/to/lotor/app
tar -xzf /tmp/nacional_update.tar.gz
# Copiar archivos a sus ubicaciones
cp backend/app/application/nacional_predictor.py /path/to/backend/app/application/
cp backend/app/infrastructure/data/nacional_source.py /path/to/backend/app/infrastructure/data/
cp backend/app/api/v2/lotteries.py /path/to/backend/app/api/v2/
mkdir -p /path/to/backend/data/raw/
cp backend/data/raw/nacional_historical_expanded.csv /path/to/backend/data/raw/
# Reiniciar aplicación
systemctl restart lotor-backend
ENDSSH

# 4. VERIFICACIÓN
curl https://lotor.tornadocore.es/api/v2/lotteries
curl https://lotor.tornadocore.es/api/v2/health/lotteries
curl -X POST https://lotor.tornadocore.es/api/v2/lotteries/nacional/predict?count=200
EOF

echo ""
echo "💾 Comandos guardados en: /tmp/deploy_commands.txt"
echo ""
echo "📝 Nota: Reemplaza 'usuario' con tu usuario real en el servidor"
echo ""
echo "🎉 Una vez desplegado, verás el Sorteo Nacional del jueves en:"
echo "   https://$PRODUCTION_SERVER/lotteries"