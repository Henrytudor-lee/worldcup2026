"""
Mavis PDP Backend Server
- FastAPI，端口 8765
- 4 个接口：/api/ranking /api/predictions /api/players /api/weights/default
- weights 通过 query string 传 JSON，前端调系数滑块触发

启动: python3 server.py
或:   uvicorn server:app --host 0.0.0.0 --port 8765
"""
import json
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import predictor
from weights_schema import DEFAULT, PRESETS, validate, merge_with_default

app = FastAPI(title="Mavis PDP Backend", version="2.1")

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
        "version": "2.1",
        "endpoints": [
            "GET /api/ranking",
            "GET /api/predictions?weights=default",
            "GET /api/players?team=法国",
            "GET /api/weights/default",
            "GET /api/weights/presets",
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
    """104 场全预测（实时按 weights 重算）"""
    w = _parse_weights(weights)
    result = predictor.compute_predictions(w)
    return {
        "predictions": result['predictions'],
        "group_standings": result['group_standings'],
        "top_8_third": result['top_8_third'],
        "round_of_32": result['round_of_32'],
        "final": result['final'],
        "third_place": result['third_place'],
        "count": len(result['predictions']),
        "weights_used": w,
    }


@app.get("/api/players")
def get_players(team: str = Query(default=None, description="可选：按国家过滤")):
    """读 1248 球员，可选按队过滤"""
    players = predictor.get_players_by_team(team)
    if team and not players:
        raise HTTPException(status_code=404, detail=f"team '{team}' not found")
    return {"players": players, "count": len(players)}


if __name__ == '__main__':
    import uvicorn
    print('启动 Mavis PDP Backend on http://localhost:8765')
    print('接口文档: http://localhost:8765/docs')
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
