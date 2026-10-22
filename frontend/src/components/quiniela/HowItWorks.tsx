import { Alert, List, Paper, SimpleGrid, Stack, Text, Title } from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'

export function HowItWorks() {
  return (
    <Paper shadow="sm" p="lg" withBorder>
      <Stack gap="lg">
        <Stack gap={2}>
          <Title order={3}>Cómo se calcula</Title>
          <Text size="sm" c="dimmed">
            Un modelo estadístico de fútbol, no una frecuencia de lotería. Cada partido tiene
            su propia distribución de resultados y el boleto se optimiza sobre ella.
          </Text>
        </Stack>

        <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">
          <Stack gap="xs">
            <Title order={5}>1. Fuerza de los equipos</Title>
            <Text size="sm">
              Poisson Dixon-Coles con pesos temporales estima ataque, defensa y ventaja de
              campo. Los partidos recientes pesan más y los equipos con pocos datos se
              contraen hacia la media de su liga.
            </Text>
          </Stack>
          <Stack gap="xs">
            <Title order={5}>2. Elo y competición</Title>
            <Text size="sm">
              Un Elo con diferencia de goles mezcla equipos de ligas distintas. En Copa y
              competiciones europeas los equipos sin histórico reciben el nivel de su
              competición, con confianza explícitamente baja.
            </Text>
          </Stack>
          <Stack gap="xs">
            <Title order={5}>3. Múltiples exactos</Title>
            <Text size="sm">
              Si un partido lleva doble o triple, la probabilidad de acertarlo es la suma de
              los signos marcados. El número total de aciertos sigue una distribución
              Poisson-binomial que se calcula con programación dinámica, sin simulaciones.
            </Text>
          </Stack>
        </SimpleGrid>

        <Stack gap="xs">
          <Title order={5}>Qué significa el resultado</Title>
          <List size="sm" spacing={4}>
            <List.Item>
              <strong>Aciertos esperados:</strong> media de partidos acertados sobre 14. El
              pleno al 15 se calcula aparte.
            </List.Item>
            <List.Item>
              <strong>Cobertura:</strong> probabilidad de que el boleto acierte ese partido,
              sumando los signos marcados.
            </List.Item>
            <List.Item>
              <strong>Probabilidad de premio:</strong> probabilidad de 10 o más aciertos. Los
              premios son de reparto y dependen de los acertantes de cada jornada.
            </List.Item>
          </List>
        </Stack>

        <Alert icon={<IconAlertTriangle size={16} />} color="red" variant="light">
          <Text size="sm">
            <strong>Aviso:</strong> ningún modelo puede predecir el fútbol con certeza. Las
            probabilidades son estimaciones calibradas, no garantías. Juega solo dinero que
            puedas permitirte perder y hazlo de forma responsable.
          </Text>
        </Alert>
      </Stack>
    </Paper>
  )
}
