import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { IconAlertTriangle, IconCheck, IconCopy, IconInfoCircle, IconSparkles } from '@tabler/icons-react'
import {
  bonolotoApi,
  type BonolotoGenerateResponse,
  type BonolotoMetaResponse,
  type BonolotoStrategy,
} from '../../services/bonoloto'
import { AnalysisPanel } from '../../components/bonoloto/AnalysisPanel'
import { CombinationCard } from '../../components/bonoloto/CombinationCard'
import { HowItWorks } from '../../components/bonoloto/HowItWorks'
import { PortfolioOverview } from '../../components/bonoloto/PortfolioOverview'
import { ProbabilityPanel } from '../../components/bonoloto/ProbabilityPanel'
import { RecommendationsPanel } from '../../components/bonoloto/RecommendationsPanel'
import { SharingRiskPanel } from '../../components/bonoloto/SharingRiskPanel'
import { formatNumber } from '../../components/bonoloto/format'

const randomSeed = () => Math.floor(Math.random() * 2_000_000_000)

export default function BonolotoPage() {
  const [meta, setMeta] = useState<BonolotoMetaResponse | null>(null)
  const [data, setData] = useState<BonolotoGenerateResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [count, setCount] = useState(10)
  const [strategy, setStrategy] = useState<BonolotoStrategy>('big_prize')

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
        <Group align="flex-end">
          <NumberInput
            label="Apuestas"
            value={count}
            onChange={(value) =>
              setCount(typeof value === 'number' ? Math.min(10, Math.max(1, value)) : 1)
            }
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
          <PortfolioOverview data={data} />

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
            <ProbabilityPanel portfolio={portfolio} />
            <SharingRiskPanel data={data} />
          </SimpleGrid>

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

          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            {data.combinations.map((combination) => (
              <CombinationCard
                key={combination.index}
                combination={combination}
                drawDate={data.dataset.next_draw}
              />
            ))}
          </SimpleGrid>

          {data.analysis && <AnalysisPanel analysis={data.analysis} />}

          {data.recommendations.length > 0 && (
            <RecommendationsPanel recommendations={data.recommendations} />
          )}

          <HowItWorks data={data} />
        </>
      )}
    </Stack>
  )
}
