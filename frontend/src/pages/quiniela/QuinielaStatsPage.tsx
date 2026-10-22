import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Grid,
  Group,
  Loader,
  Paper,
  Progress,
  ScrollArea,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { IconInfoCircle, IconSearch } from '@tabler/icons-react'
import {
  quinielaApi,
  type QuinielaStatsResponse,
  type QuinielaTeamResponse,
} from '../../services/quiniela'
import {
  formatPercent,
  formatShortDate,
  formColor,
  formLabel,
  outcomeColor,
} from '../../components/quiniela/format'

export default function QuinielaStatsPage() {
  const [stats, setStats] = useState<QuinielaStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [teamQuery, setTeamQuery] = useState('')
  const [team, setTeam] = useState<QuinielaTeamResponse | null>(null)
  const [teamLoading, setTeamLoading] = useState(false)
  const [teamError, setTeamError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    quinielaApi
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

  const searchTeam = async () => {
    if (!teamQuery.trim()) return
    setTeamLoading(true)
    setTeamError(null)
    try {
      setTeam(await quinielaApi.team(teamQuery.trim()))
    } catch (err: any) {
      setTeam(null)
      setTeamError(err.response?.data?.detail || 'No se ha encontrado el equipo')
    } finally {
      setTeamLoading(false)
    }
  }

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

  const backtest = stats.backtest

  return (
    <Stack gap="lg">
      <Stack gap={2}>
        <Title order={1}>⚽ Estadísticas de La Quiniela</Title>
        <Text c="dimmed">
          {stats.dataset.total_matches.toLocaleString('es-ES')} partidos desde{' '}
          {formatShortDate(stats.dataset.date_range.from)} hasta{' '}
          {formatShortDate(stats.dataset.date_range.to)} · {stats.dataset.teams} equipos ·{' '}
          {stats.dataset.leagues} competiciones.
        </Text>
      </Stack>

      <SimpleGrid cols={{ base: 2, sm: 3, md: 5 }} spacing="md">
        <Paper shadow="xs" p="md" withBorder>
          <Text size="xs" c="dimmed">
            Ventaja de campo
          </Text>
          <Text fw={700} size="lg">
            +{stats.model.home_advantage.toFixed(3)}
          </Text>
          <Text size="xs" c="dimmed">
            en log-goles
          </Text>
        </Paper>
        <Paper shadow="xs" p="md" withBorder>
          <Text size="xs" c="dimmed">
            Media local / empate / visitante
          </Text>
          <Text fw={700} size="lg">
            {formatPercent(stats.model.global_base['1'])} / {formatPercent(stats.model.global_base['X'])} /{' '}
            {formatPercent(stats.model.global_base['2'])}
          </Text>
          <Text size="xs" c="dimmed">
            histórico global
          </Text>
        </Paper>
        <Paper shadow="xs" p="md" withBorder>
          <Text size="xs" c="dimmed">
            Vida media de los datos
          </Text>
          <Text fw={700} size="lg">
            {Math.round(stats.model.config.half_life_days)} días
          </Text>
          <Text size="xs" c="dimmed">
            ponderación temporal
          </Text>
        </Paper>
        <Paper shadow="xs" p="md" withBorder>
          <Text size="xs" c="dimmed">
            Acierto en backtest
          </Text>
          <Text fw={700} size="lg">
            {backtest.accuracy != null ? formatPercent(backtest.accuracy) : '—'}
          </Text>
          <Text size="xs" c="dimmed">
            {backtest.matches ?? 0} partidos fuera de muestra
          </Text>
        </Paper>
        <Paper shadow="xs" p="md" withBorder>
          <Text size="xs" c="dimmed">
            Log-loss
          </Text>
          <Text fw={700} size="lg">
            {backtest.log_loss?.toFixed(3) ?? '—'}
          </Text>
          <Text size="xs" c="dimmed">
            baseline {backtest.baseline_log_loss?.toFixed(3) ?? '—'}
          </Text>
        </Paper>
      </SimpleGrid>

      <Grid>
        <Grid.Col span={{ base: 12, lg: 7 }}>
          <Paper shadow="sm" p="md" withBorder h="100%">
            <Stack gap="sm">
              <Stack gap={2}>
                <Title order={4}>Rendimiento del modelo</Title>
                <Text size="xs" c="dimmed">
                  Corte: {formatShortDate(backtest.cutoff)} · {backtest.train_matches ?? 0}{' '}
                  partidos de entrenamiento.
                </Text>
              </Stack>
              <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
                <Stack gap={0}>
                  <Text size="xs" c="dimmed">
                    Acierto del modelo
                  </Text>
                  <Text fw={700}>{backtest.accuracy != null ? formatPercent(backtest.accuracy) : '—'}</Text>
                </Stack>
                <Stack gap={0}>
                  <Text size="xs" c="dimmed">
                    Acierto baseline
                  </Text>
                  <Text fw={700}>
                    {backtest.baseline_accuracy != null ? formatPercent(backtest.baseline_accuracy) : '—'}
                  </Text>
                </Stack>
                <Stack gap={0}>
                  <Text size="xs" c="dimmed">
                    Brier score
                  </Text>
                  <Text fw={700}>{backtest.brier_score?.toFixed(3) ?? '—'}</Text>
                </Stack>
              </SimpleGrid>

              <Table verticalSpacing="xs">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Confianza</Table.Th>
                    <Table.Th>Partidos</Table.Th>
                    <Table.Th>Prob. media</Table.Th>
                    <Table.Th>Acierto real</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {(backtest.calibration ?? []).map((bucket) => (
                    <Table.Tr key={bucket.min_confidence}>
                      <Table.Td>
                        <Badge variant="light">{`≥ ${Math.round(bucket.min_confidence * 100)} %`}</Badge>
                      </Table.Td>
                      <Table.Td>{bucket.matches}</Table.Td>
                      <Table.Td>
                        {bucket.average_confidence != null
                          ? formatPercent(bucket.average_confidence)
                          : '—'}
                      </Table.Td>
                      <Table.Td>
                        {bucket.accuracy != null ? formatPercent(bucket.accuracy) : '—'}
                      </Table.Td>
                      <Table.Td>
                        <Progress
                          value={bucket.accuracy != null ? bucket.accuracy * 100 : 0}
                          color="teal"
                          size="sm"
                          style={{ width: 80 }}
                        />
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Stack>
          </Paper>
        </Grid.Col>

        <Grid.Col span={{ base: 12, lg: 5 }}>
          <Paper shadow="sm" p="md" withBorder h="100%">
            <Stack gap="md">
              <Stack gap={2}>
                <Title order={4}>Buscar equipo</Title>
                <Text size="xs" c="dimmed">
                  Consulta la fuerza estimada, la forma reciente y el último partido.
                </Text>
              </Stack>
              <Group align="flex-end">
                <TextInput
                  placeholder="Real Madrid, Osasuna..."
                  value={teamQuery}
                  onChange={(event) => setTeamQuery(event.currentTarget.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') void searchTeam()
                  }}
                  style={{ flex: 1 }}
                />
                <Button
                  leftSection={<IconSearch size={16} />}
                  onClick={() => void searchTeam()}
                  loading={teamLoading}
                >
                  Buscar
                </Button>
              </Group>
              {teamError && (
                <Alert icon={<IconInfoCircle size={16} />} color="orange" variant="light">
                  {teamError}
                </Alert>
              )}
              {team && (
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Stack gap={0}>
                      <Text fw={700}>{team.team.name}</Text>
                      <Text size="xs" c="dimmed">
                        {team.team.league_name ?? 'Sin liga'}
                      </Text>
                    </Stack>
                    <Badge color="teal" variant="light">
                      Elo {team.team.elo?.toFixed(0) ?? '—'}
                    </Badge>
                  </Group>
                  <SimpleGrid cols={1}>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Partidos en el histórico
                      </Text>
                      <Text size="sm" fw={600}>
                        {team.team.matches}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Ataque / defensa
                      </Text>
                      <Text size="sm" fw={600}>
                        {team.team.attack?.toFixed(3) ?? '—'} / {team.team.defense?.toFixed(3) ?? '—'}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Goles a favor / contra
                      </Text>
                      <Text size="sm" fw={600}>
                        {team.team.goals_for?.toFixed(2) ?? '—'} / {team.team.goals_against?.toFixed(2) ?? '—'}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Forma (últimos 5)
                      </Text>
                      <Group gap={4}>
                        {team.team.form.length === 0 && <Text size="sm">—</Text>}
                        {team.team.form.map((value, index) => (
                          <Badge
                            key={`${value}-${index}`}
                            size="sm"
                            variant="light"
                            color={formColor(value)}
                          >
                            {formLabel(value)}
                          </Badge>
                        ))}
                      </Group>
                    </Group>
                  </SimpleGrid>
                  <ScrollArea h={160}>
                    <Stack gap={4}>
                      {team.recent.map((match) => (
                        <Group key={`${match.date}-${match.home}-${match.away}`} justify="space-between">
                          <Text size="xs" c="dimmed">
                            {formatShortDate(match.date)}
                          </Text>
                          <Text size="xs">
                            {match.home} {match.score} {match.away}
                          </Text>
                          <Badge size="xs" variant="light" color={outcomeColor(match.result)}>
                            {match.result}
                          </Badge>
                        </Group>
                      ))}
                    </Stack>
                  </ScrollArea>
                </Stack>
              )}
            </Stack>
          </Paper>
        </Grid.Col>
      </Grid>

      <Paper shadow="sm" p="md" withBorder>
        <Stack gap="sm">
          <Title order={4}>Competiciones</Title>
          <ScrollArea>
            <Table striped highlightOnHover miw={820}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Competición</Table.Th>
                  <Table.Th>Partidos</Table.Th>
                  <Table.Th>Goles/partido</Table.Th>
                  <Table.Th>1</Table.Th>
                  <Table.Th>X</Table.Th>
                  <Table.Th>2</Table.Th>
                  <Table.Th>+2,5 goles</Table.Th>
                  <Table.Th>Ambos marcan</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {stats.leagues.map((league) => (
                  <Table.Tr key={league.league}>
                    <Table.Td>
                      <Group gap="xs">
                        <Badge variant="light" color="gray">
                          {league.league}
                        </Badge>
                        <Text size="sm">{league.name}</Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>{league.matches.toLocaleString('es-ES')}</Table.Td>
                    <Table.Td>{league.average_goals.toFixed(2)}</Table.Td>
                    <Table.Td>{formatPercent(league.home_win_pct / 100)}</Table.Td>
                    <Table.Td>{formatPercent(league.draw_pct / 100)}</Table.Td>
                    <Table.Td>{formatPercent(league.away_win_pct / 100)}</Table.Td>
                    <Table.Td>{formatPercent(league.over_2_5_pct / 100)}</Table.Td>
                    <Table.Td>{formatPercent(league.btts_pct / 100)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>
        </Stack>
      </Paper>

      <Paper shadow="sm" p="md" withBorder>
        <Stack gap="sm">
          <Title order={4}>Mejores equipos por Elo</Title>
          <ScrollArea>
            <Table striped highlightOnHover miw={720}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Equipo</Table.Th>
                  <Table.Th>Liga</Table.Th>
                  <Table.Th>Elo</Table.Th>
                  <Table.Th>Partidos</Table.Th>
                  <Table.Th>Ataque</Table.Th>
                  <Table.Th>Defensa</Table.Th>
                  <Table.Th>GF/partido</Table.Th>
                  <Table.Th>GC/partido</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {stats.top_teams.map((team) => (
                  <Table.Tr key={team.team}>
                    <Table.Td>
                      <Text size="sm" fw={600}>
                        {team.team}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" c="dimmed">
                        {team.league_name}
                      </Text>
                    </Table.Td>
                    <Table.Td>{team.elo.toFixed(0)}</Table.Td>
                    <Table.Td>{team.matches}</Table.Td>
                    <Table.Td>{team.attack.toFixed(3)}</Table.Td>
                    <Table.Td>{team.defense.toFixed(3)}</Table.Td>
                    <Table.Td>{team.goals_for.toFixed(2)}</Table.Td>
                    <Table.Td>{team.goals_against.toFixed(2)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>
        </Stack>
      </Paper>

      <Alert icon={<IconInfoCircle size={16} />} color="gray" variant="light">
        <Text size="sm">{stats.model.explanation}</Text>
      </Alert>
    </Stack>
  )
}
