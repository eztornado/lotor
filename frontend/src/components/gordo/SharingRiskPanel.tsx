import { Badge, Divider, Group, Paper, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconKey, IconShield, IconTarget } from '@tabler/icons-react'
import type { GordoGenerateResponse } from '../../services/gordo'
import { formatDecimal, formatShortDate, riskColor } from './format'

export function SharingRiskPanel({ data }: { data: GordoGenerateResponse }) {
  const { portfolio } = data
  return (
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
          <Badge color={riskColor(portfolio.popularity.risk)}>{portfolio.popularity.risk}</Badge>
        </Group>
        <Text size="sm" c="dimmed">
          {portfolio.popularity.low_popularity_tickets} de {portfolio.tickets} apuestas son poco
          populares. Penalizamos fechas de nacimiento (números ≤ 31), progresiones y patrones
          obvios: si el premio cae en una combinación muy jugada, se reparte entre más acertantes.
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
        <Divider />
        <Group gap="xs">
          <ThemeIcon color="yellow" variant="light" size="lg">
            <IconKey size={18} />
          </ThemeIcon>
          <Text fw={700}>Cobertura de claves</Text>
          <Badge color="yellow" variant="light">
            {portfolio.keys.distinct}/10
          </Badge>
        </Group>
        <Text size="sm" c="dimmed">
          {portfolio.keys.guaranteed_match
            ? 'Las 10 claves están cubiertas: una apuesta lleva siempre la clave ganadora y recupera 1,50 € de reintegro. La clave es compatible con el premio por aciertos: si esa apuesta suma 2 o más números, se cobran ambos.'
            : `Se usan ${portfolio.keys.distinct} claves distintas, priorizando las de mayor probabilidad histórica. Con 10 apuestas se cubrirían todas y el reintegro estaría garantizado.`}
        </Text>
        <Text size="xs" c="dimmed">
          Datos: {data.dataset.total_draws.toLocaleString('es-ES')} sorteos ·{' '}
          {formatShortDate(data.dataset.date_range.from)} →{' '}
          {formatShortDate(data.dataset.date_range.to)}
        </Text>

        <Divider />

        <Group justify="space-between">
          <Stack gap={0}>
            <Text size="xs" c="dimmed">
              Coste
            </Text>
            <Text fw={700}>{formatDecimal(portfolio.cost_eur)} €</Text>
          </Stack>
          <Stack gap={0}>
            <Text size="xs" c="dimmed">
              Reintegro esperado
            </Text>
            <Text fw={700}>
              {formatDecimal(portfolio.theoretical.expected_reintegro_eur)} €
            </Text>
          </Stack>
          <Stack gap={0}>
            <Text size="xs" c="dimmed">
              Solapamiento
            </Text>
            <Text fw={700}>{portfolio.overlap.max}</Text>
          </Stack>
        </Group>
      </Stack>
    </Paper>
  )
}

export default SharingRiskPanel
