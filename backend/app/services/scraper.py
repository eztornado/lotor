import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger
import pandas as pd
import time
import random


class PrimitivaScraper:
    """Scraper para obtener datos históricos de El Gordo de la Primitiva"""

    BASE_URL = "https://www.loteriasyapuestas.es"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _get_page(self, url: str, params: Optional[dict] = None) -> Optional[str]:
        """Obtener una página con manejo de errores"""
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def _parse_draw_result(self, html: str) -> Optional[dict]:
        """Parsear un resultado de sorteo desde HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Extraer fecha
            date_elem = soup.find('div', class_='fecha-sorteo')
            if not date_elem:
                return None

            date_str = date_elem.text.strip()
            draw_date = datetime.strptime(date_str, "%d/%m/%Y")

            # Extraer números combinación ganadora
            numbers_elem = soup.find('div', class_='combinacion-ganadora')
            if not numbers_elem:
                return None

            numbers = []
            for ball in numbers_elem.find_all('span', class_='bola'):
                num = int(ball.text.strip())
                numbers.append(num)

            if len(numbers) < 5:
                return None

            main_numbers = numbers[:5]
            key_number = numbers[5] if len(numbers) > 5 else 0

            return {
                'date': draw_date,
                'numbers': main_numbers,
                'key_number': key_number,
                'source': 'loteriasyapuestas.es'
            }

        except Exception as e:
            logger.error(f"Error parsing draw result: {e}")
            return None

    def fetch_recent_draws(self, count: int = 200) -> List[dict]:
        """
        Obtener los últimos N sorteos
        Por defecto, 200 sorteos (~4 años de datos)
        """
        logger.info(f"Fetching last {count} draws from El Gordo de la Primitiva")

        draws = []
        current_date = datetime.now()

        for week in range(count):
            draw_date = current_date - timedelta(weeks=week)
            # Ajustar al domingo más reciente
            days_since_sunday = (draw_date.weekday() - 6) % 7
            sunday_date = draw_date - timedelta(days=days_since_sunday)

            url = f"{self.BASE_URL}/es/el-gordo-de-la-primitiva/resultados"
            params = {'fecha': sunday_date.strftime('%Y-%m-%d')}

            html = self._get_page(url, params)
            if html:
                result = self._parse_draw_result(html)
                if result:
                    draws.append(result)

            # Respetar rate limiting
            time.sleep(random.uniform(1, 3))

        logger.info(f"Successfully fetched {len(draws)} draws")
        return draws

    def fetch_draw_by_date(self, date: datetime) -> Optional[dict]:
        """Obtener un sorteo específico por fecha"""
        url = f"{self.BASE_URL}/es/el-gordo-de-la-primitiva/resultados"
        params = {'fecha': date.strftime('%Y-%m-%d')}

        html = self._get_page(url, params)
        if html:
            return self._parse_draw_result(html)
        return None

    def save_to_csv(self, draws: List[dict], filepath: str):
        """Guardar los sorteos en un archivo CSV"""
        df_data = []
        for draw in draws:
            row = {
                'date': draw['date'].strftime('%Y-%m-%d'),
                'n1': draw['numbers'][0],
                'n2': draw['numbers'][1],
                'n3': draw['numbers'][2],
                'n4': draw['numbers'][3],
                'n5': draw['numbers'][4],
                'key_number': draw['key_number'],
                'source': draw.get('source', 'loteriasyapuestas.es')
            }
            df_data.append(row)

        df = pd.DataFrame(df_data)
        df = df.sort_values('date', ascending=False)
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(draws)} draws to {filepath}")

    def load_from_csv(self, filepath: str) -> List[dict]:
        """Cargar sorteos desde un archivo CSV"""
        try:
            df = pd.read_csv(filepath)
            draws = []

            for _, row in df.iterrows():
                draw = {
                    'date': datetime.strptime(row['date'], '%Y-%m-%d'),
                    'numbers': [row['n1'], row['n2'], row['n3'], row['n4'], row['n5']],
                    'key_number': row['key_number'],
                    'source': row.get('source', 'loteriasyapuestas.es')
                }
                draws.append(draw)

            logger.info(f"Loaded {len(draws)} draws from {filepath}")
            return draws

        except Exception as e:
            logger.error(f"Error loading from CSV: {e}")
            return []


class HistoricalDataManager:
    """Gestor de datos históricos con cacheo"""

    def __init__(self, data_dir: str = "./backend/data"):
        self.data_dir = data_dir
        self.raw_file = f"{data_dir}/raw/primitiva_historical.csv"
        self.processed_file = f"{data_dir}/processed/primitiva_processed.pkl"
        self.scraper = PrimitivaScraper()

    def get_historical_data(self, force_refresh: bool = False) -> List[dict]:
        """Obtener datos históricos con cacheo"""
        import os
        from pathlib import Path

        # Crear directorios si no existen
        Path(self.data_dir + "/raw").mkdir(parents=True, exist_ok=True)
        Path(self.data_dir + "/processed").mkdir(parents=True, exist_ok=True)

        # Si existe archivo y no forzamos refresh, cargar del cache
        if not force_refresh and os.path.exists(self.raw_file):
            logger.info("Loading from cache")
            draws = self.scraper.load_from_csv(self.raw_file)
            if draws:
                return draws

        # Fetch nuevos datos
        logger.info("Fetching new data")
        draws = self.scraper.fetch_recent_draws(count=200)  # ~4 años de datos

        # Guardar en cache
        self.scraper.save_to_csv(draws, self.raw_file)

        return draws

    def get_processed_data(self) -> pd.DataFrame:
        """Obtener datos procesados para ML"""
        import pickle

        if os.path.exists(self.processed_file):
            with open(self.processed_file, 'rb') as f:
                return pickle.load(f)

        # Procesar datos crudos
        draws = self.get_historical_data()
        df = self._process_draws_for_ml(draws)

        # Guardar procesados
        with open(self.processed_file, 'wb') as f:
            pickle.dump(df, f)

        return df

    def _process_draws_for_ml(self, draws: List[dict]) -> pd.DataFrame:
        """Procesar datos para machine learning"""
        data = []

        for draw in sorted(draws, key=lambda x: x['date']):
            row = {
                'date': draw['date'],
                'n1': draw['numbers'][0],
                'n2': draw['numbers'][1],
                'n3': draw['numbers'][2],
                'n4': draw['numbers'][3],
                'n5': draw['numbers'][4],
                'key_number': draw['key_number'],
                'day_of_week': draw['date'].weekday(),
                'day_of_month': draw['date'].day,
                'month': draw['date'].month,
                'year': draw['date'].year,
                'week_number': draw['date'].isocalendar()[1],
            }

            # Calcular estadísticas adicionales
            row['sum'] = sum(draw['numbers'])
            row['mean'] = row['sum'] / 5
            row['std'] = pd.Series(draw['numbers']).std()
            row['min'] = min(draw['numbers'])
            row['max'] = max(draw['numbers'])
            row['range'] = row['max'] - row['min']

            data.append(row)

        df = pd.DataFrame(data)
        return df.sort_values('date', ascending=True)
