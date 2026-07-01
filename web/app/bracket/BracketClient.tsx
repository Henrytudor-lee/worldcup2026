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

// === FIFA 2026 官方 R32 顺序 (M1-M16) — 必须与 backend/predictor.py OFFICIAL_R32_PAIRS 一致 ===
// 来源: ESPN API 2026-06-28, FIFA 官方对阵表
// 上半 (M1-M8): 南非/巴西/德国/荷兰/科特迪瓦/法国/墨西哥/英格兰
// 下半 (M9-M16): 比利时/美国/西班牙/葡萄牙/瑞士/澳大利亚/阿根廷/哥伦比亚
const OFFICIAL_R32_ORDER: string[] = [
  '南非',         // M1  vs 加拿大
  '巴西',         // M2  vs 日本
  '德国',         // M3  vs 巴拉圭
  '荷兰',         // M4  vs 摩洛哥
  '科特迪瓦',     // M5  vs 挪威
  '法国',         // M6  vs 瑞典
  '墨西哥',       // M7  vs 厄瓜多尔
  '英格兰',       // M8  vs 民主刚果
  '比利时',       // M9  vs 塞内加尔
  '美国',         // M10 vs 波黑
  '西班牙',       // M11 vs 奥地利
  '葡萄牙',       // M12 vs 克罗地亚
  '瑞士',         // M13 vs 阿尔及利亚
  '澳大利亚',     // M14 vs 埃及
  '阿根廷',       // M15 vs 佛得角
  '哥伦比亚',     // M16 vs 加纳
];

// === R16/QF/SF 配对索引 (邻接几何, 保证 4 pair 完美对齐) ===
// 邻接配对: R16[i] = R32[2i]+R32[2i+1] (跟参考图 4-pair 视觉一致)
// R16 位置 = R32 邻接 pair 中点 (12.5/37.5/62.5/87.5)
// R16 home/away 显示 JSON 配对的真实胜者 (R16[i].home, R16[i].away)
// 注: 邻接几何 + JSON home/away 配对可能在 R16 卡内 home/away 跟折线连入位置不一致
// 但视觉上 R16 位置规则 4 pair 紧贴, 是用户最看重的
const R16_PAIRING: Array<[number, number]> = [
  [0, 1],     // R16-1: W1 + W2 (邻接)
  [2, 3],     // R16-2: W3 + W4 (邻接)
  [4, 5],     // R16-3: W5 + W6 (邻接)
  [6, 7],     // R16-4: W7 + W8 (邻接)
  [8, 9],     // R16-5: W9 + W10 (邻接)
  [10, 11],   // R16-6: W11 + W12 (邻接)
  [12, 13],   // R16-7: W13 + W14 (邻接)
  [14, 15],   // R16-8: W15 + W16 (邻接)
];

// QF 邻接: R16[2i]+R16[2i+1]
// (但 JSON QF 配对不是邻接 - 让 QF 位置 = R16[2i]+R16[2i+1] 中点 = 25/75)
// 用邻接几何, QF[i] 位置 = (R16[2i] y + R16[2i+1] y) / 2
// (QF_PAIRING 用邻接索引, 但显示 QF 真实 home/away)
const QF_PAIRING: Array<[number, number]> = [
  [0, 1],     // QF-1: R16[0]+R16[1] (邻接)
  [2, 3],     // QF-2: R16[2]+R16[3] (邻接)
  [4, 5],     // QF-3: R16[4]+R16[5] (邻接)
  [6, 7],     // QF-4: R16[6]+R16[7] (邻接)
];

// SF 邻接: QF[2i]+QF[2i+1]
const SF_PAIRING: Array<[number, number]> = [
  [0, 1],     // SF-1: QF[0]+QF[1] (邻接)
  [2, 3],     // SF-2: QF[2]+QF[3] (邻接)
];



const STAGE_ORDER: Stage[] = ['R32', 'R16', 'QF', 'SF', 'FINAL'];

