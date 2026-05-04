# P0-2 事件驱动 v2：前端 WebSocket 实时通知

> **目标**：后端 EventBus 事件 → WebSocket → 前端实时通知。
> **核心链路**：`Redis Pub/Sub → WebSocket Server → React useWebSocket hook → NotificationStore`
> **设计原则**：零侵入 — 现有代码不改，只在 EventBus 和前端之间搭桥。

---

## 一、架构总览

```
[后端 Events]                   [前端]
┌──────────┐     Redis      ┌──────────────┐    WS      ┌──────────────────┐
│ Redis     │ ─── Pub/Sub → │ FastAPI WS   │ ────────→  │ useWebSocket     │
│ Pub/Sub   │               │  /ws/events  │            │ hook             │
└──────────┘               └──────────────┘            └───────┬──────────┘
      ▲                                                         │
      │  publish                                                 │  push
      │                                                          ▼
┌──────┴────────┐                                     ┌──────────────────┐
│ EventBus      │                                     │ Zustand store    │
│ (stop_loss    │                                     │ (notification +  │
│  /risk_alert) │                                     │  badge count)    │
└───────────────┘                                     └──────────────────┘
```

### 1.1 数据流

```
止损触发
  ↓ EventBus.publish(STOP_LOSS_TRIGGERED, data)
  ↓ Redis Publish → fraxverse:events:stop_loss_triggered
  ↓ FastAPI WebSocket 端点 (后台线程监听 Redis)
  ↓ JSON 序列化 → send_text()
  ↓ 前端 useWebSocket hook 收到消息
  ↓ Zustand: addNotification(item) + incrementBadge()
  ↓ 通知页 / MobileNotifications / MobileMonitor 即时渲染
```

### 1.2 事件消息格式

```json
{
  "event_type": "STOP_LOSS_TRIGGERED",
  "source": "stop_loss_monitor",
  "timestamp": 1714800000.0,
  "event_id": "a1b2c3d4e5f6",
  "title": "止损触发",
  "body": "600519.SH 贵州茅台 触发止损 @168.50 (-3.2%)",
  "level": "high",
  "data": {
    "stock_code": "600519",
    "trigger_price": 168.50,
    "loss_pct": -3.2,
    "reason": "跌破支撑位"
  }
}
```

---

## 二、实施步骤

### 步骤 1：后端 WebSocket 端点（30min）

**文件：** `src/api/routes/ws.py` · `src/api/main.py`

- 新增 `/api/v1/ws/events` WebSocket 端点
  - 验证 JWT token（从 query param `?token=xxx` 或 Sec-WebSocket-Protocol）
  - 后台线程监听 Redis Pub/Sub（监听 EventBus 的所有通道）
  - 收到事件后转换为 WS 消息格式推送给客户端
- 每个 WebSocket 连接独立监听 Redis（简单可靠，无需维护房间映射）
- 连接断开时自动清理 Redis pubsub

```python
@router.websocket("/api/v1/ws/events")
async def ws_events(websocket: WebSocket, token: str = Query(...)):
    # 1. 验证 JWT token
    user_id = verify_token(token)
    # 2. 接受连接
    await websocket.accept()
    # 3. 启动 Redis 监听（独立线程）
    pubsub = redis.pubsub()
    pubsub.subscribe("fraxverse:events:*")  # 全局监听
    # 4. 循环接收消息并推送
    while True:
        msg = pubsub.get_message(timeout=1.0)
        if msg and msg["type"] == "message":
            await websocket.send_text(msg["data"])
```

**检查点：** 后端测试：连接 WS → 发布事件 → 收到推送 ✓

---

### 步骤 2：前端 WebSocket Hook（20min）

**文件：** `frontend/src/hooks/useWebSocketEvents.ts`

- 连接建立：`new WebSocket("wss://host/api/v1/ws/events?token=xxx")`
- 自动重连：`useRef + setTimeout(reconnect, 3000)` 在 onclose 触发重连
- 心跳保持：每 30 秒 send ping
- 消息分发：收到消息后 `JSON.parse` → 调用 Zustand store 的方法

```typescript
export function useWebSocketEvents() {
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const ws = new WebSocket(`${WS_BASE}/api/v1/ws/events?token=${token}`);

    ws.onmessage = (evt) => {
      const event = JSON.parse(evt.data);
      // 写入通知 store
      useNotificationStore.getState().add(event);
      // 写入事件 store（风控专用）
      useEventStore.getState().push(event);
    };

    ws.onclose = () => setTimeout(setup, 3000); // auto-reconnect

    return () => ws.close();
  }, []);
}
```

