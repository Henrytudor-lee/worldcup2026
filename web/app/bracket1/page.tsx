import { readFile } from 'fs/promises';
import { join } from 'path';
import { BracketClient, type BracketMatch, type GroupStanding } from './BracketClient';

export const dynamic = 'force-dynamic';

type Stage = 'R16' | 'QF' | 'SF' | 'FINAL' | '3RD';

const PROJECT_ROOT = join(process.cwd(), '..');
const PREDICTIONS_PATH = join(PROJECT_ROOT, '5_算法', 'all_104_predictions.json');

export default async function BracketPage() {
  let koMatches: BracketMatch[] = [];
  let groupStandings: GroupStanding[] = [];
  let roundOf16Order: Array<[string, string]> = [];

  try {
    const raw = JSON.parse(await readFile(PREDICTIONS_PATH, 'utf-8'));
    const all: any[] = Array.isArray(raw) ? raw : raw.predictions || [];

    // KO 比赛
    koMatches = all
      .filter((m) => m.stage !== 'group')
      .map((m) => ({
        match_id: m.match_id,
        round: m.round,
        stage: m.stage as Stage,
        home: m.home,
        away: m.away,
        date: m.date ?? '',
        city: m.city ?? '',
        stadium: m.stadium ?? '',
        best_score: m.best_score ?? '',
        p_home_win: m.p_home_win ?? 0,
        p_away_win: m.p_away_win ?? 0,
        p_draw: m.p_draw ?? 0,
        winner: m.winner ?? null,
        loser: m.loser ?? null,
        actual_score: m.actual_score ?? null,
        went_to_pen: m.went_to_pen ?? false,
        data_status: m.data_status ?? 'pending',
      }));

    // 12 小组 standings — 从任意 group 比赛嵌入的 group_standings 提取
    const firstGroup = all.find((m) => m.stage === 'group');
    const gs: Record<string, Array<[string, number, number, number, number]>> = firstGroup?.group_standings || {};
    if (gs) {
      groupStandings = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'].map((g) => ({
        group: g,
        rows: (gs[g] || []) as Array<[string, number, number, number, number]>,
      }));
    }

    // 16 强配对 (M73-M88) — 从 R32 16 场胜者 + FIFA 官方 r16_indices
    const r32List = all.filter((m) => m.stage === 'R32');
    r32List.sort((a, b) => a.match_id.localeCompare(b.match_id));
    const r16Indices = [
      [0, 2], [1, 4], [3, 5], [6, 7],
      [10, 11], [8, 9], [13, 15], [12, 14],
    ] as const;
    roundOf16Order = r16Indices.map(([a, b]) => {
      const home = r32List[a]?.winner || r32List[a]?.home;
      const away = r32List[b]?.winner || r32List[b]?.home;
      return [home, away] as [string, string];
    });
  } catch (e) {
    console.error('Failed to load predictions:', e);
  }

  return (
    <BracketClient
      initialMatches={koMatches}
      groupStandings={groupStandings}
      roundOf16Order={roundOf16Order}
    />
  );
}