// === y 坐标公式 (返回 0-100 字符串) ===
// 上半 R32 8 场 y
const R32_UPPER_Y = [8.5, 16.5, 33.5, 41.5, 58.5, 66.5, 83.5, 91.5];
// 下半 R32 8 场 y (镜像上半)
const R32_LOWER_Y = R32_UPPER_Y.slice().reverse();
// R32[i] y
const r32Y = (i: number) => (i < 8 ? R32_UPPER_Y[i] : R32_LOWER_Y[i - 8]);

// R16/QF/SF 位置: 按 R32 配对 y 中点 (跟 JSON 真实配对一致, 几何不均匀但匹配 SVG 折线)
const r16YByIdx = (i: number) => {
  const [a, b] = R16_PAIRING[i];
  return (r32Y(a) + r32Y(b)) / 2;
};
const qfYByIdx = (i: number) => {
  const [a, b] = QF_PAIRING[i];
  return (r16YByIdx(a) + r16YByIdx(b)) / 2;
};
const sfYByIdx = (i: number) => {
  const [a, b] = SF_PAIRING[i];
  return (qfYByIdx(a) + qfYByIdx(b)) / 2;
};

// 列 x 位置 (CSS 用 % left 定位)
const COL_X: Record<string, number> = {
  R32: 5.5,
  R32_L: 94.5,
  R16: 16,
  R16_L: 84,
  QF: 27,
  QF_L: 73,
  SF: 38,
  SF_L: 62,
  CENTER: 50,
};

