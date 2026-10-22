import {
  Accordion,
  Badge,
  Group,
  Paper,
  Progress,
  ScrollArea,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core'
import type { QuinielaMatch, QuinielaTicket } from '../../services/quiniela'
import { formatPercent, qualityColor, signColor } from './format'

interface TicketCardProps {
  ticket: QuinielaTicket
  matches: QuinielaMatch[]
  pleno: QuinielaMatch
  mode: 'multiple' | 'simple'
}

export function TicketCard({ ticket, matches, pleno, mode }: TicketCardProps) {
  const byNumber = new Map(matches.map((match) => [match.match_number, match]))

  return (
    <Paper shadow="sm" p="md" withBorder>
      <Stack gap="md">
        <Group justify="space-between" align="flex-start" wrap="wrap">
          <Stack gap={2}>
            <Group gap="xs">
              <Title order={4}>
                {mode === 'multiple' ? 'Boleto múltiple' : `Columna ${ticket.index}`}
              </Title>
              <Badge color="teal" variant="light">
                {ticket.columns} {ticket.columns === 1 ? 'columna' : 'columnas'}
              </Badge>
            </Group>
            <Text size="xs" c="dimmed">
              {ticket.doubles} dobles · {ticket.triples} triples · {formatPercent(ticket.expected_hits / 14)} de acierto medio por partido
            </Text>
          </Stack>
          <Group gap="xs">
            <Badge variant="light">{ticket.cost.toFixed(2)} €</Badge>
            <Badge variant="light" color="orange">
              {ticket.expected_hits.toFixed(2)} / 14 aciertos
            </Badge>
            {ticket.guaranteed_hits > 0 && (
              <Badge variant="light" color="yellow">
                {ticket.guaranteed_hits} garantizado(s)
              </Badge>
            )}
          </Group>
        </Group>

        <ScrollArea>
          <Table striped highlightOnHover verticalSpacing="xs" miw={720}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th style={{ width: 44 }}>#</Table.Th>
                <Table.Th>Partido</Table.Th>
                <Table.Th>Competición</Table.Th>
                <Table.Th style={{ width: 130 }}>Signos</Table.Th>
                <Table.Th style={{ width: 110 }}>Cobertura</Table.Th>
                <Table.Th style={{ width: 120 }}>Marcador</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {ticket.signs.map((sign) => {
                const match = byNumber.get(sign.match_number)
                if (!match) return null
                return (
                  <Table.Tr key={sign.match_number}>
                    <Table.Td>
                      <Badge variant="light" color="gray">
                        {sign.match_number}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Stack gap={0}>
                        <Text size="sm" fw={600}>
                          {match.home_team}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {match.away_team}
                        </Text>
                      </Stack>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" c="dimmed">
                        {match.competition}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4} wrap="nowrap">
                        {sign.signs.map((value) => (
                          <Badge
                            key={value}
                            color={signColor(value)}
                            variant={value === sign.pick ? 'filled' : 'light'}
                            size="sm"
                          >
                            {value}
                          </Badge>
                        ))}
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Stack gap={2}>
                        <Progress
                          value={sign.coverage * 100}
                          color={sign.coverage >= 0.99 ? 'teal' : 'orange'}
                          size="sm"
                        />
                        <Text size="xs" c="dimmed">
                          {formatPercent(sign.coverage)}
                        </Text>
                      </Stack>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Badge variant="light" color={qualityColor(match.data_quality)}>
                          {match.most_likely_score}
                        </Badge>
                        <Text size="xs" c="dimmed">
                          xG {match.expected_goals.home.toFixed(1)}-{match.expected_goals.away.toFixed(1)}
                        </Text>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                )
              })}
              <Table.Tr>
                <Table.Td>
                  <Badge variant="filled" color="yellow">
                    15
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Stack gap={0}>
                    <Text size="sm" fw={600}>
                      {pleno.home_team}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {pleno.away_team}
                    </Text>
                  </Stack>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {pleno.competition}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge color="yellow" variant="filled">
                    {ticket.pleno.score}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    Pleno al 15
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {formatPercent(ticket.pleno.probability)}
                  </Text>
                </Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>
        </ScrollArea>

        {ticket.expanded_columns && ticket.expanded_columns.length > 1 && (
          <Accordion variant="contained">
            <Accordion.Item value="columns">
              <Accordion.Control>
                Ver las {ticket.expanded_columns.length} columnas del boleto
              </Accordion.Control>
              <Accordion.Panel>
                <ScrollArea h={420}>
                  <Stack gap={4}>
                    {ticket.expanded_columns.map((column, index) => (
                      <Group key={index} gap="xs" wrap="nowrap">
                        <Text size="xs" c="dimmed" style={{ width: 28, textAlign: 'right' }}>
                          {index + 1}.
                        </Text>
                        <Text size="sm" ff="monospace">
                          {column.signs.join(' · ')}
                        </Text>
                        <Badge size="xs" variant="light" color="yellow">
                          {column.pleno}
                        </Badge>
                      </Group>
                    ))}
                  </Stack>
                </ScrollArea>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        )}
        {ticket.expanded_note && (
          <Text size="xs" c="dimmed">
            {ticket.expanded_note}
          </Text>
        )}
      </Stack>
    </Paper>
  )
}
