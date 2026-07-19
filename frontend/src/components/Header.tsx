import { Group, Anchor, Text, Burger, Drawer, Stack } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconHome, IconBrain, IconChartBar, IconHistory, IconTarget } from '@tabler/icons-react'
import { Link, useLocation } from 'react-router-dom'

const navigation = [
  { name: 'Inicio', href: '/', icon: IconHome },
  { name: 'Predicción', href: '/prediction', icon: IconBrain },
  { name: 'Estadísticas', href: '/statistics', icon: IconChartBar },
  { name: 'Historial', href: '/history', icon: IconHistory },
  { name: '7 Combinaciones', href: '/weekly-combinations', icon: IconTarget },
]

export default function Header() {
  const [opened, { toggle, close }] = useDisclosure()
  const location = useLocation()

  const items = navigation.map((item) => (
    <Anchor
      key={item.href}
      component={Link}
      to={item.href}
      onClick={close}
      style={{
        color: location.pathname === item.href ? '#228be6' : 'inherit',
        fontWeight: location.pathname === item.href ? 600 : 400,
      }}
    >
      <Group gap={4}>
        <item.icon size={18} />
        <span>{item.name}</span>
      </Group>
    </Anchor>
  ))

  return (
    <header style={{
      borderBottom: '1px solid #373A40',
      padding: '1rem 0',
      background: '#1A1B1E'
    }}>
      <Group justify="space-between" px="xl">
        <Group>
          <Anchor component={Link} to="/" style={{ textDecoration: 'none' }}>
            <Text size="xl" fw={700} c="blue.4">
              🎱 LoTor
            </Text>
          </Anchor>
          <Text size="sm" c="dimmed">Predicciones El Gordo de la Primitiva</Text>
        </Group>

        <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />

        <Group gap={32} visibleFrom="sm">
          {items}
        </Group>
      </Group>

      <Drawer opened={opened} onClose={close} size="sm" hiddenFrom="sm">
        <Stack gap={16}>
          {items}
        </Stack>
      </Drawer>
    </header>
  )
}
