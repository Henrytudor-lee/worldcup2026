// 数据类型定义 - 与 backend FastAPI / 5_算法/*.json 保持一致

export interface Team {
  team: string;
  rank: number;
  fifa_rank: number;
  fw_score: number;
  mid_score: number;
  def_score: number;
  gk_score: number;
  player_score: number;
  player_r: number;
  coach_score: number;
  coach_r: number;
  total: number;
  rank_r: number;
  coach_name: string;
  coach_age: string;
  coach_honors: string;
  fw_top_names: string[];
  mid_top_names: string[];
  def_top_names: string[];
  gk_top_name: string;
}

export interface Match {
  home: string;
  away: string;
  match_id: string;
  round: string;
  stage: 'group' | 'R32' | 'R16' | 'QF' | 'SF' | 'FINAL' | '3RD';
  group?: string;
  date: string;
  stadium?: string;
  city?: string;
  roof?: string;
  lambda_home: number;
  lambda_away: number;
  p_home_win: number;
  p_draw: number;
  p_away_win: number;
  best_score: string;
  best_score_prob: number;
  expected_total: number;
  expected_diff: number;
  actual_score?: string | null;
  home_pts?: number | null;
  away_pts?: number | null;
  winner?: string | null;
  loser?: string | null;
  went_to_pen?: boolean;
  data_status?: 'real' | 'pending';
}

export interface Weights {
  position_top_n: Record<string, number>;
  status_weights: Record<string, number>;
  nat_intl: Record<string, number>;
  def_gk_weights: Record<string, number>;
  player_to_total: Record<string, number>;
  smoothing: Record<string, number>;
  [key: string]: unknown;
}

export interface Preset {
  name: string;
  description: string;
  weights: Weights;
}

export interface Player {
  球员: string;
  国家: string;
  位置: string;
  俱乐部: string;
  联赛: string;
  身价: string;
  age: string;
  国家队进球: string;
  国家队助攻: string;
  号码: string;
  主力: string;
  [key: string]: string | undefined;
}

export interface ApiRanking {
  ranking: Team[];
  weights_used: Weights;
}

export interface ApiPredictions {
  predictions: Match[];
  ranking: Team[];
  group_standings: Record<string, Array<[string, number, number, number, number]>>;
  top_8_third: Array<[string, string, number, number, number, number]>;
  round_of_32: Array<[string, string]>;
  final: {
    home: string;
    away: string;
    winner: string;
    loser: string;
    best_score: string;
    [key: string]: unknown;
  };
  third_place: {
    home: string;
    away: string;
    winner: string;
    loser: string;
    best_score: string;
    [key: string]: unknown;
  };
}

export interface ApiWeights {
  default: Weights;
  presets: Record<string, Preset>;
}
