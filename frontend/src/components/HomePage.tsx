import { Container, Title, Text, Stack, Paper, Grid, Card, Group, Button, Badge, Alert } from '@mantine/core'
import { Link } from 'react-router-dom'
import { IconBrain, IconChartBar, IconHistory, IconArrowRight, IconTarget } from '@tabler/icons-react'

export default function HomePage() {
  return (
    <Stack gap="xl">
      <div style={{ textAlign: 'center', padding: '2rem 0' }}>
        <Title order={1} c="blue.4">🎱 LoTor</Title>
        <Text size="xl" c="dimmed" mt="md">
          Sistema de Predicción con IA para El Gordo de la Primitiva
        </Text>
      </div>

      <Grid>
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Card shadow="md" padding="xl" radius="md" withBorder style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <Stack gap="md">
              <Group justify="space-between">
                <IconTarget size={48} c="white" />
                <Badge size="xl" color="white" variant="light">NUEVO</Badge>
              </Group>
              <Title order={2} c="white">🎯 Sistema de 7 Combinaciones Semanales</Title>
              <Text size="lg" c="white">
                Genera 7 combinaciones estratégicas diferentes para cada sorteo semanal. Cada combinación usa una estrategia distinta:
                ensemble ML, conservadora, equilibrada, arriesgada, patrones, aleatoria optimizada y diversificada.
              </Text>
              <Group>
                <Button
                  component={Link}
                  to="/weekly-combinations"
                  size="lg"
                  color="white"
                  variant="filled"
                  rightSection={<IconArrowRight size={20} />}
                >
                  Obtener Mis 7 Combinaciones
                </Button>
              </Group>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card shadow="sm" padding="lg" radius="md" withBorder h="100%">
            <Stack gap="md">
              <Group justify="space-between">
                <IconBrain size={32} c="blue.4" />
                <Badge color="blue" variant="light">IA/ML</Badge>
              </Group>
              <Title order={3}>Predicción Única</Title>
              <Text size="sm" c="dimmed">
                Predicción individual usando ensemble de modelos avanzados de Machine Learning.
              </Text>
              <Button component={Link} to="/prediction" rightSection={<IconArrowRight size={16} />}>
                Ver Predicción
              </Button>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card shadow="sm" padding="lg" radius="md" withBorder h="100%">
            <Stack gap="md">
              <Group justify="space-between">
                <IconChartBar size={32} c="green.4" />
                <Badge color="green" variant="light">Análisis</Badge>
              </Group>
              <Title order={3}>Estadísticas Detalladas</Title>
              <Text size="sm" c="dimmed">
                Análisis completo de frecuencias, patrones y tendencias de los sorteos históricos.
              </Text>
              <Button component={Link} to="/statistics" rightSection={<IconArrowRight size={16} />} color="green">
                Ver Estadísticas
              </Button>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card shadow="sm" padding="lg" radius="md" withBorder h="100%">
            <Stack gap="md">
              <Group justify="space-between">
                <IconHistory size={32} c="orange.4" />
                <Badge color="orange" variant="light">Datos</Badge>
              </Group>
              <Title order={3}>Historial Completo</Title>
              <Text size="sm" c="dimmed">
                Acceso a todos los sorteos históricos con filtrado por fechas y análisis de tendencias.
              </Text>
              <Button component={Link} to="/history" rightSection={<IconArrowRight size={16} />} color="orange">
                Ver Historial
              </Button>
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>

      <Paper shadow="xs" p="md" withBorder>
        <Stack gap="sm">
          <Title order={3}>🎯 Sobre El Gordo de la Primitiva</Title>
          <Text size="sm">
            • Selecciona <strong>5 números</strong> del 1 al 54
          </Text>
          <Text size="sm">
            • Elige <strong>1 número clave</strong> del 0 al 9
          </Text>
          <Text size="sm">
            • Sorteo todos los <strong>domingos</strong>
          </Text>
          <Text size="sm">
            • Premio Gordo: 5 números + número clave
          </Text>
        </Stack>
      </Paper>

      <Paper shadow="xs" p="md" withBorder style={{ background: 'rgba(255, 107, 107, 0.1)', borderColor: 'rgba(255, 107, 107, 0.3)' }}>
        <Stack gap="sm">
          <Text size="sm" c="red" fw={700}>⚠️ AVISO IMPORTANTE</Text>
          <Text size="sm">
            Este sistema es solo para fines <strong>educativos y de entretenimiento</strong>. La lotería es un juego de azar
            y ningún sistema de predicción puede garantizar resultados. Juega de forma responsable.
          </Text>
        </Stack>
      </Paper>
    </Stack>
  )
}
