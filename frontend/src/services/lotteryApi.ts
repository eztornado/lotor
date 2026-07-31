/**
 * API service para loterías multi-tipo
 */

import axios from 'axios';
import {
  LotteryType,
  PredictionResult,
  LotterySchedule,
  LotteryInfo,
  AllPredictionsResponse,
  ComparisonResponse,
} from '../types/lottery';

const API_BASE = '/api/v2';

export const lotteryApi = {
  /**
   * Obtener lista de loterías soportadas
   */
  async getSupportedLotteries(): Promise<LotteryInfo[]> {
    const response = await axios.get(`${API_BASE}/lotteries`);
    return response.data;
  },

  /**
   * Obtener horario de sorteos para una lotería
   */
  async getSchedule(lotteryType: LotteryType): Promise<LotterySchedule> {
    const response = await axios.get(`${API_BASE}/lotteries/${lotteryType}/schedule`);
    return response.data;
  },

  /**
   * Obtener predicción para una lotería específica
   */
  async predict(lotteryType: LotteryType, count: number = 200): Promise<PredictionResult> {
    const response = await axios.post(`${API_BASE}/lotteries/${lotteryType}/predict`, null, {
      params: { count }
    });
    return response.data;
  },

  /**
   * Obtener historial de sorteos para una lotería
   */
  async getHistory(
    lotteryType: LotteryType,
    count: number = 50,
    offset: number = 0
  ): Promise<{
    lottery_type: LotteryType;
    total: number;
    count: number;
    offset: number;
    draws: Array<{
      draw_date: string;
      numbers: number[];
      additional_numbers: number[];
      metadata: Record<string, any>;
    }>;
  }> {
    const response = await axios.get(`${API_BASE}/lotteries/${lotteryType}/history`, {
      params: { count, offset }
    });
    return response.data;
  },

  /**
   * Obtener predicciones para todas las loterías
   */
  async getAllPredictions(count: number = 200): Promise<AllPredictionsResponse> {
    const response = await axios.post(`${API_BASE}/predictions/all`, null, {
      params: { count }
    });
    return response.data;
  },

  /**
   * Comparar predicciones entre loterías
   */
  async comparePredictions(count: number = 200): Promise<ComparisonResponse> {
    const response = await axios.get(`${API_BASE}/predictions/comparison`, {
      params: { count }
    });
    return response.data;
  },

  /**
   * Health check de loterías
   */
  async healthCheck(): Promise<{
    overall_status: string;
    lotteries: Record<string, {
      status: string;
      model_trained?: boolean;
      available_draws?: number;
      error?: string;
    }>;
  }> {
    const response = await axios.get(`${API_BASE}/health/lotteries`);
    return response.data;
  }
};