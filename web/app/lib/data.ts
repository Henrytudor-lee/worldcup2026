// 直接读 JSON 文件 (server component 路径)

import { readFile } from 'fs/promises';
import { join } from 'path';
import type { Team, Match, ApiRanking, ApiPredictions, ApiWeights, Weights } from './types';

const PROJECT_ROOT = join(process.cwd(), '..');
const RANKING_PATH = join(PROJECT_ROOT, '5_算法', 'ranking_v20.json');
const PREDICTIONS_PATH = join(PROJECT_ROOT, '5_算法', 'all_104_predictions.json');
const WEIGHTS_PATH = join(PROJECT_ROOT, '5_算法', 'weights_v21.json');

/**
 * 排名 JSON 可能是:
 * - 数组: ranking_v20.json 是 [Team, ...]
 * - 对象: { ranking: [Team, ...], weights_used: ... }
 * 统一返回 {ranking, weights_used}
 */
export async function readRanking(): Promise<ApiRanking> {
  const raw = JSON.parse(await readFile(RANKING_PATH, 'utf-8'));
  if (Array.isArray(raw)) {
    return { ranking: raw as Team[], weights_used: {} as Weights };
  }
  return raw;
}

/**
 * 预测 JSON 可能是:
 * - 数组: all_104_predictions.json 是 [Match, ...]
 * - 对象: { predictions: [Match, ...], ... }
 */
export async function readPredictions(): Promise<ApiPredictions> {
  const raw = JSON.parse(await readFile(PREDICTIONS_PATH, 'utf-8'));
  if (Array.isArray(raw)) {
    return {
      predictions: raw as Match[],
      ranking: [],
      group_standings: {},
      top_8_third: [],
      round_of_32: [],
      final: { home: '', away: '', winner: '', loser: '', best_score: '' },
      third_place: { home: '', away: '', winner: '', loser: '', best_score: '' },
    };
  }
  return raw;
}

export async function readWeights(): Promise<ApiWeights> {
  const w: Weights = JSON.parse(await readFile(WEIGHTS_PATH, 'utf-8'));
  return { default: w, presets: {} };
}

// Aliases for compat with old api.ts call sites
export const fetchRanking = readRanking;
export const fetchPredictions = readPredictions;
export const fetchWeights = readWeights;
