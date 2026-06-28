# 🏆 WorldCup 2026 — Next.js 16 SPA

> 2026 美加墨世界杯 48 强预测 · 4 路由 (球队/赛程/配置/预测) · Server Component 直读 JSON · 23 系数实时可调

## 🚀 快速启动

```bash
# 1. 安装依赖
npm install

# 2. 启动 prod (端口 3010，8765/3000 被 video-prompt-builder 占)
./start.sh prod

# 3. 或启动 dev (Turbopack 热更新)
./start.sh dev

# 4. 停止
./start.sh stop
```

## 📁 路由

| 路由 | 内容 |
|---|---|
| `/` | ⚽ 48 强排名 (锋/中/后/门/总评/综合) |
| `/schedule` | 📅 12 小组 A-L + 全部 72 场 |
| `/config` | 🎛️ 23 系数滑块 + 6 preset |
| `/predict` | 🏆 完整 104 场 (R32→Final) + 进度条 + 决赛 |

## ⚙️ 配置

`.env.local` 切换数据源:
- `NEXT_PUBLIC_DATA_SOURCE=static` → 读 `public/static-data/*.json` (离线)
- `NEXT_PUBLIC_DATA_SOURCE=live` → 调 FastAPI (`NEXT_PUBLIC_BACKEND_URL`)

`.env.example` 提交到 git (不含 secret)

## 🛠 技术栈

- Next.js 16.2.9 (Turbopack)
- React 19.2.4
- TypeScript + ESLint
- 纯 vanilla CSS (暗色主题 + 响应式)

## 📦 数据源

Server Component 通过 `app/lib/data.ts` 直接 `fs.readFile`:
- `../../5_算法/ranking_v20.json` (排名)
- `../../5_算法/all_104_predictions.json` (104 场预测)
- `../../5_算法/weights_v21.json` (23 系数)

Client Component 通过 `app/lib/api.ts` 调 FastAPI (8766) + 静态 JSON fallback。
