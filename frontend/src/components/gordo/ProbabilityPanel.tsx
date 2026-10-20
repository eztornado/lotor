import {
  Badge,
  Divider,
  Group,
  Paper,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { IconInfoCircle, IconKey, IconTrophy } from '@tabler/icons-react'
import type { GordoPortfolio } from '../../services/gordo'
import {
  formatDecimal,
  formatOneInExact,
  formatPercent,
} from './format'

const categoryRows = [
  { key: 'prob_1', label: '1ª · 5 + clave' },
  { key: 'prob_2', label: '2ª · 5 aciertos' },
  { key: 'prob_3', label: '3ª · 4 + clave' },
  { key: 'prob_4', label: '4ª · 4 aciertos' },
  { key: 'prob_5', label: '5ª · 3 + clave' },
  { key: 'prob_6', label: '6ª · 3 aciertos' },
  { key: 'prob_7', label: '7ª · 2 + clave' },
  { key: 'prob_8', label: '8ª · 2 aciertos' },
] as const

export function ProbabilityPanel({ portfolio }: { portfolio: GordoPortfolio }) {
  const t = portfolio.theoretical
  const single = t.single_ticket

  return (
    <Paper shadow="sm" p="md" withBorder h="100%">
      <Stack gap="sm">
        <Group gap="xs">
          <ThemeIcon color="grape" variant="light" size="lg">
            <IconTrophy size={18} />
          </ThemeIcon>
          <Title order={4}>Probabilidad de premio con esta cartera</Title>
        </Group>
        <Text size="xs" c="dimmed">
          El primer premio por apuesta es siempre 1 entre 31.625.100. Con{' '}
          {portfolio.tickets} apuestas distintas, la probabilidad de la 1ª categoría es{' '}
          {formatOneInExact(t.prob_1)}. Las probabilidades de las 8 categorías son exactas para
          esta cartera de apuestas disjuntas; el reintegro por clave se muestra aparte.
        </Text>

        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
          {categoryRows.map((category) => (
            <Group key={category.key} justify="space-between" wrap="nowrap" gap="xs">
              <Text size="xs" c="dimmed">
                {category.label}
              </Text>
              <Text size="sm" fw={700}>
                {formatOneInExact(t[category.key])}
              </Text>
            </Group>
          ))}
        </SimpleGrid>

        <Divider />

        <Stack gap={8}>
          <Group justify="space-between" wrap="nowrap">
            <Text size="sm">Algún premio (2 o más)</Text>
            <Group gap={6} wrap="nowrap">
              <Badge color="teal" variant="light">
                {formatPercent(t.prob_any_prize, 2)}
              </Badge>
              <Text size="xs" c="dimmed">
                {formatOneInExact(t.prob_any_prize)}
              </Text>
            </Group>
          </Group>
          <Progress value={t.prob_any_prize * 100} color="teal" />

          <Group justify="space-between" wrap="nowrap">
            <Text size="sm">3 o más aciertos</Text>
            <Group gap={6} wrap="nowrap">
              <Badge color="blue" variant="light">
                {formatPercent(t.prob_3_plus, 2)}
              </Badge>
              <Text size="xs" c="dimmed">
                {formatOneInExact(t.prob_3_plus)}
              </Text>
            </Group>
          </Group>
          <Progress value={t.prob_3_plus * 100} color="blue" />

          <Group justify="space-between" wrap="nowrap">
            <Text size="sm">4 o más aciertos</Text>
            <Group gap={6} wrap="nowrap">
              <Badge color="indigo" variant="light">
                {formatPercent(t.prob_4_plus, 4)}
              </Badge>
              <Text size="xs" c="dimmed">
                {formatOneInExact(t.prob_4_plus)}
              </Text>
            </Group>
          </Group>
          <Progress value={t.prob_4_plus * 100} color="indigo" />

          <Group justify="space-between" wrap="nowrap">
            <Text size="sm">5 o más aciertos (con o sin clave)</Text>
            <Text size="sm" fw={700}>
              {formatOneInExact(t.prob_5_plus)}
            </Text>
          </Group>
          <Group justify="space-between" wrap="nowrap">
            <Text size="sm">Primer premio (5 + clave)</Text>
            <Text size="sm" fw={700}>
              {formatOneInExact(t.prob_1)}
            </Text>
          </Group>
        </Stack>

        <Divider />

        <Group gap="xs">
          <ThemeIcon color="yellow" variant="light" size="md">
            <IconKey size={16} />
          </ThemeIcon>
          <Text size="sm" fw={700}>
            Clave y reintegro
          </Text>
          <Badge color="yellow" variant="light">
            {formatPercent(t.prob_reintegro, 0)}
          </Badge>
        </Group>
        <Text size="xs" c="dimmed">
          {portfolio.keys.distinct} de 10 claves distintas. Cada apuesta que acierte la clave
          recupera {formatDecimal(t.reintegro_eur)} € de reintegro, sin perjuicio del premio por
          aciertos. Con 10 apuestas se cubren todas: una recupera siempre su importe.
        </Text>
        <Group justify="space-between" wrap="nowrap">
          <Text size="sm">Algún retorno (premio o reintegro)</Text>
          <Group gap={6} wrap="nowrap">
            <Badge color="lime" variant="light">
              {formatPercent(t.prob_any_return, 2)}
            </Badge>
            <Text size="xs" c="dimmed">
              {portfolio.keys.guaranteed_match
                ? 'reintegro garantizado'
                : formatOneInExact(t.prob_any_return)}
            </Text>
          </Group>
        </Group>
        <Progress value={t.prob_any_return * 100} color="lime" />

        <Divider />

        <Group justify="space-between">
          <Text size="sm">Aciertos esperados (suma de las apuestas)</Text>
          <Text fw={700}>{formatDecimal(t.expected_matches, 2)}</Text>
        </Group>

        <Text size="xs" c="dimmed">
          Por apuesta: 1ª categoría {formatOneInExact(single.prob_1)} · algún premio{' '}
          {formatOneInExact(single.prob_2_plus)} · reintegro de{' '}
          {formatDecimal(t.reintegro_eur)} € si aciertas la clave.
        </Text>

        <Group gap="xs" align="flex-start">
          <IconInfoCircle size={14} color="#868e96" style={{ marginTop: 2 }} />
          <Text size="xs" c="dimmed">
            {t.exact ? 'Cálculo combinatorio exacto' : 'Estimación por simulación'} ·{' '}
            {portfolio.simulation.simulations.toLocaleString('es-ES')} sorteos simulados (
            {formatPercent(portfolio.simulation.prob_any_prize, 2)} de algún premio). Con apuestas
            disjuntas, la probabilidad de cada categoría depende del número de apuestas, no de los
            números elegidos: el modelo decide qué jugar y la anti-popularidad reduce el riesgo de
            compartir.
          </Text>
        </Group>
      </Stack>
    </Paper>
  )
}

export default ProbabilityPanel
