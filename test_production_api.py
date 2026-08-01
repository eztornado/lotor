#!/usr/bin/env python3
"""
Test para diagnosticar por qué el Sorteo Nacional no se muestra en producción
"""

import requests
import json

print("🔍 DIAGNÓSTICO PRODUCCIÓN - SORTEO NACIONAL")
print("=" * 60)

# Test 1: Verificar endpoint /lotteries
print("\n1️⃣ Test: Endpoint /api/v2/lotteries")
try:
    # Local test
    response = requests.get('http://localhost:8000/api/v2/lotteries')
    print(f"✅ Status: {response.status_code}")

    lotteries = response.json()
    print(f"✅ Loterías devueltas: {len(lotteries)}")

    for lottery in lotteries:
        enabled = "✅" if lottery.get('enabled') else "❌"
        print(f"   {enabled} {lottery['name']}: {lottery['type']} (enabled={lottery.get('enabled')})")

    # Verificar que Nacional esté habilitado
    nacional = [l for l in lotteries if l['type'] == 'nacional']
    if nacional and nacional[0].get('enabled'):
        print("✅ Sorteo Nacional está habilitado en la API")
    else:
        print("❌ Sorteo Nacional NO está habilitado o no existe")

except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Verificar endpoint /predictions/all
print("\n2️⃣ Test: Endpoint /api/v2/predictions/all")
try:
    response = requests.post('http://localhost:8000/api/v2/predictions/all', params={'count': 200})
    print(f"✅ Status: {response.status_code}")

    data = response.json()
    print(f"✅ Estructura de respuesta: {list(data.keys())}")
    print(f"✅ Total loterías: {data.get('total_lotteries')}")

    predictions = data.get('predictions', {})
    print(f"✅ Predicciones: {list(predictions.keys())}")

    for lottery_type, prediction in predictions.items():
        if isinstance(prediction, dict) and 'predicted_numbers' in prediction:
            print(f"   ✅ {lottery_type}: {len(prediction['predicted_numbers'])} números")
            print(f"      Numbers: {prediction['predicted_numbers']}")
        else:
            print(f"   ❌ {lottery_type}: Error o sin datos - {prediction}")

    # Verificar específicamente Nacional
    if 'nacional' in predictions:
        nacional_pred = predictions['nacional']
        if isinstance(nacional_pred, dict) and 'predicted_numbers' in nacional_pred:
            print(f"✅ Sorteo Nacional tiene {len(nacional_pred['predicted_numbers'])} números")
            print(f"   Números: {nacional_pred['predicted_numbers']}")
        else:
            print(f"❌ Sorteo Nacional tiene formato incorrecto: {nacional_pred}")
    else:
        print("❌ Sorteo Nacional NO está en predictions")

except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Verificar health check
print("\n3️⃣ Test: Endpoint /api/v2/health/lotteries")
try:
    response = requests.get('http://localhost:8000/api/v2/health/lotteries')
    print(f"✅ Status: {response.status_code}")

    health = response.json()
    print(f"✅ Overall status: {health.get('overall_status')}")

    lotteries_health = health.get('lotteries', {})
    for lottery_type, status in lotteries_health.items():
        health_icon = "✅" if status.get('status') == 'healthy' else "❌"
        print(f"   {health_icon} {lottery_type}: {status.get('status')}")
        if status.get('model_trained'):
            print(f"      ✅ Model trained: {status.get('available_draws')} draws")

except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Verificar predicción específica Nacional
print("\n4️⃣ Test: Endpoint /api/v2/lotteries/nacional/predict")
try:
    response = requests.post('http://localhost:8000/api/v2/lotteries/nacional/predict', params={'count': 200})
    print(f"✅ Status: {response.status_code}")

    prediction = response.json()
    print(f"✅ Estructura: {list(prediction.keys())}")
    print(f"✅ Números predichos: {prediction.get('predicted_numbers')}")
    print(f"✅ Cantidad: {len(prediction.get('predicted_numbers', []))}")
    print(f"✅ Modelo: {prediction.get('model_used')}")
    print(f"✅ Confianza: {prediction.get('confidence')}")

    if len(prediction.get('predicted_numbers', [])) == 4:
        print("🎯 PERFECT: Predicción de 4 números correcta")
    else:
        print(f"⚠️ WARNING: Expected 4 numbers, got {len(prediction.get('predicted_numbers', []))}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n🎯 DIAGNÓSTICO FINAL")
print("=" * 60)
print("Si todos los tests pasan, el problema es:")
print("1. Frontend no actualizado en producción")
print("2. Cache del navegador")
print("3. Problema de routing en el frontend")
print("4. Error en la carga del componente JavaScript")

print("\n🔧 SOLUCIONES:")
print("1. Ver que /api/v2/lotteries devuelva Nacional con enabled=true")
print("2. Ver que /api/v2/predictions/all incluya nacional")
print("3. Ver que la predicción tenga 4 números")
print("4. Limpiar cache del navegador")
print("5. Reconstruir el frontend")