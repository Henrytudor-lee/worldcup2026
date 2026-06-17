"""
Mavis PDP Backend Server
- FastAPI，端口 8765
- 4 个接口：/api/ranking /api/predictions /api/players /api/weights/default
- weights 通过 query string 传 JSON，前端调系数滑块触发

启动: python3 server.py
或:   uvicorn server:app --host 0.0.0.0 --port 8765
"""
import json
import csv
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import predictor
import dynamic_factors
from weights_schema import DEFAULT, PRESETS, validate, merge_with_default

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="Mavis PDP Backend", version="2.3.0")

# CORS: 允许前端 8765 / 8000 / 8080 跨域调
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本地开发用
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _parse_weights(weights_str: str = Query(default="default", description="JSON 字符串 or preset name")):
    """从 query 解析 weights"""
    if not weights_str or weights_str == "default":
        return DEFAULT
    # 试 JSON
    try:
        w = json.loads(weights_str)
        merged = merge_with_default(w)
        ok, msg = validate(merged)
        if not ok:
            raise HTTPException(status_code=400, detail=f"weights invalid: {msg}")
        return merged
    except json.JSONDecodeError:
        # 不是 JSON → 试 preset 名
        if weights_str in PRESETS:
            return PRESETS[weights_str]['weights']
        raise HTTPException(status_code=400, detail=f"weights 必须是 JSON 字符串或 preset 名（{list(PRESETS.keys())}）")


@app.get("/")
def root():
    return {
        "service": "Mavis PDP Backend",
        "version": "2.3.2",
        "endpoints": [
            "GET /api/ranking",
            "GET /api/predictions?weights=default",
            "GET /api/players?team=法国",
            "GET /api/weights/default",
            "GET /api/weights/presets",
            "GET /api/dynamic-factors  (v2.2 30+ 动态因子 schema)",
            "GET /api/match-stats          (v2.3.2 已完赛列表)",
            "GET /api/match-stats/finished (v2.3.2 已完赛列表)",
            "GET /api/match-stats/{match_id} (v2.3.2 单场详细: 队伍/球员/事件)",
        ],
    }


@app.get("/api/weights/default")
def get_default_weights():
    return DEFAULT


@app.get("/api/weights/presets")
def get_presets():
    """返回 6 个 preset 的 metadata（label + weights）"""
    return {k: v for k, v in PRESETS.items()}


@app.get("/api/ranking")
def get_ranking(weights: str = Query(default="default")):
    """48 队排名（实时按 weights 重算）"""
    w = _parse_weights(weights)
    r = predictor.compute_ranking(w)
    return {"ranking": r, "count": len(r), "weights_used": w}


