'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { flag } from '../lib/flag';

type Stage = 'R32' | 'R16' | 'QF' | 'SF' | 'FINAL' | '3RD';

export interface BracketMatch {
  match_id: string;
  round: string;
  stage: Stage;
  home: string;
  away: string;
  date: string;
  city: string;
  stadium: string;
  best_score: string;
  p_home_win: number;
  p_away_win: number;
  p_draw: number;
  winner: string | null;
  loser: string | null;
  actual_score: string | null;
  went_to_pen: boolean;
  data_status: 'real' | 'pending';
}

interface Props {
  initialMatches: BracketMatch[];
}

const STAGE_META: Record<Stage, { label: string; col: number; color: string }> = {
  R32:   { label: '32 强',   col: 0, color: '#f0883e' },
  R16:   { label: '16 强',   col: 1, color: '#a371f7' },
  QF:    { label: '8 强',    col: 2, color: '#58a6ff' },
  SF:    { label: '半决赛',  col: 3, color: '#f778ba' },
  FINAL: { label: '决赛',    col: 4, color: '#ffd700' },
  '3RD': { label: '季军赛',  col: 4, color: '#cd7f32' },
};

const STAGE_ORDER: Stage[] = ['R32', 'R16', 'QF', 'SF', 'FINAL'];
const STAGE_COUNT: Record<Stage, number> = { R32: 16, R16: 8, QF: 4, SF: 2, FINAL: 1, '3RD': 1 };

const SPEED_OPTIONS = [
  { key: 'slow', label: '0.5x', ms: 1400 },
  { key: 'normal', label: '1x', ms: 700 },
  { key: 'fast', label: '2x', ms: 350 },
] as const;

type SpeedKey = (typeof SPEED_OPTIONS)[number]['key'];

