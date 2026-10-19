export const formatNumber = (value: number) => value.toString().padStart(2, '0')

export const formatOneIn = (probability: number) => {
  if (!probability || probability <= 0) return '—'
  const value = 1 / probability
  if (value >= 1_000_000) {
    return `1 entre ${(value / 1_000_000).toFixed(2).replace('.', ',')} M`
  }
  if (value >= 1_000) {
    return `1 entre ${Math.round(value).toLocaleString('es-ES')}`
  }
  return `1 entre ${value.toFixed(2).replace('.', ',')}`
}

export const formatPercent = (probability: number, decimals = 2) =>
  `${(probability * 100).toFixed(decimals).replace('.', ',')} %`

export const formatDecimal = (value: number, decimals = 2) =>
  value.toFixed(decimals).replace('.', ',')

export const formatDate = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

export const formatShortDate = (iso?: string | null) =>
  iso
    ? new Date(`${iso}T12:00:00`).toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      })
    : '—'

export const qualityColor = (grade: string) => {
  if (grade === 'alta') return 'teal'
  if (grade === 'media') return 'yellow'
  return 'orange'
}

export const popularityLabel = (value: number) => {
  if (value <= 0.12) return { label: 'Baja', color: 'teal' }
  if (value <= 0.35) return { label: 'Media', color: 'yellow' }
  return { label: 'Alta', color: 'red' }
}

export const riskColor = (risk: string) => {
  if (risk === 'bajo') return 'teal'
  if (risk === 'medio') return 'yellow'
  return 'red'
}
