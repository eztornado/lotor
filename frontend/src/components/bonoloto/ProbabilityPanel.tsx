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
import { IconTrophy } from '@tabler/icons-react'
import type { BonolotoPortfolio } from '../../services/bonoloto'
import { formatOneIn, formatPercent, formatDecimal } from './format'

export function ProbabilityPanel({
  portfolio,
}: {
  portfolio: BonolotoPortfolio
}) {
  const t = portfolio.theoretical
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
          El jackpot por apuesta es siempre 1 entre {formatOneIn(t.prob_6).replace('1 entre ', '')}. Con{' '}
          {portfolio.tickets} apuestas distintas la probabilidad se multiplica, pero sigue siendo
          pequeña.
        </Text>

        <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="xs">
          <Stack gap={0}>
            <Text size="xs" c="dimmed">
              6 aciertos
            </Text>
            <Text fw={700}>{formatOneIn(t.prob_6)}</Text>
          </Stack>
          <Stack gap={0}>
            <Text size="xs" c="dimmed">
              5 + complementario
            </Text>
            <Text fw={700}>{formatOneIn(t.prob_5_plus_complementario)}</Text>
          </Stack>
          <Stack gap={0}>
            <Text size="xs" c="dimmed">
              5 aciertos
            </Text>
            <Text fw={700}>{formatOneIn(t.prob_5)}</Text>
          </Stack>
          <Stack gap={0}>
            <Text size="xs" c="dimmed">
              5+ (con o sin comp.)
            </Text>
            <Text fw={700}>{formatOneIn(t.prob_5_plus)}</Text>
          </Stack>
        </SimpleGrid>

        <Divider />

        <Stack gap={6}>
          <Group justify="space-between">
            <Text size="sm">Algún premio de 4 o más aciertos</Text>
            <Badge color="grape" variant="light">
              {formatPercent(t.prob_4_plus)}
            </Badge>
          </Group>
          <Progress value={t.prob_4_plus * 100} color="grape" />
          <Group justify="space-between">
            <Text size="sm">Algún premio de 3 o más aciertos</Text>
            <Badge color="blue" variant="light">
              {formatPercent(t.prob_3_plus)}
            </Badge>
          </Group>
          <Progress value={t.prob_3_plus * 100} color="blue" />
          <Group justify="space-between">
            <Text size="sm">Al menos recuperar el reintegro</Text>
            <Badge color="pink" variant="light">
              {formatPercent(t.prob_reintegro)}
            </Badge>
          </Group>
          <Group justify="space-between">
            <Text size="sm">Aciertos esperados (suma de las apuestas)</Text>
            <Text fw={700}>{formatDecimal(t.expected_matches)}</Text>
          </Group>
          <Text size="xs" c="dimmed">
            Simulación de {portfolio.simulation.simulations.toLocaleString('es-ES')} sorteos sobre la
            cartera concreta. Los premios son fijos por categoría.
          </Text>
        </Stack>
      </Stack>
    </Paper>
  )
}

export default ProbabilityPanel
