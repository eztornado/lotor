from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timedelta
from collections import Counter
from loguru import logger

from app.models.schemas import StatisticsResponse, NumberStats, KeyNumberStats
from app.services.data_sources import create_data_manager

router = APIRouter()

data_manager = None


def get_data_manager():
    """Obtener data manager (lazy loading)"""
    global data_manager
    if data_manager is None:
        data_manager = create_data_manager()
    return data_manager


@router.get("/general", response_model=StatisticsResponse)
async def get_general_statistics():
    """
    Obtener estadísticas generales de los sorteos
    """
    try:
        manager = get_data_manager()
        draws = manager.get_historical_data(force_refresh=False)

        if not draws:
            raise HTTPException(
                status_code=404,
                detail="No historical data available"
            )

        # Calcular estadísticas de números
        number_counter = Counter()
        key_counter = Counter()

        for draw in draws:
            for num in draw['numbers']:
                number_counter[num] += 1
            key_counter[draw['key_number']] += 1

        total_draws = len(draws)

        # Crear estadísticas de números
        number_stats = []
        for num in range(1, 55):
            freq = number_counter.get(num, 0)
            percentage = (freq / total_draws) * 100 if total_draws > 0 else 0

            # Encontrar última vez que salió
            last_drawn = None
            for draw in sorted(draws, key=lambda x: x['date'], reverse=True):
                if num in draw['numbers']:
                    last_drawn = draw['date']
                    break

            # Determinar si es caliente/frío
            hot = freq > total_draws / 54 * 1.2  # 20% arriba de la media
            cold = freq < total_draws / 54 * 0.8  # 20% abajo de la media

            number_stats.append(NumberStats(
                number=num,
                frequency=freq,
                percentage=percentage,
                last_drawn=last_drawn,
                hot=hot,
                cold=cold
            ))

        # Crear estadísticas de números clave
        key_stats = []
        for key in range(10):
            freq = key_counter.get(key, 0)
            percentage = (freq / total_draws) * 100 if total_draws > 0 else 0

            last_drawn = None
            for draw in sorted(draws, key=lambda x: x['date'], reverse=True):
                if draw['key_number'] == key:
                    last_drawn = draw['date']
                    break

            hot = freq > total_draws / 10 * 1.2
            cold = freq < total_draws / 10 * 0.8

            key_stats.append(KeyNumberStats(
                key_number=key,
                frequency=freq,
                percentage=percentage,
                last_drawn=last_drawn,
                hot=hot,
                cold=cold
            ))

        # Encontrar combinaciones más comunes
        most_common_combinations = find_common_combinations(draws, top_n=10)

        # Análisis de patrones
        patterns = analyze_patterns(draws)

        # Calcular próximo sorteo
        today = datetime.now()
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        next_draw_date = today + timedelta(days=days_until_sunday)

        return StatisticsResponse(
            total_draws=total_draws,
            number_stats=number_stats,
            key_number_stats=key_stats,
            most_common_combinations=most_common_combinations,
            patterns=patterns,
            next_draw_date=next_draw_date
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating statistics: {str(e)}"
        )


@router.get("/number/{number}")
async def get_number_statistics(number: int):
    """
    Obtener estadísticas de un número específico
    """
    try:
        if number < 1 or number > 54:
            raise HTTPException(
                status_code=400,
                detail="Number must be between 1 and 54"
            )

        manager = get_data_manager()
        draws = manager.get_historical_data(force_refresh=False)

        # Analizar el número específico
        appearances = []
        total_with_number = 0

        for draw in draws:
            if number in draw['numbers']:
                total_with_number += 1
                appearances.append({
                    'date': draw['date'],
                    'position': draw['numbers'].index(number) + 1,
                    'key_number': draw['key_number']
                })

        # Calcular rachas
        current_streak = 0
        longest_streak = 0
        temp_streak = 0

        for draw in sorted(draws, key=lambda x: x['date']):
            if number in draw['numbers']:
                temp_streak += 1
                current_streak = temp_streak
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 0

        return {
            'number': number,
            'total_appearances': total_with_number,
            'percentage': (total_with_number / len(draws)) * 100,
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'last_appeared': appearances[0]['date'] if appearances else None,
            'recent_appearances': appearances[:10]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting number statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting number statistics: {str(e)}"
        )


@router.get("/patterns")
async def get_pattern_analysis():
    """
    Obtener análisis de patrones avanzados
    """
    try:
        manager = get_data_manager()
        draws = manager.get_historical_data(force_refresh=False)

        patterns = analyze_patterns(draws)
        patterns['consecutive_numbers'] = analyze_consecutive_numbers(draws)
        patterns['odd_even_ratio'] = analyze_odd_even_ratio(draws)
        patterns['number_ranges'] = analyze_number_ranges(draws)
        patterns['repeating_numbers'] = analyze_repeating_numbers(draws)

        return patterns

    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing patterns: {str(e)}"
        )


