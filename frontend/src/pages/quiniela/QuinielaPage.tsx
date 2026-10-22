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
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import {
  IconAlertTriangle,
  IconCheck,
  IconCopy,
  IconInfoCircle,
  IconSparkles,
} from '@tabler/icons-react'
import {
  quinielaApi,
  type QuinielaGenerateParams,
  type QuinielaGenerateResponse,
  type QuinielaJornada,
  type QuinielaMetaResponse,
  type QuinielaMode,
  type QuinielaStrategy,
} from '../../services/quiniela'
import { PortfolioOverview } from '../../components/quiniela/PortfolioOverview'
import { TicketCard } from '../../components/quiniela/TicketCard'
import { PrizePanel } from '../../components/quiniela/PrizePanel'
import { AnalysisPanel } from '../../components/quiniela/AnalysisPanel'
import { HowItWorks } from '../../components/quiniela/HowItWorks'

const randomSeed = () => Math.floor(Math.random() * 2_000_000_000)

const strategyFallback = [
  { value: 'balanced', label: 'Equilibrada' },
  { value: 'coverage', label: 'Máxima cobertura' },
  { value: 'max_probability', label: 'Máxima probabilidad' },
  { value: 'jackpot', label: 'Caza del pleno' },
]

export default function QuinielaPage() {
  const [meta, setMeta] = useState<QuinielaMetaResponse | null>(null)
  const [jornadas, setJornadas] = useState<QuinielaJornada[]>([])
  const [data, setData] = useState<QuinielaGenerateResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const [mode, setMode] = useState<QuinielaMode>('multiple')
  const [strategy, setStrategy] = useState<QuinielaStrategy>('balanced')
  const [jornada, setJornada] = useState<string | null>(null)
  const [budget, setBudget] = useState(20)
  const [maxDoubles, setMaxDoubles] = useState(4)
  const [maxTriples, setMaxTriples] = useState(2)
  const [count, setCount] = useState(5)

  const generate = async (overrides?: Partial<QuinielaGenerateParams>) => {
    setLoading(true)
    setError(null)
    setCopied(false)
    const requestedMode = overrides?.mode ?? mode
    const params: QuinielaGenerateParams = {
      jornada: overrides?.jornada ?? (jornada ? Number(jornada) : undefined),
      mode: requestedMode,
      budget: overrides?.budget ?? budget,
      max_doubles: overrides?.max_doubles ?? maxDoubles,
      max_triples: overrides?.max_triples ?? maxTriples,
      count: overrides?.count ?? count,
      // En modo múltiple el óptimo es cubrir los partidos más inciertos: todas
      // las estrategias convergen al mismo boleto, así que se usa la equilibrada.
      strategy:
        requestedMode === 'multiple'
          ? 'balanced'
          : overrides?.strategy ?? strategy,
      seed: overrides?.seed,
    }
    try {
      const result = await quinielaApi.generate(params)
      setData(result)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'No se ha podido generar el boleto')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([quinielaApi.meta(), quinielaApi.jornadas()])
      .then(([metaPayload, jornadasPayload]) => {
        if (!active) return
        setMeta(metaPayload)
        setJornadas(jornadasPayload)
        const next = metaPayload.next_jornada?.jornada ?? jornadasPayload[0]?.jornada
        if (next != null) {
          const value = String(next)
          setJornada(value)
          void generate({ jornada: next })
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

  const strategyOptions = useMemo(() => {
    const strategies = meta?.strategies ?? {}
    const entries = Object.entries(strategies).map(([value, info]) => ({
      value,
      label: info.label,
    }))
    return entries.length ? entries : strategyFallback
  }, [meta])

  const jornadaOptions = useMemo(
    () =>
      jornadas.map((item) => ({
        value: String(item.jornada),
        label: `${item.label} · ${item.competition}`,
      })),
    [jornadas],
  )

  const copyAll = async () => {
    if (!data) return
    const lines = data.tickets.map((ticket) => {
      const signs = ticket.signs
        .map((sign) => (sign.signs.length > 1 ? sign.signs.join('/') : sign.signs[0]))
        .join('  ')
      return `${ticket.index}. ${signs}  | Pleno: ${ticket.pleno.score}`
    })
    const text = [
      `La Quiniela · ${data.jornada.label} · ${data.jornada.start_date}`,
      `Modo: ${data.mode === 'multiple' ? 'múltiple' : 'columnas simples'} · ${data.strategy_label}`,
      `Coste: ${data.portfolio.cost.toFixed(2)} € · Columnas: ${data.portfolio.columns}`,
      '',
      ...lines,
      '',
      'Generado con LoTor. Juega de forma responsable.',
    ].join('\n')
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch {
      setCopied(false)
    }
  }

  const signMatches = data?.matches.filter((match) => !match.is_pleno) ?? []
  const plenoMatch = data?.matches.find((match) => match.is_pleno) ?? data?.matches[data.matches.length - 1]

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <Stack gap={2}>
          <Group gap="xs">
            <Title order={1}>⚽ La Quiniela</Title>
            <Badge color="teal" variant="light">
              Modelo estadístico
            </Badge>
          </Group>
          <Text c="dimmed" maw={820}>
            Predicciones 1-X-2 a partir del histórico de partidos, con Poisson Dixon-Coles,
            Elo y priors de competición. Optimiza un múltiple con dobles y triples o una
            cartera de columnas simples dentro de tu presupuesto.
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
            leftSection={<IconSparkles size={16} />}
            onClick={() => generate({ seed: randomSeed() })}
            loading={loading}
            disabled={loading}
          >
            Generar boleto
          </Button>
        </Group>
      </Group>

      <Paper shadow="sm" p="md" withBorder>
        <Stack gap="md">
          <Group align="flex-end" wrap="wrap">
            <Stack gap={4}>
              <Text size="xs" c="dimmed" fw={600}>
                Modo
              </Text>
              <SegmentedControl
                value={mode}
                onChange={(value) => setMode(value as QuinielaMode)}
                data={[
                  { value: 'multiple', label: 'Múltiple' },
                  { value: 'simple', label: 'Columnas simples' },
                ]}
              />
            </Stack>
            {mode === 'simple' ? (
              <Select
                label="Estrategia"
                value={strategy}
                onChange={(value) => setStrategy((value as QuinielaStrategy) || 'balanced')}
                data={strategyOptions}
                style={{ width: 220 }}
                allowDeselect={false}
              />
            ) : null}
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
            {mode === 'multiple' ? (
              <>
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
              </>
            ) : (
              <NumberInput
                label="Columnas"
                value={count}
                onChange={(value) =>
                  setCount(typeof value === 'number' ? Math.min(10, Math.max(1, value)) : 5)
                }
                min={1}
                max={10}
                style={{ width: 120 }}
              />
            )}
          </Group>
          {mode === 'multiple' ? (
            <Text size="xs" c="dimmed">
              El múltiple se optimiza automáticamente: cubre los partidos más inciertos
              hasta agotar el presupuesto y los límites de dobles/triples. Las estrategias
              de riesgo se aplican a las carteras de columnas simples.
            </Text>
          ) : (
            <Text size="xs" c="dimmed">
              La estrategia cambia cómo se reparte el riesgo entre las columnas simples:
              desde máxima cobertura hasta caza del pleno.
            </Text>
          )}
          {meta && (
            <Text size="xs" c="dimmed">
              {meta.dataset.total_matches.toLocaleString('es-ES')} partidos ·{' '}
              {meta.dataset.total_teams} equipos ·{' '}
              {meta.dataset.total_jornadas} jornadas cargadas. Precio por columna:{' '}
              {meta.game.ticket_price_eur.toFixed(2)} €.
            </Text>
          )}
        </Stack>
      </Paper>

      <Alert icon={<IconAlertTriangle size={16} />} color="red" variant="light">
        <Text size="sm">
          <strong>Aviso:</strong> La Quiniela es un juego de azar. El modelo estima
          probabilidades, no adivina resultados. Los premios son de reparto y ningún boleto
          garantiza ganancias. Juega de forma responsable.
        </Text>
      </Alert>

      {error && (
        <Alert icon={<IconInfoCircle size={16} />} color="red" title="Error">
          {error}
        </Alert>
      )}

      {loading && (
        <Group justify="center" py="xl">
          <Stack align="center">
            <Loader size="lg" />
            <Text size="sm" c="dimmed">
              Calculando probabilidades y optimizando el boleto...
            </Text>
          </Stack>
        </Group>
      )}

      {data && !loading && (
        <>
          <PortfolioOverview data={data} />

          <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
            <PrizePanel prize={data.portfolio.prize_estimate} />
            <AnalysisPanel analysis={data.analysis} />
          </SimpleGrid>

          <Group justify="space-between" align="center">
            <Stack gap={0}>
              <Title order={3}>
                {data.mode === 'multiple' ? 'Boleto generado' : 'Columnas generadas'}
              </Title>
              <Text size="sm" c="dimmed">
                {data.strategy_description}
              </Text>
            </Stack>
            <Button
              variant="light"
              leftSection={copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
              onClick={copyAll}
            >
              {copied ? 'Copiado' : 'Copiar'}
            </Button>
          </Group>

          <Stack gap="md">
            {plenoMatch &&
              data.tickets.map((ticket) => (
                <TicketCard
                  key={ticket.index}
                  ticket={ticket}
                  matches={signMatches}
                  pleno={plenoMatch}
                  mode={data.mode}
                />
              ))}
          </Stack>

          {data.recommendations.length > 0 && (
            <Paper shadow="sm" p="md" withBorder>
              <Stack gap="sm">
                <Title order={4}>Recomendaciones</Title>
                <List size="sm" spacing={4}>
                  {data.recommendations.map((recommendation) => (
                    <List.Item key={recommendation}>{recommendation}</List.Item>
                  ))}
                </List>
              </Stack>
            </Paper>
          )}

          <HowItWorks />

          <Text size="xs" c="dimmed" ta="center">
            {data.disclaimer}
          </Text>
        </>
      )}
    </Stack>
  )
}
