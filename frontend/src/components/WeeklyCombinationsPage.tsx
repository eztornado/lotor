import { useState, useEffect } from 'react'
import {
  Title, Stack, Paper, Grid, Card, Group, Button, Badge, Alert, Text, Box, Progress, NumberInput
} from '@mantine/core'
import { IconRefresh, IconInfoCircle, IconAlertTriangle, IconBulb, IconTrophy, IconShield, IconScale } from '@tabler/icons-react'
import { combinationsApi, WeeklyCombinationsResponse, Combination } from '../services/api'

export default function WeeklyCombinationsPage() {
  const [data, setData] = useState<WeeklyCombinationsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [numCombinations, setNumCombinations] = useState(7)
  const [selectedCombinations, setSelectedCombinations] = useState<Set<number>>(new Set())

  const fetchCombinations = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await combinationsApi.getWeekly(numCombinations)
      setData(result)
      setSelectedCombinations(new Set(result.combinations.map((_, i) => i))) // Select all by default
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al obtener combinaciones')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCombinations()
  }, [numCombinations])

  const toggleCombination = (index: number) => {
    const newSelected = new Set(selectedCombinations)
    if (newSelected.has(index)) {
      newSelected.delete(index)
    } else {
      newSelected.add(index)
    }
    setSelectedCombinations(newSelected)
  }

  const formatNumber = (num: number) => num.toString().padStart(2, '0')

  const getRiskIcon = (risk: string) => {
    switch (risk) {
      case 'conservative': return <IconShield size={16} />
      case 'balanced': return <IconScale size={16} />
      case 'risky': return <IconTrophy size={16} />
      default: return <IconInfoCircle size={16} />
    }
  }

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'conservative': return 'green'
      case 'balanced': return 'blue'
      case 'risky': return 'red'
      default: return 'gray'
    }
  }

  const getTotalCost = () => {
    const selected = Array.from(selectedCombinations).length
    return selected * 1.5  // 1.50€ por apuesta
  }

  return (
    <Stack gap="xl">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <Title order={2}>🎯 Tus 7 Combinaciones Semanales</Title>
        <Group>
          <NumberInput
            label="Combinaciones"
            value={numCombinations}
            onChange={(value) => setNumCombinations(typeof value === 'number' ? value : 7)}
            min={1}
            max={15}
            style={{ width: '120px' }}
          />
          <Button
            leftSection={<IconRefresh size={16} />}
            onClick={fetchCombinations}
            loading={loading}
            disabled={loading}
          >
            Actualizar
          </Button>
        </Group>
      </div>

      <Alert icon={<IconAlertTriangle size={16} />} color="red" variant="light">
        <Text size="sm">
          <strong>AVISO:</strong> Estas combinaciones son solo para fines educativos y entretenimiento. La lotería es un juego de azar. Juega de forma responsable.
        </Text>
      </Alert>

      {error && (
        <Alert icon={<IconInfoCircle size={16} />} color="red" title="Error">
          {error}
        </Alert>
      )}

      {loading && (
        <Box style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <div className="loading-spinner" />
            <Text>Generando tus combinaciones estratégicas...</Text>
          </div>
        </Box>
      )}

      {data && !loading && (
        <>
          <Paper shadow="sm" p="md" withBorder>
            <Stack gap="md">
              <Group justify="space-between">
                <Text size="lg" fw={700}>
                  Próximo Sorteo: {new Date(data.draw_date).toLocaleDateString('es-ES', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </Text>
                <Badge size="lg" color="blue">
                  {data.total_combinations} combinaciones
                </Badge>
              </Group>

              <Group>
                <Text size="sm">Seleccionadas: <strong>{selectedCombinations.size}</strong></Text>
                <Text size="sm">Coste total: <strong>{getTotalCost().toFixed(2)}€</strong></Text>
              </Group>

              <Progress
                value={data.coverage_metrics.unique_numbers_coverage}
                color="green"
                size="lg"
              />
              <Text size="xs" c="dimmed">
                Cobertura de números: {data.coverage_metrics.unique_numbers_coverage.toFixed(1)}%
              </Text>

              <Text size="xs" c="dimmed">
                Solapamiento promedio: {data.coverage_metrics.avg_combination_overlap.toFixed(1)} números por combinación
              </Text>
            </Stack>
          </Paper>

          {data.recommendations.warnings.length > 0 && (
            <Alert icon={<IconBulb size={16} />} color="yellow" variant="light">
              <Stack gap="xs">
                <Text fw={700}>Recomendaciones:</Text>
                {data.recommendations.warnings.map((warning, idx) => (
                  <Text key={idx} size="sm">• {warning}</Text>
                ))}
              </Stack>
            </Alert>
          )}

          <Paper shadow="sm" p="md" withBorder>
            <Stack gap="sm">
              <Text fw={700}>📊 Estrategia de Juego: <span style={{ textTransform: 'capitalize' }}>{data.recommendations.play_strategy}</span></Text>
              <Group>
                <Badge color="green">{data.recommendations.budget_allocation.high_confidence} de alta confianza</Badge>
                <Badge color="blue">{data.recommendations.budget_allocation.medium_confidence} de confianza media</Badge>
                <Badge color="orange">{data.recommendations.budget_allocation.low_confidence} de baja confianza</Badge>
              </Group>
            </Stack>
          </Paper>

          <Grid>
            {data.combinations.map((combo: Combination, idx: number) => (
              <Grid.Col key={idx} span={{ base: 12, md: 6, lg: 4 }}>
                <Card
                  shadow={selectedCombinations.has(idx) ? "xl" : "sm"}
                  padding="lg"
                  radius="md"
                  withBorder
                  style={{
                    background: selectedCombinations.has(idx) ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'transparent',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease'
                  }}
                  onClick={() => toggleCombination(idx)}
                >
                  <Stack gap="sm">
                    <Group justify="space-between">
                      <Badge
                        color={getRiskColor(combo.risk_level)}
                        leftSection={getRiskIcon(combo.risk_level)}
                        size="lg"
                      >
                        {combo.strategy}
                      </Badge>
                      <Badge
                        color={selectedCombinations.has(idx) ? 'white' : 'blue'}
                        variant={selectedCombinations.has(idx) ? 'filled' : 'light'}
                      >
                        {selectedCombinations.has(idx) ? '✓ Seleccionada' : 'Click para seleccionar'}
                      </Badge>
                    </Group>

                    <Text size="xs" c={selectedCombinations.has(idx) ? 'white' : 'dimmed'}>
                      {combo.description}
                    </Text>

                    <Group gap={4}>
                      {combo.numbers.map((num, numIdx) => (
                        <Box
                          key={numIdx}
                          style={{
                            background: selectedCombinations.has(idx) ? 'rgba(255,255,255,0.2)' : '#228be6',
                            color: 'white',
                            width: '35px',
                            height: '35px',
                            borderRadius: '6px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '0.9rem',
                            fontWeight: 700,
                            border: selectedCombinations.has(idx) ? '2px solid white' : 'none'
                          }}
                        >
                          {formatNumber(num)}
                        </Box>
                      ))}
                      <Box
                        style={{
                          background: selectedCombinations.has(idx) ? 'rgba(255,255,255,0.3)' : '#ed6ea0',
                          color: 'white',
                          width: '35px',
                          height: '35px',
                          borderRadius: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '0.9rem',
                          fontWeight: 700,
                          border: selectedCombinations.has(idx) ? '2px solid white' : 'none'
                        }}
                      >
                        K:{combo.key_number}
                      </Box>
                    </Group>

                    <Group>
                      <Text size="xs" c={selectedCombinations.has(idx) ? 'white' : 'dimmed'}>
                        Confianza: <strong>{(combo.confidence * 100).toFixed(1)}%</strong>
                      </Text>
                      <Badge
                        size="xs"
                        color={selectedCombinations.has(idx) ? 'white' : getRiskColor(combo.risk_level)}
                        variant={selectedCombinations.has(idx) ? 'filled' : 'light'}
                      >
                        {combo.risk_level}
                      </Badge>
                    </Group>
                  </Stack>
                </Card>
              </Grid.Col>
            ))}
          </Grid>

          {selectedCombinations.size > 0 && (
            <Paper shadow="xl" p="xl" withBorder style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              <Stack gap="md">
                <Title order={3} c="white">🎱 Tu Selección Final</Title>
                <Group>
                  <Text size="lg" c="white">
                    <strong>{selectedCombinations.size}</strong> combinaciones seleccionadas
                  </Text>
                  <Text size="lg" c="white">
                    Coste total: <strong>{getTotalCost().toFixed(2)}€</strong>
                  </Text>
                </Group>

                <Stack gap="xs">
                  {Array.from(selectedCombinations).sort((a, b) => a - b).map((idx) => {
                    const combo = data.combinations[idx]
                    return (
                      <Group key={idx} gap="xs" style={{ color: 'white' }}>
                        <Text size="sm">Combinación #{idx + 1} ({combo.strategy}):</Text>
                        {combo.numbers.map((num, numIdx) => (
                          <Box key={numIdx} style={{
                            background: 'rgba(255,255,255,0.2)',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '0.8rem',
                            fontWeight: 600
                          }}>
                            {num}
                          </Box>
                        ))}
                        <Box style={{
                          background: 'rgba(255,255,255,0.3)',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          fontWeight: 600
                        }}>
                          K:{combo.key_number}
                        </Box>
                      </Group>
                    )
                  })}
                </Stack>

                <Button
                  size="lg"
                  color="white"
                  variant="filled"
                  leftSection={<IconTrophy size={20} />}
                  style={{ alignSelf: 'flex-start' }}
                >
                  Copiar Combinaciones
                </Button>
              </Stack>
            </Paper>
          )}
        </>
      )}
    </Stack>
  )
}