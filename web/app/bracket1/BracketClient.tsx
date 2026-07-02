'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { flag } from '../lib/flag';

// === 比赛类型: R16 / QF / SF / FINAL / 3RD (省 R32, 6 小组直接进 R16) ===
type Stage = 'R16' | 'QF' | 'SF' | 'FINAL' | '3RD';

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

export interface GroupStanding {
  group: string;
  rows: Array<[string, number, number, number, number]>; // [team, pts, gd, gf, ga]
}

interface Props {
  initialMatches: BracketMatch[];
  groupStandings: GroupStanding[];
  // 16 强配对 (M73-M88), JSON 数组顺序就是 M73..M88
  roundOf16Order: Array<[string, string]>;
}

const SPEED_OPTIONS = [
  { key: 'slow', label: '0.5x', ms: 1600 },
  { key: 'normal', label: '1x', ms: 800 },
  { key: 'fast', label: '2x', ms: 400 },
] as const;
type SpeedKey = (typeof SPEED_OPTIONS)[number]['key'];

// === 12 小组组色 (边框主色) ===
const GROUP_COLORS: Record<string, string> = {
  A: '#22c55e', // 绿
  B: '#ef4444', // 红
  C: '#facc15', // 黄
  D: '#3b82f6', // 蓝
  E: '#a855f7', // 紫
  F: '#06b6d4', // 青
  G: '#ec4899', // 粉
  H: '#84cc16', // 黄绿
  I: '#f97316', // 橙
  J: '#eab308', // 金黄
  K: '#10b981', // 翠绿
  L: '#0ea5e9', // 天蓝
};

// === 几何 (R16 → QF → SF → Final 镜像 4 列 + 中央) ===
// 上半: y 0-50, 下半: y 50-100, 中央 Final y=24, 3rd y=68
// R16 上面 4 场: 7/17/27/45 (M73/M75/M77/M76 错开)
// R16 下面 4 场: 55/65/73/93 (M85/M87/M88/M86 错开)
// QF 上面 2 场: (R16[0]+R16[1])/2, (R16[2]+R16[3])/2
// QF 下面 2 场: (R16[4]+R16[5])/2, (R16[6]+R16[7])/2

// 8 场 R16 配对 (M73-M88 JSON 顺序)
// 视觉: 上半 [0,1,2,3] = M73, M75, M77, M76 (错开)
// 视觉: 下半 [4,5,6,7] = M85, M87, M88, M86 (错开)
// 配对: QF[0] = R16[0]+R16[1], QF[1] = R16[2]+R16[3]
//       QF[2] = R16[4]+R16[5], QF[3] = R16[6]+R16[7]
// SF[0] = QF[0]+QF[1], SF[1] = QF[2]+QF[3]
// FINAL = SF[0]+SF[1]
// 3RD = SF[0] 负 + SF[1] 负

// 6 小组 (上半 A-F) y 坐标
const GROUP_UPPER_Y = [4, 16, 28, 40, 52, 64]; // 6 块, 总 0-66
const GROUP_LOWER_Y = [36, 48, 60, 72, 84, 96]; // 6 块, 总 34-100
// R16 上面 4 场 y: 8/18/30/44 (跟 GROUP 配对, M73 配 A1 vs B2 等)
const R16_UPPER_Y = [8, 18, 30, 44];
// R16 下面 4 场 y
const R16_LOWER_Y = [56, 68, 78, 90];
// QF 上面 2 场
const QF_UPPER_Y = [(R16_UPPER_Y[0] + R16_UPPER_Y[1]) / 2, (R16_UPPER_Y[2] + R16_UPPER_Y[3]) / 2];
// QF 下面 2 场
const QF_LOWER_Y = [(R16_LOWER_Y[0] + R16_LOWER_Y[1]) / 2, (R16_LOWER_Y[2] + R16_LOWER_Y[3]) / 2];
// SF 上半
const SF_UPPER_Y = (QF_UPPER_Y[0] + QF_UPPER_Y[1]) / 2;
const SF_LOWER_Y = (QF_LOWER_Y[0] + QF_LOWER_Y[1]) / 2;
// FINAL 中央
const FINAL_Y = 24;
const THIRD_Y = 70;