@app.get("/api/predictions")
def get_predictions(weights: str = Query(default="default")):
    """104 场全预测（实时按 weights 重算）
    返回 additional 字段 actual_results: {(home, away): 'H-A'}
    """
    w = _parse_weights(weights)
    result = predictor.compute_predictions(w)
    # 加载真实结果 (从 match_results.csv)
    actual_results = {}
    csv_path = PROJECT_ROOT / "1_数据基础" / "match_results.csv"
    if csv_path.exists():
        with open(csv_path, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                key = f"{row['home']}_vs_{row['away']}"  # 字符串 key (JSON 友好)
                actual_results[key] = {
                    'date': row['date'],
                    'home_score': int(row['home_score']),
                    'away_score': int(row['away_score']),
                    'home': row['home'],
                    'away': row['away'],
                }
    # v2.2.3 修: 覆盖 predictions 列表里的 actual_score/home_pts/away_pts
    # predictor.compute_predictions() 把 best_score 当 actual_score (BUILT-IN 错误)
    # 必须用 actual_results (从 match_results.csv) 覆盖, 否则 SPA 显示的是预测比分不是真实比分
    for pred in result['predictions']:
        key = f"{pred['home']}_vs_{pred['away']}"
        if key in actual_results:
            ar = actual_results[key]
            pred['actual_score'] = f"{ar['home_score']}-{ar['away_score']}"
            pred['home_pts'] = 3 if ar['home_score'] > ar['away_score'] else (1 if ar['home_score'] == ar['away_score'] else 0)
            pred['away_pts'] = 3 if ar['away_score'] > ar['home_score'] else (1 if ar['home_score'] == ar['away_score'] else 0)
        else:
            # v2.2.3 修: 没真实结果 = 没踢, actual_score 应该是 null (让前端显示"未踢")
            # 之前 predictor 用 best_score 默认, 导致前端把预测当真实
            pred['actual_score'] = None
            pred['home_pts'] = None
            pred['away_pts'] = None

    # v2.2.3 修: 用真实结果重算 group_standings + R32 + KO
    # predictor 内部用 best_score 算的, 真实世界用真实比分
    # 之前 R32 一直用 best_score, 所以会出现"韩国第三但 R32 是 A1"这种诡异
    from collections import defaultdict
    group_standings_real = {}  # {group: [(team, pts, gd, gf, ga)]}
    for g in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']:
        pts = defaultdict(lambda: [0, 0, 0, 0])  # pts, GF, GA, played
        for pred in result['predictions']:
            if pred.get('group') != g or pred.get('stage') != 'group':
                continue
            key = f"{pred['home']}_vs_{pred['away']}"
            ar = actual_results.get(key)
            if not ar:
                continue  # 没真实结果 = 没踢, 跳过
            h, a = pred['home'], pred['away']
            hs, as_ = ar['home_score'], ar['away_score']
            pts[h][0] += 3 if hs > as_ else (1 if hs == as_ else 0)
            pts[h][1] += hs; pts[h][2] += as_; pts[h][3] += 1
            pts[a][0] += 3 if as_ > hs else (1 if hs == as_ else 0)
            pts[a][1] += as_; pts[a][2] += hs; pts[a][3] += 1
        # 排序: 积分 → 净胜球 → 进球 → 字母
        sorted_teams = sorted(pts.items(), key=lambda x: (-x[1][0], -(x[1][1]-x[1][2]), -x[1][1], x[0]))
        group_standings_real[g] = [(t, s[0], s[1]-s[2], s[1], s[2]) for t, s in sorted_teams]

    return {
        "predictions": result['predictions'],
        "group_standings": group_standings_real,
        "top_8_third": result['top_8_third'],
        "round_of_32": result['round_of_32'],
        "final": result['final'],
        "third_place": result['third_place'],
        "count": len(result['predictions']),
        "actual_results": actual_results,
        "weights_used": w,
    }


@app.get("/api/players")
def get_players(team: str = Query(default=None, description="可选：按国家过滤")):
    """读 1248 球员，可选按队过滤"""
    players = predictor.get_players_by_team(team)
    if team and not players:
        raise HTTPException(status_code=404, detail=f"team '{team}' not found")
    return {"players": players, "count": len(players)}


# ============================================================
# v2.2 校准系统接口
# ============================================================
@app.get("/api/dynamic-factors")
def get_dynamic_factors():
    """返 30+ 动态因子 schema (UI 滑块生成用)"""
    meta = dynamic_factors.all_factors_meta()
    defaults = dynamic_factors.default_weights()
    ranges = dynamic_factors.ranges()
    return {
        "factors": meta,
        "defaults": defaults,
        "ranges": ranges,
        "count": len(meta),
    }


# ============================================================
# v2.3.2 赛事详细数据 (ESPN 抓取 + ETL)
# ============================================================
import csv
def _load_match_stats_csv(filename):
    """读赛事统计 CSV, 返回 list[dict]"""
    csv_path = PROJECT_ROOT / "1_数据基础" / filename
    if not csv_path.exists():
        return []
    with open(csv_path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


@app.get("/api/match-stats/finished")
def list_finished_matches():
    """列出所有已完赛 (Full Time) 比赛, 含 match_id"""
    rows = _load_match_stats_csv("match_team_stats.csv")
    return {
        "matches": [
            {
                "match_id": r["match_id"],
                "espn_event_id": r["espn_event_id"],
                "date": r["date"],
                "home_team_cn": r["home_team_cn"],
                "away_team_cn": r["away_team_cn"],
                "home_score": int(r["home_score"]) if r.get("home_score") else 0,
                "away_score": int(r["away_score"]) if r.get("away_score") else 0,
                "status": r.get("status", "Full Time"),
                "venue": r.get("venue", ""),
            }
            for r in rows
        ],
        "count": len(rows),
    }


@app.get("/api/match-stats/{match_id}")
def get_match_stats(match_id: str):
    """按 match_id 返一场比赛的详细数据: 队伍统计 + 球员统计 + 事件流
    match_id 接受两种格式:
    - 长: 2026-06-11_墨西哥_vs_南非 (从 match_team_stats.csv 完整读)
    - 短: 墨西哥_vs_南非 (fallback 模糊匹配, 多场同对可能返回最近一场)
    """
    team_all = _load_match_stats_csv("match_team_stats.csv")
    player_all = _load_match_stats_csv("match_player_stats.csv")
    event_all = _load_match_stats_csv("match_events.csv")

    # 长格式: 精确匹配
    team_rows = [r for r in team_all if r["match_id"] == match_id]
    if not team_rows and "_vs_" in match_id:
        # 短格式: 按 home_vs_away 模糊匹配 (取最近一场)
        key = match_id.split("_vs_")
        if len(key) == 2:
            cands = [r for r in team_all if r["home_team_cn"] == key[0] and r["away_team_cn"] == key[1]]
            if cands:
                # 按 date 降序, 取最近
                cands.sort(key=lambda r: r["date"], reverse=True)
                team_rows = cands[:1]
                real_id = team_rows[0]["match_id"]
                player_rows = [r for r in player_all if r["match_id"] == real_id]
                event_rows = [r for r in event_all if r["match_id"] == real_id]
                if not team_rows:
                    raise HTTPException(status_code=404, detail=f"match_id '{match_id}' not found or not yet finished")
            else:
                raise HTTPException(status_code=404, detail=f"match_id '{match_id}' not found or not yet finished")
        else:
            raise HTTPException(status_code=404, detail=f"match_id '{match_id}' not found or not yet finished")
    else:
        player_rows = [r for r in player_all if r["match_id"] == match_id]
        event_rows = [r for r in event_all if r["match_id"] == match_id]

    if not team_rows:
        raise HTTPException(status_code=404, detail=f"match_id '{match_id}' not found or not yet finished")

    team = team_rows[0]
    # 球员分主客队
    home_players = [p for p in player_rows if p.get("home_away") == "home"]
    away_players = [p for p in player_rows if p.get("home_away") == "away"]

    return {
        "match": {
            "match_id": team["match_id"],
            "espn_event_id": team["espn_event_id"],
            "date": team["date"],
            "home_team_cn": team["home_team_cn"],
            "away_team_cn": team["away_team_cn"],
            "home_team_en": team["home_team_en"],
            "away_team_en": team["away_team_en"],
            "home_score": int(team["home_score"]) if team.get("home_score") else 0,
            "away_score": int(team["away_score"]) if team.get("away_score") else 0,
            "home_winner": team.get("home_winner") == "True",
            "away_winner": team.get("away_winner") == "True",
            "venue": team.get("venue", ""),
            "status": team.get("status", "Full Time"),
        },
        "team_stats": team,
        "home_players": home_players,
        "away_players": away_players,
        "events": event_rows,
    }


@app.get("/api/match-stats")
def list_or_summary():
    """默认返赛事统计汇总 (轻量列表, 前端赛程 Tab 调用)"""
    return list_finished_matches()


if __name__ == '__main__':
    import uvicorn
    print('启动 Mavis PDP Backend on http://localhost:8765')
    print('接口文档: http://localhost:8765/docs')
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
