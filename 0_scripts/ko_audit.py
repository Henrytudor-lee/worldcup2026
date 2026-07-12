"""
KO Audit v1 (2026-07-12)
========================
对 match_results.csv 中 6/29 起的 KO 完赛比赛跑 v3 predict (is_knockout=True),
对比 actual, 算:
  - 胜平负准确率 (按 stage 拆分: R32/R16/QF)
  - 比分命中率 (best_score 完全命中)
  - 加时/点球命中率 (pred 平 vs actual 加时/点球)
  - 高置信场准确率 (pred 概率 > 0.5)
  - 错分场次详情

输出:
  - 4_比赛预测/ko_audit_20260712.html (完整 HTML 报告)
  - 4_比赛预测/ko_audit_20260712.json (结构化数据)
"""
import sys, csv, json, math
from pathlib import Path
from collections import defaultdict

ROOT = Path('/Users/garcia/Desktop/WorldCup2026')
sys.path.insert(0, str(ROOT / 'backend'))
from predictor import predict_match, compute_ranking, load_fifa, poisson_pmf  # noqa


# === 1. 加载数据 ===
with open(ROOT / '1_数据基础' / 'match_results.csv') as f:
    rows = list(csv.DictReader(f))

# 2.2.5 修: ko_real_results.json 已经合并到 match_results.csv (manual_ko_update + collector)
# 但 match_results.csv 没有 'went_to_pen' 字段, 只能从 note 推断 ("点球")
# 已知 4 场加时/点球 (注: collector 重抓会覆盖 manual 的 note 字段, 这里硬补)
# 6/29 德国-巴拉圭 (1-1, 加时, 巴拉圭晋级), 6/29 荷兰-摩洛哥 (1-1, 加时, 摩洛哥晋级)
# 7/3 澳大利亚-埃及 (1-1, 加时, 埃及晋级), 7/7 瑞士-哥伦比亚 (0-0, 点球, 瑞士晋级)
KNOWN_PEN = {
    ('德国', '巴拉圭'): '点球, 巴拉圭晋级',
    ('荷兰', '摩洛哥'): '点球, 摩洛哥晋级',
    ('澳大利亚', '埃及'): '点球, 埃及晋级',
    ('瑞士', '哥伦比亚'): '点球, 瑞士晋级',
}

# 已完赛 KO 比赛 (date >= 6/29, 去重 + manual 优先)
# v2.2.5 修: dedup 优先保留带 note/stage 的 manual_ko_update 记录
ko_actual = []
seen = set()
# 排序: note 非空 / stage 非空 优先
sorted_rows = sorted(rows, key=lambda r: (
    -(1 if r.get('note', '').strip() else 0),  # 有 note 优先
    -(1 if r.get('stage', '').strip() else 0),  # 有 stage 优先
    r['date'],
))
for r in sorted_rows:
    if r['date'] < '2026-06-29':
        continue
    if not r['home_score']:
        continue
    k = (r['home'], r['away'])
    if k in seen:
        continue
    seen.add(k)
    note = (r.get('note') or '').strip()
    if not note and k in KNOWN_PEN:
        note = KNOWN_PEN[k]
    ko_actual.append({
        'date': r['date'],
        'home': r['home'],
        'away': r['away'],
        'hs': int(r['home_score']),
        'aws': int(r['away_score']),
        'stage': (r.get('stage') or '').strip(),
        'note': note,
    })

# 2.2.5 修: 6/28 南非-加拿大 不是 R32 (小组赛末轮错位抓的), 排除
# 判断: 6/28 之前已是末轮, 6/29 才是 R32 第 1 天
ko_actual = [m for m in ko_actual if m['date'] >= '2026-06-29']

# 按日期推断 stage
def infer_stage(date_str, has_explicit_stage):
    """按 ET 日期推断 KO 阶段 (6/29=R32 第1天, 7/4=R16 第1天, 7/9=QF 第1天)"""
    if has_explicit_stage:
        return has_explicit_stage
    if date_str < '2026-07-04':
        return 'R32'
    if date_str < '2026-07-09':
        return 'R16'
    return 'QF'

# 6/28 南非-加拿大 (B 组 vs A 组) 不是 KO
# 7/4 加拿大-摩洛哥 + 巴拉圭-法国 是 R16 (7/4 是 R16 第 1 天)
# 7/5-7/7 R16, 7/9-7/11 QF
for m in ko_actual:
    if not m['stage']:
        m['stage'] = infer_stage(m['date'], '')

# 排除 6/28 南非-加拿大 (如果还有)
ko_actual = [m for m in ko_actual if not (m['date'] == '2026-06-28' and m['home'] == '南非' and m['away'] == '加拿大')]

