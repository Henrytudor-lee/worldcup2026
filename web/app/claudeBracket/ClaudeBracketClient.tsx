'use client';

import { useMemo, useState } from 'react';
import type { Team } from '../lib/types';

type Stage = 'R32' | 'R16' | 'QF' | 'SF' | 'FINAL' | '3RD';
const STAGE_ORDER: Stage[] = ['R32', 'R16', 'QF', 'SF', 'FINAL'];

interface BracketMatch {
  match_id: string;
  round: string;
  stage: Stage;
  home: string;
  away: string;
  date: string;
  city?: string | null;
  stadium?: string | null;
  best_score: string;
  best_score_prob: number;
  p_home_win: number;
  p_away_win: number;
  p_draw: number;
  expected_total: number;
  expected_diff: number;
  winner: string | null;
  loser: string | null;
  actual_score: string | null;
  went_to_pen: boolean;
  data_status: 'real' | 'pending';
}

interface Props {
  initialMatches: BracketMatch[];
  groupStandings: Record<string, Array<[string, number, number, number, number]>>;
}

const STAGE_LABELS: Record<Stage, string> = {
  R32: 'R32  1/16 决赛',
  R16: 'R16  1/8 决赛',
  QF: 'QF  1/4 决赛',
  SF: 'SF  半决赛',
  FINAL: 'Final  决赛',
  '3RD': '3rd  季军赛',
};

const TEAM_FLAG: Record<string, string> = {
  '加拿大': '🇨🇦', '德国': '🇩🇪', '巴西': '🇧🇷', '挪威': '🇳🇴',
  '荷兰': '🇳🇱', '法国': '🇫🇷', '英格兰': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', '克罗地亚': '🇭🇷',
  '西班牙': '🇪🇸', '比利时': '🇧🇪', '葡萄牙': '🇵🇹', '塞内加尔': '🇸🇳',
  '摩洛哥': '🇲🇦', '阿根廷': '🇦🇷', '日本': '🇯🇵', '韩国': '🇰🇷',
  '澳大利亚': '🇦🇺', '伊朗': '🇮🇷', '沙特': '🇸🇦', '卡塔尔': '🇶🇦',
  '美国': '🇺🇸', '墨西哥': '🇲🇽', '乌拉圭': '🇺🇾', '哥伦比亚': '🇨🇴',
  '厄瓜多尔': '🇪🇨', '智利': '🇨🇱', '秘鲁': '🇵🇪', '巴拉圭': '🇵🇾',
  '瑞士': '🇨🇭', '奥地利': '🇦🇹', '丹麦': '🇩🇰', '瑞典': '🇸🇪',
  '波兰': '🇵🇱', '捷克': '🇨🇿', '塞尔维亚': '🇷🇸', '乌克兰': '🇺🇦',
  '土耳其': '🇹🇷', '苏格兰': '🏴󠁧󠁢󠁳󠁣󠁴󠁿', '威尔士': '🏴󠁧󠁢󠁷󠁬󠁳󠁿', '突尼斯': '🇹🇳',
  '埃及': '🇪🇬', '尼日利亚': '🇳🇬', '加纳': '🇬🇭', '喀麦隆': '🇨🇲',
  '科特迪瓦': '🇨🇮', '阿尔及利亚': '🇩🇿', '南非': '🇿🇦', '巴拿马': '🇵🇦',
  '哥斯达黎加': '🇨🇷', '牙买加': '🇯🇲', '新西兰': '🇳🇿', '斐济': '🇫🇯',
  '约旦': '🇯🇴', '乌兹别克斯坦': '🇺🇿', '阿联酋': '🇦🇪', '阿曼': '🇴🇲',
  '伊拉克': '🇮🇶', '中国': '🇨🇳', '印度': '🇮🇳', '朝鲜': '🇰🇵',
};

function flagEmoji(team: string): string {
  return TEAM_FLAG[team] ?? '🏳️';
}

