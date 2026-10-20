import api from './client'

// ---------------------------------------------------------------------------
// Tipos compartidos de El Gordo de la Primitiva
// ---------------------------------------------------------------------------

export interface DrawResult {
  id?: number
  date: string
  numbers: number[]
  key_number: number
  jackpot?: number
  winners?: number
  source?: string
}

export interface PredictionResult {
  prediction_date: string
  predicted_numbers: number[]
  predicted_key_number: number
  confidence: number
  model_used: string
  alternative_combinations: number[][]
  analysis?: {
    hot_numbers?: [number, number][]
    cold_numbers?: [number, number][]
    total_historical_draws?: number
    date_range?: {
      from: string
      to: string
    }
  }
}

export interface NumberStats {
  number: number
  frequency: number
  percentage: number
  last_drawn?: string
  hot: boolean
  cold: boolean
}

export interface KeyNumberStats {
  key_number: number
  frequency: number
  percentage: number
  last_drawn?: string
  hot: boolean
  cold: boolean
}

export interface StatisticsResponse {
  total_draws: number
  number_stats: NumberStats[]
  key_number_stats: KeyNumberStats[]
  most_common_combinations: number[][]
  patterns: any
  next_draw_date: string
}

export interface Combination {
  numbers: number[]
  key_number: number
  strategy: string
  confidence: number
  description: string
  risk_level: string
}

export interface WeeklyCombinationsResponse {
  draw_date: string
  combinations: Combination[]
  coverage_metrics: {
    unique_numbers_coverage: number
    avg_combination_overlap: number
    risk_distribution: Record<string, number>
    total_combinations: number
    numbers_per_combination: number
  }
  total_combinations: number
  recommendations: {
    play_strategy: string
    budget_allocation: Record<string, number>
    best_combinations: Combination[]
    warnings: string[]
  }
}

// ---------------------------------------------------------------------------
// Clientes de El Gordo
// ---------------------------------------------------------------------------

export const predictionsApi = {
  predict: async () => {
    const response = await api.post<PredictionResult>('/predictions/predict')
    return response.data
  },
  predictStatistical: async () => {
    const response = await api.post<PredictionResult>('/predictions/predict/statistical')
    return response.data
  },
  getStatus: async () => {
    const response = await api.get('/predictions/models/status')
    return response.data
  },
}

export const historyApi = {
  getRecent: async (limit = 52) => {
    const response = await api.get<DrawResult[]>(`/history/recent?limit=${limit}`)
    return response.data
  },
  getByDate: async (date: string) => {
    const response = await api.get<DrawResult>(`/history/date/${date}`)
    return response.data
  },
  getByRange: async (startDate: string, endDate?: string) => {
    const params = new URLSearchParams({
      start_date: startDate,
      ...(endDate && { end_date: endDate }),
    })
    const response = await api.get(`/history/range?${params}`)
    return response.data
  },
  refresh: async () => {
    const response = await api.get('/history/refresh')
    return response.data
  },
}

export const statsApi = {
  getGeneral: async () => {
    const response = await api.get<StatisticsResponse>('/stats/general')
    return response.data
  },
  getNumberStats: async (number: number) => {
    const response = await api.get(`/stats/number/${number}`)
    return response.data
  },
  getPatterns: async () => {
    const response = await api.get('/stats/patterns')
    return response.data
  },
}

export const combinationsApi = {
  getWeekly: async (numCombinations = 7) => {
    const response = await api.get<WeeklyCombinationsResponse>(
      `/combinations/weekly?num_combinations=${numCombinations}`,
    )
    return response.data
  },
  compare: async () => {
    const response = await api.get('/combinations/compare')
    return response.data
  },
  optimize: async (existingCombinations: number[][], keyNumbers: number[], numNew = 3) => {
    const response = await api.post('/combinations/optimize', {
      existing_combinations: existingCombinations,
      key_numbers: keyNumbers,
      num_new_combinations: numNew,
    })
    return response.data
  },
}

// ---------------------------------------------------------------------------
// Generador estadístico de El Gordo (5 números + clave)
// ---------------------------------------------------------------------------
export type GordoStrategy = 'big_prize' | 'balanced' | 'coverage' | 'statistical'

export interface GordoCombination {
  index: number
  numbers: number[]
  key_number: number
  quality: number
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
  quality_grade: string
}

export interface GordoDatasetInfo {
  total_draws: number
  date_range: { from: string; to: string }
  last_draw: {
    date: string
    numbers: number[]
    key_number?: number | null
  }
  source: string
  next_draw: string
}

