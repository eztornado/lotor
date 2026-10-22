import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Group,
  List,
  Loader,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { Link } from 'react-router-dom'
import {
  IconAlertTriangle,
  IconBrain,
  IconRefresh,
  IconSparkles,
} from '@tabler/icons-react'
import {
  quinielaApi,
  type QuinielaJornada,
  type QuinielaPredictionParams,
  type QuinielaPredictionResponse,
} from '../../services/quiniela'
import { PortfolioOverview } from '../../components/quiniela/PortfolioOverview'
import { TicketCard } from '../../components/quiniela/TicketCard'
import { PrizePanel } from '../../components/quiniela/PrizePanel'
import { AnalysisPanel } from '../../components/quiniela/AnalysisPanel'
import { formatCurrency, formatPercent, formatShortDate } from '../../components/quiniela/format'

const randomSeed = () => Math.floor(Math.random() * 2_000_000_000)

const oneIn = (probability: number): string =>
  probability > 0
    ? `1 entre ${Math.round(1 / probability).toLocaleString('es-ES')}`
    : '—'

function TargetStat({
  label,
  value,
  hint,
  color,
}: {
  label: string
  value: string
  hint?: string
  color?: string
}) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
        {label}
      </Text>
      <Text fw={700} size="xl" c={color}>
        {value}
      </Text>
      {hint && (
        <Text size="xs" c="dimmed">
          {hint}
        </Text>
      )}
    </Stack>
  )
}

