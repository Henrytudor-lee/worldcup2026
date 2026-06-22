"""
生成 MD2 预测 HTML 报告 (v1)
- 24 场按日期分组
- 重点场标星
- 显示 λ + 最可能比分 + 概率
"""
import json
from datetime import datetime

with open('/Users/garcia/Desktop/WorldCup2026/4_比赛预测/md2_predictions_best.json') as f:
    preds = json.load(f)

# 按日期分组
by_date = {}
for p in preds:
    d = p['date'][:10]  # YYYY-MM-DD
    by_date.setdefault(d, []).append(p)

# 强队清单 (重点场标星)
star_teams = ['巴西', '阿根廷', '法国', '英格兰', '西班牙', '葡萄牙', '德国',
              '荷兰', '乌拉圭', '挪威', '比利时', '墨西哥', '美国', '韩国', '日本']

# λ 撞顶 (4.10) 警告
LAMBDA_CEILING = 4.10

# 算法权重信息
with open('/Users/garcia/Desktop/WorldCup2026/5_算法/calibration_best.json') as f:
    best = json.load(f)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>WorldCup 2026 第二轮预测 (6/19-6/24) - Best Weights</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
         max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f7fa; }}
  h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
  .meta {{ background: #fff; padding: 15px; border-radius: 8px; margin: 15px 0;
           box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 14px; color: #555; }}
  .meta strong {{ color: #e74c3c; }}
  .date-group {{ background: #fff; margin: 20px 0; border-radius: 8px;
                 box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }}
  .date-header {{ background: #34495e; color: #fff; padding: 12px 18px;
                  font-size: 18px; font-weight: bold; }}
  .match {{ padding: 14px 18px; border-bottom: 1px solid #ecf0f1;
            display: grid; grid-template-columns: 100px 1fr 1.5fr 1.5fr;
            gap: 15px; align-items: center; }}
  .match:last-child {{ border-bottom: none; }}
  .match.highlight {{ background: #fffbe6; }}
  .time {{ font-weight: bold; color: #2c3e50; }}
  .teams {{ font-size: 16px; }}
  .teams .vs {{ color: #95a5a6; margin: 0 8px; }}
  .star {{ color: #f39c12; margin-right: 4px; }}
  .probs {{ font-family: monospace; font-size: 13px; }}
  .p-home {{ color: #27ae60; font-weight: bold; }}
  .p-draw {{ color: #f39c12; font-weight: bold; }}
  .p-away {{ color: #e74c3c; font-weight: bold; }}
  .detail {{ font-size: 12px; color: #7f8c8d; font-family: monospace; }}
  .ceiling {{ color: #e74c3c; font-weight: bold; }}
  .ceiling-warn {{ background: #ffebee; border-left: 4px solid #e74c3c;
                   padding: 12px 18px; margin: 15px 0; border-radius: 4px; }}
  .algorithm-info {{ background: #e8f5e9; border-left: 4px solid #4caf50;
                     padding: 12px 18px; margin: 15px 0; border-radius: 4px;
                     font-size: 13px; }}
  .group {{ color: #3498db; font-weight: bold; }}
</style>
</head>
<body>

<h1>⚽ WorldCup 2026 - 第二轮 (Match Day 2) 赛前预测</h1>

<div class="meta">
  <div><strong>📅 比赛日期:</strong> 2026-06-19 ~ 2026-06-24 (北京时间)</div>
  <div><strong>🎯 预测依据:</strong> 6/18 校准后 best weights (loss = {best['loss']:.2f}, n=24 场真实结果训练)</div>
  <div><strong>⚙️ 算法:</strong> λ = 1.3 × 持球率 × √(attack×0.001) × 教练 × 场地 × FIFA → Poisson 进球分布</div>
  <div><strong>📊 训练数据:</strong> 第一轮 24 场真实结果 (6/11-6/18, win_acc 67%, MAE 2.71)</div>
  <div><strong>🏆 冠军预测:</strong> 🇫🇷 法国 (基于 best weights, 7.8% 夺冠概率)</div>
</div>

<div class="algorithm-info">
  <strong>💡 算法当前状态:</strong><br>
  • 强队系统性低估进球期望: λ ceiling = {LAMBDA_CEILING}, 巴西/西班牙/法国/比利时/葡萄牙/阿根廷/英格兰/德国/荷兰/挪威等强队都撞顶<br>
  • 平局概率系统性低估: 6/14-6/15 四场"热门身价全平"显示算法对"强强对"和"湿热气候"识别不足<br>
  • 当前 draw_boost: 1.5, 已在 best weights 中调到最优<br>
  • 训练数据 n=24 仍偏少, 6/19 12:00 cron 会再用 n=24 重新校准一次
</div>

<div class="ceiling-warn">
  <strong>⚠️ λ Ceiling 警告:</strong> 共有 <span class="ceiling">10 场</span> 强队比赛 λ 撞顶 4.10,
  这些比赛的"真实概率"被系统性低估 (因为 λ 没法再涨). 实际比分通常比预测更悬殊.<br>
  受影响: 巴西 vs 海地 / 西班牙 vs 沙特 / 比利时 vs 伊朗 / 法国 vs 伊拉克 / 葡萄牙 vs 乌兹别克斯坦 /
  阿根廷 vs 奥地利 / 英格兰 vs 加纳 / 挪威 vs 塞内加尔 / 荷兰 vs 瑞典 / 德国 vs 科特迪瓦
</div>

"""

# 按日期输出
for date in sorted(by_date.keys()):
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][date_obj.weekday()]
    html += f'<div class="date-group">\n'
    html += f'<div class="date-header">📅 {date} ({weekday}) · 北京时间 · {len(by_date[date])} 场</div>\n'

    for p in sorted(by_date[date], key=lambda x: x['date']):
        is_highlight = any(t in p['home'] or t in p['away'] for t in star_teams)
        cls = 'match highlight' if is_highlight else 'match'

        time = p['date'][11:16]  # HH:MM
        star = '⭐' if is_highlight else '  '
        home_ceiling = '⚠️' if p['lambda_home'] >= LAMBDA_CEILING else ''
        away_ceiling = '⚠️' if p['lambda_away'] >= LAMBDA_CEILING else ''

        html += f'<div class="{cls}">\n'
        html += f'  <div class="time">{time}</div>\n'
        html += f'  <div class="teams"><span class="star">{star}</span><span class="group">[{p["group"]}]</span> <strong>{p["home"]}</strong> <span class="vs">vs</span> <strong>{p["away"]}</strong></div>\n'
        html += f'  <div class="probs">主<span class="p-home">{p["p_home_win"]*100:.1f}%</span> 平<span class="p-draw">{p["p_draw"]*100:.1f}%</span> 客<span class="p-away">{p["p_away_win"]*100:.1f}%</span></div>\n'
        html += f'  <div class="detail">最可能: <strong>{p["best_score"]}</strong> ({p["best_score_prob"]*100:.1f}%) | λ {home_ceiling}{p["lambda_home"]:.2f} vs {away_ceiling}{p["lambda_away"]:.2f}</div>\n'
        html += f'</div>\n'
    html += '</div>\n'

# 重点关注 - 强强对话
html += '<div class="date-group">\n'
html += '<div class="date-header" style="background:#e74c3c;">🔥 强强对话 - 算法对位不下的 3 场对称预测</div>\n'
sym_matches = [p for p in preds
               if abs(p['lambda_home'] - LAMBDA_CEILING) < 0.05
               and abs(p['lambda_away'] - LAMBDA_CEILING) < 0.05]
for p in sym_matches:
    html += f'<div class="match highlight">\n'
    html += f'  <div class="time">{p["date"][11:16]}</div>\n'
    html += f'  <div class="teams"><span class="star">⭐</span><span class="group">[{p["group"]}]</span> <strong>{p["home"]}</strong> <span class="vs">vs</span> <strong>{p["away"]}</strong></div>\n'
    html += f'  <div class="probs">主<span class="p-home">{p["p_home_win"]*100:.1f}%</span> 平<span class="p-draw">{p["p_draw"]*100:.1f}%</span> 客<span class="p-away">{p["p_away_win"]*100:.1f}%</span></div>\n'
    html += f'  <div class="detail">⚠️ 双强撞顶, 算法对位不下. 真实胜负 50:50 取决于临场.</div>\n'
    html += f'</div>\n'
html += '</div>\n'

html += """
<div class="meta" style="margin-top:30px; background:#fff3cd; border-left:4px solid #ffc107;">
  <strong>📌 等 6/19 12:00 cron 自动校准:</strong><br>
  • 当前 best weights 基于 n=24 训练<br>
  • 6/19 12:00 cron 会跑 50 轮贝叶斯再优化一次<br>
  • 如果新 loss 破纪录, weights 会更新 (但 save_best bug 暂未修, 不做"是否破纪录"判断)<br>
  • 6/19 第一场 00:00 捷克 vs 南非, 24:00 自动入库后 cron 会拿来训练
</div>

</body>
</html>
"""

with open('/Users/garcia/Desktop/WorldCup2026/4_比赛预测/md2_predictions_best.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'✅ HTML 报告 → /Users/garcia/Desktop/WorldCup2026/4_比赛预测/md2_predictions_best.html')
print(f'   总场次: {len(preds)} | 日期范围: {min(p["date"] for p in preds)[:10]} ~ {max(p["date"] for p in preds)[:10]}')
print(f'   重点场: {sum(1 for p in preds if any(t in p["home"] or t in p["away"] for t in star_teams))}')
print(f'   λ 撞顶: {sum(1 for p in preds if p["lambda_home"] >= LAMBDA_CEILING or p["lambda_away"] >= LAMBDA_CEILING)}')
