import {
  Badge,
  Divider,
  Grid,
  Group,
  Paper,
  Progress,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { IconChartBar, IconClock, IconFlame, IconKey, IconSnowflake } from '@tabler/icons-react'
import type { GordoAnalysis } from '../../services/gordo'
import { formatDecimal, formatShortDate } from './format'

function NumberBadges({
  items,
  color,
  suffix,
}: {
  items: GordoAnalysis['hot_numbers']
  color: string
  suffix?: (item: GordoAnalysis['hot_numbers'][number]) => string
}) {
  return (
    <Group gap={4}>
      {items.slice(0, 10).map((item) => (
        <Badge key={item.number} color={color} variant="light">
          {item.number}
          {suffix ? ` · ${suffix(item)}` : ''}
        </Badge>
      ))}
    </Group>
  )
}

export function AnalysisPanel({
  analysis,
  showFrequent = true,
  showKeys = true,
}: {
  analysis: GordoAnalysis
  showFrequent?: boolean
  showKeys?: boolean
}) {
  const maxKeyProbability = Math.max(
    ...analysis.key.map((item) => item.probability),
    0.0001,
  )
  const itemSpan = showFrequent
    ? { base: 12, sm: 6, md: 3 }
    : { base: 12, sm: 6, md: 4 }

  return (
    <Paper shadow="sm" p="md" withBorder>
      <Stack gap="md">
        <Group gap="xs">
          <ThemeIcon color="orange" variant="light" size="lg">
            <IconChartBar size={18} />
          </ThemeIcon>
          <Title order={4}>Análisis del histórico</Title>
          <Text size="xs" c="dimmed">
            {analysis.structure.draws_used.toLocaleString('es-ES')} sorteos usados por el modelo
          </Text>
        </Group>

        <Grid>
          <Grid.Col span={itemSpan}>
            <Stack gap={4}>
              <Group gap={4}>
                <IconFlame size={16} color="#f76707" />
                <Text fw={700} size="sm">
                  Mejor tendencia reciente
                </Text>
              </Group>
              <NumberBadges items={analysis.hot_numbers} color="orange" />
            </Stack>
          </Grid.Col>
          <Grid.Col span={itemSpan}>
            <Stack gap={4}>
              <Group gap={4}>
                <IconSnowflake size={16} color="#4dabf7" />
                <Text fw={700} size="sm">
                  Tendencia más fría
                </Text>
              </Group>
              <NumberBadges items={analysis.cold_numbers} color="blue" />
            </Stack>
          </Grid.Col>
          {showFrequent && (
            <Grid.Col span={itemSpan}>
              <Stack gap={4}>
                <Group gap={4}>
                  <IconChartBar size={16} color="#12b886" />
                  <Text fw={700} size="sm">
                    Más frecuentes
                  </Text>
                </Group>
                <NumberBadges
                  items={analysis.most_frequent_numbers}
                  color="teal"
                  suffix={(item) => `${item.frequency}`}
                />
              </Stack>
            </Grid.Col>
          )}
          <Grid.Col span={itemSpan}>
            <Stack gap={4}>
              <Group gap={4}>
                <IconClock size={16} />
                <Text fw={700} size="sm">
                  Más retrasados
                </Text>
              </Group>
              <NumberBadges
                items={analysis.overdue_numbers}
                color="gray"
                suffix={(item) => `${item.gap_draws} sorteos`}
              />
            </Stack>
          </Grid.Col>
        </Grid>

        <Divider />

        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Stack gap={4}>
              <Group gap={4}>
                <IconClock size={16} />
                <Text fw={700} size="sm">
                  Estructura media
                </Text>
              </Group>
              <Text size="sm" c="dimmed">
                Suma media {formatDecimal(analysis.structure.average_sum, 1)} · desviación{' '}
                {formatDecimal(analysis.structure.sum_deviation, 1)}
              </Text>
              <Text size="sm" c="dimmed">
                Amplitud media {formatDecimal(analysis.structure.average_spread, 1)}
              </Text>
              <Text size="sm" c="dimmed">
                Patrón de décadas más habitual:{' '}
                {analysis.structure.most_common_decade_pattern.pattern.join('-')} (
                {analysis.structure.most_common_decade_pattern.count} veces)
              </Text>
              <Text size="xs" c="dimmed">
                Décadas: {analysis.structure.most_common_decade_pattern.labels.join(' · ')}
              </Text>
            </Stack>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 6 }}>
            <Stack gap={4}>
              <Text fw={700} size="sm">
                Pares con mayor afinidad
              </Text>
              <Group gap={6} wrap="wrap">
                {analysis.top_pairs.slice(0, 10).map((pair) => (
                  <Badge key={pair.numbers.join('-')} variant="light" color="grape">
                    {pair.numbers.join(' + ')} ({pair.frequency})
                  </Badge>
                ))}
              </Group>
              <Text size="xs" c="dimmed">
                La afinidad se mide con el lift histórico del par, no con una garantía de salida.
              </Text>
            </Stack>
          </Grid.Col>
        </Grid>

        {showKeys && (
          <>
            <Divider />

            <Stack gap={6}>
              <Group gap="xs">
                <ThemeIcon color="yellow" variant="light" size="md">
                  <IconKey size={16} />
                </ThemeIcon>
                <Text fw={700} size="sm">
                  Claves (0–9)
                </Text>
              </Group>
              <Grid>
                {analysis.key.map((item) => (
                  <Grid.Col key={item.digit} span={{ base: 12, sm: 6, md: 4 }}>
                    <Stack gap={2}>
                      <Group justify="space-between">
                        <Badge color="yellow" variant="light">
                          Clave {item.digit}
                        </Badge>
                        <Text size="sm">
                          {formatDecimal(item.probability * 100, 1)} % · {item.frequency} veces
                        </Text>
                      </Group>
                      <Progress
                        value={(item.probability / maxKeyProbability) * 100}
                        color="yellow"
                        size="sm"
                      />
                      <Text size="xs" c="dimmed">
                        {item.gap_draws} sorteos sin salir · última vez{' '}
                        {formatShortDate(item.last_seen)}
                      </Text>
                    </Stack>
                  </Grid.Col>
                ))}
              </Grid>
            </Stack>
          </>
        )}
      </Stack>
    </Paper>
  )
}

export default AnalysisPanel