# 6/28 这条可能没在 ko_actual (因为我们过滤了 date < 6/29)

print(f'KO 完赛 (去重, 按 stage 推断): {len(ko_actual)} 场')
stage_counts = defaultdict(int)
for m in ko_actual:
    stage_counts[m['stage']] += 1
print(f'  Stage 分布: {dict(stage_counts)}')


# === 2. 加载 weights + ranking ===
weights_v21 = json.load(open(ROOT / '5_算法' / 'weights_v21.json'))
# v3 KO 调整的 weights (从 v3 json / predict_match 默认)
ko_weights = {
    **weights_v21,
    'knockout_lambda_reducer': 0.85,    # KO λ reducer
    'extra_time_prob': 0.20,            # P(平) 额外加 20%
    'extra_time_min_draw_prob': 0.25,   # P(平) 至少 25%
    'red_card_penalty': 0.70,           # 红牌 × 0.7
    'draw_boost': 1.0,                  # 不 boost 平
}
ranking = compute_ranking(weights_v21)
ranking_dict = {r['team']: r for r in ranking}
fifa = load_fifa()


# === 3. 跑 v3 KO predict ===
def predict_ko(home, away):
    """跑 v3 KO predict (is_knockout=True)"""
    return predict_match(home, away, ranking_dict, fifa, weights=ko_weights, is_knockout=True)


def evaluate_pred(pred, hs, aws):
    """算 pred 准确率"""
    p_h = pred['p_home_win']
    p_d = pred['p_draw']
    p_a = pred['p_away_win']
    pred_outcome = 'H' if p_h > p_d and p_h > p_a else ('A' if p_a > p_d and p_a > p_h else 'D')
    actual_outcome = 'H' if hs > aws else ('A' if aws > hs else 'D')
    correct = pred_outcome == actual_outcome
    score_match = pred['best_score'] == f'{hs}-{aws}'
    return {
        'pred_outcome': pred_outcome,
        'actual_outcome': actual_outcome,
        'correct': correct,
        'best_score': pred['best_score'],
        'actual_score': f'{hs}-{aws}',
        'score_match': score_match,
        'max_prob': max(p_h, p_d, p_a),
    }


audit_results = []
for m in ko_actual:
    pred = predict_ko(m['home'], m['away'])
    ev = evaluate_pred(pred, m['hs'], m['aws'])
    went_pen = '点球' in m['note']
    audit_results.append({
        **m,
        **ev,
        'went_pen': went_pen,
        'p_h': pred['p_home_win'],
        'p_d': pred['p_draw'],
        'p_a': pred['p_away_win'],
        'lambda_home': pred['lambda_home'],
        'lambda_away': pred['lambda_away'],
        'ko_adj': pred.get('ko_adjustments', {}),
    })


# === 4. 统计 ===
def stats_by_stage(results, stage_name):
    """算某 stage 的统计"""
    rs = [r for r in results if r['stage'] == stage_name]
    if not rs:
        return None
    correct = sum(1 for r in rs if r['correct'])
    score_match = sum(1 for r in rs if r['score_match'])
    # 高置信 (max_prob > 0.5) 准确率
    high_conf = [r for r in rs if r['max_prob'] > 0.5]
    high_conf_correct = sum(1 for r in high_conf if r['correct'])
    # 加时/点球
    pen_rs = [r for r in rs if r['went_pen']]
    pen_pred_d = sum(1 for r in pen_rs if r['pred_outcome'] == 'D')
    return {
        'total': len(rs),
        'correct': correct,
        'accuracy': correct / len(rs) if rs else 0,
        'score_match': score_match,
        'score_rate': score_match / len(rs) if rs else 0,
        'high_conf_total': len(high_conf),
        'high_conf_correct': high_conf_correct,
        'high_conf_accuracy': high_conf_correct / len(high_conf) if high_conf else None,
        'pen_total': len(pen_rs),
        'pen_pred_draw': pen_pred_d,
        'pen_draw_rate': pen_pred_d / len(pen_rs) if pen_rs else None,
    }


stages = ['R32', 'R16', 'QF']
all_stats = {}
for s in stages:
    all_stats[s] = stats_by_stage(audit_results, s)
all_stats['KO 总计'] = stats_by_stage(audit_results, 'KO 总计') or stats_by_stage(audit_results, '__all__')

