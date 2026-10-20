import { Box } from '@mantine/core'
import { formatKey, formatNumber } from './format'

export function Ball({
  number,
  variant = 'number',
}: {
  number: number
  variant?: 'number' | 'key'
}) {
  const isKey = variant === 'key'
  const background = isKey
    ? 'linear-gradient(135deg, #f59f00 0%, #d9480f 100%)'
    : 'linear-gradient(135deg, #4c6ef5 0%, #7048e8 100%)'

  return (
    <Box
      aria-label={isKey ? `Clave ${number}` : `Número ${number}`}
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
        border: isKey ? '1px solid rgba(255,255,255,0.35)' : undefined,
      }}
    >
      {isKey ? formatKey(number) : formatNumber(number)}
    </Box>
  )
}

export default Ball
