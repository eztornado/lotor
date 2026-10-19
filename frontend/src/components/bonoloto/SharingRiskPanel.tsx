import { Badge, Divider, Group, Paper, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconShield, IconTarget } from '@tabler/icons-react'
import type { BonolotoGenerateResponse } from '../../services/bonoloto'
import { formatShortDate, riskColor } from './format'

export function SharingRiskPanel({ data }: { data: BonolotoGenerateResponse }) {
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
          populares. Penalizamos fechas de nacimiento, progresiones y patrones obvios: si el premio
          cae en una combinación muy jugada, se reparte entre más acertantes.
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
          {formatShortDate(data.dataset.date_range.from)} → {formatShortDate(data.dataset.date_range.to)}
        </Text>
      </Stack>
    </Paper>
  )
}

export default SharingRiskPanel