export function BracketClient({ initialMatches, groupStandings, roundOf16Order }: Props) {
  const [picks, setPicks] = useState<Record<string, 'home' | 'away'>>({});
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<SpeedKey>('normal');
  const [revealedStage, setRevealedStage] = useState<Stage | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const playTokenRef = useRef(0);

  // 按 stage 分组 (忽略 R32, 走 roundOf16Order)
  const byStage = useMemo(() => {
    const out: Record<Stage, BracketMatch[]> = { R16: [], QF: [], SF: [], FINAL: [], '3RD': [] };
    initialMatches.forEach((m) => {
      if (m.stage in out) out[m.stage as Stage].push(m);
    });
    return out;
  }, [initialMatches]);

  // R16 按 roundOf16Order 顺序 (M73..M88)
  const r16Ordered = useMemo(() => {
    const all = byStage.R16;
    const map = new Map<string, BracketMatch>();
    all.forEach((m) => map.set(`${m.home}|${m.away}`, m));
    const result: BracketMatch[] = [];
    roundOf16Order.forEach(([h, a]) => {
      const m = map.get(`${h}|${a}`) || map.get(`${a}|${h}`);
      if (m) result.push(m);
    });
    if (result.length === 0) return all;
    return result;
  }, [byStage.R16, roundOf16Order]);

  // 派生: cascade (用户改 R16 → QF → SF → Final)
  const derived = useMemo(() => {
    const real: Record<Stage, BracketMatch[]> = { R16: [], QF: [], SF: [], FINAL: [], '3RD': [] };
    // R16: 根据 picks 决定 winner
    for (let i = 0; i < r16Ordered.length; i++) {
      const m = r16Ordered[i];
      const pick = picks[m.match_id];
      const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : m.winner;
      const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
      real.R16.push({ ...m, winner, loser });
    }
    // QF: 邻接 R16[2i]+R16[2i+1]
    const cascade = (src: BracketMatch[], dst: BracketMatch[], dstStage: Stage) => {
      for (let i = 0; i < dst.length; i++) {
        const m = dst[i];
        const a = src[2 * i]?.winner ?? null;
        const b = src[2 * i + 1]?.winner ?? null;
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
        real[dstStage].push({ ...m, home: newHome, away: newAway, winner, loser });
      }
    };
    cascade(real.R16, byStage.QF, 'QF');
    cascade(real.QF, byStage.SF, 'SF');
    // FINAL: SF[0] vs SF[1]
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
    // 3RD: SF[0] 负 vs SF[1] 负
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
  }, [r16Ordered, byStage, picks]);

  // === 交互 ===
  const isLocked = useCallback((m: BracketMatch) => m.data_status === 'real', []);
  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 1800);
  }, []);

  const handlePick = useCallback((team: string | null, m: BracketMatch, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (isLocked(m) || !team) {
      showToast('🔒 该场已完赛或尚未确定');
      return;
    }
    setPicks((prev) => {
      const next = { ...prev };
      const cur = next[m.match_id];
      if (cur === 'home' && m.home === team) delete next[m.match_id];
      else if (cur === 'away' && m.away === team) delete next[m.match_id];
      else if (m.home === team) next[m.match_id] = 'home';
      else if (m.away === team) next[m.match_id] = 'away';
      return next;
    });
  }, [isLocked, showToast]);

  const handleContext = useCallback((m: BracketMatch, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (isLocked(m)) { showToast('🔒 该场已完赛'); return; }
    setPicks((prev) => { const n = { ...prev }; delete n[m.match_id]; return n; });
  }, [isLocked, showToast]);

  const resetAll = useCallback(() => {
    setPicks({});
    setRevealedStage(null);
    setIsPlaying(false);
    showToast('已清空手动标记');
  }, [showToast]);

  // === 播放 ===
  const play = useCallback(async () => {
    if (isPlaying) return;
    setIsPlaying(true);
    const token = ++playTokenRef.current;
    const ms = SPEED_OPTIONS.find((s) => s.key === speed)!.ms;
    const sleep = (dur: number) => new Promise<void>((res) => {
      const start = Date.now();
      const tick = () => {
        if (token !== playTokenRef.current) return res();
        if (Date.now() - start >= dur) res();
        else setTimeout(tick, Math.min(60, dur - (Date.now() - start)));
      };
      tick();
    });
    setRevealedStage('R16');
    await sleep(ms);
    if (token !== playTokenRef.current) return;
    setRevealedStage('QF');
    await sleep(ms);
    if (token !== playTokenRef.current) return;
    setRevealedStage('SF');
    await sleep(ms);
    if (token !== playTokenRef.current) return;
    setRevealedStage('FINAL');
    await sleep(ms);
    if (token !== playTokenRef.current) return;
    setIsPlaying(false);
  }, [isPlaying, speed]);

  useEffect(() => () => { playTokenRef.current++; }, []);

  const champion = derived.FINAL[0]?.winner ?? null;
  const pickMap = picks;

  return (
    <div className="bracket-page">
      <header className="bracket-header">
        <h1 className="bracket-title">FIFA WORLD CUP 2026™</h1>
        <div className="bracket-actions">
          <div className="speed-toggle">
            {SPEED_OPTIONS.map((s) => (
              <button
                key={s.key}
                className={`speed-btn ${speed === s.key ? 'is-active' : ''}`}
                onClick={() => setSpeed(s.key)}
                disabled={isPlaying}
              >{s.label}</button>
            ))}
          </div>
          <button className="play-btn" onClick={play} disabled={isPlaying}>
            {isPlaying ? '⏸ 播放中' : '▶ 播放对阵'}
          </button>
          <button className="reset-btn" onClick={resetAll} disabled={isPlaying}>
            ↺ 重置
          </button>
        </div>
      </header>

      <div className="fifa-bracket">
        {/* SVG 连线层 */}
        <BracketConnectors revealedStage={revealedStage} />

        {/* === 列 1: 6 小组 (左) === */}
        {groupStandings.filter((g) => ['A', 'B', 'C', 'D', 'E', 'F'].includes(g.group)).map((g, i) => (
          <GroupCard key={g.group} g={g} y={GROUP_UPPER_Y[i]} side="left" upper />
        ))}

        {/* === 列 1: 6 小组 (右) === */}
        {groupStandings.filter((g) => ['G', 'H', 'I', 'J', 'K', 'L'].includes(g.group)).map((g, i) => (
          <GroupCard key={g.group} g={g} y={GROUP_LOWER_Y[i]} side="right" lower />
        ))}

        {/* === R16 上面 4 场 === */}
        {derived.R16.slice(0, 4).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-r16-slot"
            style={{ top: `${R16_UPPER_Y[idx]}%`, left: '22%' }}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'R16' || revealedStage === 'QF' || revealedStage === 'SF' || revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              showMatch
            />
          </div>
        ))}

        {/* === R16 下面 4 场 === */}
        {derived.R16.slice(4, 8).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-r16-slot"
            style={{ top: `${R16_LOWER_Y[idx]}%`, left: '78%' }}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'R16' || revealedStage === 'QF' || revealedStage === 'SF' || revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              showMatch
            />
          </div>
        ))}

        {/* === QF 上面 2 场 === */}
        {derived.QF.slice(0, 2).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-qf-slot"
            style={{ top: `${QF_UPPER_Y[idx]}%`, left: '35%' }}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'QF' || revealedStage === 'SF' || revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        ))}

        {/* === QF 下面 2 场 === */}
        {derived.QF.slice(2, 4).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-qf-slot"
            style={{ top: `${QF_LOWER_Y[idx]}%`, left: '65%' }}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'QF' || revealedStage === 'SF' || revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        ))}

        {/* === SF 上面 1 场 === */}
        {derived.SF[0] && (
          <div
            className="fiba-slot fiba-sf-slot"
            style={{ top: `${SF_UPPER_Y}%`, left: '45%' }}
          >
            <MatchPair
              m={derived.SF[0]}
              pick={pickMap[derived.SF[0].match_id]}
              locked={isLocked(derived.SF[0])}
              revealed={revealedStage === 'SF' || revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        )}

        {/* === SF 下面 1 场 === */}
        {derived.SF[1] && (
          <div
            className="fiba-slot fiba-sf-slot"
            style={{ top: `${SF_LOWER_Y}%`, left: '55%' }}
          >
            <MatchPair
              m={derived.SF[1]}
              pick={pickMap[derived.SF[1].match_id]}
              locked={isLocked(derived.SF[1])}
              revealed={revealedStage === 'SF' || revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        )}

        {/* === 中央: Final + 3rd + 奖杯 === */}
        <div className="fiba-center">
          <div className="fiba-champion-title">FINAL</div>
          {derived.FINAL[0] && (
            <div className="fiba-final-wrap" style={{ top: `${FINAL_Y}%` }}>
              <MatchPair
                m={derived.FINAL[0]}
                pick={pickMap[derived.FINAL[0].match_id]}
                locked={isLocked(derived.FINAL[0])}
                revealed={revealedStage === 'FINAL'}
                onPick={handlePick}
                onContext={handleContext}
                size="lg"
                isFinal
              />
            </div>
          )}
          <div className="fiba-trophy-wrap">
            <Trophy />
          </div>
          {derived['3RD'][0] && (
            <div className="fiba-center-3rd" style={{ top: `${THIRD_Y}%` }}>
              <div className="fiba-bronze-label">THIRD PLACE</div>
              <MatchPair
                m={derived['3RD'][0]}
                pick={pickMap[derived['3RD'][0].match_id]}
                locked={isLocked(derived['3RD'][0])}
                revealed={revealedStage === 'FINAL'}
                onPick={handlePick}
                onContext={handleContext}
                size="md"
                isThird
              />
            </div>
          )}
          {champion && (
            <div className="fiba-champion-flag">{flag(champion)}</div>
          )}
        </div>
      </div>

      {toast && <div className="bracket-toast">{toast}</div>}
    </div>
  );
}

