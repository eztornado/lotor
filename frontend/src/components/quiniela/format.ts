export const signColor = (sign: string): string => {
  if (sign === '1') return 'teal'
  if (sign === 'X') return 'orange'
  return 'blue'
}

export const signLabel = (sign: string): string => {
  if (sign === '1') return 'Local'
  if (sign === 'X') return 'Empate'
  return 'Visitante'
}

export const qualityColor = (quality: string): string => {
  if (quality === 'alta') return 'teal'
  if (quality === 'media') return 'orange'
  if (quality === 'baja') return 'yellow'
  return 'gray'
}

export const resultColor = (result: string): string => {
  if (result === 'H') return 'teal'
  if (result === 'D') return 'orange'
  return 'blue'
}

export const resultLabel = (result: string): string => {
  if (result === 'H') return '1'
  if (result === 'D') return 'X'
  return '2'
}

/** Forma de un equipo: H = victoria, D = empate, A = derrota. */
export const formLabel = (value: string): string => {
  if (value === 'H') return 'G'
  if (value === 'D') return 'E'
  return 'P'
}

export const formColor = (value: string): string => {
  if (value === 'H') return 'teal'
  if (value === 'D') return 'orange'
  return 'red'
}

/** Color para resultados ya expresados como G (ganado), E (empatado), P (perdido). */
export const outcomeColor = (value: string): string => {
  if (value === 'G') return 'teal'
  if (value === 'E') return 'orange'
  return 'red'
}

export const formatPercent = (value: number, digits = 1): string =>
  `${(value * 100).toLocaleString('es-ES', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })} %`

export const formatCurrency = (value: number, digits = 2): string =>
  `${value.toLocaleString('es-ES', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })} €`

export const formatNumber = (value: number, digits = 2): string =>
  value.toLocaleString('es-ES', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })

export const formatShortDate = (value?: string | null): string => {
  if (!value) return '—'
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export const formatDateTime = (value?: string | null): string => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
