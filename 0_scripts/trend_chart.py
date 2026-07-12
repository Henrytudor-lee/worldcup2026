"""
cron 趋势图生成脚本
读 1_数据基础/cron_history.jsonl, 生成 HTML 趋势图
供 daily-calibration cron 跑完生成报告时附加调用
"""
import json
import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "1_数据基础"
OUT_DIR = Path(__file__).resolve().parent.parent / "4_可视化"
HISTORY_FILE = DATA_DIR / "cron_history.jsonl"


def load_history():
    if not HISTORY_FILE.exists():
        return []
    rows = []
    with open(HISTORY_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def render_html(rows):
    if not rows:
        return "<p>暂无 cron 历史数据</p>"

    # 按日期排序
    rows = sorted(rows, key=lambda r: r.get('date', ''))
    dates = [r['date'] for r in rows]
    new_matches = [r.get('new_matches', 0) for r in rows]
    cum_team = [r.get('team_rows', 0) for r in rows]
    cum_player = [r.get('player_rows', 0) for r in rows]
    cum_event = [r.get('event_rows', 0) for r in rows]
    total_new = sum(new_matches)
    total_runs = len(rows)
    latest = rows[-1]
    first = rows[0]

    # 增量计算 (每行 - 上一行)
    inc_team = [0] + [cum_team[i] - cum_team[i-1] for i in range(1, len(cum_team))]
    inc_player = [0] + [cum_player[i] - cum_player[i-1] for i in range(1, len(cum_player))]
    inc_event = [0] + [cum_event[i] - cum_event[i-1] for i in range(1, len(cum_event))]

    # SVG trend chart (用纯 SVG，不用 chart library)
    W, H = 900, 400
    pad_x, pad_y = 60, 40
    chart_w, chart_h = W - pad_x * 2, H - pad_y * 2

    def scale_x(i):
        if len(rows) <= 1:
            return pad_x + chart_w / 2
        return pad_x + (i / (len(rows) - 1)) * chart_w

    def scale_y(v, vmax):
        return pad_y + chart_h - (v / max(vmax, 1)) * chart_h

    max_player = max(cum_player) if cum_player else 1
    max_event = max(cum_event) if cum_event else 1
    max_new = max(new_matches) if new_matches else 1

    # 累计球员趋势线
    player_line_pts = " ".join(f"{scale_x(i):.1f},{scale_y(v, max_player):.1f}" for i, v in enumerate(cum_player))
    event_line_pts = " ".join(f"{scale_x(i):.1f},{scale_y(v, max_event):.1f}" for i, v in enumerate(cum_event))
    team_line_pts = " ".join(f"{scale_x(i):.1f},{scale_y(v, max_player):.1f}" for i, v in enumerate(cum_team))

    # 每日新增柱状
    bar_w = max((chart_w / max(len(rows), 1)) * 0.6, 4)
    bars = []
    for i, v in enumerate(new_matches):
        x = scale_x(i) - bar_w / 2
        bar_h = scale_y(0, max_new) - scale_y(v, max_new)
        y = pad_y + chart_h - bar_h
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="#d4a574" rx="2"/>')

    # X 轴标签 (最多 8 个, 隔行)
    x_labels = []
    label_step = max(1, len(rows) // 8)
    for i in range(0, len(rows), label_step):
        x_labels.append(f'<text x="{scale_x(i):.1f}" y="{pad_y + chart_h + 18:.1f}" font-size="10" fill="#666" text-anchor="middle">{dates[i][5:]}</text>')

    # 最新数据点
    latest_y_team = scale_y(cum_team[-1], max_player)
    latest_y_player = scale_y(cum_player[-1], max_player)
    latest_y_event = scale_y(cum_event[-1], max_event)
    latest_x = scale_x(len(rows) - 1)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>WorldCup cron 趋势图</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", sans-serif; max-width: 1100px; margin: 30px auto; padding: 20px; background: #f8f8f5; color: #1a1a1a; }}
  h1 {{ color: #2c5f2d; text-align: center; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }}
  .stat-card {{ background: #fff; border-radius: 10px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
  .stat-label {{ font-size: 12px; color: #888; }}
  .stat-value {{ font-size: 24px; font-weight: 700; color: #5a3a1f; margin-top: 4px; }}
  .chart-card {{ background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin: 20px 0; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }}
  th {{ background: #5a3a1f; color: #fff; padding: 8px; text-align: left; }}
  td {{ padding: 8px; border-bottom: 1px solid #e8e0d0; }}
  tr:nth-child(even) {{ background: #faf6ee; }}
  .legend {{ display: flex; gap: 16px; justify-content: center; margin: 12px 0; font-size: 13px; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; }}
  .legend-color {{ width: 16px; height: 4px; border-radius: 2px; }}
  .meta {{ font-size: 12px; color: #888; text-align: center; margin: 20px 0; }}
  .ok {{ color: #2c5f2d; font-weight: 700; }}
  .miss {{ color: #c0392b; font-weight: 700; }}
</style>
</head>
<body>
<h1>📈 WorldCup2026 cron 数据采集趋势图</h1>
<p class="meta">自动生成 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<div class="stat-grid">
  <div class="stat-card">
    <div class="stat-label">cron 跑过次数</div>
    <div class="stat-value">{total_runs}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">总新增比赛</div>
    <div class="stat-value">{total_new}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">当前数据库 (球员)</div>
    <div class="stat-value">{latest.get('player_rows', 0)}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">当前数据库 (事件)</div>
    <div class="stat-value">{latest.get('event_rows', 0)}</div>
  </div>
</div>

<div class="chart-card">
  <h3>📊 数据库累计增长 (球队/球员/事件)</h3>
  <div class="legend">
    <div class="legend-item"><div class="legend-color" style="background:#8b4513"></div>球队 stats</div>
    <div class="legend-item"><div class="legend-color" style="background:#2c5f2d"></div>球员 stats</div>
    <div class="legend-item"><div class="legend-color" style="background:#c0392b"></div>事件 events</div>
  </div>
  <svg viewBox="0 0 {W} {H + 30}" width="100%" height="auto" style="background:#faf6ee;border-radius:6px">
    <line x1="{pad_x}" y1="{pad_y}" x2="{pad_x}" y2="{pad_y + chart_h}" stroke="#999" stroke-width="1"/>
    <line x1="{pad_x}" y1="{pad_y + chart_h}" x2="{pad_x + chart_w}" y2="{pad_y + chart_h}" stroke="#999" stroke-width="1"/>
    <polyline points="{team_line_pts}" fill="none" stroke="#8b4513" stroke-width="2"/>
    <polyline points="{player_line_pts}" fill="none" stroke="#2c5f2d" stroke-width="2.5"/>
    <polyline points="{event_line_pts}" fill="none" stroke="#c0392b" stroke-width="2"/>
    <circle cx="{latest_x:.1f}" cy="{latest_y_team:.1f}" r="4" fill="#8b4513"/>
    <circle cx="{latest_x:.1f}" cy="{latest_y_player:.1f}" r="5" fill="#2c5f2d"/>
    <circle cx="{latest_x:.1f}" cy="{latest_y_event:.1f}" r="4" fill="#c0392b"/>
    {''.join(x_labels)}
    <text x="{pad_x}" y="{pad_y - 12}" font-size="10" fill="#888">球员 stats (主)</text>
    <text x="{pad_x}" y="{pad_y - 24}" font-size="10" fill="#888">事件 + 球队 (副)</text>
  </svg>
</div>

<div class="chart-card">
  <h3>🎯 每日新增比赛 (柱状图)</h3>
  <svg viewBox="0 0 {W} {H + 30}" width="100%" height="auto" style="background:#faf6ee;border-radius:6px">
    <line x1="{pad_x}" y1="{pad_y}" x2="{pad_x}" y2="{pad_y + chart_h}" stroke="#999" stroke-width="1"/>
    <line x1="{pad_x}" y1="{pad_y + chart_h}" x2="{pad_x + chart_w}" y2="{pad_y + chart_h}" stroke="#999" stroke-width="1"/>
    {''.join(bars)}
    {''.join(x_labels)}
    <text x="{pad_x}" y="{pad_y + chart_h + 32}" font-size="10" fill="#888">日期</text>
  </svg>
</div>

<div class="chart-card">
  <h3>📋 cron 跑过详情</h3>
  <table>
    <tr>
      <th>日期</th>
      <th>新增</th>
      <th>跳过</th>
      <th>失败</th>
      <th>球队 (+)</th>
      <th>球员 (+)</th>
      <th>事件 (+)</th>
      <th>累计球员</th>
    </tr>
    {''.join(
        f'<tr>'
        f'<td>{r["date"]}</td>'
        f'<td>{r.get("new_matches", 0)}</td>'
        f'<td>{r.get("skipped_matches", 0)}</td>'
        f'<td class="{"miss" if r.get("failed_matches", 0) > 0 else "ok"}">{r.get("failed_matches", 0)}</td>'
        f'<td>+{inc_team[i]}</td>'
        f'<td>+{inc_player[i]}</td>'
        f'<td>+{inc_event[i]}</td>'
        f'<td>{r.get("player_rows", 0)}</td>'
        f'</tr>'
        for i, r in enumerate(rows)
    )}
  </table>
</div>

<p class="meta">
  范围: {first['date']} → {latest['date']} | 数据源: <code>1_数据基础/cron_history.jsonl</code>
</p>
</body></html>"""


def main():
    rows = load_history()
    if not rows:
        print("⚠️  无 cron 历史数据, 请先跑一次 espn_cron.py")
        return 1
    html = render_html(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "cron_trend_chart.html"
    out.write_text(html, encoding='utf-8')
    print(f"✅ 趋势图已生成: {out}")
    print(f"   数据条数: {len(rows)}")
    print(f"   范围: {rows[0]['date']} → {rows[-1]['date']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())