import { useState, useEffect } from 'react'
import { Title, Stack, Paper, Grid, Card, Text, Loader, Badge, Progress, Box, Group } from '@mantine/core'
import { statsApi, NumberStats, KeyNumberStats } from '../services/api'

export default function StatisticsPage() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await statsApi.getGeneral()
        setStats(data)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Error al obtener estadísticas')
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  if (loading) return <Box style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}><Loader size="xl" /></Box>
  if (error) return <Text c="red">{error}</Text>
  if (!stats) return <Text>No hay datos disponibles</Text>

  const hotNumbers = stats.number_stats.filter((n: NumberStats) => n.hot).slice(0, 10)
  const coldNumbers = stats.number_stats.filter((n: NumberStats) => n.cold).slice(0, 10)

  return (
    <Stack gap={32}>
      <Title order={2}>📊 Estadísticas Generales</Title>

      <Paper shadow="sm" p="md" withBorder>
        <Stack gap="sm">
          <Group>
            <Text size="lg" fw={700}>Total Sorteos Analizados:</Text>
            <Badge size="lg">{stats.total_draws}</Badge>
          </Group>
          <Group>
            <Text size="lg" fw={700}>Próximo Sorteo:</Text>
            <Text>{new Date(stats.next_draw_date).toLocaleDateString('es-ES')}</Text>
          </Group>
        </Stack>
      </Paper>

      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card shadow="sm" p="md" withBorder>
            <Stack gap="sm">
              <Text fw={700} c="green">🔥 Números Calientes</Text>
              {hotNumbers.map((num: NumberStats) => (
                <Group key={num.number} justify="space-between">
                  <Badge color="green" size="lg">{num.number}</Badge>
                  <Box style={{ flex: 1 }}>
                    <Progress value={num.percentage} color="green" size="sm" />
                  </Box>
                  <Text size="sm">{num.percentage.toFixed(1)}%</Text>
                </Group>
              ))}
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card shadow="sm" p="md" withBorder>
            <Stack gap="sm">
              <Text fw={700} c="blue">❄️ Números Fríos</Text>
              {coldNumbers.map((num: NumberStats) => (
                <Group key={num.number} justify="space-between">
                  <Badge color="blue" size="lg">{num.number}</Badge>
                  <Box style={{ flex: 1 }}>
                    <Progress value={num.percentage} color="blue" size="sm" />
                  </Box>
                  <Text size="sm">{num.percentage.toFixed(1)}%</Text>
                </Group>
              ))}
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>

      <Card shadow="sm" p="md" withBorder>
        <Stack gap="sm">
          <Text fw={700}>🔑 Números Clave</Text>
          <Grid>
            {stats.key_number_stats.map((keyStat: KeyNumberStats) => (
              <Grid.Col key={keyStat.key_number} span={2}>
                <Card padding="xs" withBorder={keyStat.hot || keyStat.cold} style={{
                  background: keyStat.hot ? 'rgba(92, 184, 92, 0.2)' : keyStat.cold ? 'rgba(91, 192, 222, 0.2)' : 'transparent',
                  textAlign: 'center'
                }}>
                  <Badge size="xl" color={keyStat.hot ? 'green' : keyStat.cold ? 'blue' : 'gray'}>
                    {keyStat.key_number}
                  </Badge>
                  <Text size="xs" mt={4}>{keyStat.percentage.toFixed(1)}%</Text>
                </Card>
              </Grid.Col>
            ))}
          </Grid>
        </Stack>
      </Card>
    </Stack>
  )
}
