# Mavis PDP - Windows 启动指南

## 一键启动

1. **确认 Python 已装**（3.9+，去 https://www.python.org/downloads/ 下，**安装时勾上 "Add to PATH"**）
2. **双击 `start.bat`**
3. 等 5-10 秒，看到 "√ 启动完成"
4. **浏览器打开**：
   ```
   http://localhost:8080/world_cup_2026_spa.html
   ```

## ⚠️ 重要：必须用 http:// 打开

- ✅ **对**：`http://localhost:8080/world_cup_2026_spa.html`
- ❌ **错**：双击 HTML 文件（走 `file://` 协议，浏览器禁止 fetch 后端 → 没数据）

## 停止服务

双击 `stop.bat`

## 故障排查

### 启动后浏览器没数据

1. **确认打开了正确的 URL**（必须是 `http://localhost:8080/...`，不是 `file:///...`）
2. **强制刷新**：按 `Ctrl + Shift + R`
3. **看后端日志**：`backend\.run\logs\backend.log`
4. **看前端日志**：`backend\.run\logs\frontend.log`

### 端口被占

`start.bat` 会**自动杀掉**占着 8765 / 8080 的旧进程。

如果还是起不来：
```cmd
netstat -aon | findstr ":8765"
netstat -aon | findstr ":8080"
taskkill /F /PID <上面查到的 PID>
```

### 依赖装不上

如果 `pip install` 失败：
- 试试手动装：`backend\.venv\Scripts\activate` → `pip install fastapi uvicorn scikit-optimize`
- 或换国内源：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple fastapi uvicorn scikit-optimize`

## 目录

- `start.bat` - 启动（双击）
- `stop.bat` - 停止（双击）
- `start.sh` / `stop.sh` - Mac / Linux 用
- `backend\server.py` - FastAPI 后端
- `4_比赛预测\world_cup_2026_spa.html` - 主页面
