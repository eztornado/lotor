import { Group, List, Paper, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconTicket } from '@tabler/icons-react'

export function RecommendationsPanel({ recommendations }: { recommendations: string[] }) {
  return (
    <Paper shadow="sm" p="md" withBorder>
      <Stack gap="sm">
        <Group gap="xs">
          <ThemeIcon size="lg" variant="light" color="grape">
            <IconTicket size={18} />
          </ThemeIcon>
          <Title order={4}>Recomendaciones</Title>
        </Group>
        <List spacing="xs" size="sm">
          {recommendations.map((recommendation) => (
            <List.Item key={recommendation}>
              <Text size="sm">{recommendation}</Text>
            </List.Item>
          ))}
        </List>
      </Stack>
    </Paper>
  )
}

export default RecommendationsPanel
