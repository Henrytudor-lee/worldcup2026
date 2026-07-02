'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { flag } from '../lib/flag';

// === 比赛类型: R32 / R16 / QF / SF / FINAL / 3RD ===
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

export interface GroupStanding {
  group: string;
  rows: Array<[string, number, number, number, number]>;
}

interface Props {
  initialMatches: BracketMatch[];
  groupStandings: GroupStanding[];
  // 32 强配对 (M1-M16), JSON 数组顺序就是 M1..M16
  roundOf32Order: Array<[string, string]>;
}

const SPEED_OPTIONS = [
  { key: 'slow', label: '0.5x', ms: 1600 },
  { key: 'normal', label: '1x', ms: 800 },
  { key: 'fast', label: '2x', ms: 400 },
] as const;
type SpeedKey = (typeof SPEED_OPTIONS)[number]['key'];

// === 12 小组组色 ===
const GROUP_COLORS: Record<string, string> = {
  A: '#22c55e', B: '#ef4444', C: '#facc15', D: '#3b82f6',
  E: '#a855f7', F: '#06b6d4', G: '#ec4899', H: '#84cc16',
  I: '#f97316', J: '#eab308', K: '#10b981', L: '#0ea5e9',
};

// === 6 小组均分 0-100% (A 顶, F 底) — 镜像用 (6 块) ===
const GROUP_Y = [8.33, 25, 41.67, 58.33, 75, 91.67];
// === 8 场 R32 均分 0-100% — FIFA 官方配对顺序 ===
// 上面 8 场 (M1,M3,M2,M5,M4,M6,M7,M8) 邻接配 R16 上面 4 场
const R32_UPPER_Y = [6.25, 18.75, 31.25, 43.75, 56.25, 68.75, 81.25, 93.75];
const R32_LOWER_Y = R32_UPPER_Y.slice().reverse();
// === 4 场 R16 均分 0-100% (邻接配对 y) ===
// R16[0] = (R32[0]+R32[1])/2 = 12.5
// R16[1] = (R32[2]+R32[3])/2 = 37.5
// R16[2] = (R32[4]+R32[5])/2 = 62.5
// R16[3] = (R32[6]+R32[7])/2 = 87.5
const R16_Y = [12.5, 37.5, 62.5, 87.5];
// === 2 场 QF 均分 0-100% ===
const QF_Y = [25, 75];
// === SF 上半/下半 50% 中点 ===
const SF_UPPER_Y = 25;
const SF_LOWER_Y = 75;
// === Final 中央 (50%) ===
const FINAL_Y = 25;
const THIRD_Y = 75;

// 邻接配对 R16[i] = R32[2i] + R32[2i+1]
// R32 顺序本身已经按 FIFA 官方 bracket 几何错开排好 (M3,M6,M1,M4,M12,M11,M10,M9 / M2,M5,M7,M8,M15,M14,M13,M16)
// 所以 R16 配对是邻接的
const R16_PAIRING: Array<[number, number]> = [
  [0, 1], [2, 3], [4, 5], [6, 7],   // R16 上面 4 场
  [8, 9], [10, 11], [12, 13], [14, 15], // R16 下面 4 场
];
const QF_PAIRING: Array<[number, number]> = [
  [0, 1], [2, 3], [4, 5], [6, 7],
];
const SF_PAIRING: Array<[number, number]> = [
  [0, 1], [2, 3],
];