// ============== 小组卡片 (2x2 旗 + 4 行) ==============
function GroupCard({ g, y, side, upper, lower }: { g: GroupStanding; y: number; side: 'left' | 'right'; upper?: boolean; lower?: boolean }) {
  const color = GROUP_COLORS[g.group] || '#888';
  // 4 行: pts, gd, gf, ga — 但参考图只显示 2 行 (team + ?) 或者 1 行 4 队
  // 参考图 GROUP 容器: 2x2 旗 (4 队) + 顶/底 槽位 (晋级填充)
  // 我们做 4 队 2x2 grid
  return (
    <div
      className={`fiba-group fiba-group-${side}`}
      style={{
        top: `${y}%`,
        [side === 'left' ? 'left' : 'right']: '1%',
        borderColor: color,
      }}
    >
      <div className="fiba-group-label" style={{ background: color }}>GROUP {g.group}</div>
      <div className="fiba-group-flags">
        {g.rows.slice(0, 4).map(([team, pts, gd, gf, ga], idx) => {
          // 1/2 名绿色边框 (晋级), 3 名橙, 4 名灰
          const pos = idx + 1;
          const teamColor = pos <= 2 ? '#22c55e' : pos === 3 ? '#f97316' : '#666';
          return (
            <div key={team} className={`fiba-group-flag pos-${pos}`} style={{ borderColor: teamColor }} title={`${team} P${pts} GD${gd>0?'+':''}${gd} GF${gf} GA${ga}`}>
              <span className="fiba-group-flag-emoji">{flag(team)}</span>
              <span className="fiba-group-flag-team">{team}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============== 1 场比赛 (2 个旗紧贴) ==============
function MatchPair({
  m, pick, locked, revealed, onPick, onContext, size, isCascade, isFinal, isThird, showMatch,
}: {
  m: BracketMatch;
  pick?: 'home' | 'away';
  locked: boolean;
  revealed: boolean;
  onPick: (team: string | null, m: BracketMatch, e: React.MouseEvent) => void;
  onContext: (m: BracketMatch, e: React.MouseEvent) => void;
  size: 'sm' | 'md' | 'lg';
  isCascade?: boolean;
  isFinal?: boolean;
  isThird?: boolean;
  showMatch?: boolean;
}) {
  const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : m.winner;
  const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
  // match_id 提取 MATCH 数字 (R16_M73 形式 → M73)
  const mLabel = m.match_id.replace(/^R\d+_/, '').replace(/_/g, ' ');
  return (
    <div
      className={`fiba-pair ${isCascade ? 'is-cascade' : ''} ${isFinal ? 'is-final' : ''} ${isThird ? 'is-third' : ''} ${revealed ? 'is-revealed' : ''}`}
      onContextMenu={(e) => onContext(m, e)}
    >
      {showMatch && <div className="fiba-pair-label">{mLabel}</div>}
      <FlagSlot
        team={m.home}
        isWinner={winner === m.home}
        isLoser={loser === m.home}
        locked={locked}
        onClick={(e) => onPick(m.home, m, e)}
        size={size}
      />
      <FlagSlot
        team={m.away}
        isWinner={winner === m.away}
        isLoser={loser === m.away}
        locked={locked}
        onClick={(e) => onPick(m.away, m, e)}
        size={size}
      />
    </div>
  );
}

// ============== 1 个旗 ==============
function FlagSlot({ team, isWinner, isLoser, locked, onClick, size }: {
  team: string;
  isWinner: boolean;
  isLoser: boolean;
  locked: boolean;
  onClick: (e: React.MouseEvent) => void;
  size: 'sm' | 'md' | 'lg';
}) {
  return (
    <button
      className={`fiba-flag fiba-flag-${size} ${isWinner ? 'is-winner' : ''} ${isLoser ? 'is-loser' : ''} ${locked ? 'is-locked' : ''}`}
      onClick={onClick}
    >
      <span className="fiba-flag-emoji">{flag(team)}</span>
      <span className="fiba-flag-team">{team}</span>
    </button>
  );
}

// ============== 奖杯 SVG ==============
function Trophy() {
  return (
    <svg viewBox="0 0 200 280" className="fiba-trophy-svg" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff8dc" />
          <stop offset="0.4" stopColor="#ffd700" />
          <stop offset="0.8" stopColor="#daa520" />
          <stop offset="1" stopColor="#b8860b" />
        </linearGradient>
        <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#22c55e" />
          <stop offset="1" stopColor="#15803d" />
        </linearGradient>
      </defs>
      {/* 杯身 */}
      <path d="M50,40 Q50,180 100,200 Q150,180 150,40 Z" fill="url(#goldGrad)" stroke="#b8860b" strokeWidth="2" />
      {/* 左耳 */}
      <path d="M40,50 Q15,60 20,90 Q25,100 45,90" fill="url(#goldGrad)" stroke="#b8860b" strokeWidth="2" />
      {/* 右耳 */}
      <path d="M160,50 Q185,60 180,90 Q175,100 155,90" fill="url(#goldGrad)" stroke="#b8860b" strokeWidth="2" />
      {/* 底座 */}
      <rect x="70" y="200" width="60" height="20" fill="url(#goldGrad)" stroke="#b8860b" strokeWidth="2" />
      <rect x="55" y="220" width="90" height="30" fill="url(#greenGrad)" stroke="#15803d" strokeWidth="2" />
      <rect x="45" y="250" width="110" height="20" fill="url(#goldGrad)" stroke="#b8860b" strokeWidth="2" />
      {/* 高光 */}
      <ellipse cx="80" cy="80" rx="12" ry="30" fill="#fff" opacity="0.4" />
    </svg>
  );
}

// ============== SVG 折线连接器 ==============
const STAGE_ORDER: Stage[] = ['R16', 'QF', 'SF', 'FINAL'];

function BracketConnectors({ revealedStage }: { revealedStage: Stage | null }) {
  const active = (stage: Stage) => revealedStage && STAGE_ORDER.indexOf(stage) <= STAGE_ORDER.indexOf(revealedStage);

  // 列 x 位置
  const colGroupL = 8;    // 6 小组 (左)
  const colR16L = 24;     // R16 上面 4 场
  const colQFL = 36;      // QF 上面 2 场
  const colSFL = 46;      // SF 上面 1 场
  const colCenter = 50;   // 中央 Final
  const colSFR = 54;      // SF 下面 1 场
  const colQFR = 64;      // QF 下面 2 场
  const colR16R = 76;     // R16 下面 4 场
  const colGroupR = 92;   // 6 小组 (右)
  // 槽宽 ~4%
  const w = 4;
  const colRight = (idx: number) => colX(idx) + w;
  const colLeft = (idx: number) => colX(idx);
  function colX(idx: number): number {
    if (idx === 0) return colGroupL;
    if (idx === 1) return colR16L;
    if (idx === 2) return colQFL;
    if (idx === 3) return colSFL;
    if (idx === 4) return colSFR;
    if (idx === 5) return colQFR;
    if (idx === 6) return colR16R;
    if (idx === 7) return colGroupR;
    return 0;
  }
  const midX = (a: number, b: number) => (colRight(a) + colLeft(b)) / 2;

  // R16 slot 实际 y
  const r16Y = (i: number) => (i < 4 ? R16_UPPER_Y[i] : R16_LOWER_Y[i - 4]);
  const qfY = (i: number) => (i < 2 ? QF_UPPER_Y[i] : QF_LOWER_Y[i - 2]);
  const sfY = (i: number) => (i === 0 ? SF_UPPER_Y : SF_LOWER_Y);

  return (
    <svg className="fiba-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
      {/* === 上半: Group→R16 (省 Group 详细连线, 只画 R16→QF→SF→Final) === */}

      {/* R16 上面 4 场 → QF 上面 2 场 */}
      {Array.from({ length: 2 }).map((_, k) => {
        const yTo = qfY(k);
        return (
          <g key={`r16-qf-upper-${k}`} className={`fiba-line ${active('QF') ? 'is-active' : ''}`}>
            <polyline
              points={`${colRight(1)},${r16Y(2 * k)} ${midX(1, 2)},${r16Y(2 * k)} ${midX(1, 2)},${yTo} ${colLeft(2)},${yTo}`}
              fill="none"
            />
            <polyline
              points={`${colRight(1)},${r16Y(2 * k + 1)} ${midX(1, 2)},${r16Y(2 * k + 1)} ${midX(1, 2)},${yTo} ${colLeft(2)},${yTo}`}
              fill="none"
            />
          </g>
        );
      })}

      {/* QF 上面 2 场 → SF 上面 1 场 */}
      <g className={`fiba-line ${active('SF') ? 'is-active' : ''}`}>
        <polyline
          points={`${colRight(2)},${qfY(0)} ${midX(2, 3)},${qfY(0)} ${midX(2, 3)},${sfY(0)} ${colLeft(3)},${sfY(0)}`}
          fill="none"
        />
        <polyline
          points={`${colRight(2)},${qfY(1)} ${midX(2, 3)},${qfY(1)} ${midX(2, 3)},${sfY(0)} ${colLeft(3)},${sfY(0)}`}
          fill="none"
        />
      </g>

      {/* SF 上面 1 场 → Final */}
      <g className={`fiba-line ${active('FINAL') ? 'is-active' : ''}`}>
        <polyline
          points={`${colRight(3)},${sfY(0)} ${midX(3, 4)},${sfY(0)} ${midX(3, 4)},${FINAL_Y} ${colLeft(4)},${FINAL_Y}`}
          fill="none"
        />
      </g>

      {/* Final → 3rd (失败者) */}
      <g className={`fiba-line ${active('FINAL') ? 'is-active' : ''}`}>
        <polyline
          points={`${colRight(4)},${FINAL_Y} ${midX(4, 4)},${FINAL_Y} ${midX(4, 4)},${THIRD_Y} ${colLeft(4)},${THIRD_Y}`}
          fill="none"
        />
      </g>

      {/* SF 下面 1 场 → Final */}
      <g className={`fiba-line ${active('FINAL') ? 'is-active' : ''}`}>
        <polyline
          points={`${colLeft(4)},${FINAL_Y} ${midX(4, 5)},${FINAL_Y} ${midX(4, 5)},${sfY(1)} ${colRight(5)},${sfY(1)}`}
          fill="none"
        />
      </g>

      {/* QF 下面 2 场 → SF 下面 1 场 */}
      <g className={`fiba-line ${active('SF') ? 'is-active' : ''}`}>
        <polyline
          points={`${colLeft(5)},${sfY(1)} ${midX(4, 5)},${sfY(1)} ${midX(4, 5)},${qfY(2)} ${colRight(6)},${qfY(2)}`}
          fill="none"
        />
        <polyline
          points={`${colLeft(5)},${sfY(1)} ${midX(4, 5)},${sfY(1)} ${midX(4, 5)},${qfY(3)} ${colRight(6)},${qfY(3)}`}
          fill="none"
        />
      </g>

      {/* R16 下面 4 场 → QF 下面 2 场 */}
      {Array.from({ length: 2 }).map((_, k) => {
        const yTo = qfY(k + 2);
        return (
          <g key={`r16-qf-lower-${k}`} className={`fiba-line ${active('QF') ? 'is-active' : ''}`}>
            <polyline
              points={`${colLeft(6)},${r16Y(4 + 2 * k)} ${midX(5, 6)},${r16Y(4 + 2 * k)} ${midX(5, 6)},${yTo} ${colRight(7)},${yTo}`}
              fill="none"
            />
            <polyline
              points={`${colLeft(6)},${r16Y(4 + 2 * k + 1)} ${midX(5, 6)},${r16Y(4 + 2 * k + 1)} ${midX(5, 6)},${yTo} ${colRight(7)},${yTo}`}
              fill="none"
            />
          </g>
        );
      })}
    </svg>
  );
}
