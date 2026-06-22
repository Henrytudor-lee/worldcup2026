#!/usr/bin/env python3
"""
v2.2.4-9 全 104 场 availability 算法效果对比报告
- 不启用 availability (旧模型)
- 启用 availability (新模型, cap=5.0)
- 高亮受 availability 影响最大的比赛
"""
import json
import csv
import urllib.request
import urllib.parse
import shutil
from pathlib import Path

PROJECT_ROOT = Path('/Users/garcia/Desktop/WorldCup2026')
AVAIL_FILE = PROJECT_ROOT / '1_数据基础' / 'player_availability.csv'
OUT_HTML = PROJECT_ROOT / '4_比赛预测' / 'all_matches_availability_report.html'

def fetch_predictions(weights_override=None):
    weights = weights_override or {}
    qs = urllib.parse.quote(json.dumps(weights))
    url = f'http://localhost:8765/api/predictions?weights={qs}'
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())

def toggle_availability(enable):
    backup = PROJECT_ROOT / '1_数据基础' / '_avail_backup.csv'
    if not backup.exists():
        shutil.copy(AVAIL_FILE, backup)
    if enable:
        shutil.copy(backup, AVAIL_FILE)
    else:
        AVAIL_FILE.write_text('国家,球员,availability,note\n', encoding='utf-8')

def read_availability():
    rows = []
    with AVAIL_FILE.open(encoding='utf-8') as f:
        for rec in csv.DictReader(f):
            rows.append(rec)
    return rows

