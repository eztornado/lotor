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

export default api