export function BracketClient({ initialMatches }: Props) {
  const [picks, setPicks] = useState<Record<string, 'home' | 'away'>>({});
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<SpeedKey>('normal');
  const [revealedStage, setRevealedStage] = useState<Stage | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const playTokenRef = useRef(0);

  // R32 按 OFFICIAL_R32_ORDER (M1-M16) 排序
  const r32Ordered = useMemo(() => {
    const all = initialMatches.filter((m) => m.stage === 'R32');
    if (all.length === 0) return [];
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

  // 按 match_id 拼音取 R16/QF/SF/FINAL/3RD 的 raw 顺序
  const rawByStage = useMemo(() => {
    const out: Record<Stage, BracketMatch[]> = { R32: [], R16: [], QF: [], SF: [], FINAL: [], '3RD': [] };
    const byS: Record<Stage, BracketMatch[]> = { R32: [], R16: [], QF: [], SF: [], FINAL: [], '3RD': [] };
    initialMatches.forEach((m) => { byS[m.stage].push(m); });
    (['R16', 'QF', 'SF', 'FINAL', '3RD'] as Stage[]).forEach((s) => {
      out[s] = [...byS[s]].sort((a, b) => a.match_id.localeCompare(b.match_id));
    });
    return out;
  }, [initialMatches]);

  // 派生各级对阵: R32 用 r32Ordered; R16/QF/SF/FINAL/3RD 用 cascade
  const derived = useMemo(() => {
    const real: Record<Stage, BracketMatch[]> = { R32: [], R16: [], QF: [], SF: [], FINAL: [], '3RD': [] };

    // R32: winner/loser 根据 picks 决定
    for (let i = 0; i < r32Ordered.length; i++) {
      const m = r32Ordered[i];
      const pick = picks[m.match_id];
      const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : m.winner;
      const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
      real.R32.push({ ...m, winner, loser });
    }

    // 通用级联
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

    cascade(real.R32, rawByStage.R16, R16_PAIRING, 'R16');
    cascade(real.R16, rawByStage.QF, QF_PAIRING, 'QF');
    cascade(real.QF, rawByStage.SF, SF_PAIRING, 'SF');

    // FINAL: SF[0] winner vs SF[1] winner
    if (rawByStage.FINAL[0]) {
      const m = rawByStage.FINAL[0];
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
    if (rawByStage['3RD'][0]) {
      const m = rawByStage['3RD'][0];
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
  }, [r32Ordered, rawByStage, picks]);

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

  // 暴露给子组件的 picks map
  const pickMap = picks;

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
        {/* SVG 连接线层 */}
        <BracketConnectors revealedStage={revealedStage} />

        {/* R32 上半: 8 场单独定位, 4-pair 视觉 */}
        {derived.R32.slice(0, 8).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-r32-slot"
            data-col="0"
            data-pair={Math.floor(idx / 2)}
            style={{ top: `${R32_UPPER_Y[idx]}%`, left: `${COL_X.R32}%`, '--pair': Math.floor(idx / 2), '--in-pair': idx % 2 } as React.CSSProperties}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'R32'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
            />
          </div>
        ))}

        {/* R16 上半: 4 场, y 动态算 */}
        {derived.R16.slice(0, 4).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-r16-slot"
            data-col="1"
            data-pair={Math.floor(idx / 2)}
            style={{ top: `${r16YByIdx(idx)}%`, left: `${COL_X.R16}%`, '--pair': Math.floor(idx / 2), '--in-pair': idx % 2 } as React.CSSProperties}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'R16'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        ))}

        {/* QF 上半: 2 场, y 动态算 */}
        {derived.QF.slice(0, 2).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-qf-slot"
            data-col="2"
            data-pair={idx}
            style={{ top: `${qfYByIdx(idx)}%`, left: `${COL_X.QF}%`, '--pair': idx, '--in-pair': 0 } as React.CSSProperties}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'QF'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        ))}

        {/* SF 上半: 1 场, y 动态算 */}
        {derived.SF.slice(0, 1).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-sf-slot"
            data-col="3"
            style={{ top: `${sfYByIdx(idx)}%`, left: `${COL_X.SF}%`, '--pair': 0, '--in-pair': 0 } as React.CSSProperties}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'SF'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        ))}

        {/* 中央列: WORLD CHAMPION + Final + BRONZE FINAL + 3rd + 奖杯 + 26 */}
        <div className="fiba-center">
          <div className="fiba-champion-title-wrap">
            <div className="fiba-champion-title">WORLD<br />CHAMPION</div>
            {champion && <div className="fiba-champion-flag">{flag(champion)}</div>}
          </div>
          {derived.FINAL[0] && (
            <div className="fiba-final-wrap">
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
          <div className="fiba-bronze-label">BRONZE FINAL</div>
          {derived['3RD'][0] && (
            <div className="fiba-center-3rd">
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
          <div className="fiba-trophy-wrap">
            <div className="fiba-trophy">
              <Trophy />
            </div>
          </div>
          <div className="fiba-wc26-wrap">
            <div className="fiba-wc26">
              <span className="fiba-wc26-num">26</span>
              <span className="fiba-wc26-text">FIFA WORLD CUP 2026</span>
            </div>
          </div>
        </div>

        {/* SF 下半: 1 场, y 动态算 */}
        {derived.SF.slice(1, 2).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-sf-slot fiba-sf-lower"
            data-col="5"
            style={{ top: `${sfYByIdx(idx + 1)}%`, left: `${COL_X.SF_L}%`, '--pair': 0, '--in-pair': 0 } as React.CSSProperties}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'SF'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        ))}

        {/* QF 下半: 2 场, y 动态算 */}
        {derived.QF.slice(2, 4).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-qf-slot fiba-qf-lower"
            data-col="6"
            data-pair={idx}
            style={{ top: `${qfYByIdx(idx + 2)}%`, left: `${COL_X.QF_L}%`, '--pair': idx, '--in-pair': 0 } as React.CSSProperties}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'QF'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        ))}

        {/* R16 下半: 4 场, y 动态算, 视觉顺序: R16[5](上), R16[4], R16[7], R16[6](下) */}
        {[
          { m: derived.R16[5], yi: 5, vi: 0 },
          { m: derived.R16[4], yi: 4, vi: 1 },
          { m: derived.R16[7], yi: 7, vi: 2 },
          { m: derived.R16[6], yi: 6, vi: 3 },
        ].filter(x => x.m).map(({ m, yi, vi }) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-r16-slot fiba-r16-lower"
            data-col="7"
            data-pair={Math.floor(vi / 2)}
            style={{ top: `${r16YByIdx(yi)}%`, left: `${COL_X.R16_L}%`, '--pair': Math.floor(vi / 2), '--in-pair': vi % 2 } as React.CSSProperties}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'R16'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
              isCascade
            />
          </div>
        ))}

        {/* R32 下半: 8 场, y 镜像上半 */}
        {derived.R32.slice(8, 16).map((m, idx) => (
          <div
            key={m.match_id}
            className="fiba-slot fiba-r32-slot fiba-r32-lower"
            data-col="8"
            data-pair={Math.floor(idx / 2)}
            style={{ top: `${R32_LOWER_Y[idx]}%`, left: `${COL_X.R32_L}%`, '--pair': Math.floor(idx / 2), '--in-pair': idx % 2 } as React.CSSProperties}
          >
            <MatchPair
              m={m}
              pick={pickMap[m.match_id]}
              locked={isLocked(m)}
              revealed={revealedStage === 'R32'}
              onPick={handlePick}
              onContext={handleContext}
              size="sm"
            />
          </div>
        ))}
      </div>

      {toast && <div className="bracket-toast">{toast}</div>}
    </div>
  );
}

