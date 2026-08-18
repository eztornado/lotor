#!/bin/bash
# Script de actualización semanal para datos del Sorteo Nacional
# Se ejecuta automáticamente cada semana para mantener los datos actualizados

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔄 Starting weekly Sorteo Nacional data update..."
echo "📅 Date: $(date '+%Y-%m-%d %H:%M:%S')"

# Ejecutar el script de actualización
cd "$PROJECT_ROOT/backend" || exit 1
python3 -m app.services.generate_realistic_data

if [ $? -eq 0 ]; then
    echo "✅ Sorteo Nacional data updated successfully"
    echo "📊 Next prediction will use updated historical data"
    exit 0
else
    echo "❌ Error updating Sorteo Nacional data"
    exit 1
fi