export function BracketClient({ initialMatches }: Props) {
  // ---- state ----
  // picks: match_id → 'home' | 'away' (用户在该场手动选的胜者)
  // null = 没手动选, 用 JSON 默认 winner
  const [picks, setPicks] = useState<Record<string, 'home' | 'away'>>({});
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<SpeedKey>('normal');
  const [revealedStage, setRevealedStage] = useState<Stage | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const playTokenRef = useRef(0);

  // ---- 派生：按 stage 索引 + 计算每场的胜者 ----
  const byStage = useMemo(() => {
    const out: Record<Stage, BracketMatch[]> = { R32: [], R16: [], QF: [], SF: [], FINAL: [], '3RD': [] };
    for (const m of initialMatches) out[m.stage].push(m);
    for (const s of STAGE_ORDER) out[s].sort((a, b) => a.match_id.localeCompare(b.match_id));
    return out;
  }, [initialMatches]);

  // 根据 R32 选出的胜者，递归重算 R16/QF/SF/FINAL 的实际 home/away
  const derived = useMemo(() => {
    const real: Record<Stage, BracketMatch[]> = { R32: [], R16: [], QF: [], SF: [], FINAL: [], '3RD': [] };

    // R32: 取原始数据（用户 pick 覆盖 winner 字段）
    for (const m of byStage.R32) {
      const pick = picks[m.match_id];
      const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : m.winner;
      const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
      real.R32.push({ ...m, winner, loser });
    }

    // R16: R32[2j] winner vs R32[2j+1] winner
    for (let j = 0; j < byStage.R16.length; j++) {
      const m = byStage.R16[j];
      const a = real.R32[2 * j]?.winner ?? null;
      const b = real.R32[2 * j + 1]?.winner ?? null;
      // 决定 home/away：原 JSON 的 home 是 R32[2j] 胜者，away 是 R32[2j+1] 胜者
      const newHome = a ?? m.home;
      const newAway = b ?? m.away;
      const pick = picks[m.match_id];
      let winner: string | null = m.winner;
      let loser: string | null = m.loser;
      if (pick === 'home') { winner = newHome; loser = newAway; }
      else if (pick === 'away') { winner = newAway; loser = newHome; }
      else if (winner && (winner !== newHome && winner !== newAway)) {
        // JSON 原 winner 不在新名单中（用户改了上一轮）→ 重置
        winner = null; loser = null;
      }
      real.R16.push({ ...m, home: newHome, away: newAway, winner, loser });
    }

    // QF: R16[2k] winner vs R16[2k+1] winner
    for (let k = 0; k < byStage.QF.length; k++) {
      const m = byStage.QF[k];
      const a = real.R16[2 * k]?.winner ?? null;
      const b = real.R16[2 * k + 1]?.winner ?? null;
      const newHome = a ?? m.home;
      const newAway = b ?? m.away;
      const pick = picks[m.match_id];
      let winner: string | null = m.winner;
      let loser: string | null = m.loser;
      if (pick === 'home') { winner = newHome; loser = newAway; }
      else if (pick === 'away') { winner = newAway; loser = newHome; }
      else if (winner && (winner !== newHome && winner !== newAway)) {
        winner = null; loser = null;
      }
      real.QF.push({ ...m, home: newHome, away: newAway, winner, loser });
    }

    // SF: QF[2l] winner vs QF[2l+1] winner
    for (let l = 0; l < byStage.SF.length; l++) {
      const m = byStage.SF[l];
      const a = real.QF[2 * l]?.winner ?? null;
      const b = real.QF[2 * l + 1]?.winner ?? null;
      const newHome = a ?? m.home;
      const newAway = b ?? m.away;
      const pick = picks[m.match_id];
      let winner: string | null = m.winner;
      let loser: string | null = m.loser;
      if (pick === 'home') { winner = newHome; loser = newAway; }
      else if (pick === 'away') { winner = newAway; loser = newHome; }
      else if (winner && (winner !== newHome && winner !== newAway)) {
        winner = null; loser = null;
      }
      real.SF.push({ ...m, home: newHome, away: newAway, winner, loser });
    }

    // FINAL: SF[0] winner vs SF[1] winner
    if (byStage.FINAL[0]) {
      const m = byStage.FINAL[0];
      const a = real.SF[0]?.winner ?? null;
      const b = real.SF[1]?.winner ?? null;
      const newHome = a ?? m.home;
      const newAway = b ?? m.away;
      const pick = picks[m.match_id];
      let winner: string | null = m.winner;
      let loser: string | null = m.loser;
      if (pick === 'home') { winner = newHome; loser = newAway; }
      else if (pick === 'away') { winner = newAway; loser = newHome; }
      else if (winner && (winner !== newHome && winner !== newAway)) {
        winner = null; loser = null;
      }
      real.FINAL.push({ ...m, home: newHome, away: newAway, winner, loser });
    }

    // 3RD: SF[0] loser vs SF[1] loser
    if (byStage['3RD'][0]) {
      const m = byStage['3RD'][0];
      const a = real.SF[0]?.loser ?? null;
      const b = real.SF[1]?.loser ?? null;
      const newHome = a ?? m.home;
      const newAway = b ?? m.away;
      const pick = picks[m.match_id];
      let winner: string | null = m.winner;
      let loser: string | null = m.loser;
      if (pick === 'home') { winner = newHome; loser = newAway; }
      else if (pick === 'away') { winner = newAway; loser = newHome; }
      else if (winner && (winner !== newHome && winner !== newAway)) {
        winner = null; loser = null;
      }
      real['3RD'].push({ ...m, home: newHome, away: newAway, winner, loser });
    }

    return real;
  }, [byStage, picks]);

  // ---- 交互 ----
  const isLocked = useCallback((m: BracketMatch) => m.data_status === 'real', []);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 1800);
  }, []);

  const handlePick = useCallback((m: BracketMatch, side: 'home' | 'away', e: React.MouseEvent) => {
    e.preventDefault();
    if (isLocked(m)) {
      showToast('🔒 该场已完赛，无法修改');
      return;
    }
    setPicks((prev) => {
      const next = { ...prev };
      const cur = next[m.match_id];
      // 同侧再点 → 视为取消
      if (cur === side) delete next[m.match_id];
      else next[m.match_id] = side;
      return next;
    });
  }, [isLocked, showToast]);

  const handleContext = useCallback((m: BracketMatch, e: React.MouseEvent) => {
    e.preventDefault();
    if (isLocked(m)) {
      showToast('🔒 该场已完赛，无法修改');
      return;
    }
    setPicks((prev) => {
      const next = { ...prev };
      delete next[m.match_id];
      return next;
    });
  }, [isLocked, showToast]);

  const resetAll = useCallback(() => {
    setPicks({});
    setRevealedStage(null);
    setIsPlaying(false);
    showToast('已清空手动标记');
  }, [showToast]);

  // ---- 播放 ----
  const play = useCallback(async () => {
    if (isPlaying) return;
    setIsPlaying(true);
    const token = ++playTokenRef.current;
    const ms = SPEED_OPTIONS.find((s) => s.key === speed)!.ms;

    const sleep = (dur: number) => new Promise<void>((res) => {
      const start = Date.now();
      const tick = () => {
        if (token !== playTokenRef.current) return res();
        const elapsed = Date.now() - start;
        if (elapsed >= dur) res();
        else setTimeout(tick, Math.min(60, dur - elapsed));
      };
      tick();
    });

    // R32 一次性 reveal（16 场）
    setRevealedStage('R32');
    await sleep(ms, token);
    if (token !== playTokenRef.current) return;

    // 后续阶段按"用户选 > JSON 默认 winner > null 顺序"渐进
    for (const stage of ['R16', 'QF', 'SF', 'FINAL'] as Stage[]) {
      setRevealedStage(stage);
      await sleep(ms, token);
      if (token !== playTokenRef.current) return;
    }

    setIsPlaying(false);
  }, [isPlaying, speed]);

  const stopPlay = useCallback(() => {
    playTokenRef.current++;
    setIsPlaying(false);
  }, []);

  useEffect(() => {
    return () => { playTokenRef.current++; };
  }, []);

  // ---- 统计 ----
  const realCount = initialMatches.filter((m) => m.data_status === 'real').length;
  const totalKO = 16 + 8 + 4 + 2 + 1;
  const champion = derived.FINAL[0]?.winner ?? null;

  // ---- 渲染 ----
  return (
    <div className="bracket-page">
      <header className="bracket-header">
        <div>
          <h1>🎯 手动对阵</h1>
          <p className="muted">
            左键点击国旗 = 标记晋级 · 右键 = 退回 · 🔒 = 已完赛（不可改） · {realCount}/{totalKO} 场已踢
          </p>
        </div>
        <div className="bracket-actions">
          <div className="speed-group">
            <span className="muted">速度</span>
            {SPEED_OPTIONS.map((s) => (
              <button
                key={s.key}
                className={`speed-btn ${speed === s.key ? 'active' : ''}`}
                onClick={() => setSpeed(s.key)}
                disabled={isPlaying}
              >
                {s.label}
              </button>
            ))}
          </div>
          <button
            className={`play-btn ${isPlaying ? 'playing' : ''}`}
            onClick={isPlaying ? stopPlay : play}
          >
            {isPlaying ? '⏸ 暂停' : '▶ 播放'}
          </button>
          <button className="reset-btn" onClick={resetAll} disabled={isPlaying}>
            ↺ 重置
          </button>
        </div>
      </header>

      {champion && (
        <div className="champion-banner">
          <span className="champion-trophy">🏆</span>
          <span className="champion-label">冠军</span>
          <span className="champion-team">
            <span className="champion-flag">{flag(champion)}</span>
            <span className="champion-name">{champion}</span>
          </span>
        </div>
      )}

      <div className="bracket-wrapper">
        <BracketConnectors revealedStage={revealedStage} />
        <div className="bracket-grid">
          {(['R32', 'R16', 'QF', 'SF', 'FINAL'] as Stage[]).map((stage) => (
            <BracketColumn
              key={stage}
              stage={stage}
              matches={derived[stage]}
              picks={picks}
              isLocked={isLocked}
              revealedStage={revealedStage}
              onPick={handlePick}
              onContext={handleContext}
            />
          ))}
          {/* 3RD 单独在最右一列 */}
          <BracketColumn
            stage="3RD"
            matches={derived['3RD']}
            picks={picks}
            isLocked={isLocked}
            revealedStage={revealedStage}
            onPick={handlePick}
            onContext={handleContext}
            isThird
          />
        </div>
      </div>

      {toast && <div className="bracket-toast">{toast}</div>}
    </div>
  );
}



