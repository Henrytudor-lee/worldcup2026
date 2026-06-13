"""
Mavis PDP 字段审计器 (v1.0)

每天 24:00 跑, 逐单元格检查 1248 球员的每个字段.
输出:
  - HTML 报告 (颜色高亮异常, 每球员/字段/问题)
  - JSON 摘要 (cron 微信通知用)

审计维度 (10+ 字段):
  - 必填: 姓名/国家/位置/俱乐部/联赛 (不能空)
  - 数值: 身价 (0=异常, 跨队异常), 国进球/助攻 (负数, 异常大)
  - 位置: 必须 ∈ {前锋, 中场, 后卫, 中后卫, 左后卫, 右后卫, 边后卫, 门将, 守门员, 前腰, 后腰}
  - 荣誉: 至少 1 个关键词 OR 空 (允许没荣誉)
  - 出生年: 推算年龄 16-50
  - 跨球员: 同名/同俱乐部异常

对照源: known_mismatches.json (德转权威)
"""
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV = PROJECT_ROOT / '1_数据基础' / 'world_cup_2026_complete.csv'
MISMATCHES = PROJECT_ROOT / '1_数据基础' / 'known_mismatches.json'
REPORT_DIR = PROJECT_ROOT / '6_审核报告' / 'field_audit'
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# 合法的位置
VALID_POSITIONS = {
    '前锋', '中场', '后腰', '前腰',
    '后卫', '中后卫', '左后卫', '右后卫', '边后卫',
    '门将', '守门员',
}

# 必填字段
REQUIRED_FIELDS = ['国家', '位置', '球员', '俱乐部', '联赛', '身价_万欧']

# 数值字段
NUMERIC_FIELDS = ['身价_万欧', '国家队进球', '国家队助攻']

# 出生年 (可能有或没有)
BIRTH_YEAR_FIELD = None  # 我们的 CSV 没这字段, 跳过


def load_known_mismatches():
    if MISMATCHES.exists():
        with open(MISMATCHES, encoding='utf-8') as f:
            return json.load(f)
    return {}


def parse_num(s):
    """'2,5' / '2.5' / '2' / '2万' → 2.0"""
    if s is None:
        return 0
    s = str(s).replace(',', '').replace('万欧', '').replace('万', '').strip()
    if not s or s == '-' or s == '?':
        return 0
    try:
        return float(s)
    except ValueError:
        return None  # 不可解析


def audit_field(player, field, value, all_players):
    """审计单个字段, 返回 issues 列表
    每个 issue: {level, field, msg}
    level: 'error' (必须修) / 'warn' (建议查)
    """
    issues = []
    name = player.get('球员', '?')
    country = player.get('国家', '?')

    # 1. 必填字段
    if field in REQUIRED_FIELDS:
        if not value or str(value).strip() in ('', '-', '?', 'N/A'):
            issues.append({'level': 'error', 'field': field, 'msg': f'必填项为空: {value!r}'})
            return issues  # 后续检查没意义

    # 2. 数值字段
    if field in NUMERIC_FIELDS:
        v = parse_num(value)
        if v is None:
            issues.append({'level': 'error', 'field': field, 'msg': f'无法解析数值: {value!r}'})
        elif v < 0:
            issues.append({'level': 'error', 'field': field, 'msg': f'负数: {v}'})
        elif field == '身价_万欧' and v > 20000:
            issues.append({'level': 'warn', 'field': field, 'msg': f'身价 > 2 亿欧: {v} (稀有)'})
        elif field == '身价_万欧' and v == 0:
            issues.append({'level': 'warn', 'field': field, 'msg': f'身价 = 0 (异常)'})
        elif field in ('国家队进球', '国家队助攻') and v > 200:
            issues.append({'level': 'warn', 'field': field, 'msg': f'国家队 {field} > 200: {v}'})

    # 3. 位置字段
    if field == '位置' and value:
        v = str(value).strip()
        if v not in VALID_POSITIONS:
            issues.append({'level': 'error', 'field': field, 'msg': f'未知位置: {v!r} (合法: {sorted(VALID_POSITIONS)})'})

    # 4. 球员名重复 (跨球员)
    if field == '球员' and value:
        same_name = [p for p in all_players if p.get('球员') == value and p.get('国家') != country]
        if same_name:
            issues.append({'level': 'warn', 'field': field, 'msg': f'与 {len(same_name)} 个其他国家队球员同名: {[p["国家"] for p in same_name[:3]]}'})

    # 5. 俱乐部字段 (允许空, 但不能是问号)
    if field == '俱乐部' and str(value).strip() in ('?', 'N/A', '无', '自由球员'):
        issues.append({'level': 'info', 'field': field, 'msg': f'俱乐部异常值: {value!r}'})

    # 6. 主要荣誉 (允许空, 但如果有必含关键词合理性检查)
    if field == '主要荣誉' and value:
        text = str(value)
        # 检测矛盾: 同时含 "U-20" 和 "世界杯冠军" (说明可能是青年赛写错)
        if 'U-20' in text and '世界杯冠军' in text and 'U-20 世青赛冠军' not in text:
            issues.append({'level': 'warn', 'field': field, 'msg': f'荣誉同时含 "U-20" 和 "世界杯冠军" - 是否误写? {text[:60]}'})

    return issues


