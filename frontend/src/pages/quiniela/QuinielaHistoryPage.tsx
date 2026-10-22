import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Group,
  Loader,
  NumberInput,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import { quinielaApi, type QuinielaHistoryMatch } from '../../services/quiniela'
import { formatShortDate, resultColor, resultLabel } from '../../components/quiniela/format'

export default function QuinielaHistoryPage() {
  const [matches, setMatches] = useState<QuinielaHistoryMatch[]>([])
  const [limit, setLimit] = useState(100)
  const [league, setLeague] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    quinielaApi
      .history(limit)
      .then((payload) => {
        if (active) setMatches(payload)
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

  const leagueOptions = useMemo(() => {
    const seen = new Map<string, string>()
    for (const match of matches) {
      if (!seen.has(match.league)) seen.set(match.league, match.league_name)
    }
    return Array.from(seen.entries()).map(([value, label]) => ({ value, label }))
  }, [matches])

  const filtered = useMemo(
    () =>
      matches.filter(
        (match) =>
          (!league || match.league === league) && (!result || match.result === result),
      ),
    [matches, league, result],
  )

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <Stack gap={2}>
          <Title order={1}>⚽ Historial de partidos</Title>
          <Text c="dimmed">
            Resultados recientes usados por el modelo, del más nuevo al más antiguo.
          </Text>
        </Stack>
        <Group align="flex-end" wrap="wrap">
          <Select
            label="Competición"
            value={league}
            onChange={setLeague}
            data={leagueOptions}
            clearable
            placeholder="Todas"
            style={{ width: 210 }}
          />
          <Select
            label="Resultado"
            value={result}
            onChange={setResult}
            data={[
              { value: 'H', label: '1 · Local' },
              { value: 'D', label: 'X · Empate' },
              { value: 'A', label: '2 · Visitante' },
            ]}
            clearable
            placeholder="Todos"
            style={{ width: 160 }}
          />
          <NumberInput
            label="Partidos"
            value={limit}
            onChange={(value) =>
              setLimit(typeof value === 'number' ? Math.min(500, Math.max(10, value)) : 100)
            }
            min={10}
            max={500}
            step={10}
            style={{ width: 130 }}
          />
        </Group>
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
        <Paper shadow="sm" p="md" withBorder>
          <ScrollArea>
            <Table striped highlightOnHover miw={760}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Fecha</Table.Th>
                  <Table.Th>Competición</Table.Th>
                  <Table.Th>Partido</Table.Th>
                  <Table.Th>Marcador</Table.Th>
                  <Table.Th>Signo</Table.Th>
                  <Table.Th>Cuotas 1/X/2</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {filtered.map((match) => (
                  <Table.Tr key={`${match.date}-${match.home_team}-${match.away_team}`}>
                    <Table.Td>
                      <Text size="sm">{formatShortDate(match.date)}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="light" color="gray">
                        {match.league_name}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        <strong>{match.home_team}</strong> vs {match.away_team}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" fw={600}>
                        {match.home_goals} - {match.away_goals}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge color={resultColor(match.result)} variant="light">
                        {resultLabel(match.result)}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" c="dimmed">
                        {match.odds.home?.toFixed(2) ?? '—'} / {match.odds.draw?.toFixed(2) ?? '—'} /{' '}
                        {match.odds.away?.toFixed(2) ?? '—'}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>
          {filtered.length === 0 && (
            <Text size="sm" c="dimmed" ta="center" py="md">
              No hay partidos que coincidan con los filtros.
            </Text>
          )}
        </Paper>
      )}
    </Stack>
  )
}