// ============== 单列 ==============
function BracketColumn({
  stage,
  matches,
  picks,
  isLocked,
  revealedStage,
  onPick,
  onContext,
  isThird = false,
}: {
  stage: Stage;
  matches: BracketMatch[];
  picks: Record<string, 'home' | 'away'>;
  isLocked: (m: BracketMatch) => boolean;
  revealedStage: Stage | null;
  onPick: (m: BracketMatch, side: 'home' | 'away', e: React.MouseEvent) => void;
  onContext: (m: BracketMatch, e: React.MouseEvent) => void;
  isThird?: boolean;
}) {
  const meta = STAGE_META[stage];
  return (
    <div className={`bk-col bk-col-${stage.toLowerCase()}${isThird ? ' bk-col-third' : ''}`}>
      <div className="bk-col-head" style={{ borderColor: meta.color }}>
        <span className="bk-col-label">{meta.label}</span>
        <span className="bk-col-count">{STAGE_COUNT[stage]} 场</span>
      </div>
      <div className="bk-col-body">
        {matches.map((m, idx) => {
          // R32 16 张: row 2..17 (each 1 row), offset 1 for col-head
          // R16 8 张: row 2+2*j, span 2 → 对应 R32[2j] 和 R32[2j+1] 中点
          // QF 4 张: row 2+4*k, span 4
          // SF 2 张: row 2+8*l, span 8
          // FINAL 1 张: row 2, span 16
          // 3RD 1 张: row 2, span 16
          const span =
            stage === 'R32' ? 1 :
            stage === 'R16' ? 2 :
            stage === 'QF' ? 4 :
            stage === 'SF' ? 8 :
            16;  // FINAL or 3RD
          const gridRow = `${2 + idx * span} / span ${span}`;
          return (
            <MatchCard
              key={m.match_id}
              m={m}
              pick={picks[m.match_id]}
              locked={isLocked(m)}
              stage={stage}
              revealed={revealedStage === stage || (revealedStage && STAGE_ORDER.indexOf(revealedStage) >= STAGE_ORDER.indexOf(stage))}
              gridRow={gridRow}
              onPick={onPick}
              onContext={onContext}
            />
          );
        })}
      </div>
    </div>
  );
}