# 强制算 KO 总计
total = len(audit_results)
correct = sum(1 for r in audit_results if r['correct'])
score_match = sum(1 for r in audit_results if r['score_match'])
high_conf = [r for r in audit_results if r['max_prob'] > 0.5]
high_conf_correct = sum(1 for r in high_conf if r['correct'])
pen_rs = [r for r in audit_results if r['went_pen']]
pen_pred_d = sum(1 for r in pen_rs if r['pred_outcome'] == 'D')

all_stats['KO 总计'] = {
    'total': total,
    'correct': correct,
    'accuracy': correct / total if total else 0,
    'score_match': score_match,
    'score_rate': score_match / total if total else 0,
    'high_conf_total': len(high_conf),
    'high_conf_correct': high_conf_correct,
    'high_conf_accuracy': high_conf_correct / len(high_conf) if high_conf else None,
    'pen_total': len(pen_rs),
    'pen_pred_draw': pen_pred_d,
    'pen_draw_rate': pen_pred_d / len(pen_rs) if pen_rs else None,
}

print()
print('=== KO Audit v3 准确率 (is_knockout=True) ===')
for s in ['KO 总计', 'R32', 'R16', 'QF']:
    st = all_stats[s]
    if not st: continue
    print(f"  {s}: {st['correct']}/{st['total']} = {st['accuracy']*100:.1f}%")
    if st.get('high_conf_total'):
        print(f"    高置信 (>0.5): {st['high_conf_correct']}/{st['high_conf_total']} = {st['high_conf_accuracy']*100:.1f}%")
    if st.get('pen_total'):
        print(f"    加时/点球: pred=平 {st['pen_pred_draw']}/{st['pen_total']} = {st['pen_draw_rate']*100:.1f}%")
    print(f"    比分命中: {st['score_match']}/{st['total']} = {st['score_rate']*100:.1f}%")


# === 5. 错分场次 ===
wrong = [r for r in audit_results if not r['correct']]
print(f'\n=== 错分场次 ({len(wrong)} 场) ===')
for w in wrong:
    pen = ' [点球]' if w['went_pen'] else ''
    print(f"  ❌ {w['date']} [{w['stage']:<4}] {w['home']:<8} {w['hs']}-{w['aws']} {w['away']:<8}{pen} | pred {w['pred_outcome']} ({w['best_score']}, p={w['p_h']:.2f}/{w['p_d']:.2f}/{w['p_a']:.2f})")


