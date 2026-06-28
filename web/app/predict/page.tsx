import { fetchPredictions } from '../lib/data';
import { flag } from '../lib/flag';
import type { Match } from '../lib/types';

export const dynamic = 'force-dynamic';

export default async function PredictPage() {
  let predictions: Match[] = [];
  let groupStandings: any = null;
  let finalMatch: any = null;
  let thirdMatch: any = null;
  try {
    const data = await fetchPredictions();
    predictions = data.predictions;
    groupStandings = data.group_standings;
    finalMatch = data.predictions.find((m) => m.stage === 'FINAL');
    thirdMatch = data.predictions.find((m) => m.stage === '3RD');
  } catch (e) {
    console.error('Failed to load predictions:', e);
  }

  const stages: Array<{ key: 'group' | 'R32' | 'R16' | 'QF' | 'SF' | 'FINAL' | '3RD'; label: string; total: number }> = [
    { key: 'group', label: '小组赛', total: 72 },
    { key: 'R32', label: 'R32 32强', total: 16 },
    { key: 'R16', label: 'R16 16强', total: 8 },
    { key: 'QF', label: 'QF 8强', total: 4 },
    { key: 'SF', label: 'SF 半决赛', total: 2 },
    { key: 'FINAL', label: '决赛', total: 1 },
  ];
  const stageColors: Record<string, string> = {
    group: '#2ea043', R32: '#f0883e', R16: '#a371f7', QF: '#58a6ff', SF: '#f778ba', FINAL: '#ffd700',
  };

  return (
    <div>
      <h2 className="section-title">
        🏆 完整 104 场预测
        <span className="count-badge">R32→Final 按真实小组赛出线</span>
      </h2>

      {/* 进度条 */}
      <div className="ko-progress">
        {stages.map((s) => {
          const done = predictions.filter(
            (m) => m.stage === s.key && m.data_status === 'real'
          ).length;
          const pct = s.total > 0 ? (done / s.total) * 100 : 0;
          return (
            <div key={s.key} className="ko-progress-item">
              <div className="ko-progress-label">{s.label}</div>
              <div className="ko-progress-bar">
                <div
                  className="ko-progress-fill"
                  style={{ width: `${pct}%`, background: stageColors[s.key] }}
                />
              </div>
              <div className="ko-progress-text" style={{ color: stageColors[s.key] }}>
                {done}/{s.total}
              </div>
            </div>
          );
        })}
      </div>

      {/* 冠军横幅 */}
      {finalMatch && (
        <div style={{ textAlign: 'center', padding: 16, marginBottom: 12 }}>
          <div style={{ color: 'var(--gold)', fontSize: 14, fontWeight: 'bold', letterSpacing: 3 }}>
            🏆 F I N A L
          </div>
          <div style={{ fontSize: 24, fontWeight: 'bold', marginTop: 4 }}>
            {flag(finalMatch.home)} {finalMatch.home}{' '}
            <span style={{ color: 'var(--gold)' }}>vs</span>{' '}
            {flag(finalMatch.away)} {finalMatch.away}
          </div>
          <div style={{ marginTop: 4, fontSize: 13, color: 'var(--text-2)' }}>
            预测比分 <strong style={{ color: 'var(--gold)' }}>{finalMatch.best_score}</strong>
            {finalMatch.went_to_pen && <span style={{ color: 'var(--gold)' }}> (点球)</span>}
            {' '}· 冠军 <strong style={{ color: 'var(--gold)' }}>{flag(finalMatch.winner)} {finalMatch.winner}</strong>
          </div>
        </div>
      )}

      {/* KO Bracket */}
      <div className="bracket-container">
        <div className="bracket-flow">
          {(['R32', 'R16', 'QF', 'SF', 'FINAL', '3RD'] as const).map((stage) => {
            const matches = predictions
              .filter((m) => m.stage === stage)
              .sort((a, b) => (a.match_id || '').localeCompare(b.match_id || ''));
            if (matches.length === 0) return null;
            return (
              <div key={stage} className="bracket-stage">
                <h3>
                  {stage === 'R32' ? '32 强' :
                    stage === 'R16' ? '16 强' :
                    stage === 'QF' ? '8 强' :
                    stage === 'SF' ? '半决赛' :
                    stage === 'FINAL' ? '决赛' : '季军赛'}
                </h3>
                {matches.map((m) => {
                  const cls = ['bracket-match'];
                  if (stage === 'FINAL') cls.push('final');
                  if (stage === '3RD') cls.push('third');
                  if (m.data_status === 'real') cls.push('status-real');
                  if (m.data_status === 'pending' || !m.actual_score) cls.push('status-pending');
                  if (m.winner) cls.push('has-winner');
                  return (
                    <div key={m.match_id} className={cls.join(' ')}>
                      <div className="match-date-city">
                        {m.date || '?'} · {m.city || m.stadium || '?'}
                      </div>
                      <div className={`team ${m.winner === m.home ? 'winner' : m.winner === m.away ? 'loser' : ''}`}>
                        <span>
                          {flag(m.home)} {m.home}
                          <span className="team-rank">{m.match_id?.split('_')[1]}</span>
                          {m.went_to_pen && m.winner === m.home && <span className="pen">点</span>}
                        </span>
                        <span className="score">{m.actual_score?.split('-')[0] || '?'}</span>
                      </div>
                      <div className={`team ${m.winner === m.away ? 'winner' : m.winner === m.home ? 'loser' : ''}`}>
                        <span>
                          {flag(m.away)} {m.away}
                          <span className="team-rank">{m.match_id?.split('_')[2]}</span>
                          {m.went_to_pen && m.winner === m.away && <span className="pen">点</span>}
                        </span>
                        <span className="score">{m.actual_score?.split('-')[1] || '?'}</span>
                      </div>
                      <div className={`status-badge ${m.data_status === 'real' ? 'real' : 'pending'}`}>
                        {m.data_status === 'real' ? '✅' : '🕐'} {m.data_status === 'real' ? '已踢' : '待定'}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      <p className="muted" style={{ marginTop: 12 }}>
        ℹ️ KO 配对按 FIFA 2026 官方对阵表 · 比分/胜者来自 Mavis PDP 算法 · 数据源: ESPN API 2026-06-28
      </p>
    </div>
  );
}
