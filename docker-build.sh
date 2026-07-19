#!/bin/bash
# Script para construir y probar LoTor con Docker localmente

set -e

echo "=== LoTor - Docker Build & Test ==="
echo ""

# Verificar que Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: Docker no está instalado"
    exit 1
fi

echo "1/5 Construyendo imagen LoTor..."
docker build -t lotor:latest .

echo ""
echo "2/5 Verificando imagen creada..."
docker images | grep lotor

echo ""
echo "3/5 Iniciando contenedor..."
docker run -d --name lotor_test -p 8000:8000 lotor:latest

echo ""
echo "4/4 Esperando inicio (5 segundos)..."
sleep 5

echo ""
echo "5/5 Verificando salud del servicio..."
docker exec lotor_test curl -f http://localhost:8000/health || {
    echo "❌ ERROR: Servicio no responde"
    docker logs lotor_test
    docker stop lotor_test
    docker rm lotor_test
    exit 1
}

echo ""
echo "=== ✅ TEST PASADO - Sistema funcionando ==="
echo ""
echo "Logs del contenedor:"
docker logs lotor_test --tail 20

echo ""
echo "Para detener:"
echo "  docker stop lotor_test"
echo "  docker rm lotor_test"
echo ""
echo "Para ejecutar en modo interactivo:"
echo "  docker run -it --rm -p 8000:8000 lotor:latest"
