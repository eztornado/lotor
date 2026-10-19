import {
  Anchor,
  Burger,
  Divider,
  Drawer,
  Group,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { Link, useLocation } from 'react-router-dom'
import { GAMES, getGameByPath, type GameDefinition } from '../../games'

function GameTab({ game, active }: { game: GameDefinition; active: boolean }) {
  return (
    <UnstyledButton
      component={Link}
      to={game.basePath}
      style={{
        padding: '6px 14px',
        borderRadius: 999,
        border: `1px solid ${active ? 'var(--mantine-color-gray-6)' : 'transparent'}`,
        background: active
          ? `var(--mantine-color-${game.color}-9)`
          : 'transparent',
      }}
    >
      <Group gap={6}>
        <span>{game.emoji}</span>
        <Text size="sm" fw={active ? 700 : 500} c={active ? `${game.color}.2` : 'dimmed'}>
          {game.shortName}
        </Text>
      </Group>
    </UnstyledButton>
  )
}

export default function Header() {
  const [opened, { toggle, close }] = useDisclosure()
  const location = useLocation()
  const activeGame = getGameByPath(location.pathname)

  return (
    <header
      style={{
        borderBottom: '1px solid #373A40',
        padding: '1rem 0',
        background: '#1A1B1E',
      }}
    >
      <Group justify="space-between" px="xl" wrap="nowrap">
        <Group gap="md">
          <Anchor component={Link} to="/" style={{ textDecoration: 'none' }}>
            <Text size="xl" fw={700} c="blue.4">
              🎱 LoTor
            </Text>
          </Anchor>
          <Text size="sm" c="dimmed" visibleFrom="md">
            Predicciones y generación para tus loterías
          </Text>
        </Group>

        <Group gap="xs" visibleFrom="sm">
          {GAMES.map((game) => (
            <GameTab key={game.id} game={game} active={activeGame?.id === game.id} />
          ))}
        </Group>

        <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
      </Group>

      {activeGame && (
        <Group gap="xl" px="xl" mt="md" visibleFrom="sm">
          {activeGame.nav.map((item) => {
            const active = location.pathname === item.path
            return (
              <Anchor
                key={item.path}
                component={Link}
                to={item.path}
                style={{
                  color: active ? `var(--mantine-color-${activeGame.color}-4)` : 'inherit',
                  fontWeight: active ? 600 : 400,
                }}
              >
                <Group gap={4}>
                  <item.icon size={18} />
                  <span>{item.label}</span>
                </Group>
              </Anchor>
            )
          })}
        </Group>
      )}

      <Drawer opened={opened} onClose={close} size="sm" hiddenFrom="sm" title="LoTor">
        <Stack gap="md">
          {GAMES.map((game) => (
            <Stack key={game.id} gap="xs">
              <Text fw={700}>
                {game.emoji} {game.shortName}
              </Text>
              {game.nav.map((item) => (
                <Anchor key={item.path} component={Link} to={item.path} onClick={close}>
                  <Group gap={6}>
                    <item.icon size={16} />
                    <span>{item.label}</span>
                  </Group>
                </Anchor>
              ))}
              <Divider />
            </Stack>
          ))}
        </Stack>
      </Drawer>
    </header>
  )
}
