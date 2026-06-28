"""
sync_match_results.py
=====================
将 match_results.csv 的真实赛果同步到 5_算法/all_104_predictions.json
- 小组赛: 用 CSV 真实数据覆盖 actual_score, 重算 home_pts/away_pts
  * 匹配策略: (home, away) 优先 (因为 CSV 用本地日期, JSON 用北京时间)
  * 但 6/28 的 6 场 CSV 还没有 (J/K/L 第 3 轮), 标记为 pending
- R32 之后: 全部清除 actual_score, 标记 pending
- data_status: real | pending
"""
import json
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path("/Users/garcia/Desktop/WorldCup2026")
CSV_PATH = ROOT / "1_数据基础" / "match_results.csv"
JSON_PATH = ROOT / "5_算法" / "all_104_predictions.json"

def load_csv_results():
    """按 (home, away) 索引, 跳过 et_fix 重抓的重复行 (保留最早的)"""
    results = {}
    with open(CSV_PATH) as f:
        r = csv.DictReader(f)
        for row in r:
            key = (row['home'], row['away'])
            # 只保留第一次出现 (et_fix 是修正后的数据, 但 score 应该一致)
            if key not in results:
                results[key] = (row['date'], int(row['home_score']), int(row['away_score']))
    return results

def compute_points(hs, as_):
    if hs > as_: return (3, 0)
    if hs < as_: return (0, 3)
    return (1, 1)

def sync():
    csv_results = load_csv_results()
    print(f"CSV 真实赛果 (去重): {len(csv_results)} 条")
    data = json.load(open(JSON_PATH))
    print(f"JSON 比赛总数: {len(data)}")
    real_count = pending_count = conflict_log_count = 0
    conflict_log = []
    for pred in data:
        stage = pred.get('stage', '')
        home, away = pred['home'], pred['away']
        if stage == 'group':
            csv_score = csv_results.get((home, away))
            if csv_score:
                csv_date, hs, as_ = csv_score
                new_score = f"{hs}-{as_}"
                old_score = pred.get('actual_score')
                if old_score != new_score:
                    conflict_log.append(
                        f"  {pred['match_id']}: {old_score} -> {new_score} (CSV:{csv_date})"
                    )
                    conflict_log_count += 1
                pred['actual_score'] = new_score
                h_pts, a_pts = compute_points(hs, as_)
                pred['home_pts'] = h_pts
                pred['away_pts'] = a_pts
                pred['data_status'] = 'real'
                real_count += 1
            else:
                # 6/28 的 J/K/L 第 3 轮, CSV 暂无
                pred['actual_score'] = None
                pred['home_pts'] = None
                pred['away_pts'] = None
                pred['data_status'] = 'pending'
                pending_count += 1
        else:
            pred['actual_score'] = None
            pred['home_pts'] = None
            pred['away_pts'] = None
            pred['data_status'] = 'pending'
            pending_count += 1
    print(f"\n真实赛果覆盖: {real_count} 场 (小组赛)")
    print(f"待定 (含 R32 之后 + 6/28 未踢): {pending_count} 场")
    if conflict_log:
        print(f"\n{conflict_log_count} 处冲突修复:")
        for line in conflict_log[:25]:
            print(line)
        if len(conflict_log) > 25:
            print(f"  ... 还有 {len(conflict_log)-25} 条")
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n已写回: {JSON_PATH}")
    return data

def print_group_tables(data):
    print("\n" + "="*60)
    print("12 组最终积分榜 (基于真实赛果)")
    print("="*60)
    tbl = defaultdict(lambda: {'pts':0,'gf':0,'ga':0,'played':0,'w':0,'d':0,'l':0})
    for p in data:
        if p.get('stage') != 'group': continue
        if not p.get('actual_score'): continue
        h, a = p['home'], p['away']
        sh, sa = map(int, p['actual_score'].split('-'))
        for t, sc, op in [(h, sh, sa), (a, sa, sh)]:
            tbl[t]['gf'] += sc; tbl[t]['ga'] += op; tbl[t]['played'] += 1
            if sc > op: tbl[t]['w']+=1; tbl[t]['pts']+=3
            elif sc == op: tbl[t]['d']+=1; tbl[t]['pts']+=1
            else: tbl[t]['l']+=1
    groups = defaultdict(list)
    for t, s in tbl.items():
        grp = next((x['group'] for x in data if (x['home']==t or x['away']==t) and x.get('group')), '?')
        groups[grp].append((t, s['pts'], s['gf']-s['ga'], s['gf'], s['ga'], s['w'], s['d'], s['l']))
    third_place = []
    for g in sorted(groups):
        rows = sorted(groups[g], key=lambda r:(-r[1],-r[2],-r[3],-r[5]))
        print(f"\n  组 {g}:")
        for i, r in enumerate(rows, 1):
            tag = '[晋级]' if i<=2 else ('[第3]' if i==3 else '[淘汰]')
            print(f"    {i}. {r[0]:<8} {r[5]}胜{r[6]}平{r[7]}负 净{r[2]:+d}  {r[1]}分  {tag}")
        third_place.append(rows[2])
    print("\n" + "="*60)
    print("12 个第 3 名排序 (前 8 进 32 强)")
    print("="*60)
    third_sorted = sorted(third_place, key=lambda r:(-r[1],-r[2],-r[3],-r[5]))
    for i, r in enumerate(third_sorted, 1):
        tag = '进 32 强' if i <= 8 else '出局'
        print(f"  {i:2d}. {r[0]:<8} {r[1]}分 净{r[2]:+d} 进{r[3]}  [{tag}]")

if __name__ == '__main__':
    data = sync()
    print_group_tables(data)
