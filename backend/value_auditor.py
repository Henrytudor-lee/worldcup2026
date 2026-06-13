"""
Mavis PDP 身价校对脚本 (v1.0)

对每个队, 用 web search 拿"德转 {国} 身价 2026", 然后跟 CSV 对比.
输出 CSV vs 德转 差异 (差 >30% 标红).

⚠️ 暂未实现 web 搜索 (需要 search API key)
   占位实现: 读 known_mismatches.json 里手动维护的差异名单
"""
import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV = PROJECT_ROOT / '1_数据基础' / 'world_cup_2026_complete.csv'
MISMATCHES = PROJECT_ROOT / '1_数据基础' / 'known_mismatches.json'


def load_known_mismatches():
    """读已知差异名单 (用户/agent 维护)"""
    if MISMATCHES.exists():
        with open(MISMATCHES, encoding='utf-8') as f:
            return json.load(f)
    return {}


def check_mismatches():
    """遍历 CSV 球员, 跟 known_mismatches 对比"""
    mismatches = load_known_mismatches()
    issues = []
    with open(CSV, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            name = row['球员']
            country = row['国家']
            team = row['俱乐部']
            csv_value_str = str(row.get('身价_万欧', '0') or '0').replace(',', '').strip()
            try:
                csv_value = int(float(csv_value_str))
            except ValueError:
                csv_value = 0
            key = f"{country}_{name}"
            if key in mismatches:
                expected = mismatches[key]
                if csv_value != expected:
                    issues.append({
                        'country': country, 'name': name, 'team': team,
                        'csv_value': csv_value, 'expected_value': expected,
                        'source': '德转 2026-06',
                        'delta_pct': round((csv_value - expected) / expected * 100, 1),
                    })
    return issues


if __name__ == '__main__':
    issues = check_mismatches()
    if not issues:
        print('✓ CSV 身价与已知德转数据一致 (零差异)')
    else:
        print(f'⚠️ 发现 {len(issues)} 处 CSV vs 德转差异:')
        print()
        for i in issues:
            delta = i['delta_pct']
            flag = '🔴' if abs(delta) > 50 else '🟡' if abs(delta) > 30 else '🟢'
            print(f"  {flag} {i['country']} {i['name']} ({i['team']})")
            print(f"      CSV={i['csv_value']} 万欧, 德转={i['expected_value']} 万欧, 差 {delta:+.1f}%")
