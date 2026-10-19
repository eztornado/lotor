import { useEffect, useMemo, useState } from 'react'
import {
  Accordion,
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Divider,
  Grid,
  Group,
  List,
  Loader,
  NumberInput,
  Paper,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
  Tooltip,
} from '@mantine/core'
import {
  IconAlertTriangle,
  IconChartBar,
  IconCheck,
  IconClock,
  IconCopy,
  IconFlame,
  IconInfoCircle,
  IconShield,
  IconSnowflake,
  IconSparkles,
  IconTarget,
  IconTicket,
  IconTrophy,
} from '@tabler/icons-react'
import {
  bonolotoApi,
  type BonolotoCombination,
  type BonolotoGenerateResponse,
  type BonolotoMetaResponse,
  type BonolotoStrategy,
} from '../services/api'

const formatNumber = (value: number) => value.toString().padStart(2, '0')

const formatOneIn = (probability: number) => {
  if (!probability || probability <= 0) return '—'
  const value = 1 / probability
  if (value >= 1_000_000) {
    return `1 entre ${(value / 1_000_000).toFixed(2).replace('.', ',')} M`
  }
  if (value >= 1_000) {
    return `1 entre ${Math.round(value).toLocaleString('es-ES')}`
  }
  return `1 entre ${value.toFixed(2).replace('.', ',')}`
}

const formatPercent = (probability: number, decimals = 2) =>
  `${(probability * 100).toFixed(decimals).replace('.', ',')} %`

const qualityColor = (grade: string) => {
  if (grade === 'alta') return 'teal'
  if (grade === 'media') return 'yellow'
  return 'orange'
}

const popularityLabel = (value: number) => {
  if (value <= 0.12) return { label: 'Baja', color: 'teal' }
  if (value <= 0.35) return { label: 'Media', color: 'yellow' }
  return { label: 'Alta', color: 'red' }
}

function Ball({ number, variant = 'number' }: { number: number; variant?: 'number' | 'reintegro' }) {
  const background =
    variant === 'reintegro'
      ? 'linear-gradient(135deg, #f06a9d 0%, #c026d3 100%)'
      : 'linear-gradient(135deg, #4c6ef5 0%, #7048e8 100%)'
  return (
    <Box
      style={{
        background,
        color: 'white',
        minWidth: 42,
        height: 42,
        padding: '0 8px',
        borderRadius: 10,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontSize: '1rem',
        boxShadow: '0 2px 6px rgba(0,0,0,0.25)',
      }}
    >
      {formatNumber(number)}
    </Box>
  )
}

function CombinationCard({
  combination,
  drawDate,
  onCopied,
}: {
  combination: BonolotoCombination
  drawDate: string
  onCopied: () => void
}) {
  const popularity = popularityLabel(combination.popularity)
  const copyTicket = async () => {
    const text = `Bonoloto ${drawDate} · Apuesta ${combination.index}: ${combination.numbers
      .map(formatNumber)
      .join(' - ')}  (Reintegro: ${combination.reintegro})`
    try {
      await navigator.clipboard.writeText(text)
      onCopied()
    } catch {
      // Sin permisos de portapapeles: ignoramos silenciosamente.
    }
  }

  return (
    <Card shadow="sm" padding="md" withBorder h="100%">
      <Stack gap="sm">
        <Group justify="space-between">
          <Badge variant="light">Apuesta {combination.index}</Badge>
          <Group gap={6}>
            <Badge color={qualityColor(combination.quality_grade)} variant="light">
              Calidad {combination.quality_grade}
            </Badge>
            <Badge color={popularity.color} variant="light">
              Popularidad {popularity.label}
            </Badge>
          </Group>
        </Group>

        <Group gap={6} wrap="nowrap">
          {combination.numbers.map((number) => (
            <Ball key={number} number={number} />
          ))}
          <Tooltip label="Reintegro">
            <Box>
              <Ball number={combination.reintegro} variant="reintegro" />
            </Box>
          </Tooltip>
        </Group>

        <Group gap={6}>
          {combination.tags.map((tag) => (
            <Badge key={tag} size="sm" variant="outline" color="gray">
              {tag}
            </Badge>
          ))}
        </Group>

        <Text size="xs" c="dimmed">
          Suma {combination.sum} · {combination.odd} impares / {combination.even} pares ·{' '}
          {combination.low} bajos / {combination.high} altos · {combination.consecutive_pairs}{' '}
          consecutivos
        </Text>

        <Group justify="space-between">
          <Text size="xs" c="dimmed">
            Índice del modelo: {(combination.quality * 100).toFixed(1).replace('.', ',')}
          </Text>
          <Button
            size="compact-xs"
            variant="subtle"
            leftSection={<IconCopy size={14} />}
            onClick={copyTicket}
          >
            Copiar
          </Button>
        </Group>
      </Stack>
    </Card>
  )
}