**检查点：** 浏览器打开页面 → WS 连接成功 → 发事件收到推送 ✓

---

### 步骤 3：前端 Zustand NotificationStore（20min）

**文件：** `frontend/src/stores/useNotificationStore.ts`

- 状态：`notifications: NotificationItem[]`, `unreadCount: number`, `latestEvent: EventPayload | null`
- 方法：`add(event)`, `markRead(id)`, `markAllRead()`, `clearLatest()`
- `add()` 逻辑：
  1. 将 WS 事件转换为 `NotificationItem` 格式
  2. 插入 `notifications` 列表头部（上限 200 条）
  3. `unreadCount += 1`
  4. 设置 `latestEvent`（用于通知页/弹窗/徽标）
  5. 如果是止损/风控事件，同时推入 `useEventStore`

```typescript
interface NotificationStore {
  notifications: NotificationItem[];
  unreadCount: number;
  latestEvent: EventPayload | null;
  add: (event: EventPayload) => void;
  markRead: (id: number) => void;
  markAllRead: () => void;
}
```

**检查点：** 手动调用 `add()` → notifications 更新 + unreadCount 增 1 ✓

---

### 步骤 4：前端接入 + 可视化（20min）

**文件：** `frontend/src/main.tsx` · 各页面引用

- 在 `main.tsx` 或 `App.tsx` 挂载 `useWebSocketEvents` hook
- **通知页（NotificationPage / MobileNotifications）**：从 zustand store 读数据代替 axios 拉取
- **止损/风控事件**：推入 RiskEvents store → MobileMonitor 即时更新
- **底部导航栏徽标**：`<Badge count={unreadCount}>` 显示未读数

**检查点：** 页面挂载 → WS 连接 → 收到事件 → UI 自动更新 ✓

---

### 步骤 5：Docker + Nginx 配置（15min）

**文件：** `frontend/nginx.conf` · `docker-compose.yml`

- Nginx 增加 `/ws/` location：
  ```
  location /ws/ {
      proxy_pass http://backend:8000;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host $host;
      proxy_read_timeout 86400s;
  }
  ```
- 前端 `vite.config.ts` 开发模式 proxy 也添加 `/ws` 规则

**检查点：** `docker compose up -d` → WS 连接建立正常 ✓

---

## 三、文件清单

| 文件 | 说明 | 新增/修改 |
|:-----|:------|:--------:|
| `src/api/routes/ws.py` | WebSocket 端点 + Redis 监听 | 🆕 新增 |
| `src/api/main.py` | 注册 ws_router | ✏️ 修改（+2行） |
| `frontend/src/hooks/useWebSocketEvents.ts` | WebSocket hook（自动重连） | 🆕 新增 |
| `frontend/src/stores/useNotificationStore.ts` | 通知状态管理 | 🆕 新增 |
| `frontend/src/stores/useEventStore.ts` | 风控事件状态管理 | 🆕 新增 |
| `frontend/src/main.tsx` | 挂载 useWebSocketEvents | ✏️ 修改（+3行） |
| `frontend/src/App.tsx` | 通知页/止损页改为 store 驱动 | ✏️ 修改（可选） |
| `frontend/nginx.conf` | 添加 /ws/ WebSocket 代理 | ✏️ 修改 |
| `frontend/vite.config.ts` | 开发模式 proxy 添加 /ws | ✏️ 修改 |

---

## 四、风险与注意事项

| 风险 | 影响 | 预防 |
|:-----|:------|:-----|
| WebSocket 连接中断 | 实时通知丢失 | 自动重连（3秒间隔） |
| token 过期后 WS 连接失败 | 通知不推送 | 401 时跳登录页 |
| 大量事件涌入浏览器 | UI 卡顿 | 通知列表上限 200 条，requestAnimationFrame 批量渲染 |
| Nginx 未配置 upgrade header | WS 握手失败 | 必须配 proxy_http_version 1.1 + Upgrade/Connection header |
| Redis 监听线程泄漏 | 每个 WS 连接一个线程 | WebSocket.onclose 时清理 pubsub |
| 前端不读 Nginx WS 配置 | WS 连接 404 | vite proxy 需同时配置（开发模式） |

---

## 五、验收标准

1. ✅ 后端 WebSocket 端点接受连接并验证 JWT
2. ✅ 从 Redis 收到事件 → WS 推送到前端
3. ✅ 前端自动重连（断网后恢复）
4. ✅ 通知页面实时更新（无需手动刷新）
5. ✅ 底部导航栏显示未读徽标
6. ✅ Docker 部署后 WS 连接正常
7. ✅ 现有测试全量通过
