import {
  Badge,
  Button,
  Card,
  Divider,
  Grid,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { IconArrowRight } from '@tabler/icons-react'
import { Link } from 'react-router-dom'
import { GAMES, type GameDefinition } from '../games'

function GameCard({ game }: { game: GameDefinition }) {
  const [primary, ...rest] = game.nav

  return (
    <Card
      shadow="md"
      padding="xl"
      radius="md"
      withBorder
      h="100%"
      style={{
        background: `linear-gradient(135deg, var(--mantine-color-${game.color}-9) 0%, var(--mantine-color-${game.color}-7) 100%)`,
      }}
    >
      <Stack gap="md" h="100%">
        <Group justify="space-between">
          <Text style={{ fontSize: 44 }}>{game.emoji}</Text>
          <Badge size="lg" color={`${game.color}.3`} variant="light">
            {game.tagline}
          </Badge>
        </Group>
        <Title order={2} c="white">
          {game.name}
        </Title>
        <Text size="sm" c="white" style={{ opacity: 0.9 }}>
          {game.description}
        </Text>

        <Group mt="auto">
          <Button
            component={Link}
            to={primary.path}
            size="md"
            color="white"
            variant="filled"
            rightSection={<IconArrowRight size={18} />}
          >
            {primary.label}
          </Button>
          {rest.map((item) => (
            <Button
              key={item.path}
              component={Link}
              to={item.path}
              variant="subtle"
              color="white"
              leftSection={<item.icon size={16} />}
            >
              {item.label}
            </Button>
          ))}
        </Group>
      </Stack>
    </Card>
  )
}

export default function HomePage() {
  return (
    <Stack gap="xl">
      <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
        <Title order={1} c="blue.4">
          🎱 LoTor
        </Title>
        <Text size="xl" c="dimmed" mt="md" maw={760} mx="auto">
          Predicciones con IA y generación inteligente de combinaciones para tus loterías.
        </Text>
      </div>

      <Grid>
        {GAMES.map((game) => (
          <Grid.Col key={game.id} span={{ base: 12, md: 4 }}>
            <GameCard game={game} />
          </Grid.Col>
        ))}
      </Grid>

      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
        <Paper shadow="xs" p="md" withBorder>
          <Stack gap="sm">
            <Title order={3}>🎯 El Gordo de la Primitiva</Title>
            <Text size="sm">• Selecciona <strong>5 números</strong> del 1 al 54</Text>
            <Text size="sm">• Elige <strong>1 número clave</strong> del 0 al 9</Text>
            <Text size="sm">• Sorteo todos los <strong>domingos</strong></Text>
          </Stack>
        </Paper>

        <Paper shadow="xs" p="md" withBorder>
          <Stack gap="sm">
            <Title order={3}>🍀 Bonoloto</Title>
            <Text size="sm">• Selecciona <strong>6 números</strong> del 1 al 49</Text>
            <Text size="sm">• Se añade <strong>complementario</strong> y <strong>reintegro</strong> (0–9)</Text>
            <Text size="sm">• Sorteo de <strong>lunes a sábado</strong></Text>
          </Stack>
        </Paper>

        <Paper shadow="xs" p="md" withBorder>
          <Stack gap="sm">
            <Title order={3}>⚽ La Quiniela</Title>
            <Text size="sm">• <strong>14 partidos</strong> con signos 1, X o 2</Text>
            <Text size="sm">• <strong>Pleno al 15</strong> con marcador exacto</Text>
            <Text size="sm">• Múltiples con <strong>dobles y triples</strong></Text>
          </Stack>
        </Paper>
      </SimpleGrid>

      <Paper
        shadow="xs"
        p="md"
        withBorder
        style={{ background: 'rgba(255, 107, 107, 0.1)', borderColor: 'rgba(255, 107, 107, 0.3)' }}
      >
        <Stack gap="sm">
          <Text size="sm" c="red" fw={700}>
            ⚠️ AVISO IMPORTANTE
          </Text>
          <Divider color="red.2" />
          <Text size="sm">
            Este sistema es solo para fines <strong>educativos y de entretenimiento</strong>. La
            lotería es un juego de azar y ningún sistema de predicción puede garantizar resultados.
            Juega de forma responsable.
          </Text>
        </Stack>
      </Paper>
    </Stack>
  )
}
