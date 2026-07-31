/**
 * Tipos compartidos para múltiples loterías
 */

export enum LotteryType {
  PRIMITIVA = 'primitiva',
  NACIONAL = 'nacional',
  BONOLOTO = 'bonoloto',
  EUROMILLONES = 'euromillones',
}

export interface DrawResult {
  lottery_type: LotteryType;
  draw_date: string;
  numbers: number[];
  additional_numbers: number[];
  metadata: Record<string, any>;
}

export interface PredictionResult {
  lottery_type: LotteryType;
  prediction_date: string;
  predicted_numbers: number[];
  additional_predictions: number[];
  confidence: number;
  model_used: string;
  strategy_used: string;
  analysis: {
    hot_numbers?: number[];
    cold_numbers?: number[];
    total_historical_draws?: number;
    series_frequency?: Record<string, number>;
    [key: string]: any;
  };
  alternative_combinations: Array<{
    numbers: number[];
    serie?: number;
    fraccion?: number;
    strategy: string;
    confidence: number;
  }>;
}

export interface LotterySchedule {
  lottery_type: LotteryType;
  draw_day: string;
  draw_frequency: string;
  next_draw_date?: string;
  draw_count: number;
}

export interface LotteryInfo {
  type: LotteryType;
  name: string;
  description: string;
  draw_day: string;
  enabled: boolean;
}

export interface AllPredictionsResponse {
  timestamp: string;
  predictions: Record<string, PredictionResult>;
  total_lotteries: number;
}

export interface ComparisonResponse {
  comparison: Record<string, {
    name: LotteryType;
    next_draw: string;
    draw_day: string;
    prediction: {
      numbers: number[];
      additional: number[];
      confidence: number;
      model: string;
      strategy: string;
    };
    analysis: any;
  }>;
  total_compared: number;
}