import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Group,
  Loader,
  NumberInput,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import { bonolotoApi, type BonolotoHistoryDraw } from '../../services/bonoloto'
import { Ball } from '../../components/bonoloto/Ball'
import { formatShortDate } from '../../components/bonoloto/format'

export default function BonolotoHistoryPage() {
  const [draws, setDraws] = useState<BonolotoHistoryDraw[]>([])
  const [limit, setLimit] = useState(30)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    bonolotoApi
      .history(limit)
      .then((payload) => {
        if (active) setDraws(payload)
      })
      .catch((err: any) => {
        if (active) setError(err.response?.data?.detail || 'No se ha podido cargar el historial')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [limit])

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <Stack gap={2}>
          <Title order={1}>🍀 Historial Bonoloto</Title>
          <Text c="dimmed">Últimos sorteos, del más reciente al más antiguo.</Text>
        </Stack>
        <NumberInput
          label="Sorteos a mostrar"
          value={limit}
          onChange={(value) =>
            setLimit(typeof value === 'number' ? Math.min(500, Math.max(1, value)) : 30)
          }
          min={1}
          max={500}
          step={10}
          style={{ width: 160 }}
        />
      </Group>

      {error && (
        <Alert icon={<IconInfoCircle size={16} />} color="red" title="Error">
          {error}
        </Alert>
      )}

      {loading ? (
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      ) : (
        <Stack gap="sm">
          {draws.map((draw) => (
            <Paper key={draw.date} shadow="xs" p="md" withBorder>
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text fw={700}>{formatShortDate(draw.date)}</Text>
                  <Group gap={6}>
                    {draw.complementario != null && (
                      <Badge variant="light" color="cyan">
                        C: {draw.complementario}
                      </Badge>
                    )}
                    {draw.reintegro != null && (
                      <Badge variant="light" color="pink">
                        R: {draw.reintegro}
                      </Badge>
                    )}
                  </Group>
                </Group>
                <Group gap={6}>
                  {draw.numbers.map((number) => (
                    <Ball key={number} number={number} />
                  ))}
                </Group>
              </Stack>
            </Paper>
          ))}
        </Stack>
      )}
    </Stack>
  )
}