// ============== 1 场比赛 (2 个旗紧贴) ==============
function MatchPair({
  m, pick, locked, revealed, onPick, onContext, size, isCascade, isFinal, isThird,
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
}) {
  const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : m.winner;
  const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
  return (
    <div
      className={`fiba-pair ${isCascade ? 'is-cascade' : ''} ${isFinal ? 'is-final' : ''} ${isThird ? 'is-third' : ''} ${revealed ? 'is-revealed' : ''}`}
      onContextMenu={(e) => onContext(m, e)}
    >
      <FlagSlot
        team={m.home}
        isWinner={winner === m.home}
        isLoser={loser === m.home}
        locked={locked}
        realScore={m.actual_score?.split('-')[0]}
        wentToPen={m.went_to_pen && winner === m.home}
        onClick={(e) => onPick(m.home, m, e)}
        size={size}
      />
      <FlagSlot
        team={m.away}
        isWinner={winner === m.away}
        isLoser={loser === m.away}
        locked={locked}
        realScore={m.actual_score?.split('-')[1]}
        wentToPen={m.went_to_pen && winner === m.away}
        onClick={(e) => onPick(m.away, m, e)}
        size={size}
      />
    </div>
  );
}

// ============== 1 个旗 ==============
function FlagSlot({
  team, isWinner, isLoser, locked, realScore, wentToPen, onClick, size,
}: {
  team: string;
  isWinner: boolean;
  isLoser: boolean;
  locked: boolean;
  realScore?: string;
  wentToPen?: boolean;
  onClick: (e: React.MouseEvent) => void;
  size: 'sm' | 'md' | 'lg';
}) {
  return (
    <button
      className={`fiba-flag fiba-flag-${size} ${isWinner ? 'is-winner' : ''} ${isLoser ? 'is-loser' : ''} ${locked ? 'is-locked' : ''}`}
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
      <circle cx="100" cy="50" r="35" fill="url(#trophyGold)" />
      <circle cx="100" cy="50" r="35" fill="url(#trophyGloss)" />
      <path d="M 80 35 Q 90 30 100 38 Q 110 32 118 42 Q 110 50 100 48 Q 90 52 82 45 Z" fill="rgba(80,50,0,0.5)" />
      <path d="M 88 55 Q 100 50 110 60 Q 105 70 95 68 Q 85 65 88 55 Z" fill="rgba(80,50,0,0.5)" />
      <path d="M 85 85 L 80 130 L 120 130 L 115 85 Z" fill="url(#trophyGold)" />
      <ellipse cx="100" cy="135" rx="30" ry="6" fill="url(#trophyBase)" />
      <ellipse cx="100" cy="155" rx="35" ry="8" fill="url(#trophyBase)" />
      <ellipse cx="100" cy="170" rx="40" ry="10" fill="url(#trophyBase)" />
      <ellipse cx="100" cy="155" rx="35" ry="8" fill="rgba(255,255,255,0.15)" />
      <rect x="60" y="180" width="80" height="50" rx="4" fill="url(#trophyBase)" />
      <rect x="60" y="180" width="80" height="6" fill="rgba(255,255,255,0.2)" />
      <text x="100" y="210" textAnchor="middle" fill="#3a2a00" fontSize="11" fontWeight="700" fontFamily="Arial, sans-serif" letterSpacing="1">FIFA</text>
      <text x="100" y="223" textAnchor="middle" fill="#3a2a00" fontSize="8" fontWeight="600" fontFamily="Arial, sans-serif" letterSpacing="0.5">WORLD CUP</text>
    </svg>
  );
}

