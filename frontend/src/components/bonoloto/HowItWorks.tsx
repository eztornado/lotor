import { Accordion, Alert, Badge, Group, Stack, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import type { BonolotoGenerateResponse } from '../../services/bonoloto'

export function HowItWorks({ data }: { data: BonolotoGenerateResponse }) {
  return (
    <Accordion variant="separated">
      <Accordion.Item value="como">
        <Accordion.Control>Cómo se genera la cartera</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="sm">
            <Text size="sm">
              <strong>1. Modelo de números.</strong> Se combinan frecuencia a largo plazo, frecuencia
              reciente (vida media de 45 días), retraso y afinidad de pares. El suavizado bayesiano y
              un peso máximo limitado evitan el sobreajuste: la lotería es uniforme y ningún patrón
              garantiza nada.
            </Text>
            <Text size="sm">
              <strong>2. Filtro estructural.</strong> Se puntúan suma, paridad, bajos/altos,
              distribución por décadas, consecutivos y terminaciones con las distribuciones reales
              del histórico.
            </Text>
            <Text size="sm">
              <strong>3. Anti-popularidad.</strong> Se penalizan las combinaciones que juega mucha
              gente (números ≤ 31 por fechas de nacimiento, progresiones, patrones). Es la única
              palanca real para mejorar el importe esperado de un gran premio, porque evita
              repartirlo.
            </Text>
            <Text size="sm">
              <strong>4. Optimización de cartera.</strong> Para 10 apuestas se cubren los 49 números
              con una única repetición. Para 8 o menos, se buscan apuestas disjuntas, que maximizan
              la probabilidad de al menos un premio en categorías bajas y mantienen baja la
              probabilidad de compartir categorías altas.
            </Text>
            <Text size="sm">
              <strong>5. Reintegros.</strong> Con 10 apuestas se usan los 10 dígitos posibles, de modo
              que una de ellas siempre recupera su importe.
            </Text>
            <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light">
              <Text size="sm">
                Matemáticamente, cada apuesta sigue teniendo 1 entre 13.983.816 de acertar los 6
                números. Lo que optimizamos es la cobertura y el reparto del premio, no el azar.
              </Text>
            </Alert>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>
      <Accordion.Item value="datos">
        <Accordion.Control>Datos y actualización</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="sm">
            <Text size="sm">
              El histórico se obtiene de las hojas públicas de Lotoideas (resultados oficiales de
              SELAE) y cubre desde 1988 hasta la fecha. El modelo está cacheado: si se actualiza el
              dataset, la siguiente generación usa los datos nuevos.
            </Text>
            <Group>
              <Badge variant="light">{data.dataset.total_draws.toLocaleString('es-ES')} sorteos</Badge>
              <Badge variant="light">Fuente: {data.dataset.source}</Badge>
              <Badge variant="light">Semilla: {data.seed}</Badge>
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
