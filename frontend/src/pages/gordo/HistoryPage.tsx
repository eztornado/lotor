import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  NumberInput,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { IconInfoCircle, IconRefresh } from '@tabler/icons-react'
import { gordoApi, type GordoHistoryDraw } from '../../services/gordo'
import { Ball } from '../../components/gordo/Ball'
import { formatKey, formatShortDate } from '../../components/gordo/format'

export default function HistoryPage() {
  const [draws, setDraws] = useState<GordoHistoryDraw[]>([])
  const [limit, setLimit] = useState(30)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const fetchDraws = async () => {
    setLoading(true)
    try {
      const payload = await gordoApi.history(limit)
      setDraws(payload)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'No se ha podido cargar el historial')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    setLoading(true)
    gordoApi
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

  const refresh = async () => {
    setRefreshing(true)
    setNotice(null)
    try {
      const result = await gordoApi.refresh()
      setNotice(`Histórico actualizado: ${result.total_draws.toLocaleString('es-ES')} sorteos.`)
      await fetchDraws()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'No se ha podido actualizar el histórico')
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <Stack gap={2}>
          <Group gap="xs">
            <Title order={1}>🎯 Historial El Gordo</Title>
            <Badge color="blue" variant="light">
              Desde 2005
            </Badge>
          </Group>
          <Text c="dimmed">Últimos sorteos, del más reciente al más antiguo.</Text>
        </Stack>
        <Group align="flex-end">
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
          <Button
            leftSection={<IconRefresh size={16} />}
            variant="light"
            onClick={refresh}
            loading={refreshing}
            disabled={refreshing}
          >
            Actualizar
          </Button>
        </Group>
      </Group>

      {error && (
        <Alert icon={<IconInfoCircle size={16} />} color="red" title="Error">
          {error}
        </Alert>
      )}

      {notice && (
        <Alert color="teal" variant="light">
          {notice}
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
                    <Badge variant="light" color="yellow">
                      Clave: {draw.key_number != null ? formatKey(draw.key_number) : '—'}
                    </Badge>
                    {draw.source && (
                      <Badge variant="outline" color="gray">
                        {draw.source}
                      </Badge>
                    )}
                  </Group>
                </Group>
                <Group gap={6}>
                  {draw.numbers.map((number) => (
                    <Ball key={number} number={number} />
                  ))}
                  {draw.key_number != null && (
                    <Ball number={draw.key_number} variant="key" />
                  )}
                </Group>
              </Stack>
            </Paper>
          ))}
        </Stack>
      )}
    </Stack>
  )
}