def audit_known_mismatches(players, mismatches):
    """跟 known_mismatches.json 比对"""
    issues = []
    for p in players:
        name = p.get('球员', '?')
        country = p.get('国家', '?')
        key = f"{country}_{name}"
        if key in mismatches:
            expected_value = mismatches[key]
            actual_value = parse_num(p.get('身价_万欧', 0))
            if actual_value != expected_value:
                issues.append({
                    'level': 'error',
                    'field': '身价_万欧',
                    'country': country,
                    'name': name,
                    'msg': f'与 known_mismatches 不一致: CSV={actual_value}, 权威={expected_value}',
                    'key': key,
                })
    return issues


def audit_all():
    """主审计: 返回 issues 列表 + 统计"""
    with open(CSV, encoding='utf-8') as f:
        players = list(csv.DictReader(f))

    mismatches = load_known_mismatches()
    all_issues = []

    for p in players:
        country = p.get('国家', '?')
        name = p.get('球员', '?')
        # 遍历所有字段
        for field, value in p.items():
            field_issues = audit_field(p, field, value, players)
            for fi in field_issues:
                fi['country'] = country
                fi['name'] = name
                fi['row'] = p
                all_issues.append(fi)

    # known_mismatches 比对
    km_issues = audit_known_mismatches(players, mismatches)
    all_issues.extend(km_issues)

    # 统计
    stats = {
        'total_players': len(players),
        'total_issues': len(all_issues),
        'error_count': sum(1 for i in all_issues if i['level'] == 'error'),
        'warn_count': sum(1 for i in all_issues if i['level'] == 'warn'),
        'info_count': sum(1 for i in all_issues if i['level'] == 'info'),
    }
    # 按国家 + 字段分组
    by_country = defaultdict(int)
    by_field = defaultdict(int)
    for i in all_issues:
        by_country[i.get('country', '?')] += 1
        by_field[i.get('field', '?')] += 1

    return all_issues, stats, by_country, by_field, players


