import { fetchRanking } from './lib/data';
import { flag } from './lib/flag';
import type { Team } from './lib/types';

export const dynamic = 'force-dynamic';

export default async function TeamsPage() {
  let ranking: Team[] = [];
  try {
    const data = await fetchRanking();
    ranking = data.ranking;
  } catch (e) {
    console.error('Failed to load ranking:', e);
  }

  return (
    <div>
      <h2 className="section-title">
        ⚽ 48 强排名
        <span className="count-badge">{ranking.length} 队</span>
      </h2>
      <div className="teams-grid">
        {ranking.map((t) => (
          <div key={t.team} className="team-card">
            <div className="team-header">
              <div className="team-name">
                {flag(t.team)} {t.team}
              </div>
              <div className="team-rank">#{t.rank} · FIFA {t.fifa_rank}</div>
            </div>
            <div className="team-stats">
              <div className="stat">
                <div className="lbl">锋线</div>
                <div className="val">{Math.round(t.fw_score)}</div>
              </div>
              <div className="stat">
                <div className="lbl">中场</div>
                <div className="val">{Math.round(t.mid_score)}</div>
              </div>
              <div className="stat">
                <div className="lbl">后卫</div>
                <div className="val">{Math.round(t.def_score)}</div>
              </div>
              <div className="stat">
                <div className="lbl">门将</div>
                <div className="val">{Math.round(t.gk_score)}</div>
              </div>
              <div className="stat" style={{ gridColumn: 'span 2' }}>
                <div className="lbl">总评</div>
                <div className="val" style={{ color: 'var(--accent)' }}>
                  {Math.round(t.player_score)}
                </div>
              </div>
              <div className="stat" style={{ gridColumn: 'span 2' }}>
                <div className="lbl">综合 (player + coach)</div>
                <div className="val">{t.rank_r?.toFixed?.(1) ?? t.rank_r}</div>
              </div>
            </div>
            <div className="muted" style={{ marginTop: 6, fontSize: 11 }}>
              主帅: {t.coach_name} ({t.coach_age})
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