export interface GordoPortfolio {
  tickets: number
  cost_eur: number
  coverage: {
    unique_numbers: number
    numbers_pct: number
    possible_numbers: number
    numbers_possible_pct: number
    total_numbers: number
    unique_pairs: number
    pairs_pct: number
    pairs_total: number
    pairs_total_pct: number
    unique_triples: number
    triples_pct: number
    triples_total: number
    triples_total_pct: number
  }
  overlap: { average: number; max: number }
  appearance: {
    max: number
    min: number
    distribution: Record<string, number>
  }
  popularity: {
    average_penalty: number
    low_popularity_tickets: number
    risk: string
    explanation: string
  }
  theoretical: {
    jackpot_probability: number
    jackpot_one_in: number
    prob_1: number
    prob_2: number
    prob_3: number
    prob_4: number
    prob_5: number
    prob_6: number
    prob_7: number
    prob_8: number
    prob_5_plus: number
    prob_4_plus: number
    prob_3_plus: number
    prob_7_plus: number
    prob_2_plus: number
    prob_any_prize: number
    prob_any_prize_one_in: number | null
    prob_reintegro: number
    prob_any_return: number
    prob_any_return_one_in: number | null
    reintegro_eur: number
    expected_reintegro_eur: number
    prob_key_match: number
    expected_matches: number
    expected_tickets_by_tier: Record<string, number>
    single_ticket: Record<string, number>
    exact: boolean
  }
  simulation: {
    simulations: number
    seed: number
    best_match_distribution: Record<string, number>
    category_distribution: Record<string, number>
    prob_any_prize: number
    prob_2_plus: number
    prob_3_plus: number
    prob_4_plus: number
    prob_5_plus: number
    prob_reintegro: number
    prob_key_match: number
    prob_any_return: number
  }
  keys: {
    digits: number[]
    distinct: number
    coverage_pct: number
    guaranteed_match: boolean
  }
}

export interface GordoNumberProfile {
  number: number
  frequency: number
  recent_frequency: number
  last_seen?: string | null
  gap_draws: number
  gap_days: number | null
  long_lift: number
  recent_lift: number
  weight: number
}

export interface GordoPair {
  numbers: number[]
  frequency: number
  lift: number
}

export interface GordoKeyProfile {
  digit: number
  frequency: number
  probability: number
  last_seen?: string | null
  gap_draws: number
}

export interface GordoStructure {
  draws_used: number
  average_sum: number
  sum_deviation: number
  average_spread: number
  odd_distribution: Record<string, number>
  low_distribution: Record<string, number>
  consecutive_distribution: Record<string, number>
  most_common_decade_pattern: {
    pattern: number[]
    labels: string[]
    count: number
  }
}

export interface GordoAnalysis {
  hot_numbers: GordoNumberProfile[]
  cold_numbers: GordoNumberProfile[]
  most_frequent_numbers: GordoNumberProfile[]
  overdue_numbers: GordoNumberProfile[]
  top_pairs: GordoPair[]
  key: GordoKeyProfile[]
  structure: GordoStructure
}

export interface GordoGenerateResponse {
  game: {
    name: string
    numbers_per_ticket: number
    max_number: number
    key_range: number[]
    draw_days: string
    ticket_price_eur: number
    prize_categories: Record<string, string>
  }
  generated_at: string
  seed: number
  strategy: GordoStrategy
  strategy_label: string
  strategy_description: string
  count: number
  dataset: GordoDatasetInfo
  combinations: GordoCombination[]
  portfolio: GordoPortfolio
  analysis: GordoAnalysis
  model: {
    type?: string
    version?: string
    candidate_count?: number
    pool_size?: number
    strategies?: Record<string, { label: string; description: string }>
  }
  recommendations: string[]
  disclaimer: string
}

export interface GordoMetaResponse {
  game: GordoGenerateResponse['game']
  dataset: GordoDatasetInfo
  strategies: Record<string, { label: string; description: string }>
  next_draw: string
}

export interface GordoStatsResponse {
  dataset: GordoDatasetInfo
  analysis: GordoAnalysis
  model: {
    type: string
    version: string
    total_combinations: number
    number_combinations: number
    ticket_odds: Record<string, number>
    prize_counts: Record<string, number>
    reintegro_plays: number
    ticket_price_eur: number
    strategies: Record<string, { label: string; description: string }>
  }
}

export interface GordoHistoryDraw {
  date: string
  numbers: number[]
  key_number?: number | null
  source?: string
}

export const gordoApi = {
  meta: async () => {
    const response = await api.get<GordoMetaResponse>('/gordo/meta')
    return response.data
  },
  stats: async () => {
    const response = await api.get<GordoStatsResponse>('/gordo/stats')
    return response.data
  },
  history: async (limit = 30) => {
    const response = await api.get<GordoHistoryDraw[]>(`/gordo/history?limit=${limit}`)
    return response.data
  },
  generate: async (count: number, strategy: GordoStrategy, seed?: number) => {
    const response = await api.post<GordoGenerateResponse>('/gordo/generate', {
      count,
      strategy,
      seed,
    })
    return response.data
  },
  refresh: async () => {
    const response = await api.get('/gordo/refresh')
    return response.data
  },
  nextDraw: async () => {
    const response = await api.get('/gordo/next-draw')
    return response.data
  },
}