# === 6. 输出 HTML ===
import datetime as _dt
now_str = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def fmt_pct(x):
    return f"{x*100:.1f}%" if x is not None else '-'

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>KO Audit v3 — {now_str}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 1280px; margin: 30px auto; padding: 20px; background: #f8f8f5; color: #1a1a1a; }}
  h1 {{ color: #2c5f2d; }}
  h2 {{ color: #5a3a1f; border-bottom: 2px solid #d4a574; padding-bottom: 6px; }}
  .meta {{ font-size: 12px; color: #888; }}
  .summary {{ background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin: 20px 0; }}
  .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 16px 0; }}
  .kpi {{ padding: 16px; background: #fef7e8; border-radius: 8px; }}
  .kpi-num {{ font-size: 28px; font-weight: 700; color: #5a3a1f; }}
  .kpi-label {{ color: #777; font-size: 13px; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.05); margin: 16px 0; }}
  th, td {{ padding: 8px 10px; text-align: left; font-size: 13px; }}
  th {{ background: #5a3a1f; color: #fff; }}
  tr:nth-child(even) {{ background: #faf6ee; }}
  .ok {{ color: #2c5f2d; font-weight: 700; }}
  .bad {{ color: #c0392b; font-weight: 700; }}
  .score {{ font-family: monospace; font-weight: 600; }}
  .stage {{ display: inline-block; padding: 2px 6px; background: #d4a574; color: #fff; border-radius: 4px; font-size: 11px; }}
  .pen {{ color: #c0392b; font-size: 11px; margin-left: 4px; }}
  .footer {{ margin-top: 30px; padding: 16px; background: #fff; border-radius: 8px; font-size: 13px; color: #555; }}
  .note {{ background: #fff8e1; padding: 12px; border-radius: 8px; font-size: 13px; margin: 12px 0; border-left: 4px solid #d4a574; }}
</style>
</head>
<body>
<h1>⚽ KO Audit v3 — 淘汰赛算法准确率</h1>
<p class="meta">生成时间: {now_str} | cron: ko-audit (0 */6 * * *) | KO 完赛: {total} 场 (R32: {all_stats['R32']['total']}, R16: {all_stats['R16']['total']}, QF: {all_stats['QF']['total']})</p>

<div class="summary">
<h2>📊 KO 整体准确率 (v3 算法 is_knockout=True)</h2>
<div class="kpi-row">
  <div class="kpi"><div class="kpi-num">{correct}/{total}</div><div class="kpi-label">胜平负准确 (KO 总)</div></div>
  <div class="kpi"><div class="kpi-num">{fmt_pct(all_stats['KO 总计']['accuracy'])}</div><div class="kpi-label">准确率</div></div>
  <div class="kpi"><div class="kpi-num">{score_match}/{total}</div><div class="kpi-label">比分命中</div></div>
  <div class="kpi"><div class="kpi-num">{fmt_pct(all_stats['KO 总计']['score_rate'])}</div><div class="kpi-label">比分命中率</div></div>
</div>
<div class="kpi-row">
  <div class="kpi"><div class="kpi-num">{high_conf_correct}/{len(high_conf)}</div><div class="kpi-label">高置信 (>0.5) 准确</div></div>
  <div class="kpi"><div class="kpi-num">{fmt_pct(all_stats['KO 总计']['high_conf_accuracy'])}</div><div class="kpi-label">高置信准确率</div></div>
  <div class="kpi"><div class="kpi-num">{pen_pred_d}/{len(pen_rs)}</div><div class="kpi-label">加时/点球 pred=平</div></div>
  <div class="kpi"><div class="kpi-num">{fmt_pct(all_stats['KO 总计']['pen_draw_rate'])}</div><div class="kpi-label">加时/点球 pred=平 命中率</div></div>
</div>
</div>

<h2>📋 按阶段拆分</h2>
<table>
<thead>
<tr>
  <th>阶段</th>
  <th>场次</th>
  <th>胜平负准确</th>
  <th>准确率</th>
  <th>比分命中</th>
  <th>比分率</th>
  <th>高置信准确</th>
  <th>加时/点球</th>
</tr>
</thead>
<tbody>
"""

for s in ['R32', 'R16', 'QF']:
    st = all_stats[s]
    if not st: continue
    hc = f"{st['high_conf_correct']}/{st['high_conf_total']} ({fmt_pct(st['high_conf_accuracy'])})" if st.get('high_conf_total') else '-'
    pen = f"{st['pen_pred_draw']}/{st['pen_total']} ({fmt_pct(st['pen_draw_rate'])})" if st.get('pen_total') else '-'
    html += f"""<tr>
  <td><span class="stage">{s}</span></td>
  <td>{st['total']}</td>
  <td class="{'ok' if st['accuracy'] >= 0.6 else 'bad'}">{st['correct']}/{st['total']}</td>
  <td class="{'ok' if st['accuracy'] >= 0.6 else 'bad'}">{fmt_pct(st['accuracy'])}</td>
  <td>{st['score_match']}/{st['total']}</td>
  <td>{fmt_pct(st['score_rate'])}</td>
  <td>{hc}</td>
  <td>{pen}</td>
</tr>
"""

html += f"""</tbody>
</table>

<h2>📋 全部 {total} 场 KO 比赛明细</h2>
<table>
<thead>
<tr>
  <th>阶段</th>
  <th>日期</th>
  <th>主队</th>
  <th>比分</th>
  <th>客队</th>
  <th>Pred 比分</th>
  <th>P(H/D/A)</th>
  <th>Pred</th>
  <th>Actual</th>
  <th>胜平负</th>
  <th>比分</th>
</tr>
</thead>
<tbody>
"""

for r in audit_results:
    pen = '<span class="pen">[点球]</span>' if r['went_pen'] else ''
    correct_class = 'ok' if r['correct'] else 'bad'
    score_class = 'ok' if r['score_match'] else ''
    p_text = f"{r['p_h']:.2f}/{r['p_d']:.2f}/{r['p_a']:.2f}"
    pred_str = r['pred_outcome']
    actual_str = r['actual_outcome']
    html += f"""<tr>
  <td><span class="stage">{r['stage']}</span></td>
  <td>{r['date']}</td>
  <td><b>{r['home']}</b></td>
  <td class="score">{r['hs']}-{r['aws']}{pen}</td>
  <td><b>{r['away']}</b></td>
  <td class="score">{r['best_score']}</td>
  <td class="meta">{p_text}</td>
  <td>{pred_str}</td>
  <td>{actual_str}</td>
  <td class="{correct_class}">{'✓' if r['correct'] else '✗'}</td>
  <td class="{score_class}">{'✓' if r['score_match'] else '✗'}</td>
</tr>
"""

# 错分场次摘要
html += f"""</tbody>
</table>

<h2>❌ 错分场次 ({len(wrong)} 场) — 算法改进点</h2>
<table>
<thead>
<tr>
  <th>阶段</th>
  <th>日期</th>
  <th>比赛</th>
  <th>实际</th>
  <th>Pred 比分</th>
  <th>P(H/D/A)</th>
  <th>Pred</th>
  <th>Actual</th>
  <th>分析</th>
</tr>
</thead>
<tbody>
"""

for w in wrong:
    pen = '[点球]' if w['went_pen'] else ''
    # 分析: pred vs actual 差在哪
    if w['went_pen'] and w['pred_outcome'] != 'D':
        analysis = '点球场但 pred 非平 (加时/点球命中率低)'
    elif w['actual_outcome'] == 'D' and w['pred_outcome'] != 'D':
        analysis = '实际平但 pred 非平'
    elif w['actual_outcome'] != 'D' and w['pred_outcome'] == 'D':
        analysis = 'pred 平但实际分胜负'
    elif w['pred_outcome'] == 'H' and w['actual_outcome'] == 'A':
        analysis = 'pred 主胜, 实际客胜 (实力判断错)'
    elif w['pred_outcome'] == 'A' and w['actual_outcome'] == 'H':
        analysis = 'pred 客胜, 实际主胜 (主场优势低估)'
    else:
        analysis = '-'
    p_text = f"{w['p_h']:.2f}/{w['p_d']:.2f}/{w['p_a']:.2f}"
    html += f"""<tr>
  <td><span class="stage">{w['stage']}</span></td>
  <td>{w['date']}</td>
  <td><b>{w['home']}</b> vs <b>{w['away']}</b> {pen}</td>
  <td class="score">{w['hs']}-{w['aws']}</td>
  <td class="score">{w['best_score']}</td>
  <td class="meta">{p_text}</td>
  <td>{w['pred_outcome']}</td>
  <td>{w['actual_outcome']}</td>
  <td class="meta">{analysis}</td>
</tr>
"""

html += f"""</tbody>
</table>

<div class="note">
<b>💡 v24 候选改进方向 (来自错分分析):</b>
<ul>
  <li><b>加时/点球预测</b>: 当前 pred 加时/点球命中率 {pen_pred_d}/{len(pen_rs)} = {fmt_pct(all_stats['KO 总计']['pen_draw_rate'])}, 需要提高 P(平) base</li>
  <li><b>R32 vs R16 vs QF</b>: 三阶段准确率不同, 应单独调参 (越后期越要"分胜负"而非"平")</li>
  <li><b>高置信 (>0.5) 准确率</b>: {high_conf_correct}/{len(high_conf)} = {fmt_pct(all_stats['KO 总计']['high_conf_accuracy'])} — 算法对自己"自信"的方向准不准</li>
  <li><b>比分命中率</b>: {score_match}/{total} = {fmt_pct(all_stats['KO 总计']['score_rate'])} — best_score 经常跟 actual 偏差大</li>
</ul>
</div>

<div class="footer">
<b>数据源</b>: 
match_results.csv (130 行, 7/12 collector 更新) + v3 算法 (predict_match is_knockout=True) + weights_v21.json + 默认 KO 调整 (knockout_lambda_reducer=0.85, extra_time_prob=0.20, extra_time_min_draw_prob=0.25, red_card_penalty=0.70)
<br><br>
<b>KO 完赛分布</b>: R32 {all_stats['R32']['total']} 场 (6/29-7/3) | R16 {all_stats['R16']['total']} 场 (7/4-7/7) | QF {all_stats['QF']['total']} 场 (7/9-7/11) | 合计 {total} 场
<br><br>
<b>阶段进度</b>: R32 16/16 ✓ | R16 8/8 ✓ | QF 4/4 ✓ | SF 0/2 | 3RD 0/1 | Final 0/1 (32 场 KO 已完赛 28 场, 剩 4 场 SF/3RD/Final)
<br><br>
<b>Cron</b>: ko-audit (schedule: 0 */6 * * *) | 下次跑: 2026-07-13 00:00 (Asia/Shanghai)
</div>
</body>
</html>
"""

out_html = ROOT / '4_比赛预测' / 'ko_audit_20260712.html'
out_html.write_text(html, encoding='utf-8')
print(f'\n✅ HTML 报告: {out_html}')

# 也存 JSON
out_json = ROOT / '4_比赛预测' / 'ko_audit_20260712.json'
out_json.write_text(json.dumps({
    'generated_at': now_str,
    'total': total,
    'stats': {k: v for k, v in all_stats.items() if v is not None},
    'matches': [
        {k: v for k, v in r.items() if k != 'ko_adj'} for r in audit_results
    ],
}, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
print(f'✅ JSON 数据: {out_json}')
