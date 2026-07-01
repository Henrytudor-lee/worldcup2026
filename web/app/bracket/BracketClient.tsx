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

const SPEED_OPTIONS = [
  { key: 'slow', label: '0.5x', ms: 1600 },
  { key: 'normal', label: '1x', ms: 800 },
  { key: 'fast', label: '2x', ms: 400 },
] as const;

type SpeedKey = (typeof SPEED_OPTIONS)[number]['key'];

// FIFA 2026 淘汰赛配对 (按 JSON 实际 home/away 反推, 2026-07-01 验证)
// R16[i] = R32[A] winner (R16[i].home) vs R32[B] winner (R16[i].away)
const R16_PAIRING: Array<[number, number]> = [
  [0, 4],    // R16[0]: 加拿大 vs 德国 = W1 vs W5
  [2, 11],   // R16[1]: 厄瓜多尔 vs 英格兰 = W3 vs W12
  [7, 1],    // R16[2]: 埃及 vs 哥伦比亚 = W8 vs W2
  [5, 10],   // R16[3]: 塞内加尔 vs 美国 = W6 vs W11
  [3, 9],    // R16[4]: 巴西 vs 挪威 = W4 vs W10
  [8, 15],   // R16[5]: 瑞士 vs 阿根廷 = W9 vs W16
  [12, 6],   // R16[6]: 荷兰 vs 法国 = W13 vs W7
  [14, 13],  // R16[7]: 西班牙 vs 葡萄牙 = W15 vs W14
];

// QF 配对
const QF_PAIRING: Array<[number, number]> = [
  [2, 5],   // QF[0]: 哥伦比亚 vs 阿根廷 = R16[2] vs R16[5]
  [0, 4],   // QF[1]: 德国 vs 巴西 = R16[0] vs R16[4]
  [6, 1],   // QF[2]: 荷兰 vs 英格兰 = R16[6] vs R16[1]
  [7, 3],   // QF[3]: 葡萄牙 vs 塞内加尔 = R16[7] vs R16[3]
];

// SF 配对
const SF_PAIRING: Array<[number, number]> = [
  [1, 2],  // SF[0]: 德国 vs 荷兰 = QF[1] vs QF[2]
  [3, 0],  // SF[1]: 葡萄牙 vs 阿根廷 = QF[3] vs QF[0]
];

// FIFA 2026 官方 R32 顺序 (M1-M16)
// 顺序数组的每项是 R32 match_id 中"vs"前的 home 队名
const OFFICIAL_R32_ORDER: string[] = [
  // 上半
  '南非',         // M73 (vs 加拿大)
  '哥伦比亚',     // M74 (vs 加纳)
  '墨西哥',       // M75 (vs 厄瓜多尔)
  '巴西',         // M76 (vs 日本)
  '德国',         // M77 (vs 巴拉圭)
  '比利时',       // M78 (vs 塞内加尔)
  '美国',         // M79 (vs 波黑)
  '法国',         // M80 (vs 瑞典)
  // 下半
  '埃及',         // M81 (vs 澳大利亚)
  '瑞士',         // M82 (vs 阿尔及利亚)
  '科特迪瓦',     // M83 (vs 挪威)
  '英格兰',       // M84 (vs 民主刚果)
  '荷兰',         // M85 (vs 摩洛哥)
  '葡萄牙',       // M86 (vs 克罗地亚)
  '西班牙',       // M87 (vs 奥地利)
  '阿根廷',       // M88 (vs 佛得角)
];

