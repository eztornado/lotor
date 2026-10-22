import { Badge, Group, Paper, Progress, SimpleGrid, Stack, Text, Title } from '@mantine/core'
import type { QuinielaGenerateResponse } from '../../services/quiniela'
import { formatCurrency, formatPercent, formatShortDate } from './format'

interface StatProps {
  label: string
  value: string
  hint?: string
}

function Stat({ label, value, hint }: StatProps) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
        {label}
      </Text>
      <Text fw={700} size="lg">
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

export function PortfolioOverview({ data }: { data: QuinielaGenerateResponse }) {
  const portfolio = data.portfolio
  const ticket = data.tickets[0]
  const isMultiple = data.mode === 'multiple'
  const prizeProbability = portfolio.prize_estimate.probability_any_prize
  const cumulativeFrom = (threshold: number): number =>
    portfolio.hit_distribution
      .slice(threshold)
      .reduce((total, probability) => total + probability, 0)

  return (
    <Paper shadow="sm" p="lg" withBorder>
      <Stack gap="lg">
        <Group justify="space-between" align="flex-start" wrap="wrap">
          <Stack gap={2}>
            <Group gap="xs">
              <Title order={3}>{data.jornada.label}</Title>
              <Badge
                color="teal"
                variant="light"
                title={data.jornada.competitions?.join(' · ')}
              >
                {data.jornada.competition}
              </Badge>
            </Group>
            <Text size="sm" c="dimmed">
              {formatShortDate(data.jornada.start_date)} · {data.jornada.matches} partidos ·
              Estrategia: {data.strategy_label}
            </Text>
          </Stack>
          <Group gap="xs">
            <Badge color="teal" variant="light">
              {isMultiple ? 'Múltiple' : `${portfolio.tickets} columnas`}
            </Badge>
            <Badge color="gray" variant="light">
              Semilla {data.seed}
            </Badge>
          </Group>
        </Group>

        <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }} spacing="md">
          <Stat
            label="Coste"
            value={formatCurrency(portfolio.cost)}
            hint={`Presupuesto ${formatCurrency(data.budget.requested)} · máx. ${data.budget.max_columns} col.`}
          />
          <Stat
            label="Columnas"
            value={portfolio.columns.toLocaleString('es-ES')}
            hint={isMultiple ? `${ticket?.doubles ?? 0} dobles · ${ticket?.triples ?? 0} triples` : 'Una por boleto'}
          />
          <Stat
            label="Aciertos esperados"
            value={`${portfolio.expected_total_hits.toFixed(2)} / 15`}
            hint={`Mejor columna: ${portfolio.expected_best_hits.toFixed(2)} / 14`}
          />
          <Stat
            label="Prob. de premio"
            value={formatPercent(prizeProbability)}
            hint="Al menos 10 aciertos"
          />
          <Stat
            label="Aciertos garantizados"
            value={String(portfolio.guaranteed_hits)}
            hint="Solo con triples"
          />
          <Stat
            label="Partidos cubiertos"
            value={`${data.jornada.matches}`}
            hint={`Pleno: ${data.analysis.pleno.score}`}
          />
        </SimpleGrid>

        <Stack gap={4}>
          <Group justify="space-between">
            <Text size="sm" fw={600}>
              Probabilidad de alcanzar al menos cada categoría
            </Text>
            <Text size="xs" c="dimmed">
              Modelo: {portfolio.method === 'monte_carlo' ? 'Monte Carlo' : 'Poisson-binomial exacta'}
            </Text>
          </Group>
          {Object.keys(portfolio.category_probabilities).map((category) => {
            const probability = cumulativeFrom(Number(category))
            return (
              <Group key={category} gap="sm" wrap="nowrap">
                <Badge
                  variant="light"
                  color={category === '15' ? 'yellow' : category === '14' ? 'teal' : 'gray'}
                  style={{ minWidth: 52 }}
                >
                  ≥ {category}
                </Badge>
                <Progress
                  value={Math.min(100, probability * 100)}
                  color={category === '15' ? 'yellow' : 'teal'}
                  style={{ flex: 1 }}
                  size="sm"
                />
                <Text size="xs" c="dimmed" style={{ width: 70, textAlign: 'right' }}>
                  {formatPercent(probability)}
                </Text>
              </Group>
            )
          })}
        </Stack>
      </Stack>
    </Paper>
  )
}
