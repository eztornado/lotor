import numpy as np
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timedelta
from loguru import logger
from pydantic import BaseModel

from app.ml.multi_combination import Combination, MultiCombinationGenerator, create_multi_combination_generator
from app.services.data_sources import create_data_manager
from app.services.validator import create_validator
from app.ml.models import create_models, StatisticalPredictor
from app.core.config import settings

router = APIRouter()

# Global models (lazy loading)
ensemble_model = None
statistical_model = None
data_manager = None
multi_combo_generator = None


def get_models():
    """Obtener modelos (lazy loading)"""
    global ensemble_model, statistical_model, data_manager, multi_combo_generator

    if ensemble_model is None:
        logger.info("Loading ML models...")
        ensemble_model = create_models(device='cpu')

    if statistical_model is None:
        statistical_model = StatisticalPredictor()

    if data_manager is None:
        data_manager = create_data_manager()

    if multi_combo_generator is None:
        multi_combo_generator = create_multi_combination_generator(ensemble_model, statistical_model)

    return ensemble_model, statistical_model, data_manager, multi_combo_generator


class WeeklyCombinationsResponse(BaseModel):
    """Respuesta de combinaciones semanales"""
    draw_date: str
    combinations: List[dict]
    coverage_metrics: dict
    total_combinations: int
    recommendations: dict


@router.get("/weekly", response_model=WeeklyCombinationsResponse)
async def get_weekly_combinations(num_combinations: int = 7):
    """
    Obtener múltiples combinaciones estratégicas para el sorteo de la semana

    Args:
        num_combinations: Número de combinaciones a generar (default: 7)

    Returns:
        Lista de combinaciones estratégicas con diferentes enfoques
    """
    try:
        ensemble, statistical, data_manager, generator = get_models()
        validator = create_validator()

        # Obtener datos históricos
        logger.info("Fetching historical data for weekly combinations...")
        historical_data = data_manager.get_historical_data(force_refresh=False)

        if not historical_data:
            raise HTTPException(
                status_code=500,
                detail="No historical data available"
            )

        # Entrenar modelo estadístico si no está entrenado
        if statistical.total_draws == 0:
            statistical.train(historical_data)

        # Preparar secuencia para modelos ML
        sequence = []
        for draw in sorted(historical_data, key=lambda x: x['date'])[-settings.MAX_HISTORY_LENGTH:]:
            sequence.append(draw['numbers'] + [draw['key_number']])

        # Generar combinaciones
        logger.info(f"Generating {num_combinations} strategic combinations...")
        combinations = generator.generate_weekly_combinations(sequence, num_combinations)

        # Calcular métricas de cobertura
        coverage = generator.calculate_coverage(combinations)

        # Obtener fecha del próximo sorteo
        next_draw = validator.get_next_draw_date()

        # Convertir a formato de respuesta
        combo_data = []
        for combo in combinations:
            combo_data.append({
                'numbers': combo.numbers,
                'key_number': combo.key_number,
                'strategy': combo.strategy,
                'confidence': combo.confidence,
                'description': combo.description,
                'risk_level': combo.risk_level
            })

        # Generar recomendaciones
        recommendations = generate_recommendations(combinations, coverage)

        return WeeklyCombinationsResponse(
            draw_date=next_draw.strftime('%Y-%m-%d'),
            combinations=combo_data,
            coverage_metrics=coverage,
            total_combinations=len(combinations),
            recommendations=recommendations
        )

    except Exception as e:
        logger.error(f"Error generating weekly combinations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating weekly combinations: {str(e)}"
        )


def generate_recommendations(combinations: List[Combination], coverage: dict) -> dict:
    """Generar recomendaciones basadas en las combinaciones"""

    # Análisis de riesgo
    risk_counts = {}
    for combo in combinations:
        risk_counts[combo.risk_level] = risk_counts.get(combo.risk_level, 0) + 1

    # Recomendaciones personalizadas
    recommendations = {
        'play_strategy': '',
        'budget_allocation': {},
        'best_combinations': [],
        'warnings': []
    }

    # Estrategia de juego
    if risk_counts.get('conservative', 0) >= 3:
        recommendations['play_strategy'] = 'conservative'
        recommendations['warnings'].append('Perfil conservador: menor riesgo pero menores ganancias potenciales')
    elif risk_counts.get('risky', 0) >= 2:
        recommendations['play_strategy'] = 'aggressive'
        recommendations['warnings'].append('Perfil arriesgado: mayor potencial pero mayor riesgo')
    else:
        recommendations['play_strategy'] = 'balanced'

    # Asignación de presupuesto
    total_combos = len(combinations)
    recommendations['budget_allocation'] = {
        'high_confidence': int(total_combos * 0.4),  # 40% en combinaciones de alta confianza
        'medium_confidence': int(total_combos * 0.4),  # 40% en confianza media
        'low_confidence': int(total_combos * 0.2),  # 20% en baja confianza
    }

    # Mejores combinaciones por confianza
    sorted_by_confidence = sorted(combinations, key=lambda x: x.confidence, reverse=True)
    recommendations['best_combinations'] = [
        {
            'strategy': combo.strategy,
            'confidence': combo.confidence,
            'numbers': combo.numbers,
            'key_number': combo.key_number
        }
        for combo in sorted_by_confidence[:3]
    ]

    # Cobertura de números
    if coverage['unique_numbers_coverage'] < 40:
        recommendations['warnings'].append(
            f'Baja cobertura de números únicos ({coverage["unique_numbers_coverage"]:.1f}%). Considera más diversificación.'
        )

    if coverage['avg_combination_overlap'] > 2:
        recommendations['warnings'].append(
            f'Alto solapamiento promedio ({coverage["avg_combination_overlap"]:.1f} números). Las combinaciones son muy similares.'
        )

    return recommendations


