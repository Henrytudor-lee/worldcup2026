import { fetchRanking, fetchPredictions } from '../lib/data';

export async function Header() {
  // 在 server 组件里预取数据，让首屏直接显示冠军
  const [ranking, predictions] = await Promise.all([
    fetchRanking().catch(() => null),
    fetchPredictions().catch(() => null),
  ]);

  const teams = ranking?.ranking?.length ?? 48;
  const matches = predictions?.predictions?.length ?? 104;
  const finalMatch = predictions?.predictions?.find(
    (m) => m.stage === 'FINAL'
  );
  const thirdMatch = predictions?.predictions?.find(
    (m) => m.stage === '3RD'
  );

  return (
    <header className="app-header">
      <div>
        <div className="app-title">🏆 2026 世界杯预测 · Mavis PDP</div>
        <div className="app-stats">
          <div className="app-stat">
            <div className="label">球队</div>
            <div className="value">{teams}</div>
          </div>
          <div className="app-stat">
            <div className="label">比赛</div>
            <div className="value">{matches}</div>
          </div>
          <div className="app-stat" style={{ background: 'rgba(255,215,0,0.25)' }}>
            <div className="label">冠军</div>
            <div className="value">{finalMatch?.winner ?? '?'}</div>
          </div>
          <div className="app-stat">
            <div className="label">亚军</div>
            <div className="value">{finalMatch?.loser ?? '?'}</div>
          </div>
          <div className="app-stat" style={{ background: 'rgba(205,127,50,0.25)' }}>
            <div className="label">季军</div>
            <div className="value">{thirdMatch?.winner ?? '?'}</div>
          </div>
        </div>
      </div>
    </header>
  );
}