// ============== 比赛卡 ==============
function MatchCard({
  m,
  pick,
  locked,
  stage,
  revealed,
  gridRow,
  onPick,
  onContext,
}: {
  m: BracketMatch;
  pick?: 'home' | 'away';
  locked: boolean;
  stage: Stage;
  revealed: boolean;
  gridRow: string;  // e.g. "1 / span 1" or "2 / span 2"
  onPick: (m: BracketMatch, side: 'home' | 'away', e: React.MouseEvent) => void;
  onContext: (m: BracketMatch, e: React.MouseEvent) => void;
}) {
  const meta = STAGE_META[stage];
  const realWinner = m.actual_score ? (m.winner ?? null) : m.winner;
  const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : realWinner;
  const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
  const isReal = m.data_status === 'real';

  const renderTeam = (side: 'home' | 'away') => {
    const team = side === 'home' ? m.home : m.away;
    const isWinner = winner === team;
    const isLoser = loser === team && winner !== null;
    return (
      <button
        className={`bk-team ${isWinner ? 'is-winner' : ''} ${isLoser ? 'is-loser' : ''} ${locked ? 'is-locked' : ''}`}
        disabled={locked}
        onClick={(e) => onPick(m, side, e)}
        onContextMenu={(e) => onContext(m, e)}
        title={locked ? '🔒 已完赛' : '左键=晋级 · 右键=退回'}
      >
        <span className="bk-team-flag">{flag(team)}</span>
        <span className="bk-team-name">{team}</span>
        {isReal && m.actual_score && (
          <span className="bk-team-score">
            {m.actual_score.split('-')[side === 'home' ? 0 : 1]}
          </span>
        )}
        {!isReal && m.went_to_pen && isWinner && <span className="bk-pen">点</span>}
      </button>
    );
  };

  return (
    <div
      className={`bk-card bk-card-${stage.toLowerCase()} ${isReal ? 'is-real' : 'is-pending'} ${winner ? 'has-winner' : ''} ${locked ? 'is-locked' : ''} ${stage === 'FINAL' ? 'is-final' : ''} ${stage === '3RD' ? 'is-third' : ''} ${revealed ? 'is-revealed' : ''}`}
      style={{ borderLeftColor: meta.color, gridRow }}
    >
      <div className="bk-card-head">
        <span className="bk-card-date">{m.date?.slice(5) || '?'}</span>
        {locked && <span className="bk-lock">🔒</span>}
        {!locked && pick && <span className="bk-pick-mark">✋</span>}
        {!locked && !pick && !isReal && <span className="bk-prob">{(m.p_home_win * 100).toFixed(0)}/{(m.p_away_win * 100).toFixed(0)}</span>}
      </div>
      {renderTeam('home')}
      {renderTeam('away')}
    </div>
  );
}