export function BracketClient({ initialMatches, groupStandings, roundOf32Order }: Props) {
  const [picks, setPicks] = useState<Record<string, 'home' | 'away'>>({});
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<SpeedKey>('normal');
  const [revealedStage, setRevealedStage] = useState<Stage | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const playTokenRef = useRef(0);

  // 按 stage 分组
  const byStage = useMemo(() => {
    const out: Record<Stage, BracketMatch[]> = { R32: [], R16: [], QF: [], SF: [], FINAL: [], '3RD': [] };
    initialMatches.forEach((m) => {
      if (m.stage in out) out[m.stage as Stage].push(m);
    });
    return out;
  }, [initialMatches]);

  // R32 按 FIFA 官方 bracket 几何顺序 (参考图 MATCH 73-88 顺序):
  //   上半 8 场 (MATCH 74,77,73,75,83,84,81,82) = M3,M6,M1,M4,M12,M11,M10,M9
  //   下半 8 场 (MATCH 76,78,79,80,86,88,85,87) = M2,M5,M7,M8,M15,M14,M13,M16
  // 这样 R16 上面 4 场 (89,90,93,94) 配对 = (M3胜+M6胜)(M1胜+M4胜)(M12胜+M11胜)(M10胜+M9胜)
  // 邻接配 R32[2i]+R32[2i+1] 即可得到参考图 MATCH 89-96
  const R32_BRACKET_ORDER: Array<[string, string]> = [
    // 上半 8 场 (列 2 左) — 按 R16 配对错开: (M3,M6)(M1,M4)(M12,M11)(M10,M9)
    roundOf32Order[2],  // M3  德国 vs 巴拉圭
    roundOf32Order[5],  // M6  法国 vs 瑞典
    roundOf32Order[0],  // M1  南非 vs 加拿大
    roundOf32Order[3],  // M4  荷兰 vs 摩洛哥
    roundOf32Order[11], // M12 葡萄牙 vs 克罗地亚
    roundOf32Order[10], // M11 西班牙 vs 奥地利
    roundOf32Order[9],  // M10 美国 vs 波黑
    roundOf32Order[8],  // M9  比利时 vs 塞内加尔
    // 下半 8 场 (列 2 右镜像) — 按 R16 配对错开: (M2,M7)(M5,M8)(M15,M14)(M13,M16)
    roundOf32Order[1],  // M2  巴西 vs 日本
    roundOf32Order[4],  // M5  科特迪瓦 vs 挪威
    roundOf32Order[6],  // M7  墨西哥 vs 厄瓜多尔
    roundOf32Order[7],  // M8  英格兰 vs 民主刚果
    roundOf32Order[14], // M15 阿根廷 vs 佛得角
    roundOf32Order[13], // M14 澳大利亚 vs 埃及
    roundOf32Order[12], // M13 瑞士 vs 阿尔及利亚
    roundOf32Order[15], // M16 哥伦比亚 vs 加纳
  ];

  const r32Ordered = useMemo(() => {
    const all = byStage.R32;
    if (all.length === 0) return all;
    const map = new Map<string, BracketMatch>();
    all.forEach((m) => map.set(`${m.home}|${m.away}`, m));
    map.set; // tsc
    const result: BracketMatch[] = [];
    R32_BRACKET_ORDER.forEach(([h, a]) => {
      const m = map.get(`${h}|${a}`) || map.get(`${a}|${h}`);
      if (m) result.push(m);
    });
    return result.length > 0 ? result : all;
  }, [byStage.R32, roundOf32Order]);

  // R16 保持 JSON 数组顺序 (R16-1..R16-8 = M89..M96)
  const r16Ordered = useMemo(() => [...byStage.R16], [byStage.R16]);

  // 派生 cascade
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

    // R16 (FIFA 官方错开配对, R16_PAIRING[i] 取 R32 胜者按 bracket 几何错开)
    for (let i = 0; i < r16Ordered.length; i++) {
      const m = r16Ordered[i];
      const [a, b] = R16_PAIRING[i] ?? [2 * i, 2 * i + 1];
      const srcA = real.R32[a]?.winner ?? null;
      const srcB = real.R32[b]?.winner ?? null;
      const newHome = srcA ?? m.home;
      const newAway = srcB ?? m.away;
      const pick = picks[m.match_id];
      let winner: string | null = m.winner;
      let loser: string | null = m.loser;
      if (pick === 'home') { winner = newHome; loser = newAway; }
      else if (pick === 'away') { winner = newAway; loser = newHome; }
      else if (winner && (winner !== newHome && winner !== newAway)) {
        winner = null; loser = null;
      }
      real.R16.push({ ...m, home: newHome, away: newAway, winner, loser });
    }

    // QF
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

    // FINAL
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

    // 3RD
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
  }, [r32Ordered, r16Ordered, byStage, picks]);

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
    for (const stage of ['R32', 'R16', 'QF', 'SF', 'FINAL'] as Stage[]) {
      setRevealedStage(stage);
      await sleep(ms);
      if (token !== playTokenRef.current) return;
    }
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

      <div className="fiba-bracket">
        {/* SVG 连线层 */}
        <BracketConnectors revealedStage={revealedStage} />

        {/* === 列 1: 6 小组 (左 A-F 0-100%, 右 G-L 0-100% 镜像) === */}
        {groupStandings.filter((g) => ['A', 'B', 'C', 'D', 'E', 'F'].includes(g.group)).map((g, i) => (
          <GroupCard key={g.group} g={g} y={GROUP_Y[i]} side="left" />
        ))}
        {groupStandings.filter((g) => ['G', 'H', 'I', 'J', 'K', 'L'].includes(g.group)).map((g, i) => (
          <GroupCard key={g.group} g={g} y={GROUP_Y[i]} side="right" />
        ))}

        {/* === 列 2: 8 场 R32 (左 0-100%, 右镜像 100-0%) === */}
        {derived.R32.slice(0, 8).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-r32-slot"
            style={{ top: `${R32_UPPER_Y[idx]}%`, left: '13%' }}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'R32' || revealedStage === 'R16' || revealedStage === 'QF' || revealedStage === 'SF' || revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              showMatch
            />
          </div>
        ))}
        {derived.R32.slice(8, 16).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-r32-slot"
            style={{ top: `${R32_LOWER_Y[idx]}%`, left: '87%' }}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'R32' || revealedStage === 'R16' || revealedStage === 'QF' || revealedStage === 'SF' || revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              showMatch
            />
          </div>
        ))}

        {/* === 列 3: 4 场 R16 (左 0-100%, 右镜像) === */}
        {derived.R16.slice(0, 4).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-r16-slot"
            style={{ top: `${R16_Y[idx]}%`, left: '23%' }}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'R16' || revealedStage === 'QF' || revealedStage === 'SF' || revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        ))}
        {derived.R16.slice(4, 8).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-r16-slot"
            style={{ top: `${R16_Y[idx]}%`, left: '77%' }}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'R16' || revealedStage === 'QF' || revealedStage === 'SF' || revealedStage === 'FINAL'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        ))}

        {/* === 列 4: 2 场 QF (左 0/50%, 右 50/100%) === */}
        {derived.QF.slice(0, 2).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-qf-slot"
            style={{ top: `${QF_Y[idx]}%`, left: '32%' }}
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
        {derived.QF.slice(2, 4).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-qf-slot"
            style={{ top: `${QF_Y[idx]}%`, left: '68%' }}
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

        {/* === 列 5: SF (左 25%, 右 75%) === */}
        {derived.SF[0] && (
          <div
            className="fiba-slot fiba-sf-slot"
            style={{ top: `${SF_UPPER_Y}%`, left: '41%' }}
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
        {derived.SF[1] && (
          <div
            className="fiba-slot fiba-sf-slot"
            style={{ top: `${SF_LOWER_Y}%`, left: '59%' }}
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

        {/* === 中央列: Final + 3rd + 奖杯 === */}
        <div className="fiba-center">
          <div className="fiba-champion-title">FINAL</div>
          {derived.FINAL[0] && (
            <div className="fiba-final-wrap" style={{ top: `${FINAL_Y - 6}%` }}>
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
          <div className="fiba-trophy-wrap" style={{ top: '38%' }}>
            <Trophy />
          </div>
          {derived['3RD'][0] && (
            <div className="fiba-center-3rd" style={{ top: `${THIRD_Y - 6}%` }}>
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
          {champion && <div className="fiba-champion-flag">{flag(champion)}</div>}
        </div>
      </div>

      {toast && <div className="bracket-toast">{toast}</div>}
    </div>
  );
}

// ============== 小组卡片 ==============
function GroupCard({ g, y, side }: { g: GroupStanding; y: number; side: 'left' | 'right' }) {
  const color = GROUP_COLORS[g.group] || '#888';
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

// ============== 1 场比赛 ==============
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
  const mLabel = m.match_id.replace(/^R\d+_/, '').replace(/_/g, ' ');
  return (
    <div
      className={`fiba-pair ${isCascade ? 'is-cascade' : ''} ${isFinal ? 'is-final' : ''} ${isThird ? 'is-third' : ''} ${revealed ? 'is-revealed' : ''}`}
      onContextMenu={(e) => onContext(m, e)}
    >
      {showMatch && <div className="fiba-pair-label">{mLabel}</div>}
      <FlagSlot team={m.home} isWinner={winner === m.home} isLoser={loser === m.home} locked={locked} onClick={(e) => onPick(m.home, m, e)} size={size} />
      <FlagSlot team={m.away} isWinner={winner === m.away} isLoser={loser === m.away} locked={locked} onClick={(e) => onPick(m.away, m, e)} size={size} />
    </div>
  );
}

// ============== 旗 ==============
function FlagSlot({ team, isWinner, isLoser, locked, onClick, size }: {
  team: string; isWinner: boolean; isLoser: boolean; locked: boolean;
  onClick: (e: React.MouseEvent) => void; size: 'sm' | 'md' | 'lg';
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

// ============== 奖杯 ==============
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
      <path d="M50,40 Q50,180 100,200 Q150,180 150,40 Z" fill="url(#goldGrad)" stroke="#b8860b" strokeWidth="2" />
      <path d="M40,50 Q15,60 20,90 Q25,100 45,90" fill="url(#goldGrad)" stroke="#b8860b" strokeWidth="2" />
      <path d="M160,50 Q185,60 180,90 Q175,100 155,90" fill="url(#goldGrad)" stroke="#b8860b" strokeWidth="2" />
      <rect x="70" y="200" width="60" height="20" fill="url(#goldGrad)" stroke="#b8860b" strokeWidth="2" />
      <rect x="55" y="220" width="90" height="30" fill="url(#greenGrad)" stroke="#15803d" strokeWidth="2" />
      <rect x="45" y="250" width="110" height="20" fill="url(#goldGrad)" stroke="#b8860b" strokeWidth="2" />
      <ellipse cx="80" cy="80" rx="12" ry="30" fill="#fff" opacity="0.4" />
    </svg>
  );
}

// ============== SVG 折线 ==============
const STAGE_ORDER: Stage[] = ['R32', 'R16', 'QF', 'SF', 'FINAL'];

function BracketConnectors({ revealedStage }: { revealedStage: Stage | null }) {
  const active = (stage: Stage) => revealedStage && STAGE_ORDER.indexOf(stage) <= STAGE_ORDER.indexOf(revealedStage);
  // 列 x: 5 列 (左 R32/R16/QF/SF + 右 SF/QF/R16/R32)
  const colR32L = 14;
  const colR16L = 24;
  const colQFL = 33;
  const colSFL = 42;
  const colSFR = 58;
  const colQFR = 67;
  const colR16R = 76;
  const colR32R = 86;
  const w = 3.5;
  const colLeft = (idx: number) => colX(idx);
  const colRight = (idx: number) => colX(idx) + w;
  function colX(idx: number): number {
    if (idx === 0) return colR32L;
    if (idx === 1) return colR16L;
    if (idx === 2) return colQFL;
    if (idx === 3) return colSFL;
    if (idx === 4) return colSFR;
    if (idx === 5) return colQFR;
    if (idx === 6) return colR16R;
    if (idx === 7) return colR32R;
    return 0;
  }
  const midX = (a: number, b: number) => (colRight(a) + colLeft(b)) / 2;
  const r32Y = (i: number) => (i < 8 ? R32_UPPER_Y[i] : R32_LOWER_Y[i - 8]);

  return (
    <svg className="fiba-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
      {/* R32 上面 8 场 → R16 上面 4 场 */}
      {Array.from({ length: 4 }).map((_, k) => {
        const yTo = R16_Y[k];
        return (
          <g key={`r32-r16-upper-${k}`} className={`fiba-line ${active('R16') ? 'is-active' : ''}`}>
            <polyline points={`${colRight(0)},${r32Y(2 * k)} ${midX(0, 1)},${r32Y(2 * k)} ${midX(0, 1)},${yTo} ${colLeft(1)},${yTo}`} fill="none" />
            <polyline points={`${colRight(0)},${r32Y(2 * k + 1)} ${midX(0, 1)},${r32Y(2 * k + 1)} ${midX(0, 1)},${yTo} ${colLeft(1)},${yTo}`} fill="none" />
          </g>
        );
      })}
      {/* R16 上面 4 场 → QF 上面 2 场 */}
      {Array.from({ length: 2 }).map((_, k) => {
        const yTo = QF_Y[k];
        return (
          <g key={`r16-qf-upper-${k}`} className={`fiba-line ${active('QF') ? 'is-active' : ''}`}>
            <polyline points={`${colRight(1)},${R16_Y[2 * k]} ${midX(1, 2)},${R16_Y[2 * k]} ${midX(1, 2)},${yTo} ${colLeft(2)},${yTo}`} fill="none" />
            <polyline points={`${colRight(1)},${R16_Y[2 * k + 1]} ${midX(1, 2)},${R16_Y[2 * k + 1]} ${midX(1, 2)},${yTo} ${colLeft(2)},${yTo}`} fill="none" />
          </g>
        );
      })}
      {/* QF 上面 2 场 → SF 上面 1 场 */}
      <g className={`fiba-line ${active('SF') ? 'is-active' : ''}`}>
        <polyline points={`${colRight(2)},${QF_Y[0]} ${midX(2, 3)},${QF_Y[0]} ${midX(2, 3)},${SF_UPPER_Y} ${colLeft(3)},${SF_UPPER_Y}`} fill="none" />
        <polyline points={`${colRight(2)},${QF_Y[1]} ${midX(2, 3)},${QF_Y[1]} ${midX(2, 3)},${SF_UPPER_Y} ${colLeft(3)},${SF_UPPER_Y}`} fill="none" />
      </g>
      {/* SF 上面 → Final */}
      <g className={`fiba-line ${active('FINAL') ? 'is-active' : ''}`}>
        <polyline points={`${colRight(3)},${SF_UPPER_Y} ${midX(3, 4)},${SF_UPPER_Y} ${midX(3, 4)},${FINAL_Y} ${colLeft(4)},${FINAL_Y}`} fill="none" />
      </g>
      {/* Final → 3RD */}
      <g className={`fiba-line ${active('FINAL') ? 'is-active' : ''}`}>
        <polyline points={`${colRight(4)},${FINAL_Y} 50,${FINAL_Y} 50,${THIRD_Y} ${colLeft(4)},${THIRD_Y}`} fill="none" />
      </g>
      {/* SF 下面 → Final */}
      <g className={`fiba-line ${active('FINAL') ? 'is-active' : ''}`}>
        <polyline points={`${colLeft(4)},${FINAL_Y} ${midX(4, 5)},${FINAL_Y} ${midX(4, 5)},${SF_LOWER_Y} ${colRight(5)},${SF_LOWER_Y}`} fill="none" />
      </g>
      {/* QF 下面 2 场 → SF 下面 1 场 */}
      <g className={`fiba-line ${active('SF') ? 'is-active' : ''}`}>
        <polyline points={`${colLeft(5)},${SF_LOWER_Y} ${midX(4, 5)},${SF_LOWER_Y} ${midX(4, 5)},${QF_Y[0]} ${colRight(6)},${QF_Y[0]}`} fill="none" />
        <polyline points={`${colLeft(5)},${SF_LOWER_Y} ${midX(4, 5)},${SF_LOWER_Y} ${midX(4, 5)},${QF_Y[1]} ${colRight(6)},${QF_Y[1]}`} fill="none" />
      </g>
      {/* R16 下面 4 场 → QF 下面 2 场 */}
      {Array.from({ length: 2 }).map((_, k) => {
        const yTo = QF_Y[k];
        return (
          <g key={`r16-qf-lower-${k}`} className={`fiba-line ${active('QF') ? 'is-active' : ''}`}>
            <polyline points={`${colLeft(6)},${R16_Y[2 * k]} ${midX(5, 6)},${R16_Y[2 * k]} ${midX(5, 6)},${yTo} ${colRight(7)},${yTo}`} fill="none" />
            <polyline points={`${colLeft(6)},${R16_Y[2 * k + 1]} ${midX(5, 6)},${R16_Y[2 * k + 1]} ${midX(5, 6)},${yTo} ${colRight(7)},${yTo}`} fill="none" />
          </g>
        );
      })}
      {/* R32 下面 8 场 → R16 下面 4 场 */}
      {Array.from({ length: 4 }).map((_, k) => {
        const yTo = R16_Y[k];
        return (
          <g key={`r32-r16-lower-${k}`} className={`fiba-line ${active('R16') ? 'is-active' : ''}`}>
            <polyline points={`${colLeft(7)},${r32Y(8 + 2 * k)} ${midX(6, 7)},${r32Y(8 + 2 * k)} ${midX(6, 7)},${yTo} ${colRight(8 - 1)},${yTo}`} fill="none" />
            <polyline points={`${colLeft(7)},${r32Y(8 + 2 * k + 1)} ${midX(6, 7)},${r32Y(8 + 2 * k + 1)} ${midX(6, 7)},${yTo} ${colRight(8 - 1)},${yTo}`} fill="none" />
          </g>
        );
      })}
    </svg>
  );
}