@router.get("/compare")
async def compare_combinations():
    """
    Comparar diferentes estrategias de combinaciones
    """
    try:
        ensemble, statistical, data_manager, generator = get_models()

        # Obtener datos históricos
        historical_data = data_manager.get_historical_data(force_refresh=False)

        if not historical_data:
            raise HTTPException(
                status_code=500,
                detail="No historical data available"
            )

        # Entrenar si es necesario
        if statistical.total_draws == 0:
            statistical.train(historical_data)

        # Preparar secuencia
        sequence = []
        for draw in sorted(historical_data, key=lambda x: x['date'])[-settings.MAX_HISTORY_LENGTH:]:
            sequence.append(draw['numbers'] + [draw['key_number']])

        # Generar combinaciones con diferentes estrategias
        comparison = {}

        for strategy_name, strategy_func in generator.strategies.items():
            try:
                base_prediction = generator.ensemble_model.predict(sequence)
                base_probs = np.array(base_prediction['number_probabilities'])

                combo = strategy_func(sequence, base_probs)

                comparison[strategy_name] = {
                    'numbers': combo.numbers,
                    'key_number': combo.key_number,
                    'confidence': combo.confidence,
                    'description': combo.description,
                    'risk_level': combo.risk_level
                }
            except Exception as e:
                logger.error(f"Error generating {strategy_name}: {e}")

        return {
            'strategies_comparison': comparison,
            'best_strategy': max(comparison.keys(), key=lambda k: comparison[k]['confidence']),
            'total_strategies': len(comparison)
        }

    except Exception as e:
        logger.error(f"Error comparing combinations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing combinations: {str(e)}"
        )


class CombinationOptimizationRequest(BaseModel):
    """Solicitud para optimizar combinaciones existentes"""
    existing_combinations: List[List[int]]  # Combinaciones que el usuario ya tiene
    key_numbers: List[int]  # Números clave correspondientes
    num_new_combinations: int = 3  # Número de nuevas combinaciones a generar


@router.post("/optimize")
async def optimize_combinations(request: CombinationOptimizationRequest):
    """
    Optimizar combinaciones existentes y generar nuevas complementarias
    """
    try:
        ensemble, statistical, data_manager, generator = get_models()

        # Obtener datos históricos
        historical_data = data_manager.get_historical_data(force_refresh=False)

        if not historical_data:
            raise HTTPException(
                status_code=500,
                detail="No historical data available"
            )

        # Crear Combination objects desde input del usuario
        existing_combos = []
        for i, numbers in enumerate(request.existing_combinations):
            from app.ml.multi_combination import Combination
            existing_combos.append(Combination(
                numbers=numbers,
                key_number=request.key_numbers[i] if i < len(request.key_numbers) else 0,
                strategy='user_provided',
                confidence=0.5,
                description="Combinación proporcionada por el usuario",
                risk_level='balanced'
            ))

        # Analizar combinaciones existentes
        existing_coverage = generator.calculate_coverage(existing_combos)

        # Generar nuevas combinaciones complementarias
        sequence = []
        for draw in sorted(historical_data, key=lambda x: x['date'])[-settings.MAX_HISTORY_LENGTH:]:
            sequence.append(draw['numbers'] + [draw['key_number']])

        base_prediction = generator.ensemble_model.predict(sequence)
        base_probs = np.array(base_prediction['number_probabilities'])

        new_combos = []
        for _ in range(request.num_new_combinations):
            div_combo = generator._diversified_strategy(sequence, base_probs, existing_combos + new_combos)
            new_combos.append(div_combo)

        # Calcular cobertura mejorada
        all_combos = existing_combos + new_combos
        improved_coverage = generator.calculate_coverage(all_combos)

        return {
            'existing_combinations_analysis': existing_coverage,
            'new_combinations': [
                {
                    'numbers': combo.numbers,
                    'key_number': combo.key_number,
                    'strategy': combo.strategy,
                    'description': combo.description
                }
                for combo in new_combos
            ],
            'improved_coverage': improved_coverage,
            'improvement_metrics': {
                'unique_numbers_added': improved_coverage['unique_numbers_coverage'] - existing_coverage['unique_numbers_coverage'],
                'overlap_reduction': existing_coverage['avg_combination_overlap'] - improved_coverage['avg_combination_overlap']
            }
        }

    except Exception as e:
        logger.error(f"Error optimizing combinations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error optimizing combinations: {str(e)}"
        )