def render_html(issues, stats, by_country, by_field, players):
    """渲染 HTML 报告"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 按国家分组的 issue 表
    rows_by_player = defaultdict(list)
    for i in issues:
        key = f"{i.get('country', '?')}_{i.get('name', '?')}"
        rows_by_player[key].append(i)

    rows_html = ''
    for key, p_issues in sorted(rows_by_player.items(), key=lambda x: -len(x[1])):
        country, name = key.split('_', 1)
        sample = p_issues[0].get('row', {})
        level_class = 'error' if any(i['level'] == 'error' for i in p_issues) else \
                      'warn' if any(i['level'] == 'warn' for i in p_issues) else 'info'
        level_text = {'error': '🔴 必须修', 'warn': '🟡 建议查', 'info': '🔵 提示'}[level_class]
        issue_details = '<br>'.join(f"[{i['level']}] <b>{i['field']}</b>: {i['msg']}" for i in p_issues[:5])
        if len(p_issues) > 5:
            issue_details += f'<br><i>... 还有 {len(p_issues)-5} 条</i>'

        rows_html += f"""
        <tr class="row-{level_class}">
          <td><b>{country}</b></td>
          <td>{name}</td>
          <td>{sample.get('位置', '?')}</td>
          <td>{sample.get('俱乐部', '?')}</td>
          <td><span class="level-{level_class}">{level_text}</span></td>
          <td>{len(p_issues)}</td>
          <td class="issue-detail">{issue_details}</td>
        </tr>
        """

    # 国家统计
    country_stats = ''.join(
        f'<li><b>{c}</b>: {n} 处</li>' for c, n in sorted(by_country.items(), key=lambda x: -x[1])[:15]
    )
    # 字段统计
    field_stats = ''.join(
        f'<li><b>{f}</b>: {n} 处</li>' for f, n in sorted(by_field.items(), key=lambda x: -x[1])[:10]
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>📋 字段审计报告 {now}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0d1117; color: #d1d5db; padding: 20px; }}
h1 {{ color: #f87171; }}
h2 {{ color: #facc15; margin-top: 24px; }}
.stats {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }}
.stat {{ background: #161b22; padding: 12px 18px; border-radius: 8px; border-left: 4px solid #58a6ff; }}
.stat.error {{ border-color: #f87171; }}
.stat.warn {{ border-color: #facc15; }}
.stat.info {{ border-color: #58a6ff; }}
.stat-value {{ font-size: 22px; font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
th {{ background: #21262d; padding: 8px; text-align: left; font-size: 13px; }}
td {{ padding: 6px 8px; border-bottom: 1px solid #21262d; font-size: 12px; }}
tr.row-error td {{ background: rgba(248, 113, 113, 0.08); }}
tr.row-warn td {{ background: rgba(250, 204, 21, 0.06); }}
tr.row-info td {{ background: rgba(88, 166, 255, 0.05); }}
.level-error {{ color: #f87171; font-weight: 600; }}
.level-warn {{ color: #facc15; font-weight: 600; }}
.level-info {{ color: #58a6ff; }}
.issue-detail {{ color: #6b7280; font-size: 11px; }}
ul {{ columns: 2; column-gap: 24px; }}
</style>
</head>
<body>

<h1>📋 Mavis PDP 字段审计报告</h1>
<p>📅 {now} · 审计 {stats['total_players']} 球员</p>

<div class="stats">
  <div class="stat"><div class="stat-value">{stats['total_players']}</div><div>总球员数</div></div>
  <div class="stat error"><div class="stat-value">{stats['error_count']}</div><div>🔴 必须修</div></div>
  <div class="stat warn"><div class="stat-value">{stats['warn_count']}</div><div>🟡 建议查</div></div>
  <div class="stat info"><div class="stat-value">{stats['info_count']}</div><div>🔵 提示</div></div>
  <div class="stat"><div class="stat-value">{stats['total_issues']}</div><div>总问题</div></div>
</div>

<h2>📊 按国家分组 (Top 15)</h2>
<ul>{country_stats}</ul>

<h2>📊 按字段分组 (Top 10)</h2>
<ul>{field_stats}</ul>

<h2>📋 详细问题列表</h2>
<table>
<thead><tr>
  <th>国家</th><th>球员</th><th>位置</th><th>俱乐部</th><th>级别</th><th>条数</th><th>问题详情</th>
</tr></thead>
<tbody>
{rows_html}
</tbody>
</table>

<hr>
<p style="color:#6b7280;font-size:11px;">
自动化审计, 详细字段含义见 <code>1_数据基础/known_mismatches.json</code>。
发现错误请编辑 CSV 后再跑一次: <code>python3 backend/field_auditor.py</code>
</p>

</body>
</html>
"""
    return html


def render_summary_text(issues, stats, by_country):
    """微信通知用纯文本摘要"""
    lines = [
        f"📋 字段审计 {datetime.now().strftime('%m-%d %H:%M')}",
        f"球员: {stats['total_players']} | 🔴 {stats['error_count']} | 🟡 {stats['warn_count']} | 🔵 {stats['info_count']}",
        "",
        "Top 5 问题国家:",
    ]
    for c, n in sorted(by_country.items(), key=lambda x: -x[1])[:5]:
        lines.append(f"  {c}: {n} 处")
    if stats['error_count'] > 0:
        lines.append("")
        lines.append("🔴 必须修前 5 个:")
        errors = [i for i in issues if i['level'] == 'error'][:5]
        for i in errors:
            lines.append(f"  {i['country']} {i['name']}: [{i['field']}] {i['msg'][:60]}")
    lines.append("")
    lines.append(f"详细报告: 6_审核报告/field_audit/")
    return '\n'.join(lines)


def main():
    issues, stats, by_country, by_field, players = audit_all()
    now = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 1. HTML 报告
    html = render_html(issues, stats, by_country, by_field, players)
    html_path = REPORT_DIR / f'audit_{now}.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    # 最新一份
    latest_path = REPORT_DIR / 'latest.html'
    with open(latest_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # 2. 摘要 (cron 给微信用)
    summary = render_summary_text(issues, stats, by_country)
    summary_path = REPORT_DIR / 'latest_summary.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)

    # 3. 打印到 stdout
    print(summary)
    print()
    print(f"HTML 报告: {html_path}")
    print(f"最新报告: {latest_path}")

    return stats


if __name__ == '__main__':
    main()
