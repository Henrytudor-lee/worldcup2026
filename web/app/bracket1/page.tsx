import { readFile } from 'fs/promises';
import { join } from 'path';
import { BracketClient, type BracketMatch, type GroupStanding } from './BracketClient';

export const dynamic = 'force-dynamic';

type Stage = 'R32' | 'R16' | 'QF' | 'SF' | 'FINAL' | '3RD';

const PROJECT_ROOT = join(process.cwd(), '..');
const PREDICTIONS_PATH = join(PROJECT_ROOT, '5_算法', 'all_104_predictions.json');

// === FIFA 2026 官方 32 强配对 (M1-M16) ===
const OFFICIAL_R32_PAIRS: Array<[string, string]> = [
  ['南非', '加拿大'],     // M1
  ['巴西', '日本'],       // M2
  ['德国', '巴拉圭'],     // M3
  ['荷兰', '摩洛哥'],     // M4
  ['科特迪瓦', '挪威'],   // M5
  ['法国', '瑞典'],       // M6
  ['墨西哥', '厄瓜多尔'], // M7
  ['英格兰', '民主刚果'], // M8
  ['比利时', '塞内加尔'], // M9
  ['美国', '波黑'],       // M10
  ['西班牙', '奥地利'],   // M11
  ['葡萄牙', '克罗地亚'], // M12
  ['瑞士', '阿尔及利亚'], // M13
  ['澳大利亚', '埃及'],   // M14
  ['阿根廷', '佛得角'],   // M15
  ['哥伦比亚', '加纳'],   // M16
];

export default async function BracketPage() {
  let koMatches: BracketMatch[] = [];
  let groupStandings: GroupStanding[] = [];

  try {
    const raw = JSON.parse(await readFile(PREDICTIONS_PATH, 'utf-8'));
    const all: any[] = Array.isArray(raw) ? raw : raw.predictions || [];

    // KO 比赛 (含 R32/R16/QF/SF/FINAL/3RD)
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

    // 12 小组 standings
    const firstGroup = all.find((m) => m.stage === 'group');
    const gs: Record<string, Array<[string, number, number, number, number]>> = firstGroup?.group_standings || {};
    groupStandings = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'].map((g) => ({
      group: g,
      rows: (gs[g] || []) as Array<[string, number, number, number, number]>,
    }));
  } catch (e) {
    console.error('Failed to load predictions:', e);
  }

  return (
    <BracketClient
      initialMatches={koMatches}
      groupStandings={groupStandings}
      roundOf32Order={OFFICIAL_R32_PAIRS}
    />
  );
}
