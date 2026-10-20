import { Accordion, Alert, Badge, Group, Stack, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import type { GordoGenerateResponse } from '../../services/gordo'

export function HowItWorks({ data }: { data: GordoGenerateResponse }) {
  return (
    <Accordion variant="separated">
      <Accordion.Item value="como">
        <Accordion.Control>Cómo se genera la cartera de El Gordo</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="sm">
            <Text size="sm">
              <strong>1. Modelo de números (5 del 1 al 54).</strong> Se combinan frecuencia a largo
              plazo, frecuencia reciente (vida media de 45 días), retraso y afinidad de pares. El
              suavizado bayesiano y un peso máximo limitado evitan el sobreajuste: la lotería es
              uniforme y ningún patrón garantiza nada.
            </Text>
            <Text size="sm">
              <strong>2. Filtro estructural.</strong> Se puntúan suma, paridad, bajos/altos
              (1–27 / 28–54), distribución por las 6 décadas (1–9, 10–19, 20–29, 30–39, 40–49,
              50–54), consecutivos, terminaciones y amplitud con las distribuciones reales del
              histórico.
            </Text>
            <Text size="sm">
              <strong>3. Anti-popularidad.</strong> Se penalizan las combinaciones que juega mucha
              gente: números ≤ 31 por fechas de nacimiento, progresiones, patrones obvios, bloques
              consecutivos y repeticiones del sorteo anterior. Es la única palanca real para mejorar
              el importe esperado de un gran premio, porque evita repartirlo.
            </Text>
            <Text size="sm">
              <strong>4. Optimización de cartera.</strong> Las apuestas se construyen disjuntas
              (sin números repetidos). Con 10 apuestas se cubren 50 de los 54 números, 100 pares y
              100 tríos distintos. Una búsqueda local intercambia apuestas para mejorar calidad,
              cobertura y baja popularidad sin romper la disyunción.
            </Text>
            <Text size="sm">
              <strong>5. Claves y reintegro (0–9).</strong> Se asignan claves distintas,
              priorizando las de mayor probabilidad histórica. Con 10 apuestas se cubren las 10
              claves: una lleva siempre la clave ganadora y recupera 1,50 € de reintegro. El
              reintegro es compatible con los premios de las 8 categorías: si esa apuesta acierta
              además 2 o más números, se cobran ambos.
            </Text>
            <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light">
              <Text size="sm">
                Matemáticamente, cada apuesta sigue teniendo 1 entre 31.625.100 de acertar los 5
                números y la clave. Lo que optimizamos es la cobertura y el reparto del premio, no
                el azar.
              </Text>
            </Alert>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="probabilidades">
        <Accordion.Control>Probabilidades, categorías y premios</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="sm">
            <Text size="sm">
              El Gordo tiene 8 categorías: 1ª (5 + clave), 2ª (5), 3ª (4 + clave), 4ª (4), 5ª
              (3 + clave), 6ª (3), 7ª (2 + clave) y 8ª (2). Hay 31.625.100 combinaciones posibles
              (3.162.510 de números × 10 claves). Una apuesta tiene un 6,2054 % de ganar alguna de
              las 8 categorías, sobre todo por la 8ª (2 aciertos, 1 entre 19,07).
            </Text>
            <Text size="sm">
              Además, si aciertas la clave recuperas 1,50 € de reintegro, aunque no llegues a 2
              números. La probabilidad de algún retorno (premio o reintegro) es del 15,58 % por
              apuesta. Con 10 apuestas el reintegro está garantizado, porque se cubren las 10
              claves.
            </Text>
            <Text size="sm">
              Las probabilidades de la cartera se calculan por enumeración combinatoria exacta:
              se reparten los 5 números ganadores entre las apuestas disjuntas y se prueban las 10
              claves; el reintegro se calcula aparte. La simulación de{' '}
              {data.portfolio.simulation.simulations.toLocaleString('es-ES')} sorteos se incluye
              como comprobación independiente. Para apuestas disjuntas, la probabilidad de cada
              categoría depende del número de apuestas, no de qué números se elijan: el modelo
              decide qué jugar y la anti-popularidad reduce el riesgo de compartir.
            </Text>
            <Group>
              <Badge variant="light">1ª por apuesta: 1 entre 31.625.100</Badge>
              <Badge variant="light">Algún premio por apuesta: 1 entre 16,12</Badge>
              <Badge variant="light">Coste: 1,50 € por apuesta</Badge>
            </Group>
            <Text size="xs" c="dimmed">
              Los premios de las categorías altas dependen del bote y del número de acertantes; las
              categorías bajas tienen importes fijos. Comprueba siempre las bases oficiales de
              SELAE.
            </Text>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="datos">
        <Accordion.Control>Datos y actualización</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="sm">
            <Text size="sm">
              El histórico se obtiene de la hoja pública de Lotoideas (resultados oficiales de
              SELAE) y cubre el formato actual desde el 6 de febrero de 2005. El modelo está
              cacheado: si se actualiza el dataset, la siguiente generación usa los datos nuevos.
            </Text>
            <Group>
              <Badge variant="light">{data.dataset.total_draws.toLocaleString('es-ES')} sorteos</Badge>
              <Badge variant="light">Fuente: {data.dataset.source}</Badge>
              <Badge variant="light">Semilla: {data.seed}</Badge>
              <Badge variant="light">Estrategia: {data.strategy_label}</Badge>
            </Group>
            <Text size="xs" c="dimmed">
              {data.disclaimer}
            </Text>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  )
}

export default HowItWorks
