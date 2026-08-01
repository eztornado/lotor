/**
 * Componente genérico para tarjetas de lotería
 * Muestra información de predicción para cualquier tipo de lotería
 */

import { Card, Text, Group, Badge, Button, Stack, Box, Alert } from '@mantine/core';
import {
  IconTrophy,
  IconBrain,
  IconAlertTriangle,
  IconChevronRight,
} from '@tabler/icons-react';
import { LotteryType, PredictionResult } from '../types/lottery';

interface LotteryCardProps {
  lotteryType: LotteryType;
  prediction: PredictionResult;
  onClick?: () => void;
}

const LOTTERY_NAMES: Record<LotteryType, string> = {
  [LotteryType.PRIMITIVA]: 'El Gordo de la Primitiva',
  [LotteryType.NACIONAL]: 'Sorteo Nacional',
  [LotteryType.BONOLOTO]: 'Bonoloto',
  [LotteryType.EUROMILLONES]: 'Euromillones',
};

const LOTTERY_EMOJIS: Record<LotteryType, string> = {
  [LotteryType.PRIMITIVA]: '🎰',
  [LotteryType.NACIONAL]: '🎫',
  [LotteryType.BONOLOTO]: '🎱',
  [LotteryType.EUROMILLONES]: '🌟',
};

const LOTTERY_COLORS: Record<LotteryType, string> = {
  [LotteryType.PRIMITIVA]: 'blue',
  [LotteryType.NACIONAL]: 'orange',
  [LotteryType.BONOLOTO]: 'green',
  [LotteryType.EUROMILLONES]: 'yellow',
};

export function LotteryCard({ lotteryType, prediction, onClick }: LotteryCardProps) {
  const lotteryName = LOTTERY_NAMES[lotteryType];
  const emoji = LOTTERY_EMOJIS[lotteryType];
  const color = LOTTERY_COLORS[lotteryType];

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const confidenceLevel = prediction.confidence >= 0.6 ? 'Alta' :
                         prediction.confidence >= 0.45 ? 'Media' : 'Baja';

  const confidenceColor = prediction.confidence >= 0.6 ? 'green' :
                        prediction.confidence >= 0.45 ? 'yellow' : 'red';

  return (
    <Card
      shadow="sm"
      padding="lg"
      radius="md"
      withBorder
      style={{ cursor: onClick ? 'pointer' : 'default' }}
      onClick={onClick}
    >
      <Stack gap="md">
        {/* Header */}
        <Group justify="space-between" align="center">
          <Group>
            <Text size="xl">{emoji}</Text>
            <div>
              <Text fw={500} size="lg">{lotteryName}</Text>
              <Text c="dimmed" size="sm">
                Próximo sorteo: {formatDate(prediction.prediction_date)}
              </Text>
            </div>
          </Group>
          <Badge color={color} variant="light">
            {prediction.lottery_type}
          </Badge>
        </Group>

        {/* Predicción principal */}
        <Box>
          <Group gap="xs" mb="xs">
            <IconTrophy size={16} />
            <Text fw={500} size="sm">Números Predichos</Text>
          </Group>
          <Group>
            {prediction.predicted_numbers.map((num, idx) => (
              <Badge
                key={idx}
                size="xl"
                variant="filled"
                color={color}
                c="white"
              >
                {num}
              </Badge>
            ))}
            {prediction.additional_predictions.map((num, idx) => (
              <Badge
                key={`add-${idx}`}
                size="xl"
                variant="outline"
                color={color}
              >
                {num}
              </Badge>
            ))}
          </Group>
        </Box>

        {/* Información de confianza */}
        <Group justify="space-between">
          <Group>
            <IconBrain size={16} />
            <Text size="sm">Modelo: {prediction.model_used}</Text>
          </Group>
          <Badge color={confidenceColor}>
            Confianza: {confidenceLevel} ({(prediction.confidence * 100).toFixed(0)}%)
          </Badge>
        </Group>

        {/* Alerta si confianza baja */}
        {prediction.confidence < 0.4 && (
          <Alert
            icon={<IconAlertTriangle size={16} />}
            title="Confianza baja"
            color="yellow"
            variant="light"
          >
            Esta predicción tiene un nivel de confianza bajo. Considera combinar con otras estrategias.
          </Alert>
        )}

        {/* Footer */}
        {onClick && (
          <Button
            variant="light"
            color={color}
            fullWidth
            rightSection={<IconChevronRight size={16} />}
          >
            Ver detalles
          </Button>
        )}
      </Stack>
    </Card>
  );
}