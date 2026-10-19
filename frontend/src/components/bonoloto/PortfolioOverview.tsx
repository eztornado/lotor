import { Badge, Grid, Group, Paper, Progress, Stack, Text } from '@mantine/core'
import type { BonolotoGenerateResponse } from '../../services/bonoloto'
import { formatDate, formatDecimal } from './format'

export function PortfolioOverview({ data }: { data: BonolotoGenerateResponse }) {
  const { portfolio } = data
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
              {data.game.max_number} + reintegro
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
                {formatDecimal(portfolio.coverage.numbers_pct, 1)} %
              </Text>
            </Group>
            <Progress value={portfolio.coverage.numbers_pct} color="teal" size="lg" />
            <Text size="xs" c="dimmed">
              {portfolio.coverage.unique_numbers}/{portfolio.coverage.total_numbers} números ·{' '}
              {formatDecimal(portfolio.coverage.pairs_pct, 1)} % pares ·{' '}
              {formatDecimal(portfolio.coverage.triples_pct, 1)} % tríos
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
