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
import { IconInfoCircle } from '@tabler/icons-react'
import { bonolotoApi, type BonolotoStatsResponse } from '../../services/bonoloto'
import { AnalysisPanel } from '../../components/bonoloto/AnalysisPanel'
import { formatDecimal, formatShortDate } from '../../components/bonoloto/format'

const ticketOddsLabels: Record<string, string> = {
  '6': '6 aciertos',
  '5_plus_complementario': '5 + complementario',
  '5': '5 aciertos',
  '4': '4 aciertos',
  '3': '3 aciertos',
  '3_plus': '3 o más',
}

export default function BonolotoStatsPage() {
  const [stats, setStats] = useState<BonolotoStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    bonolotoApi
      .stats()
      .then((payload) => {
        if (active) setStats(payload)
      })
      .catch((err: any) => {
        if (active) setError(err.response?.data?.detail || 'No se han podido cargar las estadísticas')
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

  return (
    <Stack gap="lg">
      <Stack gap={2}>
        <Title order={1}>🍀 Estadísticas Bonoloto</Title>
        <Text c="dimmed">
          {stats.dataset.total_draws.toLocaleString('es-ES')} sorteos desde{' '}
          {formatShortDate(stats.dataset.date_range.from)} hasta{' '}
          {formatShortDate(stats.dataset.date_range.to)}.
        </Text>
      </Stack>

      <Paper shadow="sm" p="md" withBorder>
        <Stack gap="md">
          <Title order={4}>Probabilidad por apuesta individual</Title>
          <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }} spacing="sm">
            {Object.entries(stats.model.ticket_odds).map(([key, value]) => (
              <Stack key={key} gap={0}>
                <Text size="xs" c="dimmed">
                  {ticketOddsLabels[key] ?? key}
                </Text>
                <Text fw={700}>{(1 / value).toLocaleString('es-ES', { maximumFractionDigits: 0 })}</Text>
                <Text size="xs" c="dimmed">
                  1 entre
                </Text>
              </Stack>
            ))}
          </SimpleGrid>
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
                  <Progress value={(profile.frequency / stats.analysis.most_frequent_numbers[0].frequency) * 100} />
                </Stack>
              ))}
            </Stack>
          </Paper>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Paper shadow="sm" p="md" withBorder h="100%">
            <Stack gap="sm">
              <Title order={4}>Reintegros</Title>
              {stats.analysis.reintegro.slice(0, 10).map((item) => (
                <Stack key={item.digit} gap={2}>
                  <Group justify="space-between">
                    <Badge variant="light" color="pink">
                      Dígito {item.digit}
                    </Badge>
                    <Text size="sm">
                      {formatDecimal(item.probability * 100, 1)} % · {item.frequency} veces
                    </Text>
                  </Group>
                  <Progress value={item.probability * 100 * 10} color="pink" />
                </Stack>
              ))}
            </Stack>
          </Paper>
        </Grid.Col>
      </Grid>

      <AnalysisPanel analysis={stats.analysis} />
    </Stack>
  )
}
