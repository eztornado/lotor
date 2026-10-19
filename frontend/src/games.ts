import type { ComponentType } from 'react'
import {
  IconBrain,
  IconChartBar,
  IconHistory,
  IconSparkles,
  IconTarget,
  IconTicket,
} from '@tabler/icons-react'

export type GameId = 'gordo' | 'bonoloto'

export interface GameNavItem {
  label: string
  path: string
  icon: ComponentType<{ size?: number | string; color?: string }>
}

export interface GameDefinition {
  id: GameId
  name: string
  shortName: string
  emoji: string
  /** Color de Mantine usado para acentos del juego. */
  color: string
  tagline: string
  description: string
  basePath: string
  nav: GameNavItem[]
}

/**
 * Registro central de juegos. Añadir un juego nuevo consiste en:
 *  1. Añadir una entrada aquí (con su `basePath` y su navegación).
 *  2. Añadir sus rutas en `App.tsx`.
 *  3. Implementar su cliente API en `services/`.
 */
export const GAMES: GameDefinition[] = [
  {
    id: 'gordo',
    name: 'El Gordo de la Primitiva',
    shortName: 'El Gordo',
    emoji: '🎯',
    color: 'blue',
    tagline: '5 números del 1 al 54 + número clave',
    description:
      'Predicciones con ensemble de Machine Learning, estadísticas detalladas, historial completo y el sistema de 7 combinaciones semanales.',
    basePath: '/gordo',
    nav: [
      { label: 'Predicción', path: '/gordo/prediction', icon: IconBrain },
      { label: 'Estadísticas', path: '/gordo/statistics', icon: IconChartBar },
      { label: 'Historial', path: '/gordo/history', icon: IconHistory },
      { label: '7 Combinaciones', path: '/gordo/weekly-combinations', icon: IconTarget },
    ],
  },
  {
    id: 'bonoloto',
    name: 'Bonoloto',
    shortName: 'Bonoloto',
    emoji: '🍀',
    color: 'grape',
    tagline: '6 números del 1 al 49 + complementario + reintegro',
    description:
      'Generador de carteras de 1 a 10 apuestas optimizadas con el histórico completo desde 1988: cobertura de números, pares y tríos, y anti-popularidad.',
    basePath: '/bonoloto',
    nav: [
      { label: 'Generador', path: '/bonoloto', icon: IconSparkles },
      { label: 'Estadísticas', path: '/bonoloto/estadisticas', icon: IconChartBar },
      { label: 'Historial', path: '/bonoloto/historial', icon: IconTicket },
    ],
  },
]

export const getGame = (id: GameId): GameDefinition =>
  GAMES.find((game) => game.id === id) as GameDefinition

export const getGameByPath = (pathname: string): GameDefinition | undefined =>
  GAMES.find(
    (game) => pathname === game.basePath || pathname.startsWith(`${game.basePath}/`),
  )

/**
 * Rutas heredadas (antes de la reestructuración) que redirigimos a su nueva
 * ubicación bajo `/gordo`.
 */
export const LEGACY_REDIRECTS: Array<{ from: string; to: string }> = [
  { from: '/prediction', to: '/gordo/prediction' },
  { from: '/statistics', to: '/gordo/statistics' },
  { from: '/history', to: '/gordo/history' },
  { from: '/weekly-combinations', to: '/gordo/weekly-combinations' },
]
