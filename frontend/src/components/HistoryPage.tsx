import { useState, useEffect } from 'react'
import { Title, Stack, Paper, Card, Text, Loader, Badge, Group, Button, Alert } from '@mantine/core'
import { IconRefresh, IconInfoCircle } from '@tabler/icons-react'
import { historyApi, DrawResult } from '../services/api'

export default function HistoryPage() {
  const [draws, setDraws] = useState<DrawResult[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDraws = async (forceRefresh = false) => {
    if (forceRefresh) setRefreshing(true)
    try {
      const data = await historyApi.getRecent(52)
      setDraws(data)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al obtener historial')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchDraws()
  }, [])

  const formatNumber = (num: number) => num.toString().padStart(2, '0')

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}><Loader size="xl" /></div>

  return (
    <Stack gap="xl">
      <Group justify="space-between">
        <Title order={2}>📜 Historial de Sorteos</Title>
        <Button
          leftSection={<IconRefresh size={16} />}
          onClick={() => fetchDraws(true)}
          loading={refreshing}
          disabled={refreshing}
        >
          Actualizar
        </Button>
      </Group>

      {error && (
        <Alert icon={<IconInfoCircle size={16} />} color="red" title="Error">
          {error}
        </Alert>
      )}

      <Paper shadow="sm" p="md" withBorder>
        <Text size="sm">
          Mostrando los últimos <Badge>{draws.length}</Badge> sorteos
        </Text>
      </Paper>

      <Stack gap="sm">
        {draws.map((draw, idx) => (
          <Card key={idx} shadow="xs" padding="md" withBorder>
            <Group justify="space-between" align="flex-start">
              <Stack gap={4}>
                <Text fw={700}>
                  {new Date(draw.date).toLocaleDateString('es-ES', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </Text>
                <Group gap={4}>
                  {draw.numbers.map((num, numIdx) => (
                    <Badge
                      key={numIdx}
                      size="lg"
                      style={{
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white'
                      }}
                    >
                      {formatNumber(num)}
                    </Badge>
                  ))}
                  <Badge
                    size="lg"
                    color="pink"
                    variant="filled"
                  >
                    K: {draw.key_number}
                  </Badge>
                </Group>
              </Stack>
              <Badge color="gray" variant="light">
                Sorteo #{draws.length - idx}
              </Badge>
            </Group>
          </Card>
        ))}
      </Stack>
    </Stack>
  )
}
