import { fetchPredictions } from '../lib/data';
import { BracketClient } from './BracketClient';
import type { Match } from '../lib/types';

export const dynamic = 'force-dynamic';

type Stage = 'R32' | 'R16' | 'QF' | 'SF' | 'FINAL' | '3RD';

export default async function BracketPage() {
  let koMatches: Match[] = [];
  try {
    const data = await fetchPredictions();
    koMatches = data.predictions.filter((m) => m.stage !== 'group');
  } catch (e) {
    console.error('Failed to load predictions:', e);
  }

  // 把数据序列化成 plain object（Server → Client Component 边界）
  const safe = koMatches.map((m) => ({
    match_id: m.match_id,
    round: m.round,
    stage: m.stage as Stage,
    home: m.home,
    away: m.away,
    date: m.date,
    city: m.city,
    stadium: m.stadium,
    best_score: m.best_score,
    p_home_win: m.p_home_win,
    p_away_win: m.p_away_win,
    p_draw: m.p_draw,
    winner: m.winner ?? null,
    loser: m.loser ?? null,
    actual_score: m.actual_score ?? null,
    went_to_pen: m.went_to_pen ?? false,
    data_status: m.data_status ?? 'pending',
  }));

  return <BracketClient initialMatches={safe} />;
}
