// API 客户端 - FastAPI (8766) + JSON fallback

import type { ApiRanking, ApiPredictions, ApiWeights } from './types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8766';
const USE_FALLBACK = process.env.NEXT_PUBLIC_DATA_SOURCE === 'static';

// 国旗 emoji 映射
export const FLAGS: Record<string, string> = {
  '韩国': '🇰🇷', '南非': '🇿🇦', '墨西哥': '🇲🇽', '加拿大': '🇨🇦',
  '巴西': '🇧🇷', '日本': '🇯🇵', '德国': '🇩🇪', '巴拉圭': '🇵🇾',
  '荷兰': '🇳🇱', '摩洛哥': '🇲🇦', '科特迪瓦': '🇨🇮', '挪威': '🇳🇴',
  '法国': '🇫🇷', '瑞典': '🇸🇪', '厄瓜多尔': '🇪🇨', '民主刚果': '🇨🇩',
  '比利时': '🇧🇪', '塞内加尔': '🇸🇳', '美国': '🇺🇸', '波黑': '🇧🇦',
  '西班牙': '🇪🇸', '奥地利': '🇦🇹', '葡萄牙': '🇵🇹', '克罗地亚': '🇭🇷',
  '瑞士': '🇨🇭', '阿尔及利亚': '🇩🇿', '澳大利亚': '🇦🇺', '埃及': '🇪🇬',
  '阿根廷': '🇦🇷', '佛得角': '🇨🇻', '哥伦比亚': '🇨🇴', '加纳': '🇬🇭',
  '英格兰': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', '捷克': '🇨🇿', '苏格兰': '🏴󠁧󠁢󠁳󠁣󠁴󠁿', '瑞士 ': '🇨🇭',
  '波黑 ': '🇧🇦', '卡塔尔': '🇶🇦', '海地': '🇭🇹', '土耳其': '🇹🇷',
  '伊朗': '🇮🇷', '新西兰': '🇳🇿', '沙特': '🇸🇦', '乌拉圭': '🇺🇾',
  '意大利': '🇮🇹', '波兰': '🇵🇱', '乌克兰': '🇺🇦', '威尔士': '🏴󠁧󠁢󠁷󠁬󠁳󠁿',
  '丹麦': '🇩🇰', '塞尔维亚': '🇷🇸', '罗马尼亚': '🇷🇴', '波兰 ': '🇵🇱',
  '约旦': '🇯🇴', '伊拉克': '🇮🇶', '乌兹别克斯坦': '🇺🇿', '巴拿马': '🇵🇦',
};

export function flag(team: string): string {
  return FLAGS[team] || '🏳️';
}

// 把 5_算法/*.json 加载进来作为 fallback
async function loadStatic<T>(name: string): Promise<T> {
  const url = `/static-data/${name}`;
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`Failed to load ${name}: ${r.status}`);
  return r.json();
}

async function getFastAPI<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
  const qs = params
    ? '?' + new URLSearchParams(params).toString()
    : '';
  const url = `${BACKEND_URL}${endpoint}${qs}`;
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`Backend ${endpoint} ${r.status}`);
  return r.json();
}

export async function fetchRanking(): Promise<ApiRanking> {
  if (USE_FALLBACK) {
    return loadStatic<ApiRanking>('ranking.json');
  }
  try {
    return await getFastAPI<ApiRanking>('/api/ranking', { weights: 'default' });
  } catch (e) {
    console.warn('FastAPI ranking failed, using static fallback:', e);
    return loadStatic<ApiRanking>('ranking.json');
  }
}

export async function fetchPredictions(): Promise<ApiPredictions> {
  if (USE_FALLBACK) {
    return loadStatic<ApiPredictions>('predictions.json');
  }
  try {
    return await getFastAPI<ApiPredictions>('/api/predictions', { weights: 'default' });
  } catch (e) {
    console.warn('FastAPI predictions failed, using static fallback:', e);
    return loadStatic<ApiPredictions>('predictions.json');
  }
}

export async function fetchWeights(): Promise<ApiWeights> {
  if (USE_FALLBACK) {
    return loadStatic<ApiWeights>('weights.json');
  }
  try {
    const [d, p] = await Promise.all([
      getFastAPI<WeightsType>('/api/weights/default'),
      getFastAPI<Record<string, PresetType>>('/api/weights/presets'),
    ]);
    return { default: d, presets: p };
  } catch (e) {
    console.warn('FastAPI weights failed, using static fallback:', e);
    return loadStatic<ApiWeights>('weights.json');
  }
}

// 类型辅助（避免循环引用）
type WeightsType = ApiWeights['default'];
type PresetType = ApiWeights['presets'][string];