export default function BonolotoPage() {
  const [meta, setMeta] = useState<BonolotoMetaResponse | null>(null)
  const [data, setData] = useState<BonolotoGenerateResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [count, setCount] = useState(10)
  const [strategy, setStrategy] = useState<BonolotoStrategy>('big_prize')

  const randomSeed = () => Math.floor(Math.random() * 2_000_000_000)

  const generate = async (seed?: number) => {
    setLoading(true)
    setError(null)
    try {
      const result = await bonolotoApi.generate(count, strategy, seed)
      setData(result)
      setCopied(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'No se han podido generar las combinaciones')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    bonolotoApi
      .meta()
      .then((payload) => {
        if (active) setMeta(payload)
      })
      .catch(() => undefined)
    bonolotoApi
      .generate(10, 'big_prize')
      .then((payload) => {
        if (active) setData(payload)
      })
      .catch((err: any) => {
        if (active) setError(err.response?.data?.detail || 'Error cargando Bonoloto')
      })
    return () => {
      active = false
    }
  }, [])

  const strategyOptions = useMemo(() => {
    const strategies = meta?.strategies ?? data?.model?.strategies ?? {}
    return Object.entries(strategies).map(([value, info]: [string, any]) => ({
      value,
      label: info.label,
    }))
  }, [meta, data])

  const copyAll = async () => {
    if (!data) return
    const lines = data.combinations.map(
      (combination) =>
        `${combination.index}. ${combination.numbers.map(formatNumber).join(' - ')}  (R: ${
          combination.reintegro
        })`,
    )
    const text = [
      `Bonoloto · Próximo sorteo ${data.dataset.next_draw}`,
      `Estrategia: ${data.strategy_label}`,
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

  const portfolio = data?.portfolio
  const analysis = data?.analysis

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <Stack gap={2}>
          <Group gap="xs">
            <Title order={1}>🍀 Bonoloto</Title>
            <Badge color="grape" variant="light">
              Generador inteligente
            </Badge>
          </Group>
          <Text c="dimmed" maw={760}>
            Cartera optimizada de hasta 10 apuestas. Combina el histórico completo desde 1988,
            filtros estructurales, detección de combinaciones populares y optimización de cobertura
            de números, pares y tríos.
          </Text>
        </Stack>
        <Group>
          <NumberInput
            label="Apuestas"
            value={count}
            onChange={(value) => setCount(typeof value === 'number' ? Math.min(10, Math.max(1, value)) : 1)}
            min={1}
            max={10}
            style={{ width: 110 }}
          />
          <Select
            label="Estrategia"
            value={strategy}
            onChange={(value) => setStrategy((value as BonolotoStrategy) || 'big_prize')}
            data={
              strategyOptions.length
                ? strategyOptions
                : [
                    { value: 'big_prize', label: 'Máximo premio' },
                    { value: 'balanced', label: 'Equilibrada' },
                    { value: 'coverage', label: 'Máxima cobertura' },
                    { value: 'statistical', label: 'Estadística pura' },
                  ]
            }
            style={{ width: 210 }}
          />
          <Button
            leftSection={<IconSparkles size={16} />}
            onClick={() => generate(randomSeed())}
            loading={loading}
            disabled={loading}
            mt={24}
          >
            Generar cartera
          </Button>
        </Group>
      </Group>

      <Alert icon={<IconAlertTriangle size={16} />} color="red" variant="light">
        <Text size="sm">
          <strong>Aviso:</strong> la lotería es un juego de azar. Ninguna estrategia puede predecir el
          resultado ni garantizar premios. La ventaja real de esta herramienta es la cobertura y
          evitar combinaciones muy jugadas (menos reparto del premio). Juega de forma responsable.
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
              Analizando {meta?.dataset?.total_draws ?? 'los'} sorteos y optimizando la cartera...
            </Text>
          </Stack>
        </Group>
      )}

      {data && portfolio && !loading && (
        <>
          <Paper shadow="sm" p="md" withBorder>
            <Grid>
              <Grid.Col span={{ base: 12, md: 4 }}>
                <Stack gap={4}>
                  <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                    Próximo sorteo
                  </Text>
                  <Text size="xl" fw={700}>
                    {new Date(`${data.dataset.next_draw}T12:00:00`).toLocaleDateString('es-ES', {
                      weekday: 'long',
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    })}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {data.game.draw_days} · 6 números del 1 al 49 + reintegro
                  </Text>
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 4 }}>
                <Stack gap={4}>
                  <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                    Cartera
                  </Text>
                  <Group gap="lg">
                    <Stack gap={0}>
                      <Text size="xl" fw={700}>
                        {portfolio.tickets}
                      </Text>
                      <Text size="xs" c="dimmed">
                        apuestas
                      </Text>
                    </Stack>
                    <Stack gap={0}>
                      <Text size="xl" fw={700}>
                        {portfolio.cost_eur.toFixed(2).replace('.', ',')} €
                      </Text>
                      <Text size="xs" c="dimmed">
                        coste total
                      </Text>
                    </Stack>
                    <Stack gap={0}>
                      <Text size="xl" fw={700}>
                        {portfolio.reintegros.distinct}/10
                      </Text>
                      <Text size="xs" c="dimmed">
                        reintegros
                      </Text>
                    </Stack>
                  </Group>
                  {portfolio.reintegros.guaranteed_match && (
                    <Badge color="teal" variant="light" w="fit-content">
                      Reintegro garantizado en una apuesta
                    </Badge>
                  )}
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 4 }}>
                <Stack gap={6}>
                  <Group justify="space-between">
                    <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                      Cobertura de números
                    </Text>
                    <Text size="sm" fw={700}>
                      {portfolio.coverage.numbers_pct.toFixed(1).replace('.', ',')} %
                    </Text>
                  </Group>
                  <Progress value={portfolio.coverage.numbers_pct} color="teal" size="lg" />
                  <Text size="xs" c="dimmed">
                    {portfolio.coverage.unique_numbers}/{portfolio.coverage.total_numbers} números ·{' '}
                    {portfolio.coverage.pairs_pct.toFixed(1).replace('.', ',')} % pares ·{' '}
                    {portfolio.coverage.triples_pct.toFixed(1).replace('.', ',')} % tríos
                  </Text>
                  <Text size="xs" c="dimmed">
                    Solapamiento medio {portfolio.overlap.average.toFixed(2).replace('.', ',')} ·
                    máximo {portfolio.overlap.max}
                  </Text>
                </Stack>
              </Grid.Col>
            </Grid>
          </Paper>

          <Grid>
            <Grid.Col span={{ base: 12, md: 7 }}>
              <Paper shadow="sm" p="md" withBorder h="100%">
                <Stack gap="sm">
                  <Group gap="xs">
                    <ThemeIcon color="grape" variant="light" size="lg">
                      <IconTrophy size={18} />
                    </ThemeIcon>
                    <Title order={4}>Probabilidad de premio con esta cartera</Title>
                  </Group>
                  <Text size="xs" c="dimmed">
                    El jackpot por apuesta es siempre 1 entre 13.983.816. Con {portfolio.tickets}{' '}
                    apuestas distintas la probabilidad se multiplica, pero sigue siendo pequeña.
                  </Text>

                  <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="xs">
                    <Stack gap={0}>
                      <Text size="xs" c="dimmed">
                        6 aciertos
                      </Text>
                      <Text fw={700}>{formatOneIn(portfolio.theoretical.prob_6)}</Text>
                    </Stack>
                    <Stack gap={0}>
                      <Text size="xs" c="dimmed">
                        5 + complementario
                      </Text>
                      <Text fw={700}>
                        {formatOneIn(portfolio.theoretical.prob_5_plus_complementario)}
                      </Text>
                    </Stack>
                    <Stack gap={0}>
                      <Text size="xs" c="dimmed">
                        5 aciertos
                      </Text>
                      <Text fw={700}>{formatOneIn(portfolio.theoretical.prob_5)}</Text>
                    </Stack>
                    <Stack gap={0}>
                      <Text size="xs" c="dimmed">
                        5+ (con o sin comp.)
                      </Text>
                      <Text fw={700}>{formatOneIn(portfolio.theoretical.prob_5_plus)}</Text>
                    </Stack>
                  </SimpleGrid>

                  <Divider />

                  <Stack gap={6}>
                    <Group justify="space-between">
                      <Text size="sm">Algún premio de 4 o más aciertos</Text>
                      <Badge color="grape" variant="light">
                        {formatPercent(portfolio.theoretical.prob_4_plus)}
                      </Badge>
                    </Group>
                    <Progress value={portfolio.theoretical.prob_4_plus * 100} color="grape" />
                    <Group justify="space-between">
                      <Text size="sm">Algún premio de 3 o más aciertos</Text>
                      <Badge color="blue" variant="light">
                        {formatPercent(portfolio.theoretical.prob_3_plus)}
                      </Badge>
                    </Group>
                    <Progress value={portfolio.theoretical.prob_3_plus * 100} color="blue" />
                    <Group justify="space-between">
                      <Text size="sm">Al menos recuperar el reintegro</Text>
                      <Badge color="pink" variant="light">
                        {formatPercent(portfolio.theoretical.prob_reintegro)}
                      </Badge>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm">Aciertos esperados (suma de las 10 apuestas)</Text>
                      <Text fw={700}>{portfolio.theoretical.expected_matches.toFixed(2)}</Text>
                    </Group>
                    <Text size="xs" c="dimmed">
                      Simulación de {portfolio.simulation.simulations.toLocaleString('es-ES')}{' '}
                      sorteos sobre la cartera concreta. Los premios son fijos por categoría.
                    </Text>
                  </Stack>
                </Stack>
              </Paper>
            </Grid.Col>

            <Grid.Col span={{ base: 12, md: 5 }}>
              <Paper shadow="sm" p="md" withBorder h="100%">
                <Stack gap="sm">
                  <Group gap="xs">
                    <ThemeIcon color="teal" variant="light" size="lg">
                      <IconShield size={18} />
                    </ThemeIcon>
                    <Title order={4}>Riesgo de compartir premio</Title>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">Índice de popularidad medio</Text>
                    <Badge
                      color={
                        portfolio.popularity.risk === 'bajo'
                          ? 'teal'
                          : portfolio.popularity.risk === 'medio'
                            ? 'yellow'
                            : 'red'
                      }
                    >
                      {portfolio.popularity.risk}
                    </Badge>
                  </Group>
                  <Text size="sm" c="dimmed">
                    {portfolio.popularity.low_popularity_tickets} de {portfolio.tickets} apuestas son
                    poco populares. Penalizamos fechas de nacimiento, progresiones y patrones obvios:
                    si el premio cae en una combinación muy jugada, se reparte entre más acertantes.
                  </Text>
                  <Divider />
                  <Group gap="xs">
                    <ThemeIcon color="grape" variant="light" size="lg">
                      <IconTarget size={18} />
                    </ThemeIcon>
                    <Text fw={700}>{data.strategy_label}</Text>
                  </Group>
                  <Text size="sm" c="dimmed">
                    {data.strategy_description}
                  </Text>
                  <Text size="xs" c="dimmed">
                    Datos: {data.dataset.total_draws.toLocaleString('es-ES')} sorteos ·{' '}
                    {new Date(`${data.dataset.date_range.from}T12:00:00`).toLocaleDateString('es-ES')}{' '}
                    → {new Date(`${data.dataset.date_range.to}T12:00:00`).toLocaleDateString('es-ES')}
                  </Text>
                </Stack>
              </Paper>
            </Grid.Col>
          </Grid>

          <Group justify="space-between">
            <Title order={3}>Combinaciones generadas</Title>
            <Button
              variant="light"
              leftSection={copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
              onClick={copyAll}
            >
              {copied ? 'Copiado' : 'Copiar todas'}
            </Button>
          </Group>

          <SimpleGrid cols={{ base: 1, sm: 2, lg: 2 }} spacing="md">
            {data.combinations.map((combination) => (
              <CombinationCard
                key={combination.index}
                combination={combination}
                drawDate={data.dataset.next_draw}
                onCopied={() => undefined}
              />
            ))}
          </SimpleGrid>

          {analysis && (
            <Paper shadow="sm" p="md" withBorder>
              <Stack gap="md">
                <Group gap="xs">
                  <ThemeIcon color="orange" variant="light" size="lg">
                    <IconChartBar size={18} />
                  </ThemeIcon>
                  <Title order={4}>Análisis del histórico</Title>
                </Group>
                <Grid>
                  <Grid.Col span={{ base: 12, md: 4 }}>
                    <Stack gap={4}>
                      <Group gap={4}>
                        <IconFlame size={16} color="#f76707" />
                        <Text fw={700} size="sm">
                          Números con mejor tendencia reciente
                        </Text>
                      </Group>
                      <Group gap={4}>
                        {analysis.hot_numbers?.slice(0, 10).map((item: any) => (
                          <Badge key={item.number} color="orange" variant="light">
                            {item.number}
                          </Badge>
                        ))}
                      </Group>
                    </Stack>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, md: 4 }}>
                    <Stack gap={4}>
                      <Group gap={4}>
                        <IconSnowflake size={16} color="#4dabf7" />
                        <Text fw={700} size="sm">
                          Números más retrasados
                        </Text>
                      </Group>
                      <Group gap={4}>
                        {analysis.overdue_numbers?.slice(0, 10).map((item: any) => (
                          <Badge key={item.number} color="blue" variant="light">
                            {item.number}
                          </Badge>
                        ))}
                      </Group>
                    </Stack>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, md: 4 }}>
                    <Stack gap={4}>
                      <Group gap={4}>
                        <IconClock size={16} />
                        <Text fw={700} size="sm">
                          Estructura media
                        </Text>
                      </Group>
                      <Text size="sm" c="dimmed">
                        Suma media {analysis.structure?.average_sum} · desviación{' '}
                        {analysis.structure?.sum_deviation}
                      </Text>
                      <Text size="sm" c="dimmed">
                        Patrón de décadas más habitual:{' '}
                        {analysis.structure?.most_common_decade_pattern?.pattern?.join('-')}
                      </Text>
                    </Stack>
                  </Grid.Col>
                </Grid>
                <Divider />
                <Group gap="lg" wrap="wrap">
                  {analysis.top_pairs?.slice(0, 5).map((pair: any) => (
                    <Badge key={pair.numbers.join('-')} variant="light" color="grape">
                      {pair.numbers.join(' + ')} ({pair.frequency})
                    </Badge>
                  ))}
                </Group>
              </Stack>
            </Paper>
          )}

          <Paper shadow="sm" p="md" withBorder>
            <Stack gap="sm">
              <Group gap="xs">
                <IconTicket size={18} />
                <Title order={4}>Recomendaciones</Title>
              </Group>
              <List spacing="xs" size="sm">
                {data.recommendations.map((recommendation) => (
                  <List.Item key={recommendation}>{recommendation}</List.Item>
                ))}
              </List>
            </Stack>
          </Paper>

          <Accordion variant="separated">
            <Accordion.Item value="como">
              <Accordion.Control>Cómo se genera la cartera</Accordion.Control>
              <Accordion.Panel>
                <Stack gap="sm">
                  <Text size="sm">
                    <strong>1. Modelo de números.</strong> Se combinan frecuencia a largo plazo,
                    frecuencia reciente (vida media de 45 días), retraso y afinidad de pares. El
                    suavizado bayesiano y un peso máximo limitado evitan el sobreajuste: la lotería
                    es uniforme y ningún patrón garantiza nada.
                  </Text>
                  <Text size="sm">
                    <strong>2. Filtro estructural.</strong> Se puntúan suma, paridad, bajos/altos,
                    distribución por décadas, consecutivos y terminaciones con las distribuciones
                    reales del histórico.
                  </Text>
                  <Text size="sm">
                    <strong>3. Anti-popularidad.</strong> Se penalizan las combinaciones que juega
                    mucha gente (números ≤ 31 por fechas de nacimiento, progresiones, patrones). Es
                    la única palanca real para mejorar el importe esperado de un gran premio, porque
                    evita repartirlo.
                  </Text>
                  <Text size="sm">
                    <strong>4. Optimización de cartera.</strong> Para 10 apuestas se cubren los 49
                    números con una única repetición. Para 8 o menos, se buscan apuestas disjuntas,
                    que maximizan la probabilidad de al menos un premio en categorías bajas y
                    mantienen baja la probabilidad de compartir categorías altas.
                  </Text>
                  <Text size="sm">
                    <strong>5. Reintegros.</strong> Con 10 apuestas se usan los 10 dígitos posibles,
                    de modo que una de ellas siempre recupera su importe.
                  </Text>
                  <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light">
                    <Text size="sm">
                      Matemáticamente, cada apuesta sigue teniendo 1 entre 13.983.816 de acertar los
                      6 números. Lo que optimizamos es la cobertura y el reparto del premio, no el
                      azar.
                    </Text>
                  </Alert>
                </Stack>
              </Accordion.Panel>
            </Accordion.Item>
            <Accordion.Item value="datos">
              <Accordion.Control>Datos y actualización</Accordion.Control>
              <Accordion.Panel>
                <Stack gap="sm">
                  <Text size="sm">
                    El histórico se obtiene de las hojas públicas de Lotoideas (resultados oficiales
                    de SELAE) y cubre desde 1988 hasta la fecha. El modelo está cacheado: si se
                    actualiza el dataset, la siguiente generación usa los datos nuevos.
                  </Text>
                  <Group>
                    <Badge variant="light">
                      {data.dataset.total_draws.toLocaleString('es-ES')} sorteos
                    </Badge>
                    <Badge variant="light">Fuente: {data.dataset.source}</Badge>
                    <Badge variant="light">Semilla: {data.seed}</Badge>
                  </Group>
                  <Text size="xs" c="dimmed">
                    {data.disclaimer}
                  </Text>
                </Stack>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        </>
      )}
    </Stack>
  )
}
