# Mavis PDP - Windows 启动指南

## 一键启动

1. **确认 Python 已装**（3.9+，去 https://www.python.org/downloads/ 下，**安装时勾上 "Add to PATH"**）
2. **双击 `start.bat`**（本机访问）
   - 或双击 `start_remote.bat`（**跨电脑访问**，会自动放行 Windows 防火墙）
3. 等 5-10 秒，看到 "√ 启动完成"
4. **浏览器打开**：
   - 本机：`http://localhost:8080/world_cup_2026_spa.html`
   - 跨电脑：用 `start_remote.bat` 输出的 `http://<本机IP>:8080/world_cup_2026_spa.html`

## ⚠️ 重要：必须用 http:// 打开

- ✅ **对**：`http://localhost:8080/world_cup_2026_spa.html`
- ❌ **错**：双击 HTML 文件（走 `file://` 协议，浏览器禁止 fetch 后端 → 没数据）

## 启动脚本区别

| 脚本 | 用途 | 适合场景 |
|------|------|---------|
| `start.bat` | 本机启动，后端绑 localhost | 你一个人在自己电脑看 |
| `start_remote.bat` | 跨电脑启动，后端绑 0.0.0.0 + 自动加防火墙规则 | A 电脑跑服务，B 电脑浏览器访问 |
| `stop.bat` | 停止 8765/8080 端口上的服务 | 关闭时 |

## 停止服务

双击 `stop.bat`

## 环境诊断

双击 `0_scripts\check_env.bat`，把输出截图发给我即可。
脚本会检查：Python / pip / venv / 项目结构 / 端口占用 / 关键依赖 / 网络 / 中文路径。

## 故障排查

### 启动后浏览器没数据

1. **确认打开了正确的 URL**（必须是 `http://localhost:8080/...`，不是 `file:///...`）
2. **强制刷新**：按 `Ctrl + Shift + R`
3. **看后端日志**：`backend\.run\logs\backend.log`
4. **看前端日志**：`backend\.run\logs\frontend.log`

### 跨电脑访问不到（start_remote.bat 用法）

如果 B 电脑访问不到 A：
1. A 和 B 在**同一局域网**（同一 WiFi/网段）
2. A 电脑 **Windows Defender 允许 Python** 通过（设置 → 应用 → 已安装应用 → Python → 允许）
3. 路由器没有 AP 隔离（家庭路由一般没问题）
4. 试 `cmd` 里 `ping <A 的 IP>` 看通不通

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

### 中文路径访问有问题

如果项目放在带中文的目录里出问题：
- 把项目移到纯英文路径（比如 `D:\WorldCup2026\`）
- 或者右键 → 属性 → 取消"只读"勾选

## 目录

- `start.bat` - 启动（双击，本机访问）
- `start_remote.bat` - 启动（双击，跨电脑访问）
- `stop.bat` - 停止（双击）
- `start.sh` / `stop.sh` - Mac / Linux 用
- `0_scripts\check_env.bat` - 环境诊断（双击）
- `backend\server.py` - FastAPI 后端
- `4_比赛预测\world_cup_2026_spa.html` - 主页面
