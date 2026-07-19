import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict, Tuple
from loguru import logger
import random
from collections import Counter


class TransformerPredictor(nn.Module):
    """Modelo Transformer para predicción de series temporales"""

    def __init__(
        self,
        vocab_size: int = 55,  # 0-54 (usamos 0 como padding)
        d_model: int = 128,
        nhead: int = 8,
        num_layers: int = 4,
        dropout: float = 0.1,
        max_seq_length: int = 52
    ):
        super().__init__()
        self.d_model = d_model
        self.max_seq_length = max_seq_length

        # Embedding de números
        self.number_embedding = nn.Embedding(vocab_size, d_model)
        self.positional_encoding = PositionalEncoding(d_model, max_seq_length)

        # Encoder Transformer
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers)

        # Cabeza de predicción
        self.prediction_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, vocab_size - 1)  # Excluir padding
        )

        # Cabeza para número clave
        self.key_number_head = nn.Sequential(
            nn.Linear(d_model, d_model // 4),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 4, 10)  # 0-9
        )

    def forward(self, src: torch.Tensor, mask: torch.Tensor = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        src: (batch_size, seq_length) - secuencia de números
        """
        # Embedding
        x = self.number_embedding(src)  # (batch, seq, d_model)
        x = self.positional_encoding(x)

        # Transformer encoding
        x = self.transformer_encoder(x, src_key_padding_mask=mask)  # (batch, seq, d_model)

        # Usar el último token para predicción
        last_token = x[:, -1, :]  # (batch, d_model)

        # Predicciones
        number_logits = self.prediction_head(last_token)  # (batch, vocab_size-1)
        key_logits = self.key_number_head(last_token)  # (batch, 10)

        return number_logits, key_logits


class PositionalEncoding(nn.Module):
    """Codificación posional sinusoidal"""

    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)

        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (batch, seq_len, d_model)
        """
        return x + self.pe[:x.size(1), :].transpose(0, 1)


class LSTMPredictor(nn.Module):
    """Modelo LSTM para predicción de sorteos"""

    def __init__(
        self,
        vocab_size: int = 55,
        embedding_dim: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(
            embedding_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        self.number_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, vocab_size - 1)
        )

        self.key_number_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 10)
        )

    def forward(self, src: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        src: (batch_size, seq_length)
        """
        x = self.embedding(src)
        lstm_out, (h_n, c_n) = self.lstm(x)

        # Usar el último hidden state
        last_hidden = h_n[-1]  # (batch, hidden_dim)

        number_logits = self.number_head(last_hidden)
        key_logits = self.key_number_head(last_hidden)

        return number_logits, key_logits


class EnsemblePredictor:
    """Ensemble de múltiples modelos para predicción"""

    def __init__(self, models: List[nn.Module], device: str = 'cpu'):
        self.models = models
        self.device = device
        for model in self.models:
            model.eval()
            model.to(device)

    def predict(self, sequence: List[List[int]]) -> Dict:
        """
        Realizar predicción ensemble
        sequence: Lista de sorteos anteriores [n1, n2, n3, n4, n5, key]
        """
        from app.services.scraper import HistoricalDataManager

        # Preparar input
        input_data = self._prepare_input(sequence)

        number_predictions = []
        key_predictions = []

        with torch.no_grad():
            for model in self.models:
                number_logits, key_logits = model(input_data)

                # Obtener probabilidades
                number_probs = torch.softmax(number_logits, dim=-1).cpu().numpy()[0]
                key_probs = torch.softmax(key_logits, dim=-1).cpu().numpy()[0]

                number_predictions.append(number_probs)
                key_predictions.append(key_probs)

        # Promediar predicciones
        avg_number_probs = np.mean(number_predictions, axis=0)
        avg_key_probs = np.mean(key_predictions, axis=0)

        # Seleccionar 5 números más probables
        top_numbers = self._select_top_numbers(avg_number_probs)

        # Seleccionar número clave más probable
        key_number = int(np.argmax(avg_key_probs))

        # Generar combinaciones alternativas
        alternatives = self._generate_alternatives(avg_number_probs, key_number)

        return {
            'predicted_numbers': top_numbers,
            'predicted_key_number': key_number,
            'confidence': float(avg_key_probs[key_number]),
            'number_probabilities': avg_number_probs.tolist(),
            'key_probabilities': avg_key_probs.tolist(),
            'alternative_combinations': alternatives,
            'model_used': 'ensemble'
        }

    def _prepare_input(self, sequence: List[List[int]]) -> torch.Tensor:
        """Preparar input tensor para los modelos"""
        from app.core.config import settings

        max_seq = settings.MAX_HISTORY_LENGTH

        # Aplanar cada sorteo en una secuencia
        flattened = []
        for draw in sequence[-max_seq:]:
            flattened.extend(draw)

        # Padding si es necesario
        while len(flattened) < max_seq * 6:
            flattened.append(0)  # Padding token

        # Truncar si es muy largo
        flattened = flattened[:max_seq * 6]

        # Crear tensor
        tensor = torch.LongTensor([flattened]).to(self.device)
        return tensor

    def _select_top_numbers(self, probs: np.ndarray) -> List[int]:
        """Seleccionar los 5 números más probables"""
        # Ajustar índices (+1 porque los números son 1-54, probs es 0-53)
        adjusted_probs = np.zeros(55)
        adjusted_probs[1:55] = probs  # Mover probs 0-53 a 1-54

        # Evitar repeticiones y asegurar 5 números
        selected = []
        remaining_probs = adjusted_probs.copy()

        for _ in range(5):
            best_num = int(np.argmax(remaining_probs))
            if best_num not in selected and 1 <= best_num <= 54:
                selected.append(best_num)
            remaining_probs[best_num] = -1  # Marcar como usado

        return sorted(selected)

    def _generate_alternatives(self, number_probs: np.ndarray, key_number: int, n: int = 3) -> List[List[int]]:
        """Generar combinaciones alternativas"""
        alternatives = []
        adjusted_probs = np.zeros(55)
        adjusted_probs[1:55] = number_probs

        for i in range(n):
            # Añadir un poco de ruido aleatorio
            noisy_probs = adjusted_probs.copy()
            noise = np.random.normal(0, 0.1, len(noisy_probs))
            noisy_probs += noise

            # Seleccionar 5 números diferentes
            selected = []
            remaining_probs = noisy_probs.copy()

            for _ in range(5):
                best_num = int(np.argmax(remaining_probs))
                if best_num not in selected and 1 <= best_num <= 54:
                    selected.append(best_num)
                remaining_probs[best_num] = -1

            alternatives.append(sorted(selected))

        return alternatives


class StatisticalPredictor:
    """Predictor basado en análisis estadístico"""

    def __init__(self):
        self.number_frequencies = Counter()
        self.key_frequencies = Counter()
        self.total_draws = 0

    def train(self, historical_data: List[dict]):
        """Entrenar con datos históricos"""
        self.total_draws = len(historical_data)

        for draw in historical_data:
            for num in draw['numbers']:
                self.number_frequencies[num] += 1
            self.key_frequencies[draw['key_number']] += 1

        logger.info(f"Trained on {self.total_draws} draws")

    def predict(self, current_date) -> Dict:
        """Realizar predicción basada en estadísticas"""
        # Números calientes (frecuencia alta)
        hot_numbers = [num for num, freq in self.number_frequencies.most_common(20)]

        # Números fríos (frecuencia baja)
        cold_numbers = [num for num, freq in self.number_frequencies.most_common()[-20:]]

        # Mezcla: 2 calientes, 2 medios, 1 frío
        mid_numbers = hot_numbers[5:15]
        predicted = [
            hot_numbers[0],
            hot_numbers[1],
            random.choice(mid_numbers),
            random.choice(mid_numbers),
            random.choice(cold_numbers)
        ]

        # Número clave más frecuente
        key_number = self.key_frequencies.most_common(1)[0][0]

        return {
            'predicted_numbers': sorted(predicted),
            'predicted_key_number': key_number,
            'confidence': 0.45,  # Confianza moderada para modelo estadístico
            'model_used': 'statistical',
            'hot_numbers': hot_numbers[:10],
            'cold_numbers': cold_numbers[:10],
            'alternative_combinations': []
        }


def create_models(device: str = 'cpu') -> EnsemblePredictor:
    """Crear y cargar modelos"""
    from app.core.config import settings

    models = []

    # Modelo Transformer
    transformer = TransformerPredictor(
        vocab_size=settings.MAX_NUMBER + 1,
        max_seq_length=settings.MAX_HISTORY_LENGTH
    )
    models.append(transformer)

    # Modelo LSTM
    lstm = LSTMPredictor(vocab_size=settings.MAX_NUMBER + 1)
    models.append(lstm)

    # Crear ensemble
    ensemble = EnsemblePredictor(models, device=device)

    logger.info(f"Created ensemble with {len(models)} models")
    return ensemble
