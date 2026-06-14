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
import threading
import queue
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import predictor
import calibrator
import dynamic_factors
from weights_schema import DEFAULT, PRESETS, validate, merge_with_default

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="Mavis PDP Backend", version="2.2.1")

# 校准日志: {run_id: Queue} 全局 dict
CALIB_QUEUES: dict = {}

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
        "version": "2.2",
        "endpoints": [
            "GET /api/ranking",
            "GET /api/predictions?weights=default",
            "GET /api/players?team=法国",
            "GET /api/weights/default",
            "GET /api/weights/presets",
            "GET /api/dynamic-factors  (v2.2 30+ 动态因子 schema)",
            "GET /api/calibration       (v2.2 校准评估 + 历史)",
            "POST /api/calibration/run  (v2.2 触发贝叶斯校准)",
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
    return {
        "predictions": result['predictions'],
        "group_standings": result['group_standings'],
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


@app.get("/api/calibration")
def get_calibration(weights: str = Query(default="default")):
    """校准评估 + 历史
    1. 用当前 weights 评估 match_results.csv
    2. 返校准历史 (calibration_history.json)
    """
    w = _parse_weights(weights)
    ev = calibrator.evaluate(w, verbose=False)
    summary = calibrator.get_calibration_summary()
    return {
        "evaluation": ev,
        "history": summary.get('history', []),
        "best": summary.get('best'),
    }


@app.post("/api/calibration/run")
def run_calibration(
    n_iter: int = Query(default=20, ge=1, le=20000),
    use_bayes: bool = Query(default=True),
):
    """触发贝叶斯校准 (后台异步跑, 1-2 分钟)
    返回 run_id, 前端用 EventSource 监听 /api/calibration/stream?run_id=xxx
    """
    run_id = str(uuid.uuid4())[:8]
    q = queue.Queue(maxsize=1000)
    CALIB_QUEUES[run_id] = q

    def _run():
        def log_callback(level, msg):
            try:
                q.put_nowait({'level': level, 'msg': msg, 'ts': time.time()})
            except queue.Full:
                pass  # 队列满就丢, 避免阻塞主流程
        try:
            calibrator.calibrate(n_iter=n_iter, use_bayes=use_bayes,
                                 verbose=False, log_callback=log_callback)
        except Exception as e:
            log_callback('error', f"calibrate 异常: {e}")
        finally:
            log_callback('close', 'DONE')  # 关闭信号

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return {
        "status": "started",
        "run_id": run_id,
        "n_iter": n_iter,
        "method": "bayes" if use_bayes else "grid",
        "stream_url": f"/api/calibration/stream?run_id={run_id}",
        "message": f"校准已启动 ({n_iter} 轮), 通过 EventSource 监听 stream_url 实时看日志",
    }


@app.get("/api/calibration/stream")
def calibration_stream(run_id: str = Query(...)):
    """SSE 流式输出校准日志

    前端: new EventSource(`/api/calibration/stream?run_id=${run_id}`)
    """
    if run_id not in CALIB_QUEUES:
        raise HTTPException(status_code=404, detail=f"run_id '{run_id}' 不存在或已完成")

    q = CALIB_QUEUES[run_id]

    def event_stream():
        # 启动消息
        yield f"data: {json.dumps({'level': 'info', 'msg': f'📡 SSE 已连接 (run_id={run_id})'})}\n\n"
        while True:
            try:
                item = q.get(timeout=30)  # 30s 无消息自动断
            except queue.Empty:
                # 心跳包
                yield ": heartbeat\n\n"
                continue
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            if item.get('level') == 'close':
                break
        # 清理
        CALIB_QUEUES.pop(run_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


if __name__ == '__main__':
    import uvicorn
    print('启动 Mavis PDP Backend on http://localhost:8765')
    print('接口文档: http://localhost:8765/docs')
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
