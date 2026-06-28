import { fetchPredictions } from '../lib/data';
import { flag } from '../lib/flag';
import type { Match } from '../lib/types';

export const dynamic = 'force-dynamic';

const GROUPS_UPPER = ['A', 'B', 'C', 'D', 'E', 'F'];
const GROUPS_LOWER = ['G', 'H', 'I', 'J', 'K', 'L'];

export default async function SchedulePage() {
  let predictions: Match[] = [];
  try {
    const data = await fetchPredictions();
    predictions = data.predictions;
  } catch (e) {
    console.error('Failed to load predictions:', e);
  }

  const groupMatches = predictions.filter((m) => m.stage === 'group');

  // 算每组积分
  const standings: Record<string, Record<string, {
    pts: number; gf: number; ga: number; gp: number; w: number; d: number; l: number;
  }>> = {};

  for (const m of groupMatches) {
    if (!m.actual_score) continue;
    const [hs, as] = m.actual_score.split('-').map(Number);
    const g = m.group!;
    if (!standings[g]) standings[g] = {};
    for (const side of ['home', 'away'] as const) {
      const team = m[side];
      if (!standings[g][team]) standings[g][team] = { pts: 0, gf: 0, ga: 0, gp: 0, w: 0, d: 0, l: 0 };
    }
    standings[g][m.home].gp++;
    standings[g][m.away].gp++;
    standings[g][m.home].gf += hs;
    standings[g][m.home].ga += as;
    standings[g][m.away].gf += as;
    standings[g][m.away].ga += hs;
    if (hs > as) {
      standings[g][m.home].pts += 3; standings[g][m.home].w++;
      standings[g][m.away].l++;
    } else if (hs < as) {
      standings[g][m.away].pts += 3; standings[g][m.away].w++;
      standings[g][m.home].l++;
    } else {
      standings[g][m.home].pts += 1; standings[g][m.away].pts += 1;
      standings[g][m.home].d++; standings[g][m.away].d++;
    }
  }

  const renderGroup = (g: string) => {
    const teams = standings[g] || {};
    const sorted = Object.entries(teams)
      .map(([team, s]) => ({ team, ...s, gd: s.gf - s.ga }))
      .sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf || a.team.localeCompare(b.team));
    const matches = groupMatches
      .filter((m) => m.group === g)
      .sort((a, b) => (a.round || '').localeCompare(b.round || ''));

    return (
      <div key={g} className="group-card">
        <div className="group-title">第 {g} 组</div>
        <table className="standings-table">
          <thead>
            <tr>
              <th>#</th>
              <th style={{ textAlign: 'left' }}>球队</th>
              <th>赛</th><th>胜</th><th>平</th><th>负</th>
              <th>净</th><th>分</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((t, i) => (
              <tr
                key={t.team}
                className={i < 2 ? 'qualified' : i === 2 ? 'third' : 'row-out'}
              >
                <td>{i + 1}</td>
                <td className="team-name">{flag(t.team)} {t.team}</td>
                <td>{t.gp}</td><td>{t.w}</td><td>{t.d}</td><td>{t.l}</td>
                <td>{t.gd > 0 ? '+' : ''}{t.gd}</td>
                <td className="pts">{t.pts}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="matches-list">
          {matches.map((m) => (
            <div key={m.match_id} className="match-row">
              <span>
                {flag(m.home)} {m.home} <span className="muted">vs</span> {flag(m.away)} {m.away}
              </span>
              <span className="score">{m.actual_score || '?'}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div>
      <h2 className="section-title">
        📅 小组赛 (72 场)
        <span className="count-badge">全部已踢</span>
      </h2>
      <p className="muted" style={{ marginBottom: 12 }}>
        绿底=已晋级 16 强 · 橙底=候选最佳第 3
      </p>
      <h3 className="section-title" style={{ fontSize: 14 }}>
        🟦 上半区 (A-F, 6 组 · 36 场)
      </h3>
      <div className="groups-container">
        {GROUPS_UPPER.map(renderGroup)}
      </div>
      <h3 className="section-title" style={{ fontSize: 14, marginTop: 24 }}>
        🟥 下半区 (G-L, 6 组 · 36 场)
      </h3>
      <div className="groups-container">
        {GROUPS_LOWER.map(renderGroup)}
      </div>
    </div>
  );
}