export default function QuinielaPredictionPage() {
  const [jornadas, setJornadas] = useState<QuinielaJornada[]>([])
  const [data, setData] = useState<QuinielaPredictionResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [jornada, setJornada] = useState<string | null>(null)
  const [budget, setBudget] = useState(20)
  const [maxDoubles, setMaxDoubles] = useState(4)
  const [maxTriples, setMaxTriples] = useState(2)

  const predict = async (overrides?: Partial<QuinielaPredictionParams>) => {
    setLoading(true)
    setError(null)
    const params: QuinielaPredictionParams = {
      jornada: overrides?.jornada ?? (jornada ? Number(jornada) : undefined),
      budget: overrides?.budget ?? budget,
      max_doubles: overrides?.max_doubles ?? maxDoubles,
      max_triples: overrides?.max_triples ?? maxTriples,
      seed: overrides?.seed,
    }
    try {
      setData(await quinielaApi.prediction(params))
    } catch (err: any) {
      setError(err.response?.data?.detail || 'No se ha podido calcular la predicción')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([quinielaApi.meta(), quinielaApi.jornadas()])
      .then(([meta, items]) => {
        if (!active) return
        setJornadas(items)
        const next = meta.next_jornada?.jornada ?? items[0]?.jornada
        if (next != null) {
          const value = String(next)
          setJornada(value)
          void predict({ jornada: next })
        }
      })
      .catch((err: any) => {
        if (active) setError(err.response?.data?.detail || 'Error cargando La Quiniela')
      })
    return () => {
      active = false
    }
    // La carga inicial solo debe ejecutarse una vez.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const jornadaOptions = useMemo(
    () =>
      jornadas.map((item) => ({
        value: String(item.jornada),
        label: `${item.label} · ${item.competition}`,
      })),
    [jornadas],
  )

  const ticket = data?.tickets[0]
  const plenoMatch =
    data?.matches.find((match) => match.is_pleno) ??
    data?.matches[data.matches.length - 1]
  const backtest = data?.model.backtest

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <Stack gap={2}>
          <Group gap="xs">
            <Title order={1}>🧠 Predicción IA · La Quiniela</Title>
            <Badge color="teal" variant="light">
              Máxima probabilidad de pleno
            </Badge>
          </Group>
          <Text c="dimmed" maw={860}>
            El sistema usa el histórico de partidos, el ensemble Poisson Dixon-Coles + Elo
            y una optimización exacta para elegir la combinación con mayor probabilidad de
            premio alto. No es la opción más conservadora: prioriza el pleno al 15.
          </Text>
        </Stack>
        <Group align="flex-end" wrap="wrap">
          <Select
            label="Jornada"
            value={jornada}
            onChange={setJornada}
            data={jornadaOptions}
            style={{ width: 250 }}
            allowDeselect={false}
          />
          <Button
            leftSection={<IconRefresh size={16} />}
            onClick={() => predict({ seed: randomSeed() })}
            loading={loading}
            disabled={loading}
          >
            Calcular predicción
          </Button>
        </Group>
      </Group>

      <Paper shadow="sm" p="md" withBorder>
        <Group align="flex-end" wrap="wrap">
          <NumberInput
            label="Presupuesto (€)"
            value={budget}
            onChange={(value) =>
              setBudget(typeof value === 'number' ? Math.max(0.75, value) : 20)
            }
            min={0.75}
            max={1000}
            step={0.75}
            decimalScale={2}
            style={{ width: 150 }}
          />
          <NumberInput
            label="Máx. dobles"
            value={maxDoubles}
            onChange={(value) =>
              setMaxDoubles(typeof value === 'number' ? Math.min(7, Math.max(0, value)) : 4)
            }
            min={0}
            max={7}
            style={{ width: 120 }}
          />
          <NumberInput
            label="Máx. triples"
            value={maxTriples}
            onChange={(value) =>
              setMaxTriples(typeof value === 'number' ? Math.min(4, Math.max(0, value)) : 2)
            }
            min={0}
            max={4}
            style={{ width: 120 }}
          />
          <Text size="xs" c="dimmed" maw={420}>
            P(15) = P(acertar los 14 partidos) × P(pleno). El optimizador reparte la
            cobertura donde más sube esa probabilidad.
          </Text>
        </Group>
      </Paper>

      <Alert icon={<IconSparkles size={16} />} color="teal" variant="light">
        <Group justify="space-between" wrap="wrap">
          <Text size="sm">
            ¿Buscas maximizar la probabilidad de premios menores o ajustar el riesgo?
            Usa el generador de múltiples y columnas simples.
          </Text>
          <Button component={Link} to="/quiniela" size="xs" variant="light">
            Ir al Generador
          </Button>
        </Group>
      </Alert>

      <Alert icon={<IconAlertTriangle size={16} />} color="red" variant="light">
        <Text size="sm">
          <strong>Aviso:</strong> el premio del pleno es de reparto y la probabilidad de
          acertar es muy baja. Ningún modelo garantiza premios. Juega solo lo que puedas
          permitirte.
        </Text>
      </Alert>

      {error && (
        <Alert icon={<IconAlertTriangle size={16} />} color="red" title="Error">
          {error}
        </Alert>
      )}

      {loading && (
        <Group justify="center" py="xl">
          <Stack align="center">
            <Loader size="lg" />
            <Text size="sm" c="dimmed">
              Ajustando el modelo y optimizando la probabilidad del pleno...
            </Text>
          </Stack>
        </Group>
      )}

      {data && ticket && plenoMatch && !loading && (
        <>
          <PortfolioOverview data={data} />

          <Paper shadow="sm" p="lg" withBorder>
            <Stack gap="lg">
              <Group justify="space-between" align="flex-start" wrap="wrap">
                <Stack gap={2}>
                  <Group gap="xs">
                    <IconBrain size={20} />
                    <Title order={3}>Objetivo: premio máximo</Title>
                  </Group>
                  <Text size="sm" c="dimmed">
                    {data.jornada.label} · {formatShortDate(data.jornada.start_date)} ·{' '}
                    {data.tickets[0].variant ?? data.strategy_label}
                  </Text>
                </Stack>
                <Badge color="yellow" variant="light">
                  {data.tickets[0].columns} columnas ·{' '}
                  {formatCurrency(data.tickets[0].cost)}
                </Badge>
              </Group>

              <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
                <TargetStat
                  label="Pleno al 15"
                  value={formatPercent(data.target.top_prize_probability, 4)}
                  hint={oneIn(data.target.top_prize_probability)}
                  color="yellow"
                />
                <TargetStat
                  label="14 aciertos"
                  value={formatPercent(data.target.second_prize_probability, 3)}
                  hint={oneIn(data.target.second_prize_probability)}
                />
                <TargetStat
                  label="Al menos 13"
                  value={formatPercent(data.target.at_least_13_probability, 3)}
                  hint="Acumulado 13-15"
                />
                <TargetStat
                  label="Retorno medio"
                  value={formatCurrency(data.target.expected_return.average)}
                  hint={`Coste ${formatCurrency(data.tickets[0].cost)} · rango ${formatCurrency(
                    data.target.expected_return.low,
                  )} - ${formatCurrency(data.target.expected_return.high)}`}
                />
              </SimpleGrid>

              <Text size="xs" c="dimmed">
                Las probabilidades son exactas bajo el modelo (Poisson-binomial) y no
                incluyen correlaciones entre partidos. El retorno usa premios medios
                orientativos y es pari-mutuel.
              </Text>
            </Stack>
          </Paper>

          <Group justify="space-between" align="center">
            <Title order={3}>Combinación principal</Title>
            <Badge variant="light" color="teal">
              {data.tickets[0].doubles} dobles · {data.tickets[0].triples} triples
            </Badge>
          </Group>

          <TicketCard
            ticket={data.tickets[0]}
            matches={data.matches}
            pleno={plenoMatch}
            mode="multiple"
          />

          <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
            <Paper shadow="sm" p="md" withBorder h="100%">
              <Stack gap="md">
                <Stack gap={2}>
                  <Title order={4}>Por qué esta combinación</Title>
                  <Text size="xs" c="dimmed">
                    Razonamiento generado a partir del modelo y del histórico.
                  </Text>
                </Stack>
                <List size="sm" spacing="xs">
                  {data.reasoning.map((line) => (
                    <List.Item key={line}>{line}</List.Item>
                  ))}
                </List>
              </Stack>
            </Paper>
            <AnalysisPanel analysis={data.analysis} />
          </SimpleGrid>

          <PrizePanel prize={data.portfolio.prize_estimate} />

          <Paper shadow="sm" p="md" withBorder>
            <Stack gap="sm">
              <Group justify="space-between" wrap="wrap">
                <Stack gap={2}>
                  <Title order={4}>Modelo y validación</Title>
                  <Text size="xs" c="dimmed">
                    {data.model.type} · {data.model.version}
                  </Text>
                </Stack>
                <Group gap="xs">
                  {backtest?.accuracy != null && (
                    <Badge color="teal" variant="light">
                      Acierto {formatPercent(backtest.accuracy)}
                    </Badge>
                  )}
                  {backtest?.baseline_accuracy != null && (
                    <Badge color="gray" variant="light">
                      Base {formatPercent(backtest.baseline_accuracy)}
                    </Badge>
                  )}
                  {backtest?.log_loss != null && (
                    <Badge color="blue" variant="light">
                      Log-loss {backtest.log_loss.toFixed(3)}
                    </Badge>
                  )}
                  <Badge color="grape" variant="light">
                    {data.model.dataset.total_matches.toLocaleString('es-ES')} partidos
                  </Badge>
                </Group>
              </Group>
              <Text size="sm">{data.model.explanation}</Text>
              <Text size="xs" c="dimmed">
                La "IA" es un ensemble estadístico calibrado con backtest; no se usa un
                LLM generativo para decidir los signos. El razonamiento se deriva de las
                probabilidades y del histórico.
              </Text>
              <Text size="xs" c="dimmed">
                Backtest fuera de muestra sobre {backtest?.matches ?? 0} partidos. La
                ventaja frente a la base mide si las probabilidades ordenan mejor que
                elegir siempre el resultado más frecuente.
              </Text>
            </Stack>
          </Paper>

          {data.alternatives.length > 0 && (
            <Stack gap="md">
              <Stack gap={2}>
                <Title order={3}>Alternativas con alta probabilidad</Title>
                <Text size="sm" c="dimmed">
                  Variantes forzando el segundo signo en los partidos más abiertos. Sirven
                  para comparar escenarios, no para duplicar el mismo boleto.
                </Text>
              </Stack>
              {data.alternatives.map((alternative) => (
                <Stack key={alternative.index} gap="xs">
                  <Group gap="xs">
                    <Badge color="teal" variant="light">
                      Alternativa {alternative.index - 1}
                    </Badge>
                    <Text size="sm" c="dimmed">
                      {alternative.variant}
                    </Text>
                  </Group>
                  <TicketCard
                    ticket={alternative}
                    matches={data.matches}
                    pleno={plenoMatch}
                    mode="multiple"
                  />
                </Stack>
              ))}
            </Stack>
          )}
        </>
      )}
    </Stack>
  )
}
