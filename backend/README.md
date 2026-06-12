# Mavis PDP Backend

FastAPI 后端，跑 2026 世界杯预测算法。直接读取 `1_数据基础/*.csv`，按 weights 入参重算 48 队排名 + 104 场预测。

## 启动

```bash
# 装依赖（一次性）
pip3 install fastapi uvicorn --break-system-packages

# 启动
python3 server.py

# 验证
curl http://localhost:8765/
```

启动后访问 http://localhost:8765/docs 看自动生成的 Swagger 文档。

## 4 个接口

| 方法 | 路径 | 用途 | 耗时 |
|---|---|---|---|
| GET | `/api/ranking?weights=...` | 48 队排名 | ~50ms |
| GET | `/api/predictions?weights=...` | 104 场预测 | ~50ms |
| GET | `/api/players?team=...` | 1248 球员 | ~30ms |
| GET | `/api/weights/default` | 16 系数默认值 | <1ms |
| GET | `/api/weights/presets` | 6 preset 元数据 | <1ms |

**weights 入参格式**：
- 方式 A：JSON 字符串（前端调系数用）`?weights=%7B%22position_top_n%22%3A...%7D`
- 方式 B：preset 名（UI 切预设用）`?weights=coach_heavy`

## 文件清单

- `server.py` — FastAPI 入口
- `predictor.py` — 算法包装层（接受 weights 注入到 ranking + predictions）
- `weights_schema.py` — 16 系数 schema + 范围校验 + 6 preset
- `README.md` — 本文件

## 与前端的协作

```
┌─────────────────┐
│ 浏览器           │
│ (SPA 81KB)      │
└────────┬────────┘
         │ fetch http://localhost:8765/api/predictions?weights=...
         ↓
┌─────────────────┐
│ FastAPI (8765)  │
│ server.py       │
└────────┬────────┘
         │ predictor.compute_predictions(weights)
         ↓
┌─────────────────┐
│ 直接读 CSV      │
│ 1_数据基础/*.csv│
└─────────────────┘
```

启动后端时建议**先启动**——前端 HTML 加载时立即 fetch 4 个接口拿默认数据。

## 调权重后看效果

```bash
# 调成"教练为王"看决赛变化
curl -s "http://localhost:8765/api/predictions?weights=coach_heavy" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'决赛: {d[\"final\"][\"home\"]} vs {d[\"final\"][\"away\"]} → 冠军 {d[\"final\"][\"winner\"]}')
"
```
