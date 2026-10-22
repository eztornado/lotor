import { Badge, Group, List, Paper, Progress, SimpleGrid, Stack, Text, Title } from '@mantine/core'
import type { QuinielaAnalysis } from '../../services/quiniela'
import { formatPercent, signColor } from './format'

function MatchList({
  title,
  items,
}: {
  title: string
  items: QuinielaAnalysis['most_confident']
}) {
  return (
    <Stack gap="xs">
      <Text size="sm" fw={600}>
        {title}
      </Text>
      {items.map((item) => (
        <Group key={item.match_number} justify="space-between" wrap="nowrap">
          <Group gap="xs" wrap="nowrap">
            <Badge variant="light" color="gray">
              {item.match_number}
            </Badge>
            <Text size="sm">{item.match}</Text>
          </Group>
          <Group gap={4} wrap="nowrap">
            <Badge color={signColor(item.pick)} variant="light" size="sm">
              {item.pick}
            </Badge>
            <Text size="xs" c="dimmed">
              {formatPercent(item.probability)}
            </Text>
          </Group>
        </Group>
      ))}
    </Stack>
  )
}

export function AnalysisPanel({ analysis }: { analysis: QuinielaAnalysis }) {
  const quality = analysis.data_quality
  const totalQuality = Object.values(quality).reduce((total, value) => total + value, 0) || 1

  return (
    <Paper shadow="sm" p="md" withBorder h="100%">
      <Stack gap="md">
        <Stack gap={2}>
          <Title order={4}>Lectura del modelo</Title>
          <Text size="xs" c="dimmed">
            Confianza media: {formatPercent(analysis.average_confidence)} · El pleno se juega
            aparte y es la parte más difícil.
          </Text>
        </Stack>

        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <MatchList
            title="Partidos más claros"
            items={analysis.most_confident}
          />
          <MatchList
            title="Partidos más abiertos"
            items={analysis.most_uncertain}
          />
        </SimpleGrid>

        <Stack gap={4}>
          <Text size="sm" fw={600}>
            Calidad de los datos
          </Text>
          {Object.entries(quality).map(([label, value]) => (
            <Group key={label} gap="sm" wrap="nowrap">
              <Text size="xs" c="dimmed" style={{ width: 70 }}>
                {label}
              </Text>
              <Progress value={(value / totalQuality) * 100} size="sm" style={{ flex: 1 }} />
              <Text size="xs" c="dimmed" style={{ width: 24, textAlign: 'right' }}>
                {value}
              </Text>
            </Group>
          ))}
        </Stack>

        <Stack gap={4}>
          <Text size="sm" fw={600}>
            Pleno al 15: {analysis.pleno.score} ({formatPercent(analysis.pleno.probability)})
          </Text>
          <List size="xs" spacing={2}>
            {analysis.pleno.alternatives.map((option) => (
              <List.Item key={option.score}>
                Marcador {option.score}: {formatPercent(option.probability)}
              </List.Item>
            ))}
          </List>
        </Stack>
      </Stack>
    </Paper>
  )
}
