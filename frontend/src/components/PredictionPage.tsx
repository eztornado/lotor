import { useState, useEffect } from 'react'
import {
  Container, Title, Stack, Paper, Grid, Card, Group, Button, Badge,
  Alert, Text, Loader, NumberInput, ActionIcon, Box
} from '@mantine/core'
import { IconBrain, IconRefresh, IconInfoCircle, IconArrowRight, IconAlertTriangle } from '@tabler/icons-react'
import { predictionsApi } from '../services/api'

interface Prediction {
  prediction_date: string
  predicted_numbers: number[]
  predicted_key_number: number
  confidence: number
  model_used: string
  alternative_combinations: number[][]
  analysis?: any
}

export default function PredictionPage() {
  const [prediction, setPrediction] = useState<Prediction | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [customNumbers, setCustomNumbers] = useState<number[]>([1, 2, 3, 4, 5])
  const [customKey, setCustomKey] = useState(0)

  const fetchPrediction = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await predictionsApi.predict()
      setPrediction(result)
      setCustomNumbers(result.predicted_numbers)
      setCustomKey(result.predicted_key_number)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al obtener predicción')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPrediction()
  }, [])

  const handleNumberChange = (index: number, value: number | string) => {
    const numValue = typeof value === 'string' ? parseInt(value) || 1 : value
    const newNumbers = [...customNumbers]
    newNumbers[index] = Math.max(1, Math.min(54, numValue))
    setCustomNumbers(newNumbers)
  }

  const formatNumber = (num: number) => num.toString().padStart(2, '0')

  return (
    <Stack gap="xl">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title order={2}>🎯 Predicción para Próximo Sorteo</Title>
        <Button
          leftSection={<IconRefresh size={16} />}
          onClick={fetchPrediction}
          loading={loading}
          disabled={loading}
        >
          Actualizar Predicción
        </Button>
      </div>

      <Alert icon={<IconAlertTriangle size={16} />} color="red" variant="light">
        <Text size="sm">
          <strong>AVISO:</strong> Esta predicción es solo para fines educativos y entretenimiento. La lotería es un juego
          de azar. Juega de forma responsable.
        </Text>
      </Alert>

      {error && (
        <Alert icon={<IconInfoCircle size={16} />} color="red" title="Error">
          {error}
        </Alert>
      )}

      {loading && (
        <Box style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
          <Loader size="xl" />
        </Box>
      )}

      {prediction && !loading && (
        <>
          <Grid>
            <Grid.Col span={{ base: 12, md: 8 }}>
              <Paper shadow="sm" p="md" withBorder>
                <Stack gap="md">
                  <Group justify="space-between">
                    <Text size="lg" fw={700}>
                      Próximo Sorteo: {new Date(prediction.prediction_date).toLocaleDateString('es-ES', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </Text>
                    <Badge color="blue" size="lg">Confianza: {(prediction.confidence * 100).toFixed(1)}%</Badge>
                  </Group>

                  <Stack gap="sm" mt="md">
                    <Text size="sm" fw={600}>Números Predichos:</Text>
                    <Group>
                      {prediction.predicted_numbers.map((num, idx) => (
                        <Card
                          key={idx}
                          shadow="sm"
                          padding="md"
                          radius="md"
                          withBorder
                          style={{
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            color: 'white',
                            minWidth: '60px',
                            textAlign: 'center',
                            fontWeight: 700,
                            fontSize: '1.2rem'
                          }}
                        >
                          {formatNumber(num)}
                        </Card>
                      ))}
                    </Group>
                  </Stack>

                  <Stack gap="sm" mt="md">
                    <Text size="sm" fw={600}>Número Clave:</Text>
                    <Card
                      shadow="sm"
                      padding="md"
                      radius="md"
                      withBorder
                      style={{
                        background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                        color: 'white',
                        width: '60px',
                        textAlign: 'center',
                        fontWeight: 700,
                        fontSize: '1.5rem'
                      }}
                    >
                      {prediction.predicted_key_number}
                    </Card>
                  </Stack>

                  <Group mt="md">
                    <Badge color="green" variant="light">Modelo: {prediction.model_used}</Badge>
                    {prediction.analysis && (
                      <Badge color="orange" variant="light">
                        Datos: {prediction.analysis.total_historical_draws} sorteos
                      </Badge>
                    )}
                  </Group>
                </Stack>
              </Paper>
            </Grid.Col>

            <Grid.Col span={{ base: 12, md: 4 }}>
              <Paper shadow="sm" p="md" withBorder h="100%">
                <Stack gap="sm">
                  <Title order={4}>Combinaciones Alternativas</Title>
                  <Text size="xs" c="dimmed">
                    Otras combinaciones con alta probabilidad
                  </Text>

                  {prediction.alternative_combinations.map((combo, idx) => (
                    <Card key={idx} shadow="xs" padding="sm" withBorder>
                      <Group gap={4}>
                        {combo.map((num, numIdx) => (
                          <Box
                            key={numIdx}
                            style={{
                              background: '#228be6',
                              color: 'white',
                              width: '30px',
                              height: '30px',
                              borderRadius: '4px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '0.8rem',
                              fontWeight: 600
                            }}
                          >
                            {num}
                          </Box>
                        ))}
                      </Group>
                    </Card>
                  ))}
                </Stack>
              </Paper>
            </Grid.Col>
          </Grid>

          {prediction.analysis?.hot_numbers && (
            <Paper shadow="sm" p="md" withBorder>
              <Stack gap="sm">
                <Title order={4}>📊 Análisis de Números</Title>
                <Grid>
                  <Grid.Col span={6}>
                    <Text size="sm" fw={600} c="green">Números Calientes:</Text>
                    <Group mt={4} gap={4}>
                      {prediction.analysis.hot_numbers.slice(0, 10).map(([num, freq]: [number, number]) => (
                        <Badge key={num} color="green" variant="light">
                          {num} ({freq})
                        </Badge>
                      ))}
                    </Group>
                  </Grid.Col>
                  <Grid.Col span={6}>
                    <Text size="sm" fw={600} c="red">Números Fríos:</Text>
                    <Group mt={4} gap={4}>
                      {prediction.analysis.cold_numbers.slice(0, 10).map(([num, freq]: [number, number]) => (
                        <Badge key={num} color="red" variant="light">
                          {num} ({freq})
                        </Badge>
                      ))}
                    </Group>
                  </Grid.Col>
                </Grid>
              </Stack>
            </Paper>
          )}

          <Paper shadow="sm" p="md" withBorder>
            <Stack gap="sm">
              <Title order={4}>🎱 Simular Combinación</Title>
              <Text size="xs" c="dimmed">
                Ajusta los números para simular tu propia combinación
              </Text>

              <Group>
                {customNumbers.map((num, idx) => (
                  <NumberInput
                    key={idx}
                    value={num}
                    onChange={(value) => handleNumberChange(idx, value)}
                    min={1}
                    max={54}
                    style={{ width: '70px' }}
                    size="sm"
                  />
                ))}
              </Group>

              <NumberInput
                label="Número Clave"
                value={customKey}
                onChange={(value) => setCustomKey(typeof value === 'number' ? value : parseInt(value) || 0)}
                min={0}
                max={9}
                style={{ width: '100px' }}
                size="sm"
              />
            </Stack>
          </Paper>
        </>
      )}
    </Stack>
  )
}
