import api from './client'

// ---------------------------------------------------------------------------
// Bonoloto
// ---------------------------------------------------------------------------
export type BonolotoStrategy = 'big_prize' | 'balanced' | 'coverage' | 'statistical'

export interface BonolotoCombination {
  index: number
  numbers: number[]
  reintegro: number
  quality: number
  quality_grade: string
  total_score: number
  popularity: number
  sum: number
  odd: number
  even: number
  low: number
  high: number
  consecutive_pairs: number
  decades: number[]
  tags: string[]
  theoretical: Record<string, number>
}

export interface BonolotoDatasetInfo {
  total_draws: number
  date_range: { from: string; to: string }
  last_draw: {
    date: string
    numbers: number[]
    complementario?: number | null
    reintegro?: number | null
  }
  source: string
  next_draw: string
}

export interface BonolotoPortfolio {
  tickets: number
  cost_eur: number
  coverage: {
    unique_numbers: number
    numbers_pct: number
    total_numbers: number
    unique_pairs: number
    pairs_pct: number
    unique_triples: number
    triples_pct: number
  }
  overlap: { average: number; max: number }
  appearance: { max: number; min: number; distribution: Record<string, number> }
  popularity: {
    average_penalty: number
    low_popularity_tickets: number
    risk: string
    explanation: string
  }
  theoretical: {
    jackpot_probability: number
    jackpot_one_in: number
    prob_6: number
    prob_5_plus: number
    prob_5_plus_complementario: number
    prob_5: number
    prob_4_plus: number
    prob_3_plus: number
    prob_any_main_prize: number
    prob_reintegro: number
    prob_any_prize: number
    expected_matches: number
    expected_tickets_by_tier: Record<string, number>
    single_ticket: Record<string, number>
  }
  simulation: {
    simulations: number
    seed: number
    best_match_distribution: Record<string, number>
    prob_3_plus: number
    prob_4_plus: number
    prob_5_plus: number
  }
  reintegros: {
    digits: number[]
    distinct: number
    coverage_pct: number
    guaranteed_match: boolean
  }
}

export interface BonolotoNumberProfile {
  number: number
  frequency: number
  recent_frequency: number
  last_seen?: string | null
  gap_draws: number
  gap_days: number
  long_lift: number
  recent_lift: number
  weight: number
}

export interface BonolotoPair {
  numbers: number[]
  frequency: number
  lift: number
}

export interface BonolotoReintegroProfile {
  digit: number
  frequency: number
  probability: number
  last_seen?: string | null
  gap_draws: number
}

export interface BonolotoStructure {
  draws_used: number
  average_sum: number
  sum_deviation: number
  average_spread: number
  odd_distribution: Record<string, number>
  low_distribution: Record<string, number>
  consecutive_distribution: Record<string, number>
  most_common_decade_pattern: { pattern: number[]; labels: string[]; count: number }
}

export interface BonolotoAnalysis {
  hot_numbers: BonolotoNumberProfile[]
  cold_numbers: BonolotoNumberProfile[]
  most_frequent_numbers: BonolotoNumberProfile[]
  overdue_numbers: BonolotoNumberProfile[]
  top_pairs: BonolotoPair[]
  reintegro: BonolotoReintegroProfile[]
  structure: BonolotoStructure
}

export interface BonolotoGenerateResponse {
  game: {
    name: string
    numbers_per_ticket: number
    max_number: number
    reintegro_range: number[]
    draw_days: string
    ticket_price_eur: number
    prize_categories: Record<string, string>
  }
  generated_at: string
  seed: number
  strategy: BonolotoStrategy
  strategy_label: string
  strategy_description: string
  count: number
  dataset: BonolotoDatasetInfo
  combinations: BonolotoCombination[]
  portfolio: BonolotoPortfolio
  analysis: BonolotoAnalysis
  model: {
    type?: string
    version?: string
    strategies?: Record<string, { label: string; description: string }>
  }
  recommendations: string[]
  disclaimer: string
}

export interface BonolotoMetaResponse {
  game: BonolotoGenerateResponse['game']
  dataset: BonolotoDatasetInfo
  strategies: Record<string, { label: string; description: string }>
  next_draw: string
}

export interface BonolotoStatsResponse {
  dataset: BonolotoDatasetInfo
  analysis: BonolotoAnalysis
  model: {
    type: string
    version: string
    ticket_odds: Record<string, number>
    strategies: Record<string, { label: string; description: string }>
  }
}

export interface BonolotoHistoryDraw {
  date: string
  numbers: number[]
  complementario?: number | null
  reintegro?: number | null
  source?: string
}

export const bonolotoApi = {
  meta: async () => {
    const response = await api.get<BonolotoMetaResponse>('/bonoloto/meta')
    return response.data
  },
  stats: async () => {
    const response = await api.get<BonolotoStatsResponse>('/bonoloto/stats')
    return response.data
  },
  history: async (limit = 30) => {
    const response = await api.get<BonolotoHistoryDraw[]>(`/bonoloto/history?limit=${limit}`)
    return response.data
  },
  generate: async (count: number, strategy: BonolotoStrategy, seed?: number) => {
    const response = await api.post<BonolotoGenerateResponse>('/bonoloto/generate', {
      count,
      strategy,
      seed,
    })
    return response.data
  },
  refresh: async () => {
    const response = await api.get('/bonoloto/refresh')
    return response.data
  },
}
