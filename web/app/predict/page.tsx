import { fetchPredictions } from '../lib/data';
import { flag } from '../lib/flag';
import type { Match } from '../lib/types';

export const dynamic = 'force-dynamic';

type Stage = 'R32' | 'R16' | 'QF' | 'SF' | 'FINAL' | '3RD';

const STAGE_META: Record<Stage, { label: string; color: string }> = {
  R32: { label: '32 强', color: '#f0883e' },
  R16: { label: '16 强', color: '#a371f7' },
  QF: { label: '8 强', color: '#58a6ff' },
  SF: { label: '半决赛', color: '#f778ba' },
  FINAL: { label: '决赛', color: '#ffd700' },
  '3RD': { label: '季军赛', color: '#cd7f32' },
};

export default async function PredictPage() {
  let predictions: Match[] = [];
  let finalMatch: Match | undefined;
  let thirdMatch: Match | undefined;
  try {
    const data = await fetchPredictions();
    predictions = data.predictions;
    finalMatch = predictions.find((m) => m.stage === 'FINAL');
    thirdMatch = predictions.find((m) => m.stage === '3RD');
  } catch (e) {
    console.error('Failed to load predictions:', e);
  }

  const groupDone = predictions.filter((m) => m.stage === 'group' && m.data_status === 'real').length;
  const koStages: Stage[] = ['R32', 'R16', 'QF', 'SF', 'FINAL'];
  const koDone = predictions.filter((m) => koStages.includes(m.stage as Stage) && m.data_status === 'real').length;
  const koTotal = 16 + 8 + 4 + 2 + 1;

  const runnerUp = finalMatch?.loser;
  const thirdWinner = thirdMatch?.winner;

  // 渲染比赛卡
  const renderMatchCard = (m: Match, opts: { highlight?: 'final' | 'third' } = {}) => {
    const isPending = m.data_status === 'pending' || !m.actual_score;
    const isFinal = opts.highlight === 'final';
    const isThird = opts.highlight === 'third';
    return (
      <div
        key={m.match_id}
        className={`br-card${isFinal ? ' br-final' : ''}${isThird ? ' br-third' : ''}${isPending ? ' br-pending' : ' br-real'}${m.winner ? ' br-has-winner' : ''}`}
      >
        <div className="br-card-head">
          <span className="br-card-date">{m.date?.slice(5) || '?'}</span>
          <span className="br-card-venue">{m.city || m.stadium || '?'}</span>
        </div>
        <div className={`br-team ${m.winner === m.home ? 'is-winner' : m.winner === m.away ? 'is-loser' : ''}`}>
          <span className="br-team-name">
            <span className="br-flag">{flag(m.home)}</span>
            <span className="br-team-text">{m.home}</span>
            {m.went_to_pen && m.winner === m.home && <span className="br-pen">点</span>}
          </span>
          <span className="br-score">{m.actual_score?.split('-')[0] ?? <span className="br-pending">·</span>}</span>
        </div>
        <div className={`br-team ${m.winner === m.away ? 'is-winner' : m.winner === m.home ? 'is-loser' : ''}`}>
          <span className="br-team-name">
            <span className="br-flag">{flag(m.away)}</span>
            <span className="br-team-text">{m.away}</span>
            {m.went_to_pen && m.winner === m.away && <span className="br-pen">点</span>}
          </span>
          <span className="br-score">{m.actual_score?.split('-')[1] ?? <span className="br-pending">·</span>}</span>
        </div>
      </div>
    );
  };

  // Bracket 数据
  const r32 = predictions.filter((m) => m.stage === 'R32').sort((a, b) => (a.match_id || '').localeCompare(b.match_id || ''));
  const r16 = predictions.filter((m) => m.stage === 'R16').sort((a, b) => (a.match_id || '').localeCompare(b.match_id || ''));
  const qf = predictions.filter((m) => m.stage === 'QF').sort((a, b) => (a.match_id || '').localeCompare(b.match_id || ''));
  const sf = predictions.filter((m) => m.stage === 'SF').sort((a, b) => (a.match_id || '').localeCompare(b.match_id || ''));

  // 渲染一张卡 + 行内连接器
  // R32 卡：右侧延伸短水平线 (--line-h: 16px)
  // R16/QF/SF/Final 卡：左侧 1) 水平短线 --line-h: 16px; 2) 上方/下方垂直线 --line-v: 20px
  //     当 R16[j] 是 R32[2j] + R32[2j+1] 的下一轮：
  //       R16[j] 的左侧 50% 处（垂直中线）需要从 R32[2j] 右边的水平线 + R32[2j+1] 右边的水平线
  //       交汇到 R16[j] 的左侧 → 实际就是 R16[j] 卡片左侧画一个"┤"形
  //     R16[0] 顶部需不需要线？不需要（只有 R32 两条线汇聚到这里）

  // 简化版：
  // - 每张 R32 卡右侧画水平短线
  // - 每张 R16/QF/SF/Final 卡左侧画 "┤" 形（左边缘水平+50% 高度处垂直短线）
  //   垂直短线长度 = (j%2===0 ? -8 : 8) * 卡片行高 + 中点对齐 R32[2j+1]/R32[2j]
  //   但 CSS 难算，改用相邻线的中点对齐

  // 最简单：每张非 R32 卡都画 "┤" 形（左侧水平 + 中心垂直短线）
  // 每张 R32 卡画 "├" 形（右侧水平 + 中心垂直短线）
  // 但 R32 不需要垂直线，只有 R32→R16 水平连接
  // R16[0] 左侧：水平短线 + 中心垂直短线（指向上一组 R32 中心）
  //   实际在 R16[0] 的 50% 高度画一个 "┤" 形（向左 16px 水平 + 上下 16px 垂直）

  // 折线方案：每张"接收"卡片（不在最左列的）画：
  //   ::before: 左 0, 中心 0, 水平线 16px 宽 1px 高
  //   ::after: 左 -16px, 中心 0, 垂直线 1px 宽 32px 高（指向上一对 R32 中心）
  // 注意 ::after 是定位在卡片中心点的上方/下方

  return (
    <div className="predict-page">
      <h2 className="section-title">
        🏆 完整 104 场预测
        <span className="count-badge">R32→Final 按真实小组赛出线 · FIFA 官方对阵</span>
      </h2>

      {finalMatch && (
        <section className="podium">
          <div className="podium-card podium-silver">
            <div className="podium-medal">🥈</div>
            <div className="podium-rank">亚军</div>
            <div className="podium-team">
              <span className="podium-flag">{flag(runnerUp || '')}</span>
              <span className="podium-name">{runnerUp || '待定'}</span>
            </div>
            <div className="podium-score">{finalMatch.best_score}</div>
          </div>
          <div className="podium-card podium-gold">
            <div className="podium-medal">🏆</div>
            <div className="podium-rank podium-rank-gold">冠 军</div>
            <div className="podium-team">
              <span className="podium-flag">{flag(finalMatch.winner || '')}</span>
              <span className="podium-name">{finalMatch.winner || '待定'}</span>
            </div>
            <div className="podium-score podium-score-gold">
              {finalMatch.best_score}
              {finalMatch.went_to_pen && <span className="podium-pen">点球</span>}
            </div>
            <div className="podium-vs">
              <span>{flag(finalMatch.home)} {finalMatch.home}</span>
              <span className="podium-vs-sep">vs</span>
              <span>{flag(finalMatch.away)} {finalMatch.away}</span>
            </div>
            <div className="podium-meta">
              {finalMatch.date} · {finalMatch.city}
            </div>
          </div>
          {thirdMatch && (
            <div className="podium-card podium-bronze">
              <div className="podium-medal">🥉</div>
              <div className="podium-rank">季军</div>
              <div className="podium-team">
                <span className="podium-flag">{flag(thirdWinner || '')}</span>
                <span className="podium-name">{thirdWinner || '待定'}</span>
              </div>
              <div className="podium-score">{thirdMatch.best_score}</div>
            </div>
          )}
        </section>
      )}

      <section className="progress-block">
        <div className="progress-row">
          <div className="progress-label">
            <span className="progress-stage">小组赛</span>
            <span className="progress-count">{groupDone}/72</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${(groupDone / 72) * 100}%`, background: '#2ea043' }} />
          </div>
        </div>
        <div className="progress-row">
          <div className="progress-label">
            <span className="progress-stage">淘汰赛</span>
            <span className="progress-count">{koDone}/31</span>
          </div>
          <div className="progress-bar progress-bar-ko">
            {koStages.map((s) => {
              const total = s === 'R32' ? 16 : s === 'R16' ? 8 : s === 'QF' ? 4 : s === 'SF' ? 2 : 1;
              const done = predictions.filter((m) => m.stage === s && m.data_status === 'real').length;
              return (
                <div
                  key={s}
                  className="progress-seg"
                  style={{ width: `${(done / total) * 100}%`, background: STAGE_META[s].color }}
                  title={`${STAGE_META[s].label}: ${done}/${total}`}
                />
              );
            })}
          </div>
        </div>
      </section>

      <section className="bracket-wrap">
        <div className="bracket-heads">
          {(['R32', 'R16', 'QF', 'SF', 'FINAL'] as const).map((s) => (
            <div key={s} className="bracket-head-cell" style={{ color: STAGE_META[s].color }}>
              <span className="bracket-head-dot" style={{ background: STAGE_META[s].color }} />
              {STAGE_META[s].label}
            </div>
          ))}
        </div>

        <div className="bracket-grid">
          {/* R32 列 - 16 张, row 1-16 */}
          <div className="br-col br-col-r32">
            {r32.map((m, i) => (
              <div key={m.match_id} className="br-cell" style={{ gridRow: `${i + 1} / span 1` }}>
                {renderMatchCard(m)}
              </div>
            ))}
          </div>
          {/* R16 列 - 8 张 */}
          <div className="br-col br-col-r16">
            {r16.map((m, j) => (
              <div key={m.match_id} className="br-cell" style={{ gridRow: `${2 * j + 1} / span 2` }}>
                {renderMatchCard(m)}
              </div>
            ))}
          </div>
          {/* QF 列 - 4 张 */}
          <div className="br-col br-col-qf">
            {qf.map((m, k) => (
              <div key={m.match_id} className="br-cell" style={{ gridRow: `${4 * k + 1} / span 4` }}>
                {renderMatchCard(m)}
              </div>
            ))}
          </div>
          {/* SF 列 - 2 张 */}
          <div className="br-col br-col-sf">
            {sf.map((m, l) => (
              <div key={m.match_id} className="br-cell" style={{ gridRow: `${8 * l + 1} / span 8` }}>
                {renderMatchCard(m)}
              </div>
            ))}
          </div>
          {/* Final 列 - 1 张 */}
          <div className="br-col br-col-final">
            {finalMatch && (
              <div className="br-cell" style={{ gridRow: '1 / span 16' }}>
                {renderMatchCard(finalMatch, { highlight: 'final' })}
              </div>
            )}
          </div>

          {/* SVG 折线层 */}
          <BracketConnectors />
        </div>
      </section>

      {thirdMatch && (
        <section className="third-place">
          <div className="third-place-head">
            <span className="third-place-medal">🥉</span>
            <span className="third-place-title">季军赛</span>
            <span className="third-place-date">{thirdMatch.date} · {thirdMatch.city}</span>
          </div>
          {renderMatchCard(thirdMatch, { highlight: 'third' })}
        </section>
      )}

      <p className="muted predict-footer">
        ℹ️ KO 配对按 FIFA 2026 官方对阵表 · 比分/胜者来自 Mavis PDP 算法 · 数据源: ESPN API 2026-06-28
      </p>
    </div>
  );
}

// SVG 折线：固定在卡片区域，覆盖所有线
function BracketConnectors() {
  // 16 rows，rows 编号 1-16
  // 卡片中心 y 位置（百分比）：
  //   R32[i] center = (i + 0.5) / 16 * 100%
  //   R16[j] center = (2j+1.5) / 16 * 100%
  //   QF[k] center = (4k+2.5) / 16 * 100%
  //   SF[l] center = (8l+4.5) / 16 * 100%
  //   Final center = 50%
  // 列 x 位置：grid-template-columns: repeat(5, 1fr) + gap 16px (4 个 gap)
  //   实际列宽 = (100% - 64px) / 5
  //   列 i 起始 x = i * (col_w + 16)
  //   列 i 结束 x = i * (col_w + 16) + col_w
  //   我们用 viewBox 100x100，5 列等分，列间 gap 也用 viewBox 单位
  //   col_w = 18, gap = 2 (5 cols * 18 + 4 * 2 = 98, 留 1 边距)
  //   列 i left = i * 20, right = i * 20 + 18
  //   卡片 right edge = col_right
  //   下一列 left edge = next_col_left = (i+1) * 20
  //   midX = (col_right + next_col_left) / 2 = (i*20+18 + (i+1)*20) / 2 = (40i + 38) / 2 = 20i + 19
  //   简化：col 0 right=18, col 1 left=20, mid=19
  //          col 1 right=38, col 2 left=40, mid=39
  //          col 2 right=58, col 3 left=60, mid=59
  //          col 3 right=78, col 4 left=80, mid=79

  const ROWS = 16;
  const cy = (row: number) => ((row + 0.5) / ROWS) * 100;
  const r32Y = (i: number) => cy(i);
  const r16Y = (j: number) => cy(2 * j + 1.5);
  const qfY = (k: number) => cy(4 * k + 2.5);
  const sfY = (l: number) => cy(8 * l + 4.5);
  const finalY = 50;

  const col = (idx: number) => ({ left: idx * 20, right: idx * 20 + 18 });
  const midX = (i: number) => i * 20 + 19;

  // 水平段长度 = mid - col_right = 1 单位（很窄）
  // 视觉上：水平短线 1 单位 + 垂直线 0 单位（直接到 midX）
  // 实际需要：col right 到 midX 水平段，midX 上垂直段，midX 到 next col left 水平段
  // 总水平长度 = 2 单位，垂直任意

  return (
    <svg className="br-svg" viewBox="0 0 100 100" preserveAspectRatio="none">

      {/* R32 → R16: 8 对 */}
      {Array.from({ length: 8 }).map((_, j) => {
        const yTo = r16Y(j);
        return (
          <g key={`r32-r16-${j}`} className="br-line">
            <polyline
              points={`${col(0).right},${r32Y(2 * j)} ${midX(0)},${r32Y(2 * j)} ${midX(0)},${yTo} ${col(1).left},${yTo}`}
              fill="none"
            />
            <polyline
              points={`${col(0).right},${r32Y(2 * j + 1)} ${midX(0)},${r32Y(2 * j + 1)} ${midX(0)},${yTo} ${col(1).left},${yTo}`}
              fill="none"
            />
          </g>
        );
      })}
      {/* R16 → QF: 4 对 */}
      {Array.from({ length: 4 }).map((_, k) => {
        const yTo = qfY(k);
        return (
          <g key={`r16-qf-${k}`} className="br-line">
            <polyline
              points={`${col(1).right},${r16Y(2 * k)} ${midX(1)},${r16Y(2 * k)} ${midX(1)},${yTo} ${col(2).left},${yTo}`}
              fill="none"
            />
            <polyline
              points={`${col(1).right},${r16Y(2 * k + 1)} ${midX(1)},${r16Y(2 * k + 1)} ${midX(1)},${yTo} ${col(2).left},${yTo}`}
              fill="none"
            />
          </g>
        );
      })}
      {/* QF → SF: 2 对 */}
      {Array.from({ length: 2 }).map((_, l) => {
        const yTo = sfY(l);
        return (
          <g key={`qf-sf-${l}`} className="br-line">
            <polyline
              points={`${col(2).right},${qfY(2 * l)} ${midX(2)},${qfY(2 * l)} ${midX(2)},${yTo} ${col(3).left},${yTo}`}
              fill="none"
            />
            <polyline
              points={`${col(2).right},${qfY(2 * l + 1)} ${midX(2)},${qfY(2 * l + 1)} ${midX(2)},${yTo} ${col(3).left},${yTo}`}
              fill="none"
            />
          </g>
        );
      })}
      {/* SF → Final: 1 对 */}
      <g className="br-line br-line-final">
        <polyline
          points={`${col(3).right},${sfY(0)} ${midX(3)},${sfY(0)} ${midX(3)},${finalY} ${col(4).left},${finalY}`}
          fill="none"
        />
        <polyline
          points={`${col(3).right},${sfY(1)} ${midX(3)},${sfY(1)} ${midX(3)},${finalY} ${col(4).left},${finalY}`}
          fill="none"
        />
      </g>
    </svg>
  );
}
