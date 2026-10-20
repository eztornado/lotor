import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Grid,
  Group,
  Loader,
  Paper,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { IconInfoCircle, IconKey } from '@tabler/icons-react'
import { gordoApi, type GordoStatsResponse } from '../../services/gordo'
import { AnalysisPanel } from '../../components/gordo/AnalysisPanel'
import { formatDecimal, formatPercent, formatShortDate } from '../../components/gordo/format'

const ticketOddsLabels: Record<string, string> = {
  '1': '1ª · 5 + clave',
  '2': '2ª · 5 aciertos',
  '3': '3ª · 4 + clave',
  '4': '4ª · 4 aciertos',
  '5': '5ª · 3 + clave',
  '6': '6ª · 3 aciertos',
  '7': '7ª · 2 + clave',
  '8': '8ª · 2 aciertos',
  any_prize: 'Algún premio (2+)',
  reintegro: 'Reintegro (clave)',
  any_return: 'Algún retorno (premio o reintegro)',
}

export default function StatisticsPage() {
  const [stats, setStats] = useState<GordoStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    gordoApi
      .stats()
      .then((payload) => {
        if (active) setStats(payload)
      })
      .catch((err: any) => {
        if (active)
          setError(err.response?.data?.detail || 'No se han podido cargar las estadísticas')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return (
      <Group justify="center" py="xl">
        <Loader size="lg" />
      </Group>
    )
  }

  if (error) {
    return (
      <Alert icon={<IconInfoCircle size={16} />} color="red" title="Error">
        {error}
      </Alert>
    )
  }

  if (!stats) return null

  const maxFrequency = Math.max(
    ...stats.analysis.most_frequent_numbers.map((profile) => profile.frequency),
    1,
  )
  const maxKeyProbability = Math.max(
    ...stats.analysis.key.map((item) => item.probability),
    0.0001,
  )

  return (
    <Stack gap="lg">
      <Stack gap={2}>
        <Group gap="xs">
          <Title order={1}>🎯 Estadísticas El Gordo</Title>
          <Badge color="blue" variant="light">
            Histórico completo
          </Badge>
        </Group>
        <Text c="dimmed">
          {stats.dataset.total_draws.toLocaleString('es-ES')} sorteos desde{' '}
          {formatShortDate(stats.dataset.date_range.from)} hasta{' '}
          {formatShortDate(stats.dataset.date_range.to)}.
        </Text>
      </Stack>

      <Paper shadow="sm" p="md" withBorder>
        <Stack gap="md">
          <Title order={4}>Probabilidad por apuesta individual</Title>
          <SimpleGrid cols={{ base: 2, sm: 3, md: 5 }} spacing="sm">
            {Object.entries(stats.model.ticket_odds).map(([key, value]) => (
              <Stack key={key} gap={0}>
                <Text size="xs" c="dimmed">
                  {ticketOddsLabels[key] ?? key}
                </Text>
                <Text fw={700}>
                  {(1 / value).toLocaleString('es-ES', { maximumFractionDigits: 0 })}
                </Text>
                <Text size="xs" c="dimmed">
                  1 entre ·{' '}
                  {value >= 0.01 ? formatPercent(value, 2) : formatPercent(value, 6)}
                </Text>
              </Stack>
            ))}
          </SimpleGrid>
          <Text size="xs" c="dimmed">
            La 8ª categoría premia 2 aciertos, por eso la probabilidad de algún premio por apuesta
            es del 6,2054 %. Además, la clave devuelve 1,50 € de reintegro (1 entre 10), aunque no
            se acierten 2 números; por eso la probabilidad de algún retorno es del 15,58 %. El
            primer premio (5 + clave) es 1 entre 31.625.100.
          </Text>
        </Stack>
      </Paper>

      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Paper shadow="sm" p="md" withBorder h="100%">
            <Stack gap="sm">
              <Title order={4}>Números más frecuentes</Title>
              {stats.analysis.most_frequent_numbers.slice(0, 10).map((profile) => (
                <Stack key={profile.number} gap={2}>
                  <Group justify="space-between">
                    <Badge variant="light">Nº {profile.number}</Badge>
                    <Text size="sm">{profile.frequency} veces</Text>
                  </Group>
                  <Progress value={(profile.frequency / maxFrequency) * 100} />
                </Stack>
              ))}
            </Stack>
          </Paper>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Paper shadow="sm" p="md" withBorder h="100%">
            <Stack gap="sm">
              <Group gap="xs">
                <IconKey size={18} color="#f59f00" />
                <Title order={4}>Claves (0–9)</Title>
              </Group>
              {stats.analysis.key.map((item) => (
                <Stack key={item.digit} gap={2}>
                  <Group justify="space-between">
                    <Badge variant="light" color="yellow">
                      Clave {item.digit}
                    </Badge>
                    <Text size="sm">
                      {formatDecimal(item.probability * 100, 1)} % · {item.frequency} veces
                    </Text>
                  </Group>
                  <Progress
                    value={(item.probability / maxKeyProbability) * 100}
                    color="yellow"
                  />
                </Stack>
              ))}
            </Stack>
          </Paper>
        </Grid.Col>
      </Grid>

      <AnalysisPanel analysis={stats.analysis} showFrequent={false} showKeys={false} />
    </Stack>
  )
}
