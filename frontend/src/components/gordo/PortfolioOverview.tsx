import { Badge, Grid, Group, Paper, Progress, Stack, Text } from '@mantine/core'
import type { GordoGenerateResponse } from '../../services/gordo'
import { formatDate, formatDecimal, formatShortDate } from './format'

export function PortfolioOverview({ data }: { data: GordoGenerateResponse }) {
  const { portfolio } = data
  const ticketWord = portfolio.tickets === 1 ? 'apuesta' : 'apuestas'
  return (
    <Paper shadow="sm" p="md" withBorder>
      <Grid>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Stack gap={4}>
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
              Próximo sorteo
            </Text>
            <Text size="xl" fw={700}>
              {formatDate(data.dataset.next_draw)}
            </Text>
            <Text size="xs" c="dimmed">
              {data.game.draw_days} · {data.game.numbers_per_ticket} números del 1 al{' '}
              {data.game.max_number} + clave ({data.game.key_range[0]}–
              {data.game.key_range[1]})
            </Text>
            <Text size="xs" c="dimmed">
              {data.dataset.total_draws.toLocaleString('es-ES')} sorteos ·{' '}
              {formatShortDate(data.dataset.date_range.from)} →{' '}
              {formatShortDate(data.dataset.date_range.to)}
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
                  {formatDecimal(portfolio.cost_eur)} €
                </Text>
                <Text size="xs" c="dimmed">
                  coste total
                </Text>
              </Stack>
              <Stack gap={0}>
                <Text size="xl" fw={700}>
                  {portfolio.keys.distinct}/10
                </Text>
                <Text size="xs" c="dimmed">
                  claves
                </Text>
              </Stack>
            </Group>
            {portfolio.keys.guaranteed_match && (
              <Badge color="yellow" variant="light" w="fit-content">
                Reintegro de 1,50 € garantizado
              </Badge>
            )}
            {portfolio.overlap.max === 0 && (
              <Badge color="teal" variant="light" w="fit-content">
                Apuestas disjuntas: sin números repetidos
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
                {formatDecimal(portfolio.coverage.numbers_pct, 1)} %
              </Text>
            </Group>
            <Progress value={portfolio.coverage.numbers_pct} color="teal" size="lg" />
            <Text size="xs" c="dimmed">
              {portfolio.coverage.unique_numbers}/{portfolio.coverage.total_numbers} números ·{' '}
              {formatDecimal(portfolio.coverage.numbers_possible_pct, 1)} % de la cobertura posible
              con {portfolio.tickets} {ticketWord}
            </Text>
            <Text size="xs" c="dimmed">
              {portfolio.coverage.unique_pairs}/
              {portfolio.coverage.pairs_total.toLocaleString('es-ES')} pares (
              {formatDecimal(portfolio.coverage.pairs_total_pct, 1)} %) ·{' '}
              {portfolio.coverage.unique_triples}/
              {portfolio.coverage.triples_total.toLocaleString('es-ES')} tríos (
              {formatDecimal(portfolio.coverage.triples_total_pct, 1)} %)
            </Text>
            <Text size="xs" c="dimmed">
              Solapamiento medio {formatDecimal(portfolio.overlap.average)} · máximo{' '}
              {portfolio.overlap.max}
            </Text>
          </Stack>
        </Grid.Col>
      </Grid>
    </Paper>
  )
}

export default PortfolioOverview