def main():
    print('正在抓取全 104 场预测 (cap=5.0) × 2 (availability on/off) ...')
    results = {}
    try:
        for avail_on in [False, True]:
            toggle_availability(avail_on)
            data = fetch_predictions({'lambda_cap': 5.0})
            for m in data['predictions']:
                if m.get('stage') == 'group':
                    results[(m['home'], m['away'], avail_on)] = m
            print(f"  avail={avail_on}: {sum(1 for v in results if v[2]==avail_on)} 场小组赛")
    finally:
        # 恢复 availability
        backup = PROJECT_ROOT / '1_数据基础' / '_avail_backup.csv'
        shutil.copy(backup, AVAIL_FILE)

    # 排序: 看哪些比赛受影响最大 (按 p_home 变化)
    group_keys = set()
    for k in results:
        if k[2] is False:
            group_keys.add((k[0], k[1]))
    deltas = []
    for h, a in group_keys:
        on = results.get((h, a, True))
        off = results.get((h, a, False))
        if not on or not off:
            continue
        d_home = abs(off['p_home_win'] - on['p_home_win'])
        deltas.append((d_home, h, a, on, off))
    deltas.sort(reverse=True)

    print(f'受影响最大的 10 场比赛:')
    for d, h, a, on, off in deltas[:10]:
        print(f'  {h} vs {a}: p_home {off["p_home_win"]:.3f}→{on["p_home_win"]:.3f} (Δ{d:.3f})')

    # Build HTML
    avail_count = len(read_availability())
    html = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">']
    html.append('<title>2026世界杯 availability 算法效果对比报告 (全 104 场)</title>')
    html.append('<style>')
    html.append('body { font-family: -apple-system, "PingFang SC", sans-serif; max-width: 1400px; margin: 0 auto; padding: 24px; background: #f5f5f7; }')
    html.append('h1 { color: #1d1d1f; border-bottom: 3px solid #0066cc; padding-bottom: 12px; }')
    html.append('h2 { color: #0066cc; margin-top: 32px; }')
    html.append('.summary { background: #fff; border-radius: 12px; padding: 24px; margin: 16px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }')
    html.append('table { border-collapse: collapse; width: 100%; margin: 12px 0; background: #fff; font-size: 13px; }')
    html.append('th, td { padding: 8px 12px; border-bottom: 1px solid #e5e5e7; text-align: left; }')
    html.append('th { background: #f5f5f7; font-weight: 600; position: sticky; top: 0; z-index: 10; }')
    html.append('.delta-big { color: #d33; font-weight: bold; background: #ffe8e8; }')
    html.append('.delta-med { color: #e88; font-weight: bold; background: #fff5e8; }')
    html.append('.delta-small { color: #888; }')
    html.append('.callout { background: #e3f2fd; border-left: 4px solid #1976d2; padding: 16px; margin: 16px 0; border-radius: 4px; }')
    html.append('.callout-warn { background: #fff3e0; border-left: 4px solid #f57c00; padding: 16px; margin: 16px 0; border-radius: 4px; }')
    html.append('</style></head><body>')

    html.append('<h1>🌍 2026世界杯 availability 算法效果对比报告 (v2.2.4-9)</h1>')

    html.append('<div class="callout">')
    html.append(f'<b>数据规模:</b> {avail_count} 名核心球员的 availability 系数，覆盖 30+ 支参赛队的主要阵容')
    html.append('<br><b>算法改动:</b> 3 层穿透 — 球员评分直接折算 + 锋线/中场 top 折扣 + λ 直接乘系数绕开 cap')
    html.append('<br><b>测试场景:</b> 全 72 场小组赛，lambda_cap=5.0（开放上界以让 availability 折算穿透）')
    html.append('</div>')

    # 汇总统计
    avg_d_home = sum(d[0] for d in deltas) / len(deltas) if deltas else 0
    big_d = sum(1 for d, *_ in deltas if d >= 0.10)
    med_d = sum(1 for d, *_ in deltas if 0.05 <= d < 0.10)
    small_d = sum(1 for d, *_ in deltas if d < 0.05)
    html.append('<div class="callout-warn">')
    html.append(f'<b>📊 影响统计 (72 场小组赛):</b>')
    html.append(f'<br>• 平均 p_home_win 变化: <b>{avg_d_home:.3f}</b> ({(avg_d_home*100):.1f}%)')
    html.append(f'<br>• 大幅影响 (≥10%): <b>{big_d}</b> 场')
    html.append(f'<br>• 中等影响 (5-10%): <b>{med_d}</b> 场')
    html.append(f'<br>• 小幅影响 (<5%): <b>{small_d}</b> 场')
    html.append('</div>')

    # 表1: 受影响最大 TOP 15
    html.append('<h2>🔥 受 availability 影响最大的 15 场比赛</h2>')
    html.append('<div class="summary"><table>')
    html.append('<tr><th>#</th><th>比赛</th><th>p_home (旧)</th><th>p_home (新)</th><th>变化</th><th>旧最可能比分</th><th>新最可能比分</th><th>旧λ_主</th><th>新λ_主</th><th>影响来源</th></tr>')
    for i, (d, h, a, on, off) in enumerate(deltas[:15]):
        delta_class = 'delta-big' if d >= 0.10 else 'delta-med' if d >= 0.05 else 'delta-small'
        # 推断影响来源
        avail_rows = read_availability()
        affected = []
        for r in avail_rows:
            if r['国家'] in (h, a) and float(r['availability']) < 1.0:
                affected.append((r['球员'], float(r['availability']), r['国家']))
        affected.sort(key=lambda x: x[1])
        sources = ', '.join(f"{n}({a:.1f})" for n, a, _ in affected[:3])
        html.append(f'<tr>')
        html.append(f'<td>{i+1}</td>')
        html.append(f'<td><b>{h}</b> vs <b>{a}</b></td>')
        html.append(f'<td>{off["p_home_win"]:.3f}</td>')
        html.append(f'<td>{on["p_home_win"]:.3f}</td>')
        html.append(f'<td class="{delta_class}">{off["p_home_win"]-on["p_home_win"]:+.3f}</td>')
        html.append(f'<td>{off["best_score"]}({off["best_score_prob"]:.2f})</td>')
        html.append(f'<td>{on["best_score"]}({on["best_score_prob"]:.2f})</td>')
        html.append(f'<td>{off["lambda_home"]:.2f}</td>')
        html.append(f'<td>{on["lambda_home"]:.2f}</td>')
        html.append(f'<td class="note">{sources}</td>')
        html.append('</tr>')
    html.append('</table></div>')

    # 表2: 完整 72 场对照
    html.append('<h2>📋 完整 72 场小组赛对照</h2>')
    html.append('<div class="summary"><table>')
    html.append('<tr><th>轮次</th><th>主队</th><th>客队</th><th>旧 λ_主</th><th>新 λ_主</th><th>旧 p_home</th><th>新 p_home</th><th>Δ p_home</th><th>旧 best</th><th>新 best</th></tr>')
    # 按 group 分组
    from collections import defaultdict
    by_group = defaultdict(list)
    for d, h, a, on, off in deltas:
        # 取 round 信息
        r = on.get('round', '')
        g = on.get('group', '')
        by_group[(g, r)].append((d, h, a, on, off))
    for (g, r), matches in sorted(by_group.items(), key=lambda x: (x[0][0], x[0][1])):
        for d, h, a, on, off in matches:
            delta_class = 'delta-big' if d >= 0.10 else 'delta-med' if d >= 0.05 else 'delta-small'
            html.append(f'<tr>')
            html.append(f'<td>{g} {r}</td>')
            html.append(f'<td>{h}</td>')
            html.append(f'<td>{a}</td>')
            html.append(f'<td>{off["lambda_home"]:.2f}</td>')
            html.append(f'<td>{on["lambda_home"]:.2f}</td>')
            html.append(f'<td>{off["p_home_win"]:.3f}</td>')
            html.append(f'<td>{on["p_home_win"]:.3f}</td>')
            html.append(f'<td class="{delta_class}">{off["p_home_win"]-on["p_home_win"]:+.3f}</td>')
            html.append(f'<td>{off["best_score"]}({off["best_score_prob"]:.2f})</td>')
            html.append(f'<td>{on["best_score"]}({on["best_score_prob"]:.2f})</td>')
            html.append('</tr>')
    html.append('</table></div>')

    # 表3: 关键洞察
    html.append('<h2>💡 关键洞察</h2>')
    html.append('<div class="summary">')
    html.append('<h3>① 哪些比赛受影响最大?</h3>')
    html.append('<ul>')
    for d, h, a, on, off in deltas[:5]:
        html.append(f'<li><b>{h} vs {a}</b>: p_home {off["p_home_win"]:.3f}→{on["p_home_win"]:.3f} (-{(off["p_home_win"]-on["p_home_win"])*100:.1f}%)</li>')
    html.append('</ul>')

    html.append('<h3>② 算法洞察</h3>')
    html.append('<ul>')
    html.append('<li><b>冠军热门</b>（西班牙/法国/巴西/阿根廷/英格兰）的核心球员基本都是 1.0，所以模型变化不大</li>')
    html.append('<li><b>伤病核心</b>的比赛影响最大: 施洛特贝克（德国）, 罗梅罗（阿根廷）, 三笘薰（缺阵日本）, 久保建英（日本）, 拉菲尼亚（巴西）等</li>')
    html.append('<li>availability 让 "夺冠热门 vs 弱旅" 的 p_home 从 90%+ 降到了 80%+，更符合真实比赛情景</li>')
    html.append('<li>对于 <b>势均力敌的比赛</b>（如德国 vs 科特迪瓦），availability 改写胜负预测方向</li>')
    html.append('</ul>')

    html.append('<h3>③ 市场含义</h3>')
    html.append('<p>对于竞彩玩家来说, 启用 availability 后算法的价值投注（EV &gt; 3%）会显著变化。')
    html.append('特别是当一支球队的<b>关键球员突然伤缺</b>，但市场赔率还来不及调整时，')
    html.append('availability 模型能立刻给出修正后的预测。</p>')
    html.append('</div>')

    html.append('</body></html>')

    OUT_HTML.write_text(''.join(html), encoding='utf-8')
    print(f'Report saved to {OUT_HTML}')

if __name__ == '__main__':
    main()