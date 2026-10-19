import axios from 'axios'

const API_BASE_URL = '/api/v1'

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

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Predictions
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

// History
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

// Statistics
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

// Multi Combinations
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

export const combinationsApi = {
  getWeekly: async (numCombinations = 7) => {
    const response = await api.get<WeeklyCombinationsResponse>(`/combinations/weekly?num_combinations=${numCombinations}`)
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
      num_new_combinations: numNew
    })
    return response.data
  },
}

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
  analysis: any
  model: any
  recommendations: string[]
  disclaimer: string
}

export interface BonolotoMetaResponse {
  game: BonolotoGenerateResponse['game']
  dataset: any
  strategies: Record<string, { label: string; description: string }>
  next_draw: string
}

export const bonolotoApi = {
  meta: async () => {
    const response = await api.get<BonolotoMetaResponse>('/bonoloto/meta')
    return response.data
  },
  stats: async () => {
    const response = await api.get('/bonoloto/stats')
    return response.data
  },
  history: async (limit = 30) => {
    const response = await api.get(`/bonoloto/history?limit=${limit}`)
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

export default api
