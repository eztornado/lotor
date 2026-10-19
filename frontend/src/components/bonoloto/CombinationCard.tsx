import { Badge, Button, Card, Group, Stack, Text, Tooltip } from '@mantine/core'
import { IconCopy } from '@tabler/icons-react'
import type { BonolotoCombination } from '../../services/bonoloto'
import { Ball } from './Ball'
import {
  formatDecimal,
  formatNumber,
  popularityLabel,
  qualityColor,
} from './format'

export function CombinationCard({
  combination,
  drawDate,
}: {
  combination: BonolotoCombination
  drawDate: string
}) {
  const popularity = popularityLabel(combination.popularity)

  const copyTicket = async () => {
    const text = `Bonoloto ${drawDate} · Apuesta ${combination.index}: ${combination.numbers
      .map(formatNumber)
      .join(' - ')}  (Reintegro: ${combination.reintegro})`
    try {
      await navigator.clipboard.writeText(text)
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
            <div>
              <Ball number={combination.reintegro} variant="reintegro" />
            </div>
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
            Índice del modelo: {formatDecimal(combination.quality * 100, 1)}
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

export default CombinationCard