export function BracketClient({ initialMatches }: Props) {
  // ---- state ----
  const [picks, setPicks] = useState<Record<string, 'home' | 'away'>>({});
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<SpeedKey>('normal');
  const [revealedStage, setRevealedStage] = useState<Stage | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const playTokenRef = useRef(0);

  // ---- 用官方对阵表 M73-M88 顺序生成 R32 ----
  const r32Ordered = useMemo(() => {
    const all = initialMatches.filter((m) => m.stage === 'R32');
    if (all.length === 0) return [];
    // 用 OFFICIAL_R32_ORDER (按 home 队名) 排
    const orderMap = new Map<string, number>();
    OFFICIAL_R32_ORDER.forEach((home, idx) => orderMap.set(home, idx));
    const sorted = [...all].sort((a, b) => {
      const idxA = orderMap.get(a.home);
      const idxB = orderMap.get(b.home);
      if (idxA !== undefined && idxB !== undefined) return idxA - idxB;
      if (idxA !== undefined) return -1;
      if (idxB !== undefined) return 1;
      return a.match_id.localeCompare(b.match_id);
    });
    return sorted.slice(0, 16);
  }, [initialMatches]);

  // ---- 派生：按 R32 选出的胜者递推 R16/QF/SF/Final/3rd ----
  const derived = useMemo(() => {
    const real: Record<Stage, BracketMatch[]> = { R32: [], R16: [], QF: [], SF: [], FINAL: [], '3RD': [] };

    // R32
    for (let i = 0; i < r32Ordered.length; i++) {
      const m = r32Ordered[i];
      const pick = picks[m.match_id];
      const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : m.winner;
      const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
      real.R32.push({ ...m, winner, loser });
    }

    // 通用级联函数: 用指定的 pairing 数组
    const cascade = (
      srcList: BracketMatch[],
      dstList: BracketMatch[],
      pairing: Array<[number, number]>,
      dst: Stage,
    ) => {
      for (let i = 0; i < dstList.length; i++) {
        const m = dstList[i];
        const [aIdx, bIdx] = pairing[i] ?? [2 * i, 2 * i + 1];
        const a = srcList[aIdx]?.winner ?? null;
        const b = srcList[bIdx]?.winner ?? null;
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
        real[dst].push({ ...m, home: newHome, away: newAway, winner, loser });
      }
    };

    const r16Raw = initialMatches.filter((m) => m.stage === 'R16').sort((a, b) => a.match_id.localeCompare(b.match_id));
    const qfRaw = initialMatches.filter((m) => m.stage === 'QF').sort((a, b) => a.match_id.localeCompare(b.match_id));
    const sfRaw = initialMatches.filter((m) => m.stage === 'SF').sort((a, b) => a.match_id.localeCompare(b.match_id));
    const finRaw = initialMatches.filter((m) => m.stage === 'FINAL');
    const thirdRaw = initialMatches.filter((m) => m.stage === '3RD');

    cascade(real.R32, r16Raw, R16_PAIRING, 'R16');
    cascade(real.R16, qfRaw, QF_PAIRING, 'QF');
    cascade(real.QF, sfRaw, SF_PAIRING, 'SF');

    // FINAL: SF[0] winner vs SF[1] winner
    if (finRaw[0]) {
      const m = finRaw[0];
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
    if (thirdRaw[0]) {
      const m = thirdRaw[0];
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
  }, [r32Ordered, picks, initialMatches]);

  // ---- 交互 ----
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
        if (Date.now() - start >= dur) res();
        else setTimeout(tick, Math.min(60, dur - (Date.now() - start)));
      };
      tick();
    });

    setRevealedStage('R32');
    await sleep(ms);
    if (token !== playTokenRef.current) return;
    for (const stage of ['R16', 'QF', 'SF', 'FINAL'] as Stage[]) {
      setRevealedStage(stage);
      await sleep(ms);
      if (token !== playTokenRef.current) return;
    }
    setIsPlaying(false);
  }, [isPlaying, speed]);

  const stopPlay = useCallback(() => {
    playTokenRef.current++;
    setIsPlaying(false);
  }, []);

  useEffect(() => () => { playTokenRef.current++; }, []);

  const champion = derived.FINAL[0]?.winner ?? null;
  const thirdWinner = derived['3RD'][0]?.winner ?? null;

  return (
    <div className="bracket-page">
      <header className="bracket-header">
        <h1 className="bracket-title">FIFA WORLD CUP 2026™</h1>
        <div className="bracket-actions">
          <div className="speed-group">
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
            {isPlaying ? '⏸ 暂停' : '▶ 播放对阵'}
          </button>
          <button className="reset-btn" onClick={resetAll} disabled={isPlaying}>
            ↺ 重置
          </button>
        </div>
      </header>

      <div className="fiba-bracket">
        {/* ====== 8 列布局 ====== */}
        {/* L1: 上半 R32 8 场 | L2: 上半 R16 4 场 | L3: 上半 QF 2 场 | L4: 上半 SF 1 场 */}
        {/* L5: 下半 SF 1 场 | L6: 下半 QF 2 场 | L7: 下半 R16 4 场 | L8: 下半 R32 8 场 */}
        <div className="fiba-half fiba-upper">
          <R32Column
            matches={derived.R32.slice(0, 8)}
            picks={picks}
            isLocked={isLocked}
            revealed={revealedStage === 'R32'}
            onPick={handlePick}
            onContext={handleContext}
            half="upper"
          />
          <CascadeColumn
            matches={derived.R16}
            picks={picks}
            isLocked={isLocked}
            revealed={revealedStage === 'R16'}
            onPick={handlePick}
            onContext={handleContext}
            half="upper"
            count={4}
            step={2}
            nextCount={2}
            label="R16"
          />
          <CascadeColumn
            matches={derived.QF}
            picks={picks}
            isLocked={isLocked}
            revealed={revealedStage === 'QF'}
            onPick={handlePick}
            onContext={onContextSafe}
            half="upper"
            count={2}
            step={4}
            nextCount={1}
            label="QF"
          />
          <FinalSlot
            matches={derived.SF}
            picks={picks}
            isLocked={isLocked}
            revealed={revealedStage === 'SF'}
            onPick={handlePick}
            onContext={handleContext}
            half="upper"
          />
        </div>

        {/* ====== 中央: WORLD CHAMPION 标题 + 决赛旗 + BRONZE FINAL 标签 + 3rd 旗 + 奖杯 ====== */}
        <div className="fiba-center">
          <div className="fiba-center-section">
            <div className="fiba-champion-title">WORLD<br/>CHAMPION</div>
            <FinalCard
              m={derived.FINAL[0]}
              pick={picks[derived.FINAL[0]?.match_id ?? '']}
              locked={derived.FINAL[0] ? isLocked(derived.FINAL[0]) : false}
              revealed={revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
            />
            <div className="fiba-bronze-label">BRONZE FINAL</div>
            <ThirdCard
              m={derived['3RD'][0]}
              pick={picks[derived['3RD'][0]?.match_id ?? '']}
              locked={derived['3RD'][0] ? isLocked(derived['3RD'][0]) : false}
              revealed={revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
            />
          </div>
          <div className="fiba-trophy">
            <Trophy />
          </div>
          <div className="fiba-wc26">
            <span className="fiba-wc26-num">26</span>
            <span className="fiba-wc26-text">FIFA WORLD CUP 2026</span>
          </div>
        </div>

        {/* ====== 下半 (镜像) ====== */}
        <div className="fiba-half fiba-lower">
          <FinalSlot
            matches={derived.SF.slice(1, 2)}
            picks={picks}
            isLocked={isLocked}
            revealed={revealedStage === 'SF'}
            onPick={handlePick}
            onContext={handleContext}
            half="lower"
          />
          <CascadeColumn
            matches={derived.QF.slice(2, 4)}
            picks={picks}
            isLocked={isLocked}
            revealed={revealedStage === 'QF'}
            onPick={handlePick}
            onContext={onContextSafe}
            half="lower"
            count={2}
            step={4}
            nextCount={1}
            label="QF"
          />
          <CascadeColumn
            matches={derived.R16.slice(4, 8)}
            picks={picks}
            isLocked={isLocked}
            revealed={revealedStage === 'R16'}
            onPick={handlePick}
            onContext={handleContext}
            half="lower"
            count={4}
            step={2}
            nextCount={2}
            label="R16"
          />
          <R32Column
            matches={derived.R32.slice(8, 16)}
            picks={picks}
            isLocked={isLocked}
            revealed={revealedStage === 'R32'}
            onPick={handlePick}
            onContext={handleContext}
            half="lower"
          />
        </div>
      </div>

      {toast && <div className="bracket-toast">{toast}</div>}
    </div>
  );
}

// 安全右键回调 (避免未传导致错误)
function onContextSafe() {}

// ============== R32 单列 (8 场堆叠) ==============
function R32Column({
  matches, picks, isLocked, revealed, onPick, onContext, half,
}: {
  matches: BracketMatch[];
  picks: Record<string, 'home' | 'away'>;
  isLocked: (m: BracketMatch) => boolean;
  revealed: boolean;
  onPick: (team: string | null, m: BracketMatch, e: React.MouseEvent) => void;
  onContext: (m: BracketMatch, e: React.MouseEvent) => void;
  half: 'upper' | 'lower';
}) {
  return (
    <div className={`fiba-col fiba-col-r32 fiba-col-r32-${half}`}>
      {matches.map((m, idx) => (
        <MatchSlot
          key={m.match_id}
          m={m}
          pick={picks[m.match_id]}
          locked={isLocked(m)}
          revealed={revealed}
          onPick={onPick}
          onContext={onContext}
          // R32: 每场 2 个旗子垂直堆叠 (home 在上, away 在下)
        />
      ))}
    </div>
  );
}

// ============== 1 场比赛 (含 home/away 旗) ==============
function MatchSlot({
  m, pick, locked, revealed, onPick, onContext,
}: {
  m: BracketMatch;
  pick?: 'home' | 'away';
  locked: boolean;
  revealed: boolean;
  onPick: (team: string | null, m: BracketMatch, e: React.MouseEvent) => void;
  onContext: (m: BracketMatch, e: React.MouseEvent) => void;
}) {
  const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : m.winner;
  const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
  return (
    <div
      className={`fiba-match ${locked ? 'is-locked' : ''} ${revealed ? 'is-revealed' : ''} ${m.data_status === 'real' ? 'is-real' : ''}`}
      onContextMenu={(e) => onContext(m, e)}
    >
      <FlagChip
        team={m.home}
        isWinner={winner === m.home}
        isLoser={loser === m.home}
        locked={locked || m.data_status === 'real'}
        realScore={m.actual_score?.split('-')[0]}
        wentToPen={m.went_to_pen && winner === m.home}
        onClick={(e) => onPick(m.home, m, e)}
      />
      <FlagChip
        team={m.away}
        isWinner={winner === m.away}
        isLoser={loser === m.away}
        locked={locked || m.data_status === 'real'}
        realScore={m.actual_score?.split('-')[1]}
        wentToPen={m.went_to_pen && winner === m.away}
        onClick={(e) => onPick(m.away, m, e)}
      />
    </div>
  );
}

// ============== 1 面旗 (圆角矩形 + emoji) ==============
function FlagChip({
  team, isWinner, isLoser, locked, realScore, wentToPen, onClick,
}: {
  team: string;
  isWinner: boolean;
  isLoser: boolean;
  locked: boolean;
  realScore?: string;
  wentToPen?: boolean;
  onClick: (e: React.MouseEvent) => void;
}) {
  return (
    <button
      className={`fiba-flag ${isWinner ? 'is-winner' : ''} ${isLoser ? 'is-loser' : ''} ${locked ? 'is-locked' : ''}`}
      onClick={onClick}
      title={locked ? '🔒 已完赛' : '左键晋级 / 右键退回'}
    >
      <span className="fiba-flag-emoji">{flag(team)}</span>
      {isWinner && <span className="fiba-flag-star">★</span>}
      {realScore !== undefined && realScore !== null && (
        <span className="fiba-flag-score">{realScore}</span>
      )}
      {wentToPen && <span className="fiba-flag-pen">点</span>}
    </button>
  );
}

// ==============? 旗 (无队伍) ==============
function EmptyFlag() {
  return (
    <div className="fiba-flag fiba-flag-empty">
      <span className="fiba-flag-q">?</span>
    </div>
  );
}

// ============== Cascade 列 (R16/QF: 几个空旗槽位 + 比赛旗) ==============
function CascadeColumn({
  matches, picks, isLocked, revealed, onPick, onContext, half, count, step, nextCount, label,
}: {
  matches: BracketMatch[];
  picks: Record<string, 'home' | 'away'>;
  isLocked: (m: BracketMatch) => boolean;
  revealed: boolean;
  onPick: (team: string | null, m: BracketMatch, e: React.MouseEvent) => void;
  onContext: (m: BracketMatch, e: React.MouseEvent) => void;
  half: 'upper' | 'lower';
  count: number;
  step: number;
  nextCount: number;
  label: string;
}) {
  return (
    <div className={`fiba-col fiba-col-cascade fiba-col-${label.toLowerCase()} fiba-col-${label.toLowerCase()}-${half}`}>
      {matches.slice(0, count).map((m, idx) => (
        <div key={m.match_id} className="fiba-cascade-cell">
          <MatchSlot
            m={m}
            pick={picks[m.match_id]}
            locked={isLocked(m)}
            revealed={revealed}
            onPick={onPick}
            onContext={onContext}
          />
        </div>
      ))}
    </div>
  );
}

// ============== FinalSlot (SF: 1 个比赛) ==============
function FinalSlot({
  matches, picks, isLocked, revealed, onPick, onContext, half,
}: {
  matches: BracketMatch[];
  picks: Record<string, 'home' | 'away'>;
  isLocked: (m: BracketMatch) => boolean;
  revealed: boolean;
  onPick: (team: string | null, m: BracketMatch, e: React.MouseEvent) => void;
  onContext: (m: BracketMatch, e: React.MouseEvent) => void;
  half: 'upper' | 'lower';
}) {
  return (
    <div className={`fiba-col fiba-col-sf fiba-col-sf-${half}`}>
      {matches.slice(0, 1).map((m) => (
        <MatchSlot
          key={m.match_id}
          m={m}
          pick={picks[m.match_id]}
          locked={isLocked(m)}
          revealed={revealed}
          onPick={onPick}
          onContext={onContext}
        />
      ))}
    </div>
  );
}

// ============== 决赛中央卡 (大旗 + WORLD CHAMPION) ==============
function FinalCard({ m, pick, locked, revealed, onPick, onContext }: any) {
  if (!m) return <EmptyFlag />;
  const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : m.winner;
  const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
  return (
    <div
      className={`fiba-final-card ${locked ? 'is-locked' : ''} ${revealed ? 'is-revealed' : ''}`}
      onContextMenu={(e) => onContext(m, e)}
    >
      <FlagChip
        team={m.home}
        isWinner={winner === m.home}
        isLoser={loser === m.home}
        locked={locked}
        realScore={m.actual_score?.split('-')[0]}
        wentToPen={m.went_to_pen && winner === m.home}
        onClick={(e) => onPick(m.home, m, e)}
        large
      />
      <FlagChip
        team={m.away}
        isWinner={winner === m.away}
        isLoser={loser === m.away}
        locked={locked}
        realScore={m.actual_score?.split('-')[1]}
        wentToPen={m.went_to_pen && winner === m.away}
        onClick={(e) => onPick(m.away, m, e)}
        large
      />
    </div>
  );
}

function ThirdCard({ m, pick, locked, revealed, onPick, onContext }: any) {
  if (!m) return <EmptyFlag />;
  const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : m.winner;
  const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
  return (
    <div
      className={`fiba-third-card ${locked ? 'is-locked' : ''} ${revealed ? 'is-revealed' : ''}`}
      onContextMenu={(e) => onContext(m, e)}
    >
      <FlagChip
        team={m.home}
        isWinner={winner === m.home}
        isLoser={loser === m.home}
        locked={locked}
        realScore={m.actual_score?.split('-')[0]}
        onClick={(e) => onPick(m.home, m, e)}
      />
      <FlagChip
        team={m.away}
        isWinner={winner === m.away}
        isLoser={loser === m.away}
        locked={locked}
        realScore={m.actual_score?.split('-')[1]}
        onClick={(e) => onPick(m.away, m, e)}
      />
    </div>
  );
}

// ============== 奖杯 SVG ==============
function Trophy() {
  return (
    <svg viewBox="0 0 200 280" className="fiba-trophy-svg" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="trophyGold" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#f9d976" />
          <stop offset="35%" stopColor="#e6a83a" />
          <stop offset="65%" stopColor="#b8860b" />
          <stop offset="100%" stopColor="#7a5a00" />
        </linearGradient>
        <linearGradient id="trophyBase" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#d4a843" />
          <stop offset="50%" stopColor="#a47a18" />
          <stop offset="100%" stopColor="#5a3f00" />
        </linearGradient>
        <radialGradient id="trophyGloss" cx="30%" cy="30%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.7)" />
          <stop offset="50%" stopColor="rgba(255,255,255,0)" />
        </radialGradient>
      </defs>
      {/* Globe top */}
      <circle cx="100" cy="50" r="35" fill="url(#trophyGold)" />
      <circle cx="100" cy="50" r="35" fill="url(#trophyGloss)" />
      {/* Continents (abstract) */}
      <path d="M 80 35 Q 90 30 100 38 Q 110 32 118 42 Q 110 50 100 48 Q 90 52 82 45 Z" fill="rgba(80,50,0,0.5)" />
      <path d="M 88 55 Q 100 50 110 60 Q 105 70 95 68 Q 85 65 88 55 Z" fill="rgba(80,50,0,0.5)" />
      {/* Stem */}
      <path d="M 85 85 L 80 130 L 120 130 L 115 85 Z" fill="url(#trophyGold)" />
      <ellipse cx="100" cy="135" rx="30" ry="6" fill="url(#trophyBase)" />
      {/* Base ring */}
      <ellipse cx="100" cy="155" rx="35" ry="8" fill="url(#trophyBase)" />
      <ellipse cx="100" cy="170" rx="40" ry="10" fill="url(#trophyBase)" />
      <ellipse cx="100" cy="155" rx="35" ry="8" fill="rgba(255,255,255,0.15)" />
      {/* Plinth */}
      <rect x="60" y="180" width="80" height="50" rx="4" fill="url(#trophyBase)" />
      <rect x="60" y="180" width="80" height="6" fill="rgba(255,255,255,0.2)" />
      {/* Reflection text "WORLD CUP" on plinth */}
      <text x="100" y="210" textAnchor="middle" fill="#3a2a00" fontSize="11" fontWeight="700" fontFamily="Arial, sans-serif" letterSpacing="1">FIFA</text>
      <text x="100" y="223" textAnchor="middle" fill="#3a2a00" fontSize="8" fontWeight="600" fontFamily="Arial, sans-serif" letterSpacing="0.5">WORLD CUP</text>
    </svg>
  );
}
