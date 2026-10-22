import { Alert, Badge, Paper, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core'
import { IconAlertTriangle, IconInfoCircle } from '@tabler/icons-react'
import type { QuinielaPrizeEstimate } from '../../services/quiniela'
import { formatCurrency, formatPercent } from './format'

const signedPercent = (value: number): string => {
  const formatted = (value * 100).toLocaleString('es-ES', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })
  return `${value > 0 ? '+' : ''}${formatted} %`
}

export function PrizePanel({ prize }: { prize: QuinielaPrizeEstimate }) {
  const optimistic = prize.roi.average > 0

  return (
    <Paper shadow="sm" p="md" withBorder h="100%">
      <Stack gap="md">
        <GroupTitle />

        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
          <Stack gap={0}>
            <Text size="xs" c="dimmed">
              Probabilidad de premio
            </Text>
            <Text fw={700} size="lg">
              {formatPercent(prize.probability_any_prize)}
            </Text>
            <Text size="xs" c="dimmed">
              10 o más aciertos
            </Text>
          </Stack>
          <Stack gap={0}>
            <Text size="xs" c="dimmed">
              Retorno esperado medio
            </Text>
            <Text fw={700} size="lg">
              {formatCurrency(prize.expected_return.average)}
            </Text>
            <Text size="xs" c="dimmed">
              Coste {formatCurrency(prize.cost)}
            </Text>
          </Stack>
          <Stack gap={0}>
            <Text size="xs" c="dimmed">
              ROI medio estimado
            </Text>
            <Text fw={700} size="lg" c={optimistic ? 'teal' : 'orange'}>
              {signedPercent(prize.roi.average)}
            </Text>
            <Text size="xs" c="dimmed">
              Rango {signedPercent(prize.roi.low)} a {signedPercent(prize.roi.high)}
            </Text>
          </Stack>
        </SimpleGrid>

        <Table verticalSpacing="xs">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Categoría</Table.Th>
              <Table.Th>Prob. exacta</Table.Th>
              <Table.Th>Premio medio</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {Object.entries(prize.by_category).map(([category, item]) => (
              <Table.Tr key={category}>
                <Table.Td>
                  <Badge variant="light" color={category === '15' ? 'yellow' : 'teal'}>
                    {category} aciertos
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{formatPercent(item.probability)}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{formatCurrency(item.average_prize, 2)}</Text>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>

        <Text size="xs" c="dimmed">
          El retorno es conservador: suma solo el mejor boleto. Un múltiple puede
          cobrar varias categorías a la vez, pero los premios son de reparto.
        </Text>

        {optimistic ? (
          <Alert icon={<IconAlertTriangle size={16} />} color="orange" variant="light">
            <Text size="sm">
              La estimación media sale favorable, pero es la parte más incierta del modelo:
              los premios son de reparto y pueden ser mucho menores. No es una promesa de
              rentabilidad.
            </Text>
          </Alert>
        ) : (
          <Alert icon={<IconInfoCircle size={16} />} color="gray" variant="light">
            <Text size="sm">{prize.note}</Text>
          </Alert>
        )}
      </Stack>
    </Paper>
  )
}

function GroupTitle() {
  return (
    <Stack gap={2}>
      <Title order={4}>Premios y valor esperado</Title>
      <Text size="xs" c="dimmed">
        Estimación orientativa con premios medios; La Quiniela reparte según acertantes.
      </Text>
    </Stack>
  )
}
