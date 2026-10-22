import api from './client'

// ---------------------------------------------------------------------------
// La Quiniela
// ---------------------------------------------------------------------------
export type QuinielaMode = 'multiple' | 'simple'
export type QuinielaStrategy = 'balanced' | 'coverage' | 'max_probability' | 'jackpot'

export interface QuinielaGameInfo {
  name: string
  matches: number
  sign_matches: number
  pleno_match: number
  ticket_price_eur: number
  max_doubles: number
  max_triples: number
  prize_categories: Record<string, string>
}

export interface QuinielaJornada {
  season: string
  jornada: number
  label: string
  start_date: string
  matches: number
  competition: string
  competitions?: string[]
}

export interface QuinielaTeamInfo {
  name: string
  known: boolean
  league?: string
  league_name?: string
  matches: number
  elo: number | null
  attack: number | null
  defense: number | null
  goals_for: number | null
  goals_against: number | null
  form: string[]
  last_match: string | null
}

export interface QuinielaScoreOption {
  score: string
  probability: number
}

export interface QuinielaH2H {
  matches: number
  home_wins: number
  draws: number
  away_wins: number
  results: Array<{ date: string; score: string; home: string; away: string }>
}

export interface QuinielaMatch {
  match_number: number
  home_team: string
  away_team: string
  home: QuinielaTeamInfo
  away: QuinielaTeamInfo
  competition: string
  kickoff: string
  is_pleno: boolean
  is_women: boolean
  probabilities: Record<'1' | 'X' | '2', number>
  fair_odds: Record<'1' | 'X' | '2', number>
  expected_goals: { home: number; away: number }
  most_likely_score: string
  score_probability: number
  score_options: QuinielaScoreOption[]
  confidence: number
  data_quality: string
  h2h: QuinielaH2H
  notes: string[]
  pick: '1' | 'X' | '2'
  edge: number
  entropy: number
}

export interface QuinielaSign {
  match_number: number
  signs: string[]
  pick: string
  coverage: number
}

export interface QuinielaPrizeEstimate {
  probability_any_prize: number
  expected_return: { low: number; average: number; high: number }
  cost: number
  roi: { low: number; average: number; high: number }
  by_category: Record<string, { probability: number; average_prize: number }>
  note: string
}

export interface QuinielaTicket {
  index: number
  signs: QuinielaSign[]
  pleno: { score: string; probability: number }
  columns: number
  cost: number
  doubles: number
  triples: number
  expected_hits: number
  expected_total_hits: number
  guaranteed_hits: number
  hits_14_distribution: number[]
  hit_distribution: number[]
  category_probabilities: Record<string, number>
  prize_estimate: QuinielaPrizeEstimate
  coverage: number[]
  expanded_columns: Array<{ signs: string[]; pleno: string }> | null
  expanded_note: string | null
}

export interface QuinielaPortfolio {
  tickets: number
  columns: number
  cost: number
  expected_best_hits: number
  expected_total_hits: number
  guaranteed_hits: number
  hits_14_distribution: number[]
  hit_distribution: number[]
  category_probabilities: Record<string, number>
  prize_estimate: QuinielaPrizeEstimate
  coverage: string[][]
  method: string
  simulations: number
}

export interface QuinielaAnalysis {
  most_confident: Array<{
    match_number: number
    match: string
    pick: string
    probability: number
  }>
  most_uncertain: Array<{
    match_number: number
    match: string
    pick: string
    probability: number
  }>
  average_confidence: number
  data_quality: Record<string, number>
  pleno: {
    score: string
    probability: number
    alternatives: QuinielaScoreOption[]
  }
}

export interface QuinielaGenerateResponse {
  game: QuinielaGameInfo
  generated_at: string
  seed: number
  mode: QuinielaMode
  strategy: QuinielaStrategy
  strategy_label: string
  strategy_description: string
  jornada: QuinielaJornada
  budget: {
    requested: number
    max_doubles: number
    max_triples: number
    max_columns: number
    max_cost: number
    ticket_price: number
  }
  matches: QuinielaMatch[]
  tickets: QuinielaTicket[]
  portfolio: QuinielaPortfolio
  analysis: QuinielaAnalysis
  recommendations: string[]
  disclaimer: string
}

