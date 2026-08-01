/**
 * Dashboard multi-lotería
 * Muestra predicciones para todos los tipos de lotería soportados
 */

import { useState, useEffect } from 'react';
import {
  Container,
  Title,
  Stack,
  Grid,
  Alert,
  Group,
  Text,
  Badge,
  LoadingOverlay,
  Button,
} from '@mantine/core';
import { IconRefresh, IconAlertTriangle, IconTrophy } from '@tabler/icons-react';
import { LotteryType, PredictionResult, LotteryInfo } from '../types/lottery';
import { lotteryApi } from '../services/lotteryApi';
import { LotteryCard } from './LotteryCard';

export function MultiLotteryDashboard() {
  const [lotteries, setLotteries] = useState<LotteryInfo[]>([]);
  const [predictions, setPredictions] = useState<Record<LotteryType, PredictionResult>>({} as Record<LotteryType, PredictionResult>);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadLotteries = async () => {
    try {
      const data = await lotteryApi.getSupportedLotteries();
      setLotteries(data.filter(l => l.enabled));
    } catch (err) {
      console.error('Error loading lotteries:', err);
      setError('Error al cargar loterías soportadas');
    }
  };

  const loadPredictions = async () => {
    try {
      setError(null);
      const response = await lotteryApi.getAllPredictions();
      setPredictions(response.predictions);
    } catch (err) {
      console.error('Error loading predictions:', err);
      setError('Error al cargar predicciones');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const refreshPredictions = async () => {
    setRefreshing(true);
    await loadPredictions();
  };

  useEffect(() => {
    loadLotteries();
    loadPredictions();
  }, []);

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <LoadingOverlay visible />
      </Container>
    );
  }

  return (
    <Container size="xl" py="xl">
      <Stack gap="xl">
        {/* Header */}
        <Group justify="space-between" align="center">
          <div>
            <Title order={2}>Dashboard de Loterías</Title>
            <Text c="dimmed">Predicciones para todas las loterías activas</Text>
          </div>
          <Button
            leftSection={<IconRefresh size={16} />}
            onClick={refreshPredictions}
            loading={refreshing}
            variant="light"
          >
            Actualizar
          </Button>
        </Group>

        {/* Error Alert */}
        {error && (
          <Alert
            icon={<IconAlertTriangle size={16} />}
            title="Error"
            color="red"
            variant="light"
          >
            {error}
          </Alert>
        )}

        {/* Stats */}
        <Group>
          <Badge size="lg" leftSection={<IconTrophy size={14} />}>
            {lotteries.length} Loterías Activas
          </Badge>
          <Badge size="lg" color={Object.keys(predictions).length > 0 ? 'green' : 'red'}>
            {Object.keys(predictions).length} Predicciones Disponibles
          </Badge>
        </Group>

        {/* Loterías Grid */}
        <Grid>
          {lotteries.map((lottery) => {
            const prediction = predictions[lottery.type as LotteryType];
            // Skip if no prediction or prediction has error
            if (!prediction || (prediction as any).error) {
              console.warn(`No valid prediction for ${lottery.type}:`, prediction);
              return null;
            }

            return (
              <Grid.Col key={lottery.type} span={{ base: 12, md: 6, lg: 4 }}>
                <LotteryCard
                  lotteryType={lottery.type as LotteryType}
                  prediction={prediction}
                  onClick={() => {
                    // Navigate to detailed view
                    window.location.href = `/lottery/${lottery.type}`;
                  }}
                />
              </Grid.Col>
            );
          })}
        </Grid>

        {/* Empty State */}
        {Object.keys(predictions).length === 0 && (
          <Alert
            icon={<IconAlertTriangle size={16} />}
            title="Sin predicciones"
            color="yellow"
            variant="light"
          >
            No hay predicciones disponibles en este momento. Intenta actualizar más tarde.
          </Alert>
        )}
      </Stack>
    </Container>
  );
}