// ============== SVG 连接线 ==============
// 9 列布局: R32(1) R16(2) QF(3) SF(4) Center(5) SF(6) QF(7) R16(8) R32(9)
// y 坐标按 4-pair 几何:
//   R32 pair 中心: 12.5%, 37.5%, 62.5%, 87.5% (8 场)
//   R16 pair 中心: 12.5%, 37.5%, 62.5%, 87.5% (4 场, 间距更大)
//   QF: 18.75%, 68.75% (2 场)
//   SF: 43.75% (1 场) — 上半; 下半 56.25%
//   Final: 32%; 3rd: 68%; 奖杯: 78%
function BracketConnectors({ revealedStage }: { revealedStage: Stage | null }) {
  // 用外部 r32Y / r16YByIdx / qfYByIdx / sfYByIdx
  // R32 上半 8 场: R32_UPPER_Y = [8.5, 16.5, 33.5, 41.5, 58.5, 66.5, 83.5, 91.5]
  // R32 下半 8 场: R32_LOWER_Y = reverse
  // R16 8 场: y = (r32Y(a) + r32Y(b)) / 2
  // QF/SF 同样
  const finalY = 30;  // Final 在 30% (中央偏上)
  const thirdY = 65;  // 3rd 在 65%

  // 列 x 位置 (9 等分, 留 2% padding)
  const COL_W = 10.4; // 100 / 9.6 ≈ 10.4
  const GAP = 0.2;
  const startX = 1;
  const colLeft = (idx: number) => startX + idx * (COL_W + GAP);
  const colRight = (idx: number) => colLeft(idx) + COL_W;
  const midX = (i: number) => colRight(i) + GAP / 2;

  return (
    <svg className="fiba-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
      {/* R32 → R16 上半 4 对 */}
      {Array.from({ length: 4 }).map((_, j) => {
        const yTo = r16YByIdx(j);
        const active = revealedStage && STAGE_ORDER.indexOf('R16') <= STAGE_ORDER.indexOf(revealedStage);
        return (
          <g key={`r32-r16-upper-${j}`} className={`fiba-line ${active ? 'is-active' : ''}`}>
            <polyline
              points={`${colRight(0)},${r32Y(2 * j)} ${midX(0)},${r32Y(2 * j)} ${midX(0)},${yTo} ${colLeft(1)},${yTo}`}
              fill="none"
            />
            <polyline
              points={`${colRight(0)},${r32Y(2 * j + 1)} ${midX(0)},${r32Y(2 * j + 1)} ${midX(0)},${yTo} ${colLeft(1)},${yTo}`}
              fill="none"
            />
          </g>
        );
      })}

      {/* R16 → QF 上半 2 对 */}
      {Array.from({ length: 2 }).map((_, k) => {
        const yTo = qfYByIdx(k);
        const active = revealedStage && STAGE_ORDER.indexOf('QF') <= STAGE_ORDER.indexOf(revealedStage);
        return (
          <g key={`r16-qf-upper-${k}`} className={`fiba-line ${active ? 'is-active' : ''}`}>
            <polyline
              points={`${colRight(1)},${r16YByIdx(2 * k)} ${midX(1)},${r16YByIdx(2 * k)} ${midX(1)},${yTo} ${colLeft(2)},${yTo}`}
              fill="none"
            />
            <polyline
              points={`${colRight(1)},${r16YByIdx(2 * k + 1)} ${midX(1)},${r16YByIdx(2 * k + 1)} ${midX(1)},${yTo} ${colLeft(2)},${yTo}`}
              fill="none"
            />
          </g>
        );
      })}

      {/* QF → SF 上半 1 对 */}
      <g className={`fiba-line ${revealedStage && STAGE_ORDER.indexOf('SF') <= STAGE_ORDER.indexOf(revealedStage) ? 'is-active' : ''}`}>
        <polyline
          points={`${colRight(2)},${qfYByIdx(0)} ${midX(2)},${qfYByIdx(0)} ${midX(2)},${sfYByIdx(0)} ${colLeft(3)},${sfYByIdx(0)}`}
          fill="none"
        />
        <polyline
          points={`${colRight(2)},${qfYByIdx(1)} ${midX(2)},${qfYByIdx(1)} ${midX(2)},${sfYByIdx(0)} ${colLeft(3)},${sfYByIdx(0)}`}
          fill="none"
        />
      </g>

      {/* SF → Final 上半 */}
      <g className={`fiba-line ${revealedStage === 'FINAL' || revealedStage === 'SF' ? 'is-active' : ''}`}>
        <polyline
          points={`${colRight(3)},${sfYByIdx(0)} ${midX(3)},${sfYByIdx(0)} ${midX(3)},${finalY} ${colLeft(4)},${finalY}`}
          fill="none"
        />
      </g>

      {/* Final → 3rd (失败者) */}
      <g className={`fiba-line ${revealedStage === 'FINAL' ? 'is-active' : ''}`}>
        <polyline
          points={`${colRight(4)},${finalY} ${midX(4)},${finalY} ${midX(4)},${thirdY} ${colLeft(4)},${thirdY}`}
          fill="none"
        />
      </g>

      {/* SF 下半 → Final 下半 */}
      <g className={`fiba-line ${revealedStage === 'FINAL' || revealedStage === 'SF' ? 'is-active' : ''}`}>
        <polyline
          points={`${colLeft(4)},${finalY} ${midX(5)},${finalY} ${midX(5)},${sfYByIdx(1)} ${colRight(5)},${sfYByIdx(1)}`}
          fill="none"
        />
      </g>

      {/* QF → SF 下半 1 对 */}
      <g className={`fiba-line ${revealedStage && STAGE_ORDER.indexOf('SF') <= STAGE_ORDER.indexOf(revealedStage) ? 'is-active' : ''}`}>
        <polyline
          points={`${colLeft(5)},${sfYByIdx(1)} ${midX(6)},${sfYByIdx(1)} ${midX(6)},${qfYByIdx(2)} ${colRight(6)},${qfYByIdx(2)}`}
          fill="none"
        />
        <polyline
          points={`${colLeft(5)},${sfYByIdx(1)} ${midX(6)},${sfYByIdx(1)} ${midX(6)},${qfYByIdx(3)} ${colRight(6)},${qfYByIdx(3)}`}
          fill="none"
        />
      </g>

      {/* R16 → QF 下半 2 对 */}
      {Array.from({ length: 2 }).map((_, k) => {
        const yTo = qfYByIdx(k + 2);
        const active = revealedStage && STAGE_ORDER.indexOf('QF') <= STAGE_ORDER.indexOf(revealedStage);
        return (
          <g key={`r16-qf-lower-${k}`} className={`fiba-line ${active ? 'is-active' : ''}`}>
            <polyline
              points={`${colLeft(7)},${r16YByIdx(2 * k + 4)} ${midX(7)},${r16YByIdx(2 * k + 4)} ${midX(7)},${yTo} ${colRight(7)},${yTo}`}
              fill="none"
            />
            <polyline
              points={`${colLeft(7)},${r16YByIdx(2 * k + 5)} ${midX(7)},${r16YByIdx(2 * k + 5)} ${midX(7)},${yTo} ${colRight(7)},${yTo}`}
              fill="none"
            />
          </g>
        );
      })}

      {/* R32 → R16 下半 4 对 (使用 r16LowerY) */}
      {Array.from({ length: 4 }).map((_, j) => {
        const yTo = r16YByIdx(j + 4);
        const active = revealedStage && STAGE_ORDER.indexOf('R16') <= STAGE_ORDER.indexOf(revealedStage);
        return (
          <g key={`r32-r16-lower-${j}`} className={`fiba-line ${active ? 'is-active' : ''}`}>
            <polyline
              points={`${colLeft(8)},${r32Y(2 * j)} ${midX(8)},${r32Y(2 * j)} ${midX(8)},${yTo} ${colRight(8)},${yTo}`}
              fill="none"
            />
            <polyline
              points={`${colLeft(8)},${r32Y(2 * j + 1)} ${midX(8)},${r32Y(2 * j + 1)} ${midX(8)},${yTo} ${colRight(8)},${yTo}`}
              fill="none"
            />
          </g>
        );
      })}
    </svg>
  );
}