// ============== 7 列 SVG 连接器 ==============
function BracketConnectors({ revealedStage }: { revealedStage: Stage | null }) {
  // 6 列布局 + 5 gap
  // CSS 列宽 (px): 200/200/200/200/220/180 = 1200, gap 20 × 5 = 100
  // 总宽 1300 → viewBox 100
  // col 0-3 = 200/1300 ≈ 15.38; col 4 = 220/1300 ≈ 16.92; col 5 = 180/1300 ≈ 13.85
  // gap = 20/1300 ≈ 1.54
  // midX(i) = col(i).right + gap/2

  const COL_W = [15.38, 15.38, 15.38, 15.38, 16.92, 13.85];
  const GAP = 1.54;
  const ROWS = 16;
  // 行 1 是列头，16 场卡占 row 2-17
  const HEADER_ROW = 1;
  const HEADER_H = 5;  // 列头占约 5% 高度
  const PLAY_AREA_TOP = HEADER_H;  // 比赛区从 5% 开始
  const PLAY_AREA_BOT = 100;
  const r32Y = (i: number) => PLAY_AREA_TOP + ((i + 0.5) / ROWS) * (PLAY_AREA_BOT - PLAY_AREA_TOP);
  const r16Y = (j: number) => PLAY_AREA_TOP + ((2 * j + 1.5) / ROWS) * (PLAY_AREA_BOT - PLAY_AREA_TOP);
  const qfY = (k: number) => PLAY_AREA_TOP + ((4 * k + 2.5) / ROWS) * (PLAY_AREA_BOT - PLAY_AREA_TOP);
  const sfY = (l: number) => PLAY_AREA_TOP + ((8 * l + 4.5) / ROWS) * (PLAY_AREA_BOT - PLAY_AREA_TOP);
  const finalY = PLAY_AREA_TOP + (8.5 / ROWS) * (PLAY_AREA_BOT - PLAY_AREA_TOP);
  const colLeft = (() => {
    let acc = 0;
    const arr = [0];
    for (let i = 0; i < COL_W.length - 1; i++) {
      acc += COL_W[i] + GAP;
      arr.push(acc);
    }
    return arr;
  })();
  const col = (idx: number) => ({ left: colLeft[idx], right: colLeft[idx] + COL_W[idx] });
  const midX = (i: number) => col(i).right + GAP / 2;

  return (
    <svg className="bk-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
      {/* R32 → R16: 8 对 */}
      {Array.from({ length: 8 }).map((_, j) => (
        <g key={`r32-r16-${j}`} className={`bk-line ${revealedStage && STAGE_ORDER.indexOf('R16') <= STAGE_ORDER.indexOf(revealedStage) ? 'is-active' : ''}`}>
          <polyline
            points={`${col(0).right},${r32Y(2 * j)} ${midX(0)},${r32Y(2 * j)} ${midX(0)},${r16Y(j)} ${col(1).left},${r16Y(j)}`}
            fill="none"
          />
          <polyline
            points={`${col(0).right},${r32Y(2 * j + 1)} ${midX(0)},${r32Y(2 * j + 1)} ${midX(0)},${r16Y(j)} ${col(1).left},${r16Y(j)}`}
            fill="none"
          />
        </g>
      ))}
      {/* R16 → QF: 4 对 */}
      {Array.from({ length: 4 }).map((_, k) => (
        <g key={`r16-qf-${k}`} className={`bk-line ${revealedStage && STAGE_ORDER.indexOf('QF') <= STAGE_ORDER.indexOf(revealedStage) ? 'is-active' : ''}`}>
          <polyline
            points={`${col(1).right},${r16Y(2 * k)} ${midX(1)},${r16Y(2 * k)} ${midX(1)},${qfY(k)} ${col(2).left},${qfY(k)}`}
            fill="none"
          />
          <polyline
            points={`${col(1).right},${r16Y(2 * k + 1)} ${midX(1)},${r16Y(2 * k + 1)} ${midX(1)},${qfY(k)} ${col(2).left},${qfY(k)}`}
            fill="none"
          />
        </g>
      ))}
      {/* QF → SF: 2 对 */}
      {Array.from({ length: 2 }).map((_, l) => (
        <g key={`qf-sf-${l}`} className={`bk-line ${revealedStage && STAGE_ORDER.indexOf('SF') <= STAGE_ORDER.indexOf(revealedStage) ? 'is-active' : ''}`}>
          <polyline
            points={`${col(2).right},${qfY(2 * l)} ${midX(2)},${qfY(2 * l)} ${midX(2)},${sfY(l)} ${col(3).left},${sfY(l)}`}
            fill="none"
          />
          <polyline
            points={`${col(2).right},${qfY(2 * l + 1)} ${midX(2)},${qfY(2 * l + 1)} ${midX(2)},${sfY(l)} ${col(3).left},${sfY(l)}`}
            fill="none"
          />
        </g>
      ))}
      {/* SF → Final: 1 对 */}
      <g className={`bk-line ${revealedStage && STAGE_ORDER.indexOf('FINAL') <= STAGE_ORDER.indexOf(revealedStage) ? 'is-active' : ''}`}>
        <polyline
          points={`${col(3).right},${sfY(0)} ${midX(3)},${sfY(0)} ${midX(3)},${finalY} ${col(4).left},${finalY}`}
          fill="none"
        />
        <polyline
          points={`${col(3).right},${sfY(1)} ${midX(3)},${sfY(1)} ${midX(3)},${finalY} ${col(4).left},${finalY}`}
          fill="none"
        />
      </g>
      {/* Final → 3RD: 失败者汇聚到季军赛 (在 Final 下方) */}
      <g className={`bk-line ${revealedStage && STAGE_ORDER.indexOf('FINAL') <= STAGE_ORDER.indexOf(revealedStage) ? 'is-active' : ''}`}>
        <polyline
          points={`${col(4).right},${finalY - 2} ${midX(4)},${finalY - 2} ${midX(4)},${finalY + 3} ${col(5).left},${finalY + 3}`}
          fill="none"
        />
      </g>
    </svg>
  );
}