export interface QuinielaMetaResponse {
  game: QuinielaGameInfo
  dataset: {
    total_matches: number
    date_range: { from: string; to: string } | null
    total_teams: number
    total_jornadas: number
    next_jornada: {
      season: string
      jornada: number
      start_date: string
      matches: number
      competition: string
      competitions?: string[]
    } | null
    leagues: Array<{ code: string; name: string; matches: number }>
  }
  strategies: Record<string, { label: string; description: string }>
  next_jornada: QuinielaMetaResponse['dataset']['next_jornada']
}

export interface QuinielaStatsResponse {
  dataset: {
    total_matches: number
    date_range: { from: string; to: string }
    teams: number
    leagues: number
    reference_date: string
    home_advantage: number
    half_life_days: number
  }
  model: {
    type: string
    version: string
    config: Record<string, number>
    strategies: Record<string, { label: string; description: string }>
    home_advantage: number
    global_base: Record<string, number>
    next_jornada: QuinielaMetaResponse['dataset']['next_jornada']
    explanation: string
  }
  leagues: Array<{
    league: string
    name: string
    matches: number
    average_goals: number
    home_win_pct: number
    draw_pct: number
    away_win_pct: number
    over_2_5_pct: number
    btts_pct: number
  }>
  top_teams: Array<{
    team: string
    league: string
    league_name: string
    elo: number
    matches: number
    attack: number
    defense: number
    goals_for: number
    goals_against: number
  }>
  backtest: {
    matches?: number
    train_matches?: number
    cutoff?: string
    accuracy?: number
    baseline_accuracy?: number
    log_loss?: number
    baseline_log_loss?: number
    brier_score?: number
    calibration?: Array<{
      min_confidence: number
      matches: number
      accuracy: number | null
      average_confidence: number | null
    }>
    error?: string
  }
}

export interface QuinielaHistoryMatch {
  date: string
  league: string
  league_name: string
  home_team: string
  away_team: string
  home_goals: number
  away_goals: number
  result: string
  odds: { home: number | null; draw: number | null; away: number | null }
}

export interface QuinielaTeamResponse {
  team: QuinielaTeamInfo
  recent: Array<{
    date: string
    home: string
    away: string
    score: string
    result: string
  }>
}

export interface QuinielaGenerateParams {
  jornada?: number
  season?: string
  mode: QuinielaMode
  budget: number
  max_doubles: number
  max_triples: number
  count: number
  strategy: QuinielaStrategy
  seed?: number
}

export const quinielaApi = {
  meta: async () => {
    const response = await api.get<QuinielaMetaResponse>('/quiniela/meta')
    return response.data
  },
  jornadas: async () => {
    const response = await api.get<QuinielaJornada[]>('/quiniela/jornadas')
    return response.data
  },
  jornada: async (jornada?: number, season?: string) => {
    const params = new URLSearchParams()
    if (jornada != null) params.set('jornada', String(jornada))
    if (season) params.set('season', season)
    const response = await api.get(`/quiniela/jornada?${params.toString()}`)
    return response.data
  },
  generate: async (params: QuinielaGenerateParams) => {
    const response = await api.post<QuinielaGenerateResponse>('/quiniela/generate', params)
    return response.data
  },
  stats: async () => {
    const response = await api.get<QuinielaStatsResponse>('/quiniela/stats')
    return response.data
  },
  history: async (limit = 50) => {
    const response = await api.get<QuinielaHistoryMatch[]>(`/quiniela/history?limit=${limit}`)
    return response.data
  },
  team: async (name: string) => {
    const response = await api.get<QuinielaTeamResponse>(`/quiniela/teams/${encodeURIComponent(name)}`)
    return response.data
  },
  refresh: async (scope: 'fixtures' | 'matches' | 'all' = 'fixtures') => {
    const response = await api.get(`/quiniela/refresh?scope=${scope}`)
    return response.data
  },
}
