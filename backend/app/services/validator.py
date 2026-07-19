from datetime import datetime, timedelta
from typing import List, Dict
from loguru import logger


class DataValidator:
    """Validador de datos para asegurar información actualizada"""

    def __init__(self):
        self.current_date = datetime.now()
        self.tolerance_days = 7  # Tolerancia de 7 días para último sorteo

    def validate_dataset_freshness(self, draws: List[Dict]) -> Dict[str, any]:
        """Validar que los datos están actualizados"""

        if not draws:
            return {
                'valid': False,
                'error': 'No draws available',
                'current_date': self.current_date.strftime('%Y-%m-%d')
            }

        # Obtener fecha más reciente en el dataset
        most_recent_date = None
        for draw in draws:
            draw_date = draw.get('date')
            if isinstance(draw_date, str):
                draw_date = datetime.fromisoformat(draw_date.replace('Z', '+00:00'))
            elif isinstance(draw_date, datetime):
                pass
            else:
                continue

            if most_recent_date is None or draw_date > most_recent_date:
                most_recent_date = draw_date

        if not most_recent_date:
            return {
                'valid': False,
                'error': 'Could not determine most recent draw date',
                'current_date': self.current_date.strftime('%Y-%m-%d')
            }

        # Calcular días desde el último sorteo
        days_since_last_draw = (self.current_date - most_recent_date).days

        # El último sorteo debería ser domingo
        last_draw_weekday = most_recent_date.strftime('%A')

        # Validar
        is_recent = days_since_last_draw <= self.tolerance_days

        result = {
            'valid': is_recent,
            'current_date': self.current_date.strftime('%Y-%m-%d'),
            'most_recent_draw': most_recent_date.strftime('%Y-%m-%d'),
            'days_since_last_draw': days_since_last_draw,
            'last_draw_weekday': last_draw_weekday,
            'tolerance_days': self.tolerance_days,
            'total_draws': len(draws)
        }

        if not is_recent:
            result['warning'] = f'Dataset is {days_since_last_draw} days old. Last draw was on {most_recent_date.strftime("%Y-%m-%d")}.'
            logger.warning(result['warning'])
        else:
            logger.info(f'Dataset is fresh: last draw {days_since_last_draw} days ago ({most_recent_date.strftime("%Y-%m-%d")})')

        return result

    def get_next_draw_date(self) -> datetime:
        """Calcular fecha del próximo sorteo (domingo)"""

        today = self.current_date
        days_until_sunday = (6 - today.weekday()) % 7

        if days_until_sunday == 0:
            # Si hoy es domingo, calcular siguiente domingo
            days_until_sunday = 7

        next_sunday = today + timedelta(days=days_until_sunday)

        logger.info(f"Today: {today.strftime('%Y-%m-%d')} ({today.strftime('%A')})")
        logger.info(f"Next draw: {next_sunday.strftime('%Y-%m-%d')} ({days_until_sunday} days from now)")

        return next_sunday

    def validate_draw_format(self, draw: Dict) -> bool:
        """Validar formato de un sorteo individual"""

        required_fields = ['date', 'numbers', 'key_number']

        # Verificar campos requeridos
        for field in required_fields:
            if field not in draw:
                logger.error(f"Missing required field: {field}")
                return False

        # Validar números
        numbers = draw['numbers']
        if not isinstance(numbers, list) or len(numbers) != 5:
            logger.error(f"Invalid numbers format: {numbers}")
            return False

        # Validar rango de números (1-54)
        for num in numbers:
            if not isinstance(num, int) or num < 1 or num > 54:
                logger.error(f"Invalid number: {num} (must be 1-54)")
                return False

        # Validar número clave (0-9)
        key_number = draw['key_number']
        if not isinstance(key_number, int) or key_number < 0 or key_number > 9:
            logger.error(f"Invalid key number: {key_number} (must be 0-9)")
            return False

        # Validar fecha
        date = draw['date']
        try:
            if isinstance(date, str):
                datetime.fromisoformat(date.replace('Z', '+00:00'))
            elif not isinstance(date, datetime):
                logger.error(f"Invalid date type: {type(date)}")
                return False
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            return False

        return True

    def clean_and_validate_dataset(self, draws: List[Dict]) -> List[Dict]:
        """Limpiar y validar dataset completo"""

        valid_draws = []
        invalid_count = 0

        for i, draw in enumerate(draws):
            if self.validate_draw_format(draw):
                valid_draws.append(draw)
            else:
                invalid_count += 1
                logger.warning(f"Invalid draw at index {i}: {draw}")

        if invalid_count > 0:
            logger.warning(f"Removed {invalid_count} invalid draws from dataset")

        return valid_draws


def create_validator() -> DataValidator:
    """Crear validador con fecha actual"""
    return DataValidator()
