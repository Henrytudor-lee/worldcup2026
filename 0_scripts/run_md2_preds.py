"""
第二轮 (MD2) 预测 - 用 best weights
输出 JSON + HTML 报告
"""
import sys, json
sys.path.insert(0, '/Users/garcia/Desktop/WorldCup2026/backend')
import predictor

# 加载 best weights
with open('/Users/garcia/Desktop/WorldCup2026/5_算法/calibration_best.json') as f:
    best = json.load(f)
weights = best['weights']
print(f'✅ best weights (loss={best["loss"]})')

# 跑全赛程预测
preds = predictor.compute_predictions(weights)
all_preds = preds.get('predictions', [])

# 过滤第2轮 (round 包含 "第2轮")
md2_preds = [p for p in all_preds if '第2轮' in str(p.get('round', ''))]
print(f'✅ 第2轮: {len(md2_preds)} 场')

# 保存 JSON
out_json = '/Users/garcia/Desktop/WorldCup2026/4_比赛预测/md2_predictions_best.json'
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(md2_preds, f, ensure_ascii=False, indent=2)
print(f'✅ JSON → {out_json}')

# 输出重点场
print()
print('=== MD2 重点场预测 ===')
highlights = ['巴西', '阿根廷', '法国', '英格兰', '西班牙', '葡萄牙', '德国', '荷兰', '乌拉圭', '挪威', '比利时', '墨西哥', '美国', '韩国', '日本']
for p in sorted(md2_preds, key=lambda x: x['date']):
    is_highlight = any(t in p['home'] or t in p['away'] for t in highlights)
    marker = '⭐' if is_highlight else '  '
    print(f"  {marker} {p['date']} | {p['home']} vs {p['away']} ({p['group']})")
    print(f"      主{p['p_home_win']*100:.1f}% 平{p['p_draw']*100:.1f}% 客{p['p_away_win']*100:.1f}% | {p['best_score']} ({p['best_score_prob']*100:.1f}%) | λ={p['lambda_home']:.2f} vs {p['lambda_away']:.2f}")
