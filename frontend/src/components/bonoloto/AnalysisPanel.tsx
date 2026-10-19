import { Badge, Divider, Grid, Group, Paper, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconChartBar, IconClock, IconFlame, IconSnowflake } from '@tabler/icons-react'
import type { BonolotoAnalysis } from '../../services/bonoloto'
import { formatShortDate } from './format'

export function AnalysisPanel({ analysis }: { analysis: BonolotoAnalysis }) {
  return (
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
                {analysis.hot_numbers?.slice(0, 10).map((item) => (
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
                {analysis.overdue_numbers?.slice(0, 10).map((item) => (
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
          {analysis.top_pairs?.slice(0, 5).map((pair) => (
            <Badge key={pair.numbers.join('-')} variant="light" color="grape">
              {pair.numbers.join(' + ')} ({pair.frequency})
            </Badge>
          ))}
        </Group>

        {analysis.reintegro && analysis.reintegro.length > 0 && (
          <>
            <Divider />
            <Stack gap={4}>
              <Text fw={700} size="sm">
                Reintegros más frecuentes
              </Text>
              <Group gap={6} wrap="wrap">
                {analysis.reintegro.slice(0, 10).map((item) => (
                  <Badge key={item.digit} variant="light" color="pink">
                    {item.digit} · {(item.probability * 100).toFixed(1).replace('.', ',')} % ·{' '}
                    {item.frequency} veces
                  </Badge>
                ))}
              </Group>
              <Text size="xs" c="dimmed">
                Última aparición más reciente:{' '}
                {formatShortDate(
                  analysis.reintegro
                    .map((item) => item.last_seen)
                    .filter(Boolean)
                    .sort()
                    .reverse()[0],
                )}
              </Text>
            </Stack>
          </>
        )}
      </Stack>
    </Paper>
  )
}

export default AnalysisPanel
