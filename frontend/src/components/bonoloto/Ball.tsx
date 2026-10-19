import { Box } from '@mantine/core'
import { formatNumber } from './format'

export function Ball({
  number,
  variant = 'number',
}: {
  number: number
  variant?: 'number' | 'reintegro'
}) {
  const background =
    variant === 'reintegro'
      ? 'linear-gradient(135deg, #f06a9d 0%, #c026d3 100%)'
      : 'linear-gradient(135deg, #4c6ef5 0%, #7048e8 100%)'
  return (
    <Box
      style={{
        background,
        color: 'white',
        minWidth: 42,
        height: 42,
        padding: '0 8px',
        borderRadius: 10,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontSize: '1rem',
        boxShadow: '0 2px 6px rgba(0,0,0,0.25)',
      }}
    >
      {formatNumber(number)}
    </Box>
  )
}

export default Ball
