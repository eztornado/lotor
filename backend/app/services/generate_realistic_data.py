#!/usr/bin/env python3
"""
Script para generar datos históricos realistas del Sorteo Nacional
Reemplaza los datos dummy con patrones obvios por datos estadísticamente realistas
"""

import sys
import os
import random
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd

# Agregar backend al path
sys.path.append(str(Path(__file__).parent.parent))

def has_obvious_pattern(num_str: str) -> bool:
    """Detectar patrones obvios como 12345, 54321, 11111"""
    if num_str in '1234567890' or num_str in '0987654321':
        return True
    if len(set(num_str)) == 1:
        return True
    if len(num_str) >= 4:
        half = len(num_str) // 2
        if num_str[:half] == num_str[half:half*2]:
            return True
    return False

def generate_realistic_number() -> int:
    """Generar un número realista de 5 dígitos sin patrones obvios"""
    while True:
        num = random.randint(10000, 99999)
        if not has_obvious_pattern(str(num)):
            return num

def generate_realistic_historical_data(count: int = 238) -> list:
    """Generar datos históricos realistas para Sorteo Nacional"""
    logger.info(f"Generating {count} realistic historical draws for Sorteo Nacional")

    draws = []
    current_date = datetime.now()

    for week in range(count):
        # Calcular jueves correspondiente
        draw_date = current_date - timedelta(weeks=week)
        days_since_thursday = (draw_date.weekday() - 3) % 7
        thursday_date = draw_date - timedelta(days=days_since_thursday)

        # Generar 4 números realistas
        numbers = []
        while len(numbers) < 4:
            num = generate_realistic_number()
            if num not in numbers:
                numbers.append(num)

        numbers.sort()

        # Serie y fracción más realistas
        serie = random.randint(1, 10)
        fraccion = random.randint(1, 100)

        draw = {
            'date': thursday_date.strftime('%Y-%m-%d'),
            'n1': numbers[0],
            'n2': numbers[1],
            'n3': numbers[2],
            'n4': numbers[3],
            'serie': serie,
            'fraccion': fraccion,
            'source': 'realistic_simulation'
        }
        draws.append(draw)

    logger.info(f"Generated {len(draws)} realistic draws")
    return draws

def save_to_csv(draws: list, filepath: str):
    """Guardar los sorteos en un archivo CSV"""
    # Crear directorio si no existe
    import os
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    df = pd.DataFrame(draws)
    df = df.sort_values('date', ascending=False)
    df.to_csv(filepath, index=False)
    logger.info(f"Saved {len(draws)} draws to {filepath}")

def main():
    """Función principal"""
    logger.info("🔄 Generating realistic Sorteo Nacional historical data...")

    try:
        # Generar datos realistas
        draws = generate_realistic_historical_data(count=238)

        # Guardar en CSV
        csv_path = "/app/data/raw/nacional_historical_expanded.csv"
        save_to_csv(draws, csv_path)

        logger.info(f"✅ Successfully updated Sorteo Nacional data: {len(draws)} draws")
        logger.info(f"📁 Data saved to: {csv_path}")

        # Mostrar muestra de datos
        logger.info("📊 Sample data (last 3 draws):")
        for draw in draws[:3]:
            logger.info(f"   {draw['date']}: [{draw['n1']}, {draw['n2']}, {draw['n3']}, {draw['n4']}]")

        return True

    except Exception as e:
        logger.error(f"❌ Error generating realistic data: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)