// R32 顺序: 按 match_id 数字排
const R32_ORDER = [
  'M49', 'M50', 'M51', 'M52', 'M53', 'M54', 'M55', 'M56',
  'M57', 'M58', 'M59', 'M60', 'M61', 'M62', 'M63', 'M64',
];
// FIFA R32 配对 — 16 场 8 对 (字母索引 = R32 match_id 序号 0-15)
const R32_PAIRING: Array<[number, number]> = [
  [0, 2],   // M49(0) vs M51(2)
  [1, 4],   // M50(1) vs M53(4)
  [3, 5],   // M52(3) vs M54(5)
  [6, 7],   // M55(6) vs M56(7)
  [10, 11], // M59(10) vs M60(11)
  [8, 9],   // M57(8) vs M58(9)
  [13, 15], // M62(13) vs M64(15)
  [12, 14], // M61(12) vs M63(14)
];

const QF_PAIRING: Array<[number, number]> = [[0, 1], [2, 3], [4, 5], [6, 7]];
const SF_PAIRING: Array<[number, number]> = [[0, 1], [2, 3]];

export function ClaudeBracketClient({ initialMatches, groupStandings }: Props) {
  const [picks, setPicks] = useState<Record<string, 'home' | 'away'>>({});
  const [revealed, setRevealed] = useState(false);

  // 按 stage 分组 + 排序
  const byStage = useMemo(() => {
    const out: Record<Stage, BracketMatch[]> = {
      R32: [], R16: [], QF: [], SF: [], FINAL: [], '3RD': [],
    };
    initialMatches.forEach((m) => out[m.stage].push(m));

    out.R32.sort((a, b) => {
      const ai = R32_ORDER.indexOf(a.match_id);
      const bi = R32_ORDER.indexOf(b.match_id);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });
    // R16/QF/SF/FINAL/3RD 保持 JSON 顺序
    return out;
  }, [initialMatches]);

  // 派生 winner/loser (含 picks 覆盖)
  const derived = useMemo(() => {
    const real: Record<Stage, BracketMatch[]> = {
      R32: [], R16: [], QF: [], SF: [], FINAL: [], '3RD': [],
    };

    for (const m of byStage.R32) {
      const pick = picks[m.match_id];
      const winner = pick === 'home' ? m.home : pick === 'away' ? m.away : m.winner;
      const loser = pick === 'home' ? m.away : pick === 'away' ? m.home : m.loser;
      real.R32.push({ ...m, winner, loser });
    }

    const cascade = (
      src: BracketMatch[],
      dst: BracketMatch[],
      pairing: Array<[number, number]>,
      stage: Stage,
    ) => {
      for (let i = 0; i < dst.length; i++) {
        const m = dst[i];
        const [a, b] = pairing[i] ?? [2 * i, 2 * i + 1];
        const home = src[a]?.winner ?? m.home;
        const away = src[b]?.winner ?? m.away;
        const pick = picks[m.match_id];
        let winner: string | null = m.winner;
        let loser: string | null = m.loser;
        if (pick === 'home') { winner = home; loser = away; }
        else if (pick === 'away') { winner = away; loser = home; }
        else if (winner && winner !== home && winner !== away) {
          winner = null; loser = null;
        }
        real[stage].push({ ...m, home, away, winner, loser });
      }
    };

    cascade(real.R32, byStage.R16, R32_PAIRING, 'R16');
    cascade(real.R16, byStage.QF, QF_PAIRING, 'QF');
    cascade(real.QF, byStage.SF, SF_PAIRING, 'SF');

    if (byStage.FINAL[0]) {
      const m = byStage.FINAL[0];
      const home = real.SF[0]?.winner ?? m.home;
      const away = real.SF[1]?.winner ?? m.away;
      const pick = picks[m.match_id];
      let winner: string | null = m.winner;
      let loser: string | null = m.loser;
      if (pick === 'home') { winner = home; loser = away; }
      else if (pick === 'away') { winner = away; loser = home; }
      else if (winner && winner !== home && winner !== away) {
        winner = null; loser = null;
      }
      real.FINAL.push({ ...m, home, away, winner, loser });
    }

    if (byStage['3RD'][0]) {
      const m = byStage['3RD'][0];
      const home = real.SF[0]?.loser ?? m.home;
      const away = real.SF[1]?.loser ?? m.away;
      const pick = picks[m.match_id];
      let winner: string | null = m.winner;
      let loser: string | null = m.loser;
      if (pick === 'home') { winner = home; loser = away; }
      else if (pick === 'away') { winner = away; loser = home; }
      else if (winner && winner !== home && winner !== away) {
        winner = null; loser = null;
      }
      real['3RD'].push({ ...m, home, away, winner, loser });
    }

    return real;
  }, [byStage, picks]);

  const handlePick = (matchId: string, side: 'home' | 'away') => {
    setPicks((prev) => ({ ...prev, [matchId]: side }));
  };

  const resetPicks = () => setPicks({});

  // 统计
  const stats = useMemo(() => {
    const champion = derived.FINAL[0]?.winner ?? null;
    const finalist = derived.FINAL[0]?.loser ?? null;
    const third = derived['3RD'][0]?.winner ?? null;
    const totalKO = derived.R32.length + derived.R16.length + derived.QF.length + derived.SF.length + derived.FINAL.length + derived['3RD'].length;
    const userPicks = Object.keys(picks).length;
    return { champion, finalist, third, totalKO, userPicks };
  }, [derived, picks]);

  return (
    <div className="claude-page">
      <header className="claude-header">
        <h1 className="claude-title">🤖 Claude 对阵</h1>
        <p className="claude-subtitle">Mavis PDP v2.1 预测 · 4 维 λ 对位泊松 · 用户可覆盖</p>
        <div className="claude-actions">
          <button
            type="button"
            className={`claude-toggle ${!revealed ? 'on' : ''}`}
            onClick={() => setRevealed(false)}
          >
            🎯 仅显示 Claude 预测
          </button>
          <button
            type="button"
            className={`claude-toggle ${revealed ? 'on' : ''}`}
            onClick={() => setRevealed(true)}
          >
            🏆 显示冠军/亚军/季军
          </button>
          <button type="button" className="claude-reset" onClick={resetPicks} disabled={stats.userPicks === 0}>
            ↺ 重置 ({stats.userPicks})
          </button>
        </div>
      </header>

      {revealed && (
        <section className="claude-podium">
          <PodiumCard title="🏆 冠军" team={stats.champion} accent="gold" />
          <PodiumCard title="🥈 亚军" team={stats.finalist} accent="silver" />
          <PodiumCard title="🥉 季军" team={stats.third} accent="bronze" />
        </section>
      )}

      {(['R32', 'R16', 'QF', 'SF', 'FINAL'] as Stage[]).map((stage) => {
        const matches = derived[stage];
        if (matches.length === 0) return null;
        return (
          <section key={stage} className="claude-stage">
            <h2 className="claude-stage-title">{STAGE_LABELS[stage]}</h2>
            <div className={`claude-grid claude-grid-${stage.toLowerCase()}`}>
              {matches.map((m) => (
                <MatchCard
                  key={m.match_id}
                  m={m}
                  pick={picks[m.match_id]}
                  onPick={handlePick}
                  showChampion={revealed}
                />
              ))}
            </div>
          </section>
        );
      })}

      {derived['3RD'][0] && (
        <section className="claude-stage">
          <h2 className="claude-stage-title">{STAGE_LABELS['3RD']}</h2>
          <div className="claude-grid claude-grid-final">
            <MatchCard
              m={derived['3RD'][0]}
              pick={picks[derived['3RD'][0].match_id]}
              onPick={handlePick}
              showChampion={revealed}
            />
          </div>
        </section>
      )}

      {Object.keys(groupStandings).length > 0 && (
        <section className="claude-stage">
          <h2 className="claude-stage-title">小组赛最终排名（Claude 预测）</h2>
          <div className="claude-groups">
            {Object.entries(groupStandings).map(([grp, rows]) => (
              <div key={grp} className="claude-group-card">
                <h3 className="claude-group-name">{grp}</h3>
                <table className="claude-group-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>队</th>
                      <th>分</th>
                      <th>胜</th>
                      <th>平</th>
                      <th>负</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr key={row[0]} className={i < 2 ? 'is-qualified' : (i === 2 ? 'is-possible' : '')}>
                        <td>{i + 1}</td>
                        <td>
                          <span className="claude-group-flag">{flagEmoji(row[0])}</span>
                          {row[0]}
                        </td>
                        <td>{row[1]}</td>
                        <td>{row[2]}</td>
                        <td>{row[3]}</td>
                        <td>{row[4]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function PodiumCard({ title, team, accent }: { title: string; team: string | null; accent: 'gold' | 'silver' | 'bronze' }) {
  return (
    <div className={`claude-podium-card claude-podium-${accent}`}>
      <div className="claude-podium-title">{title}</div>
      <div className="claude-podium-flag">{team ? flagEmoji(team) : '?'}</div>
      <div className="claude-podium-team">{team ?? '待定'}</div>
    </div>
  );
}

function MatchCard({
  m,
  pick,
  onPick,
  showChampion,
}: {
  m: BracketMatch;
  pick: 'home' | 'away' | undefined;
  onPick: (id: string, side: 'home' | 'away') => void;
  showChampion: boolean;
}) {
  const isLocked = m.data_status === 'real';
  const claudePick: 'home' | 'away' | null =
    m.p_home_win > m.p_away_win ? 'home' : m.p_away_win > m.p_home_win ? 'away' : null;
  const isUserOverridden = pick !== undefined && pick !== claudePick;

  const renderTeam = (side: 'home' | 'away') => {
    const team = side === 'home' ? m.home : m.away;
    const prob = side === 'home' ? m.p_home_win : m.p_away_win;
    const isClaudeWinner = claudePick === side;
    const isUserWinner = pick ? pick === side : false;
    const showWinnerStyle = showChampion
      ? (isUserWinner || (!pick && isClaudeWinner))
      : isClaudeWinner;

    return (
      <button
        type="button"
        className={`claude-team ${showWinnerStyle ? 'is-winner' : 'is-loser'} ${pick === side ? 'is-picked' : ''}`}
        disabled={isLocked}
        onClick={() => onPick(m.match_id, side)}
      >
        <span className="claude-team-flag">{flagEmoji(team)}</span>
        <span className="claude-team-name">{team}</span>
        <span className="claude-team-prob">{(prob * 100).toFixed(0)}%</span>
      </button>
    );
  };

  const pTotal = m.p_home_win + m.p_away_win;
  const homeBarPct = pTotal > 0 ? (m.p_home_win / pTotal) * 100 : 50;

  return (
    <div className={`claude-match ${isLocked ? 'is-locked' : ''} ${isUserOverridden ? 'is-overridden' : ''}`}>
      <header className="claude-match-head">
        <span className="claude-match-id">{m.match_id}</span>
        <span className="claude-match-meta">
          {m.date} · {m.city ?? '?'}
        </span>
        {isLocked && <span className="claude-match-lock">🔒</span>}
      </header>

      <div className="claude-match-body">
        {renderTeam('home')}
        <div className="claude-match-prob-bar">
          <div className="claude-match-prob-home" style={{ width: `${homeBarPct}%` }} />
          <div className="claude-match-prob-mid">VS</div>
          <div className="claude-match-prob-away" style={{ width: `${100 - homeBarPct}%` }} />
        </div>
        {renderTeam('away')}
      </div>

      <footer className="claude-match-foot">
        <span>Claude 预测: <b>{m.best_score}</b></span>
        <span className="claude-match-prob-score">{(m.best_score_prob * 100).toFixed(1)}%</span>
      </footer>
    </div>
  );
}