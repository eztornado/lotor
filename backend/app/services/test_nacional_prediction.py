#!/usr/bin/env python3
"""
Test para verificar que el sistema de predicción del Sorteo Nacional funciona correctamente
con los nuevos datos realistas
"""

import sys
from pathlib import Path
from loguru import logger

# Agregar backend al path
sys.path.append(str(Path(__file__).parent.parent))

from app.application.nacional_predictor import NacionalPredictor
from datetime import datetime

def test_nacional_prediction():
    """Probar el sistema de predicción del Sorteo Nacional"""
    logger.info("🧪 Testing Sorteo Nacional prediction system...")

    try:
        predictor = NacionalPredictor()

        # Obtener datos históricos
        logger.info("📊 Fetching historical data...")
        historical_data = predictor.get_historical_data(count=10)

        if not historical_data:
            logger.error("❌ No historical data available")
            return False

        logger.info(f"✅ Got {len(historical_data)} historical draws")

        # Mostrar últimos 3 sorteos
        logger.info("📅 Last 3 draws:")
        for draw in historical_data[:3]:
            logger.info(f"   {draw.draw_date.strftime('%Y-%m-%d')}: {draw.numbers}")

        # Verificar que no hay patrones obvios
        logger.info("🔍 Checking for obvious patterns...")
        obvious_patterns = ['12345', '54321', '11111', '22222', '33333', '44444', '98765', '01234']

        has_obvious = False
        for draw in historical_data:
            for num in draw.numbers:
                num_str = str(num).zfill(5)
                if any(pattern in num_str for pattern in obvious_patterns):
                    logger.warning(f"⚠️ Found obvious pattern: {num_str} in {draw.draw_date.strftime('%Y-%m-%d')}")
                    has_obvious = True

        if not has_obvious:
            logger.info("✅ No obvious patterns found in historical data")

        # Realizar predicción
        logger.info("🔮 Making prediction...")
        prediction = predictor.predict(historical_data)

        logger.info(f"✅ Prediction generated successfully!")
        logger.info(f"📅 Prediction date: {prediction.prediction_date.strftime('%Y-%m-%d')}")
        logger.info(f"🎰 Predicted numbers: {prediction.predicted_numbers}")
        logger.info(f"📊 Confidence: {prediction.confidence:.2%}")
        logger.info(f"🤖 Model used: {prediction.model_used}")

        # Verificar que la predicción no tiene patrones obvios
        predicted_nums_str = [str(num).zfill(5) for num in prediction.predicted_numbers]
        has_obvious_prediction = any(any(pattern in num_str for pattern in obvious_patterns)
                                     for num_str in predicted_nums_str)

        if has_obvious_prediction:
            logger.warning("⚠️ Prediction contains obvious patterns")
            return False
        else:
            logger.info("✅ Prediction looks realistic (no obvious patterns)")

        # Verificar distribución de números
        logger.info("📈 Number distribution analysis:")
        ranges = {
            '10000-24999': sum(1 for n in prediction.predicted_numbers if 10000 <= n <= 24999),
            '25000-49999': sum(1 for n in prediction.predicted_numbers if 25000 <= n <= 49999),
            '50000-74999': sum(1 for n in prediction.predicted_numbers if 50000 <= n <= 74999),
            '75000-99999': sum(1 for n in prediction.predicted_numbers if 75000 <= n <= 99999)
        }

        for range_name, count in ranges.items():
            logger.info(f"   {range_name}: {count} numbers")

        logger.info("✅ All tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Error testing Nacional prediction: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_nacional_prediction()
    logger.info("🎉 Test completed!" if success else "💥 Test failed!")
    sys.exit(0 if success else 1)