def find_common_combinations(draws: List[dict], top_n: int = 10) -> List[List[int]]:
    """Encontrar las combinaciones más comunes"""
    from itertools import combinations

    combo_counter = Counter()

    for draw in draws:
        # Crear combinaciones de 3 números
        nums = draw['numbers']
        for combo in combinations(sorted(nums), 3):
            combo_counter[combo] += 1

    # Obtener las más comunes
    most_common = combo_counter.most_common(top_n)

    return [list(combo) for combo, count in most_common]


def analyze_patterns(draws: List[dict]) -> dict:
    """Analizar patrones en los sorteos"""
    patterns = {
        'average_sum': 0,
        'average_key_number': 0,
        'most_drawn_day': 'Sunday',
        'number_distribution': {},
        'key_number_distribution': {}
    }

    if not draws:
        return patterns

    # Calcular sumas
    sums = [sum(draw['numbers']) for draw in draws]
    patterns['average_sum'] = sum(sums) / len(sums)

    # Número clave promedio
    key_nums = [draw['key_number'] for draw in draws]
    patterns['average_key_number'] = sum(key_nums) / len(key_nums)

    # Distribución de números
    from collections import Counter
    num_dist = Counter()
    for draw in draws:
        for num in draw['numbers']:
            num_dist[num] += 1

    patterns['number_distribution'] = dict(num_dist.most_common(10))

    # Distribución de número clave
    key_dist = Counter(key_nums)
    patterns['key_number_distribution'] = dict(key_dist)

    return patterns


def analyze_consecutive_numbers(draws: List[dict]) -> dict:
    """Analizar números consecutivos"""
    consecutive_stats = {
        'draws_with_consecutive': 0,
        'average_consecutive_per_draw': 0,
        'consecutive_pairs': Counter()
    }

    for draw in draws:
        nums = sorted(draw['numbers'])
        consecutive_count = 0

        for i in range(len(nums) - 1):
            if nums[i + 1] - nums[i] == 1:
                consecutive_count += 1
                consecutive_stats['consecutive_pairs'][(nums[i], nums[i + 1])] += 1

        if consecutive_count > 0:
            consecutive_stats['draws_with_consecutive'] += 1

    if draws:
        consecutive_stats['average_consecutive_per_draw'] = (
            consecutive_stats['draws_with_consecutive'] / len(draws)
        )

    # Convertir Counter a dict para serialización
    consecutive_stats['consecutive_pairs'] = dict(
        consecutive_stats['consecutive_pairs'].most_common(5)
    )

    return consecutive_stats


def analyze_odd_even_ratio(draws: List[dict]) -> dict:
    """Analizar ratio de números pares/impares"""
    ratios = []

    for draw in draws:
        odd_count = sum(1 for num in draw['numbers'] if num % 2 == 1)
        even_count = 5 - odd_count
        ratios.append({
            'odd': odd_count,
            'even': even_count,
            'ratio': f"{odd_count}:{even_count}"
        })

    # Encontrar ratio más común
    from collections import Counter
    ratio_counter = Counter(r['ratio'] for r in ratios)

    return {
        'most_common_ratio': ratio_counter.most_common(1)[0] if ratio_counter else ('N/A', 0),
        'average_odds': sum(r['odd'] for r in ratios) / len(ratios) if ratios else 0,
        'average_evens': sum(r['even'] for r in ratios) / len(ratios) if ratios else 0
    }


def analyze_number_ranges(draws: List[dict]) -> dict:
    """Analizar rangos de números"""
    range_stats = {
        '1-10': 0,
        '11-20': 0,
        '21-30': 0,
        '31-40': 0,
        '41-54': 0
    }

    for draw in draws:
        for num in draw['numbers']:
            if 1 <= num <= 10:
                range_stats['1-10'] += 1
            elif 11 <= num <= 20:
                range_stats['11-20'] += 1
            elif 21 <= num <= 30:
                range_stats['21-30'] += 1
            elif 31 <= num <= 40:
                range_stats['31-40'] += 1
            elif 41 <= num <= 54:
                range_stats['41-54'] += 1

    total = sum(range_stats.values())
    percentages = {k: (v / total * 100) if total > 0 else 0 for k, v in range_stats.items()}

    return {
        'counts': range_stats,
        'percentages': percentages
    }


def analyze_repeating_numbers(draws: List[dict]) -> dict:
    """Analizar números que se repiten entre sorteos consecutivos"""
    repeating_stats = {
        'total_repetitions': 0,
        'average_repetitions_per_draw': 0,
        'most_repeated_numbers': Counter()
    }

    sorted_draws = sorted(draws, key=lambda x: x['date'])

    for i in range(1, len(sorted_draws)):
        prev_nums = set(sorted_draws[i - 1]['numbers'])
        curr_nums = set(sorted_draws[i]['numbers'])

        repeated = prev_nums.intersection(curr_nums)
        repeating_stats['total_repetitions'] += len(repeated)

        for num in repeated:
            repeating_stats['most_repeated_numbers'][num] += 1

    if sorted_draws:
        repeating_stats['average_repetitions_per_draw'] = (
            repeating_stats['total_repetitions'] / (len(sorted_draws) - 1)
        )

    # Convertir Counter a dict
    repeating_stats['most_repeated_numbers'] = dict(
        repeating_stats['most_repeated_numbers'].most_common(10)
    )

    return repeating_stats
