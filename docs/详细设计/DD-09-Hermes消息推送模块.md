# DD-09 · Hermes消息推送模块

> 碎片宇宙（FraxVerse）智能量化交易系统 · 详细设计文档
> 版本：V1.0 | 创建：2026-05-01
> 公共约定引用：[DD-00-文档规范与公共约定](./DD-00-文档规范与公共约定.md)
> FraxVerse命名：Hermes→「信使星」 | 推送→「心念传递」 | 确认→「意念回响」

---

## 1. 模块概述

### 1.1 职责边界

本模块负责：

- **消息推送基础设施** — 统一管理所有交易事件、风控告警、系统通知的推送通道
- **微信交互式确认** — 支持建议模式下的交易确认（3种粒度）、参数变更审批
- **推送优先级队列** — 四级优先级（最高/高/中/低），最高优先级消息插队发送
- **失败重试与降级** — 推送失败自动重试，Hermes不可用时降级为系统内通知
- **推送去重与防刷** — 相同事件短时间内不重复推送，告警风暴时聚合发送
- **通知历史管理** — 所有推送记录持久化，支持按类型/时间/状态筛选查询
- **推送配置热管理** — 8类事件独立开关，变更后即时生效无需重启

**不负责**：

- 交易决策生成（见 DD-03 / DD-04）
- 风控规则判断（见 DD-06）
- 止损触发执行（见 DD-05）
- 微信通道底层连接维护（Hermes外部服务职责）
- 新闻采集与情绪分析（见 DD-02 / DD-04）

### 1.2 依赖关系

```
DD-09 Hermes消息推送模块
  ├── 依赖 DD-01 — users 表（推送目标用户）
  ├── 依赖 DD-03 — stock_pool / strategy_params（Agent精选结果数据源）
  ├── 依赖 DD-04 — agent_decisions / agent_discussions（Agent讨论与决策）
  ├── 依赖 DD-05 — trade_orders / positions / stop_loss_conditions（交易事件数据源）
  ├── 依赖 DD-06 — risk_events（风控告警数据源）
  ├── 依赖 DD-07 — experience / param_change_log（参数变更审批）
  ├── 依赖 DD-02 — news（舆情事件数据源）
  ├── 依赖 Redis — 推送队列 + 去重缓存 + 配置热加载
  ├── 依赖 Hermes — 外部消息通道（send_message API）
  └── 被依赖 — DD-08前端（通知历史页面 / 推送配置页面）
```

### 1.3 PRD追溯

| PRD章节 | 需求点 | DD-09覆盖 |
|:--------|:-------|:----------|
| 4.3.3 事件消息推送 | 8种推送事件+消息模板 | ✅ 第3节完整定义 |
| 4.3.3 交易确认模式 | 建议模式3种确认粒度 | ✅ 第4.2节交互式确认 |
| 4.6.1 推送配置 | 8个独立开关 | ✅ 第2.1.3节 push_config |
| 4.7 参数变更安全规则 | 人工审批+微信确认 | ✅ 第4.3节参数变更审批 |
| 6.5 Hermes通道 | send_message 工具 | ✅ 第4.1节推送管线 |
| 舆情+风控联动 | 告警推送 | ✅ DD-06调用DD-09 |
| Agent异常 | 权重降低告警 | ✅ DD-04调用DD-09 |
| 暂停复苏路径 | 复苏通知推送 | ✅ DD-06调用DD-09 |

---

## 2. 核心数据模型

### 2.1 数据库表设计

#### 2.1.1 notifications 表 — 通知记录（权威 DD-09 所有）

```sql
CREATE TABLE notifications (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         INTEGER         NOT NULL REFERENCES users(id),
    event_type      VARCHAR(40)     NOT NULL,    -- 事件类型，见 2.2 枚举
    priority        VARCHAR(10)     NOT NULL DEFAULT 'normal', -- critical/high/normal/low
    title           VARCHAR(200)    NOT NULL,    -- 通知标题
    content         TEXT            NOT NULL,    -- 通知正文（结构化文本）
    content_json    JSONB           DEFAULT '{}', -- 结构化数据（供前端渲染）
    push_channel    VARCHAR(20)     NOT NULL DEFAULT 'wechat', -- wechat/in_app/both
    push_status     VARCHAR(20)     NOT NULL DEFAULT 'pending', -- 见 2.3 状态机
    wechat_msg_id   VARCHAR(100),                -- Hermes返回的消息ID
    confirm_type    VARCHAR(20),                -- 确认类型: trade_confirm/param_approve/none
    confirm_status  VARCHAR(20)     DEFAULT 'none', -- none/pending/confirmed/rejected/expired
    confirm_payload JSONB           DEFAULT '{}', -- 确认上下文（订单ID/参数变更等）
    confirm_reply   TEXT,                        -- 用户回复原文
    confirm_at      TIMESTAMPTZ,                 -- 确认时间
    expire_at       TIMESTAMPTZ,                 -- 确认过期时间
    retry_count     SMALLINT        NOT NULL DEFAULT 0,
    max_retry       SMALLINT        NOT NULL DEFAULT 3,
    last_retry_at   TIMESTAMPTZ,                 -- 最近一次重试时间
    dedup_key       VARCHAR(100),                -- 去重键（事件类型+标的+日期等组合）
    is_read         BOOLEAN         NOT NULL DEFAULT FALSE,
    read_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id, created_at DESC);
CREATE INDEX idx_notifications_type ON notifications(event_type, created_at DESC);
CREATE INDEX idx_notifications_status ON notifications(push_status, priority)
    WHERE push_status IN ('pending', 'retrying');
CREATE INDEX idx_notifications_confirm ON notifications(confirm_status, expire_at)
    WHERE confirm_status = 'pending';
CREATE INDEX idx_notifications_dedup ON notifications(dedup_key, created_at DESC)
    WHERE dedup_key IS NOT NULL;
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read, created_at DESC)
    WHERE is_read = FALSE;

COMMENT ON TABLE notifications IS '通知记录，所有推送和系统内通知统一存储';
```

**字段说明**：

| 字段 | 说明 |
|:-----|:-----|
| event_type | 事件类型枚举，见 2.2 |
| priority | critical=最高, high=高, normal=中, low=低 |
| push_channel | wechat=仅微信, in_app=仅系统内, both=双通道 |
| push_status | 见 2.3 状态机 |
| confirm_type | trade_confirm=交易确认, param_approve=参数审批, none=无需确认 |
| confirm_payload | JSON结构，如 `{"order_ids": [...], "trade_mode": "advisory"}` |
| dedup_key | 去重键，格式: `{event_type}:{stock_code}:{date}` 或 `{event_type}:{param_key}:{date}` |

#### 2.1.2 push_config 表 — 推送配置（权威 DD-09 所有）

```sql
CREATE TABLE push_config (
    id              SERIAL          PRIMARY KEY,
    user_id         INTEGER         NOT NULL REFERENCES users(id),
    event_type      VARCHAR(40)     NOT NULL,    -- 对应 notifications.event_type
    is_enabled      BOOLEAN         NOT NULL DEFAULT TRUE,
    push_channel    VARCHAR(20)     NOT NULL DEFAULT 'both', -- wechat/in_app/both
    quiet_hours_start TIME,                      -- 免打扰开始时间（如22:00）
    quiet_hours_end   TIME,                      -- 免打扰结束时间（如08:00）
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, event_type)
);

COMMENT ON TABLE push_config IS '推送事件配置，8类事件独立开关+通道选择';
```

**初始数据**（系统初始化时为用户创建8条配置）：

```sql
-- 系统初始化后自动插入
INSERT INTO push_config (user_id, event_type, is_enabled, push_channel) VALUES
    (:uid, 'agent_pick',        TRUE, 'both'),
    (:uid, 'trade_open',        TRUE, 'both'),
    (:uid, 'trade_close',       TRUE, 'both'),
    (:uid, 'trade_add',         TRUE, 'both'),
    (:uid, 'risk_alert',        TRUE, 'both'),
    (:uid, 'sentiment_event',   TRUE, 'both'),
    (:uid, 'daily_review',      TRUE, 'both'),
    (:uid, 'strategy_anomaly',  TRUE, 'both');
```

#### 2.1.3 notification_templates 表 — 消息模板（权威 DD-09 所有）

```sql
CREATE TABLE notification_templates (
    id              SERIAL          PRIMARY KEY,
    event_type      VARCHAR(40)     NOT NULL,
    template_name   VARCHAR(100)    NOT NULL,
    title_template  VARCHAR(200)    NOT NULL,    -- 标题模板，支持 {var} 占位
    body_template   TEXT            NOT NULL,     -- 正文模板，支持 {var} 占位
    json_schema     JSONB           DEFAULT '{}', -- content_json 的结构定义
    priority        VARCHAR(10)     NOT NULL,     -- 默认优先级
    confirm_type    VARCHAR(20)     DEFAULT 'none', -- 是否需要确认
    confirm_expire_minutes INTEGER  DEFAULT 0,    -- 确认过期时间（分钟），0=不过期
    version         INTEGER         NOT NULL DEFAULT 1,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE(event_type, template_name, version)
);

COMMENT ON TABLE notification_templates IS '消息推送模板，支持变量占位和版本管理';
```

**初始模板数据**：

| event_type | template_name | title_template | priority | confirm_type | confirm_expire_minutes |
|:-----------|:-------------|:---------------|:---------|:------------|:----------------------|
| agent_pick | daily_pick | 📊 今日Agent精选结果 | high | none | 0 |
| trade_open | open_notify | 📈 开仓通知 | high | trade_confirm | 30 |
| trade_close | close_notify | ⚠️ 止损触发 / 🎯 止盈触发 | high | none | 0 |
| trade_add | add_notify | 📊 加仓通知 | normal | trade_confirm | 30 |
| risk_alert | risk_warning | 🚨 风控告警 | critical | none | 0 |
| sentiment_event | sentiment_alert | 📰 舆情事件 | high | none | 0 |
| daily_review | daily_summary | 📋 今日交易复盘 | low | none | 0 |
| strategy_anomaly | anomaly_alert | ⚠️ 策略异常 | critical | none | 0 |
| param_approve | param_change | 🔧 参数变更审批 | high | param_approve | 1440 |

#### 2.1.4 Schema所有权声明

| 表 | 所有者 | 可读写模块 | 只读模块 |
|:---|:------|:----------|:---------|
| notifications | DD-09 | DD-09 | DD-08(查询) |
| push_config | DD-09 | DD-09 | DD-08(查询) |
| notification_templates | DD-09 | DD-09 | — |

### 2.2 事件类型枚举

```python
class EventType(str, Enum):
    """推送事件类型 — 与 PRD 4.3.3 对齐"""
    AGENT_PICK       = "agent_pick"        # Agent精选结果
    TRADE_OPEN       = "trade_open"        # 开仓
    TRADE_CLOSE      = "trade_close"       # 平仓（止盈/止损）
    TRADE_ADD        = "trade_add"         # 加仓
    RISK_ALERT       = "risk_alert"        # 风控告警
    SENTIMENT_EVENT  = "sentiment_event"   # 舆情事件
    DAILY_REVIEW     = "daily_review"      # 每日复盘
    STRATEGY_ANOMALY = "strategy_anomaly"  # 策略异常
    PARAM_APPROVE    = "param_approve"     # 参数变更审批（内部事件，非PRD 8类但4.7要求）
```

**优先级映射**（与 PRD 4.3.3 推送配置表对齐）：

```python
EVENT_PRIORITY_MAP = {
    EventType.RISK_ALERT:       "critical",  # 最高
    EventType.STRATEGY_ANOMALY: "critical",  # 最高
    EventType.AGENT_PICK:       "high",
    EventType.TRADE_OPEN:       "high",
    EventType.TRADE_CLOSE:      "high",
    EventType.SENTIMENT_EVENT:  "high",
    EventType.TRADE_ADD:        "normal",    # 中
    EventType.DAILY_REVIEW:     "low",
    EventType.PARAM_APPROVE:    "high",
}

PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}
```

### 2.3 推送状态机

```
                    ┌──────────────────────────────────────────────┐
                    │                                              │
                    ▼                                              │
  ┌─────────┐  send   ┌─────────┐  success  ┌──────────┐         │
  │ pending │───────▶│ sending │─────────▶│ sent     │         │
  └─────────┘        └────┬────┘           └──────────┘         │
       │                  │ fail                                │
       │                  ▼                                     │
       │            ┌──────────┐  retry   ┌──────────┐          │
       │            │ failed   │─────────▶│ retrying │──────────┘
       │            └────┬─────┘          └──────────┘
       │                 │ max_retry
       │                 ▼
       │            ┌──────────┐
       │            │ dead     │
       │            └──────────┘
       │
       │  Hermes不可用(降级)
       ▼
  ┌──────────┐
  │ degraded │  ← 降级为系统内通知，微信端待Hermes恢复后补发
  └──────────┘
```

**状态说明**：

| 状态 | 说明 | 可转换至 |
|:-----|:-----|:---------|
| pending | 待发送 | sending, degraded |
| sending | 正在发送 | sent, failed |
| sent | 发送成功 | — (终态) |
| failed | 发送失败 | retrying, dead |
| retrying | 重试中 | sending, failed, dead |
| dead | 重试耗尽 | — (终态，需人工介入) |
| degraded | 降级模式 | pending (Hermes恢复后) |

### 2.4 确认状态机

```
  ┌───────┐  confirm   ┌───────────┐
  │ none  │───────────▶│ pending   │
  └───────┘           └─────┬─────┘
                            │
                 ┌──────────┼──────────┐
                 ▼          ▼          ▼
           ┌──────────┐ ┌──────────┐ ┌──────────┐
           │confirmed │ │ rejected │ │ expired  │
           └──────────┘ └──────────┘ └──────────┘
```

**确认超时规则**：

| confirm_type | 超时时间 | 超时后行为 |
|:-------------|:---------|:----------|
| trade_confirm | 30分钟 | 订单取消，推送超时通知 |
| param_approve | 24小时 | 变更不生效，保持原参数 |
| none | — | 无需确认 |

---

## 3. API契约

### 3.1 推送配置管理

#### 3.1.1 GET /api/v1/push/config — 获取推送配置列表

**请求**：

```http
GET /api/v1/push/config
Authorization: Bearer {token}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "configs": [
      {
        "id": 1,
        "eventType": "agent_pick",
        "isEnabled": true,
        "pushChannel": "both",
        "quietHoursStart": null,
        "quietHoursEnd": null
      }
    ]
  }
}
```

#### 3.1.2 PUT /api/v1/push/config/{event_type} — 更新推送配置

**请求**：

```http
PUT /api/v1/push/config/risk_alert
Authorization: Bearer {token}
Content-Type: application/json

{
  "isEnabled": true,
  "pushChannel": "wechat",
  "quietHoursStart": "22:00",
  "quietHoursEnd": "08:00"
}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 5,
    "eventType": "risk_alert",
    "isEnabled": true,
    "pushChannel": "wechat",
    "quietHoursStart": "22:00",
    "quietHoursEnd": "08:00"
  }
}
```

**校验规则**：

| 字段 | 规则 |
|:-----|:-----|
| isEnabled | boolean |
| pushChannel | enum: wechat/in_app/both |
| quietHoursStart | HH:MM格式或null，必须与quietHoursEnd成对 |
| quietHoursEnd | HH:MM格式或null，必须与quietHoursStart成对 |
| 免打扰限制 | critical优先级事件不受免打扰限制，始终推送 |

### 3.2 通知历史

#### 3.2.1 GET /api/v1/push/notifications — 查询通知列表

**请求**：

```http
GET /api/v1/push/notifications?page=1&page_size=20&event_type=risk_alert&is_read=false&start_date=2026-05-01&end_date=2026-05-01&priority=critical
Authorization: Bearer {token}
```

**查询参数**：

| 参数 | 类型 | 必选 | 说明 |
|:-----|:-----|:----:|:-----|
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页条数，默认20，最大100 |
| event_type | string | 否 | 按事件类型筛选 |
| is_read | boolean | 否 | 按已读状态筛选 |
| start_date | date | 否 | 开始日期 |
| end_date | date | 否 | 结束日期 |
| priority | string | 否 | 按优先级筛选 |

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 101,
        "eventType": "risk_alert",
        "priority": "critical",
        "title": "🚨 风控告警",
        "content": "组合回撤达-8.5%，超过阈值-8%",
        "contentJson": { ... },
        "pushStatus": "sent",
        "confirmStatus": "none",
        "isRead": false,
        "createdAt": "2026-05-01T10:30:00+08:00"
      }
    ],
    "total": 156,
    "page": 1,
    "pageSize": 20,
    "unreadCount": 12
  }
}
```

#### 3.2.2 PATCH /api/v1/push/notifications/{id}/read — 标记已读

**请求**：

```http
PATCH /api/v1/push/notifications/101/read
Authorization: Bearer {token}
```

#### 3.2.3 POST /api/v1/push/notifications/read-all — 全部标记已读

**请求**：

```http
POST /api/v1/push/notifications/read-all
Authorization: Bearer {token}
Content-Type: application/json

{
  "eventTypes": ["risk_alert", "strategy_anomaly"]  // 可选，为空则全部
}
```

#### 3.2.4 GET /api/v1/push/notifications/unread-count — 未读计数

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "totalCount": 12,
    "byType": {
      "risk_alert": 3,
      "trade_open": 2,
      "agent_pick": 5,
      "sentiment_event": 2
    },
    "byPriority": {
      "critical": 3,
      "high": 7,
      "normal": 2,
      "low": 0
    }
  }
}
```

### 3.3 交互式确认

#### 3.3.1 POST /api/v1/push/confirm/{notification_id} — 确认/拒绝

**请求**：

```http
POST /api/v1/push/confirm/101
Authorization: Bearer {token}
Content-Type: application/json

{
  "action": "confirm",          // confirm / reject
  "reply": "确认",              // 用户回复原文（可选）
  "modifications": {            // 粒度3：手动修改后确认
    "orders": [
      {
        "orderId": "ORD001",
        "targetPrice": 15.00,   // 修改目标价
        "quantity": 500          // 修改数量
      }
    ]
  }
}
```

**响应（确认成功）**：

```json
{
  "code": 0,
  "message": "confirm_success",
  "data": {
    "notificationId": 101,
    "confirmStatus": "confirmed",
    "affectedOrders": ["ORD001"],
    "orderStatus": "pending_submit"
  }
}
```

**响应（确认失败-已过期）**：

```json
{
  "code": 40101,
  "message": "confirm_expired",
  "data": {
    "notificationId": 101,
    "confirmStatus": "expired",
    "orderStatus": "cancelled"
  }
}
```

#### 3.3.2 POST /api/v1/push/confirm/batch — 批量确认（粒度1：一键全部）

**请求**：

```http
POST /api/v1/push/confirm/batch
Authorization: Bearer {token}
Content-Type: application/json

{
  "action": "confirm",
  "notificationIds": [101, 102, 103]   // 为空则确认当日所有pending
}
```

### 3.4 内部API（模块间调用）

#### 3.4.1 POST /api/v1/push/_internal/send — 发送推送

**此端点仅限内部服务调用，前端不可访问。**

**请求**：

```json
{
  "eventType": "trade_open",
  "userId": 1,
  "title": "📈 开仓通知",
  "content": "标的：航天发展 (000547.SZ)\n方向：买入开仓\n成交价：15.30元",
  "contentJson": {
    "stockCode": "000547.SZ",
    "stockName": "航天发展",
    "direction": "buy",
    "price": 15.30,
    "quantity": 1300,
    "amount": 19890.00,
    "positionRatio": 0.198,
    "stopLossPrice": 14.50,
    "takeProfitPrice": 17.00
  },
  "confirmType": "trade_confirm",
  "confirmPayload": {
    "orderIds": ["ORD001"],
    "tradeMode": "advisory"
  },
  "dedupKey": "trade_open:000547.SZ:2026-05-01"
}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "notificationId": 101,
    "pushStatus": "pending",
    "dedupSkipped": false
  }
}
```

#### 3.4.2 POST /api/v1/push/_internal/batch-send — 批量发送

**用于Agent精选结果等一次性推送多条消息的场景。**

```json
{
  "eventType": "agent_pick",
  "userId": 1,
  "items": [
    {
      "title": "🏆 推荐买入 #1：航天发展",
      "content": "...",
      "contentJson": { ... }
    },
    {
      "title": "🏆 推荐买入 #2：XXXXXX",
      "content": "...",
      "contentJson": { ... }
    }
  ],
  "footer": "⚠️ 今日有3只标的因风控未通过",
  "dedupKey": "agent_pick:2026-05-01"
}
```

**说明**：batch-send 会将多条消息合并为一条完整推送发送，避免消息轰炸。

---

## 4. 业务逻辑伪代码

### 4.1 推送发送管线

```pseudocode
async def send_notification(event_type: EventType, user_id: int,
                            title: str, content: str, content_json: dict,
                            confirm_type: str = "none",
                            confirm_payload: dict = None,
                            dedup_key: str = None) -> Notification:
    """推送发送主入口 — 所有模块调用此函数触发推送"""

    # [1] 检查推送开关
    config = [REDIS] get f"push_config:{user_id}:{event_type}"
    if config is None:
        config = [DB] SELECT * FROM push_config WHERE user_id=? AND event_type=?
        [REDIS] setex f"push_config:{user_id}:{event_type}" 300 config

    if not config.is_enabled:
        log.info(f"推送已关闭: {event_type}, user={user_id}")
        return None

    # [2] 去重检查（同一事件+标的+日期不重复推送）
    if dedup_key:
        dedup_flag = [REDIS] setnx f"push_dedup:{dedup_key}" "1"
        if not dedup_flag:
            # 已存在相同去重键，检查是否在聚合窗口内
            last_ntf = [DB] SELECT id FROM notifications
                       WHERE dedup_key=? AND created_at > NOW() - INTERVAL '5 minutes'
                       LIMIT 1
            if last_ntf:
                log.info(f"推送去重跳过: {dedup_key}")
                return last_ntf  # 返回已有记录
        [REDIS] expire f"push_dedup:{dedup_key}" 3600  # 1小时过期

    # [3] 免打扰检查（critical不受限制）
    priority = EVENT_PRIORITY_MAP[event_type]
    if priority != "critical" and config.quiet_hours_start:
        now = localtime()
        if is_in_quiet_hours(now, config.quiet_hours_start, config.quiet_hours_end):
            log.info(f"免打扰期跳过: {event_type}")
            # 写入DB但标记为pending，免打扰期结束后统一发送
            ntf = create_notification(status="pending", is_snoozed=True)
            return ntf

    # [4] 确认过期时间
    expire_minutes = 0
    if confirm_type == "trade_confirm":
        expire_minutes = 30
    elif confirm_type == "param_approve":
        expire_minutes = 1440  # 24小时

    # [5] 创建通知记录
    ntf = [DB] INSERT INTO notifications (
        user_id, event_type, priority, title, content, content_json,
        push_channel=config.push_channel, push_status='pending',
        confirm_type=confirm_type, confirm_status='pending' if confirm_type != 'none' else 'none',
        confirm_payload=confirm_payload,
        expire_at=NOW() + INTERVAL f'{expire_minutes} minutes' if expire_minutes > 0 else NULL,
        dedup_key=dedup_key
    ) RETURNING *

    # [6] 推入优先级队列
    [REDIS] zadd f"push_queue:{PRIORITY_ORDER[priority]}" ntf.id ntf.created_at.timestamp()

    # [7] 触发异步发送
    await dispatch_push_worker(ntf)

    return ntf
```

### 4.2 推送Worker与Hermes对接

```pseudocode
async def dispatch_push_worker(notification: Notification):
    """异步推送Worker — 按优先级消费队列"""

    # [1] 更新状态为sending
    [DB] UPDATE notifications SET push_status='sending', updated_at=NOW() WHERE id=?

    # [2] 检查Hermes可用性
    hermes_available = [REDIS] get "hermes:health"
    if hermes_available != "ok":
        # Hermes不可用，降级处理
        await degrade_notification(notification)
        return

    # [3] 根据push_channel决定发送方式
    if notification.push_channel in ("wechat", "both"):
        try:
            # 调用Hermes send_message
            result = await hermes_send_message(
                user_id=notification.user_id,
                title=notification.title,
                content=notification.content,
                msg_type="interactive" if notification.confirm_type != "none" else "plain",
                confirm_options=build_confirm_options(notification) if notification.confirm_type != "none" else None
            )

            if result.success:
                [DB] UPDATE notifications
                     SET push_status='sent', wechat_msg_id=result.msg_id, updated_at=NOW()
                     WHERE id=?
                [REDIS] incr f"push_stats:sent:{notification.event_type}:{today()}"
            else:
                await handle_push_failure(notification, result.error)

        except HermesConnectionError:
            await degrade_notification(notification)
        except HermesRateLimitError:
            # 限流，延迟重试
            await asyncio.sleep(5)
            await handle_push_failure(notification, "rate_limited")

    if notification.push_channel in ("in_app", "both"):
        # 系统内通知无需发送，DB记录即可
        # 通过WebSocket推送前端
        await ws_broadcast(notification.user_id, {
            "type": "notification",
            "data": notification_to_dict(notification)
        })

    # [4] 推送统计
    [REDIS] incr f"push_stats:total:{notification.event_type}:{today()}"


async def hermes_send_message(user_id: int, title: str, content: str,
                               msg_type: str = "plain",
                               confirm_options: dict = None) -> HermesResult:
    """Hermes send_message 封装"""

    payload = {
        "user_id": user_id,
        "message": f"{title}\n{content}",
        "msg_type": msg_type,     # plain / interactive
    }

    if confirm_options:
        payload["buttons"] = confirm_options.get("buttons", [])
        payload["expire_at"] = confirm_options.get("expire_at")

    # 调用Hermes API（HTTP）
    response = await http_post(
        url=f"{HERMES_BASE_URL}/api/v1/send",
        json=payload,
        timeout=10  # 10秒超时
    )

    return HermesResult(
        success=response.status_code == 200,
        msg_id=response.json().get("msg_id"),
        error=response.json().get("error") if response.status_code != 200 else None
    )


def build_confirm_options(notification: Notification) -> dict:
    """根据确认类型构建微信交互按钮"""

    if notification.confirm_type == "trade_confirm":
        # 交易确认：提供确认/拒绝按钮
        return {
            "buttons": [
                {"label": "✅ 全部确认", "action": "confirm_all", "value": notification.id},
                {"label": "❌ 全部拒绝", "action": "reject_all", "value": notification.id},
                {"label": "📝 逐条确认", "action": "detail", "value": notification.id}
            ],
            "expire_at": notification.expire_at.isoformat()
        }

    elif notification.confirm_type == "param_approve":
        # 参数审批：提供通过/拒绝按钮
        return {
            "buttons": [
                {"label": "✅ 批准变更", "action": "confirm", "value": notification.id},
                {"label": "❌ 拒绝变更", "action": "reject", "value": notification.id}
            ],
            "expire_at": notification.expire_at.isoformat()
        }

    return None
```

### 4.3 推送失败重试

```pseudocode
async def handle_push_failure(notification: Notification, error: str):
    """推送失败处理 — 指数退避重试"""

    notification.retry_count += 1

    if notification.retry_count >= notification.max_retry:
        # 重试耗尽，标记为dead
        [DB] UPDATE notifications
             SET push_status='dead', updated_at=NOW()
             WHERE id=?
        # 创建系统内降级通知
        [DB] INSERT INTO notifications (user_id, event_type, priority, title, content, push_channel, push_status)
             VALUES (notification.user_id, 'system', 'high',
                     '⚠️ 推送发送失败',
                     f'微信推送失败({error})，请检查Hermes连接。原通知: {notification.title}',
                     'in_app', 'sent')
        [REDIS] incr f"push_stats:dead:{notification.event_type}:{today()}"
        return

    # 指数退避: 30s → 60s → 120s → 240s
    backoff_seconds = 30 * (2 ** notification.retry_count)
    next_retry_at = NOW() + timedelta(seconds=backoff_seconds)

    [DB] UPDATE notifications
         SET push_status='retrying', retry_count=?, last_retry_at=NOW(), updated_at=NOW()
         WHERE id=?

    # 延迟推入重试队列
    [REDIS] zadd f"push_retry_queue" notification.id next_retry_at.timestamp()

    log.warning(f"推送失败，{backoff_seconds}秒后重试({notification.retry_count}/{notification.max_retry}): {error}")


async def degrade_notification(notification: Notification):
    """降级处理 — Hermes不可用时转为系统内通知"""

    [DB] UPDATE notifications
         SET push_channel='in_app', push_status='degraded', updated_at=NOW()
         WHERE id=?

    # 通过WebSocket推送到前端
    await ws_broadcast(notification.user_id, {
        "type": "notification",
        "data": notification_to_dict(notification),
        "degraded": True  # 标记为降级模式
    })

    # 注册Hermes恢复回调（补发微信推送）
    [REDIS] sadd "hermes_pending_compensate" notification.id

    log.warning(f"推送降级为系统内通知: id={notification.id}, event={notification.event_type}")


async def hermes_recovery_compensate():
    """Hermes恢复后补发降级通知"""

    pending_ids = [REDIS] smembers "hermes_pending_compensate"
    for ntf_id in pending_ids:
        ntf = [DB] SELECT * FROM notifications WHERE id=? AND push_status='degraded'
        if ntf and ntf.push_channel in ("wechat", "both"):
            # 重新推入发送队列
            [REDIS] zadd f"push_queue:{PRIORITY_ORDER[ntf.priority]}" ntf.id ntf.created_at.timestamp()
            [REDIS] srem "hermes_pending_compensate" ntf_id

    log.info(f"Hermes恢复，补发{len(pending_ids)}条降级通知")
```

### 4.4 告警风暴聚合

```pseudocode
async def aggregate_alert_storm(event_type: EventType, user_id: int) -> bool:
    """告警风暴检测与聚合 — 短时间内大量相同类型告警时聚合为一条"""

    window_key = f"alert_storm:{user_id}:{event_type}"
    count = [REDIS] incr window_key
    if count == 1:
        [REDIS] expire window_key 300  # 5分钟窗口

    STORM_THRESHOLD = 5  # 5分钟内超过5条相同类型告警

    if count >= STORM_THRESHOLD:
        # 触发风暴聚合：取消队列中的同类型pending通知，替换为一条聚合摘要
        pending_ids = [REDIS] zrangebyscore f"push_queue:{PRIORITY_ORDER[EVENT_PRIORITY_MAP[event_type]]}" -inf +inf
        storm_ids = []
        for pid in pending_ids:
            ntf = [DB] SELECT event_type, push_status FROM notifications WHERE id=?
            if ntf and ntf.event_type == event_type and ntf.push_status == 'pending':
                storm_ids.append(pid)

        # 批量取消
        for sid in storm_ids[:-1]:  # 保留最后一条
            [DB] UPDATE notifications SET push_status='dead', updated_at=NOW() WHERE id=?

        # 修改最后一条为聚合摘要
        last_ntf = [DB] SELECT * FROM notifications WHERE id=storm_ids[-1]
        last_ntf.content = f"⚠️ 过去5分钟内共{count}条{event_type}告警，已聚合\n\n最新一条:\n{last_ntf.content}"
        [DB] UPDATE notifications SET content=?, updated_at=NOW() WHERE id=?

        [REDIS] del window_key  # 重置计数
        return True  # 已聚合

    return False  # 未触发风暴
```

### 4.5 交互式确认处理

```pseudocode
async def handle_wechat_confirm(notification_id: int, action: str,
                                 reply: str = None, modifications: dict = None):
    """处理微信端确认回复"""

    ntf = [DB] SELECT * FROM notifications WHERE id=? FOR UPDATE

    if not ntf:
        raise NotFoundError("通知不存在")

    if ntf.confirm_status != "pending":
        raise BusinessError(40102, "通知已处理", {"status": ntf.confirm_status})

    if ntf.expire_at and ntf.expire_at < NOW():
        # 确认超时
        await handle_confirm_expired(ntf)
        raise BusinessError(40101, "确认已过期", {"status": "expired"})

    if action == "confirm":
        # ===== 交易确认 =====
        if ntf.confirm_type == "trade_confirm":
            if modifications and modifications.get("orders"):
                # 粒度3：手动修改后确认
                for mod in modifications["orders"]:
                    await apply_order_modification(mod)
            # 将订单状态从 pending_confirm → pending_submit
            order_ids = ntf.confirm_payload.get("order_ids", [])
            for oid in order_ids:
                [DB] UPDATE trade_orders SET status='pending_submit', updated_at=NOW()
                     WHERE id=? AND status='pending_confirm'
            await notify_trade_executor(order_ids)

        # ===== 参数审批 =====
        elif ntf.confirm_type == "param_approve":
            param_key = ntf.confirm_payload.get("param_key")
            new_value = ntf.confirm_payload.get("new_value")
            # 写入 param_change_log
            [DB] INSERT INTO param_change_log (param_key, old_value, new_value, change_reason, approved_by, approved_at)
                 VALUES (param_key, ntf.confirm_payload["old_value"], new_value, ntf.confirm_payload["reason"], 'wechat', NOW())
            # 自动回测验证（PRD 4.7: 每次调参后自动跑7天回测）
            backtest_task = await trigger_param_backtest(param_key, new_value)
            # 回测结果异步回调更新参数生效状态

        [DB] UPDATE notifications
             SET confirm_status='confirmed', confirm_reply=?, confirm_at=NOW(), updated_at=NOW()
             WHERE id=?

    elif action == "reject":
        if ntf.confirm_type == "trade_confirm":
            order_ids = ntf.confirm_payload.get("order_ids", [])
            for oid in order_ids:
                [DB] UPDATE trade_orders SET status='cancelled', updated_at=NOW()
                     WHERE id=? AND status='pending_confirm'

        elif ntf.confirm_type == "param_approve":
            # 变更不生效
            pass

        [DB] UPDATE notifications
             SET confirm_status='rejected', confirm_reply=?, confirm_at=NOW(), updated_at=NOW()
             WHERE id=?

    # 推送确认结果反馈
    await send_confirmation_feedback(ntf, action)


async def handle_confirm_expired(ntf: Notification):
    """确认超时处理"""

    [DB] UPDATE notifications SET confirm_status='expired', updated_at=NOW() WHERE id=?

    if ntf.confirm_type == "trade_confirm":
        order_ids = ntf.confirm_payload.get("order_ids", [])
        for oid in order_ids:
            [DB] UPDATE trade_orders SET status='cancelled', updated_at=NOW()
                 WHERE id=? AND status='pending_confirm'

    elif ntf.confirm_type == "param_approve":
        # 保持原参数，不生效
        pass

    # 推送超时通知
    await send_notification(
        event_type=ntf.event_type,
        user_id=ntf.user_id,
        title="⏰ 确认已超时",
        content=f"以下通知的确认已超时，操作已自动取消:\n{ntf.title}",
        content_json={"original_notification_id": ntf.id},
        confirm_type="none"
    )


async def notify_trade_executor(order_ids: list):
    """通知交易执行器处理已确认的订单"""

    # 通过Redis pub/sub通知DD-05交易执行模块
    [REDIS] publish "trade:order:confirmed" json.dumps({
        "order_ids": order_ids,
        "confirmed_at": NOW().isoformat(),
        "confirm_source": "wechat"
    })
```

### 4.6 消息模板渲染

```pseudocode
def render_message_template(event_type: EventType, data: dict) -> tuple[str, str, dict]:
    """渲染消息模板 — 返回 (title, content, content_json)"""

    template = [DB] SELECT * FROM notification_templates
               WHERE event_type=? AND is_active=TRUE ORDER BY version DESC LIMIT 1

    # 替换变量占位
    title = template.title_template
    content = template.body_template

    for key, value in data.items():
        title = title.replace(f"{{{key}}}", str(value))
        content = content.replace(f"{{{key}}}", str(value))

    return title, content, data


# ===== 各事件类型的模板渲染函数 =====

def render_agent_pick(stock_picks: list[dict], risk_rejected_count: int) -> tuple:
    """Agent精选结果推送 — PRD 4.3.3 L782-813"""

    lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━━", "📊 今日Agent精选结果", "━━━━━━━━━━━━━━━━━━━━━━━━━━", ""]

    for i, pick in enumerate(stock_picks, 1):
        lines.append(f"🏆 推荐买入 #{i}：{pick['name']} ({pick['code']})")
        lines.append(f"├── 筛选策略：{pick['strategy']}")
        lines.append(f"├── 入选理由：{pick['reason']}")
        lines.append(f"├── 主线猎手：{pick['hunter_score_detail']} ({pick['hunter_score']}分)")
        lines.append(f"├── 资金侦探：{pick['fund_score_detail']} ({pick['fund_score']}分)")
        lines.append(f"├── 情绪捕手：{pick['sentiment_score_detail']} ({pick['sentiment_score']}分)")
        lines.append(f"├── 经验法官：{pick['judge_score_detail']} ({pick['judge_score']}分)")
        lines.append(f"├── 目标买入价：{pick['target_price_range']}")
        lines.append(f"├── 建议仓位：{pick['position_pct']}% (可用资金{pick['available_amount']:,.0f}元)")
        lines.append(f"├── 止损价：{pick['stop_loss_price']}元 ({pick['stop_loss_pct']}%)")
        lines.append(f"└── 止盈价：{pick['take_profit_price']}元 (+{pick['take_profit_pct']}%)")
        lines.append("")

    if risk_rejected_count > 0:
        lines.append(f"⚠️ 今日有{risk_rejected_count}只标的因风控未通过（详见系统记录）")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    content = "\n".join(lines)
    content_json = {"picks": stock_picks, "risk_rejected_count": risk_rejected_count}

    return "📊 今日Agent精选结果", content, content_json


def render_trade_open(order: dict, position_summary: dict) -> tuple:
    """开仓通知 — PRD 4.3.3 L816-833"""

    content = f"""━━━━━━━━━━━━━━━━━━━━━━━━
📈 开仓通知
━━━━━━━━━━━━━━━━━━━━━━━━
标的：{order['stock_name']} ({order['stock_code']})
方向：买入开仓
成交价：{order['price']}元
数量：{order['quantity']}股
金额：{order['amount']:,.0f}元
仓位占比：{order['position_pct']:.1f}%
止损价：{order['stop_loss_price']}元 ({order['stop_loss_pct']:.1f}%)
止盈价：{order['take_profit_price']}元 (+{order['take_profit_pct']:.1f}%)
触发条件：{order['trigger_condition']}
───────────────────────
当前总仓位：{position_summary['total_position_pct']:.1f}%
当日盈亏：{position_summary['daily_pnl_pct']:+.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━"""

    content_json = {**order, **position_summary}
    return "📈 开仓通知", content, content_json


def render_trade_close(close_type: str, position: dict) -> tuple:
    """平仓通知 — PRD 4.3.3 L836-848"""

    icon = "⚠️ 止损触发" if close_type == "stop_loss" else "🎯 止盈触发"

    content = f"""━━━━━━━━━━━━━━━━━━━━━━━━
{icon}
━━━━━━━━━━━━━━━━━━━━━━━━
标的：{position['stock_name']} ({position['stock_code']})
触发原因：{position['trigger_reason']}
现价：{position['current_price']}元
持仓天数：{position['holding_days']}天
盈亏：{position['pnl_pct']:+.1f}% ({position['pnl_amount']:+,.0f}元)
操作：{position['action_taken']}
后续建议：{position['suggestion']}
━━━━━━━━━━━━━━━━━━━━━━━━"""

    return icon, content, {**position, "close_type": close_type}


def render_daily_review(review_data: dict) -> tuple:
    """每日复盘推送 — PRD 4.3.3 L851-876"""

    content = f"""━━━━━━━━━━━━━━━━━━━━━━━━
📋 今日交易复盘 ({review_data['date']})
━━━━━━━━━━━━━━━━━━━━━━━━
当日操作：
{review_data['operations']}

当前持仓：
{review_data['positions']}

股票池状态：
  今日候选{review_data['pool_candidates']}只 → Agent分析 → 最终精选{review_data['pool_selected']}只 → 开仓{review_data['pool_opened']}只

经验库更新：
  今日新增经验：{review_data['new_experiences']}条
  经验库总量：{review_data['total_experiences']}条

系统状态：
  策略引擎：{'✅ 正常' if review_data['strategy_ok'] else '❌ 异常'}
  Agent服务：{'✅ 正常' if review_data['agent_ok'] else '❌ 异常'}
  miniQMT连接：{'✅ 正常' if review_data['qmt_ok'] else '❌ 异常'}
  数据同步：{'✅ 今日完成' if review_data['sync_ok'] else '❌ 未完成'}
━━━━━━━━━━━━━━━━━━━━━━━━"""

    return f"📋 今日交易复盘 ({review_data['date']})", content, review_data


def render_risk_alert(alert: dict) -> tuple:
    """风控告警推送 — PRD最高优先级"""

    content = f"""━━━━━━━━━━━━━━━━━━━━━━━━
🚨 风控告警
━━━━━━━━━━━━━━━━━━━━━━━━
告警类型：{alert['alert_type']}
当前值：{alert['current_value']}
阈值：{alert['threshold']}
触发时间：{alert['trigger_time']}
建议操作：{alert['suggested_action']}
自动处置：{alert['auto_action']}
━━━━━━━━━━━━━━━━━━━━━━━━"""

    return "🚨 风控告警", content, alert


def render_param_approve(param_change: dict) -> tuple:
    """参数变更审批推送 — PRD 4.7"""

    content = f"""━━━━━━━━━━━━━━━━━━━━━━━━
🔧 参数变更审批
━━━━━━━━━━━━━━━━━━━━━━━━
参数名称：{param_change['param_name']}
当前值：{param_change['old_value']}
建议值：{param_change['new_value']}
变更原因：{param_change['reason']}
触发来源：{param_change['source']}  # agent_feedback / weekly_review
回测验证：{'✅ 已通过' if param_change.get('backtest_passed') else '⏳ 待验证'}
━━━━━━━━━━━━━━━━━━━━━━━━
请回复"确认"或"拒绝""""

    return "🔧 参数变更审批", content, param_change
```

### 4.7 推送配置热加载

```pseudocode
async def update_push_config(user_id: int, event_type: str, updates: dict):
    """更新推送配置 — 即时生效"""

    # [1] 数据库更新
    [DB] UPDATE push_config
         SET is_enabled=?, push_channel=?, quiet_hours_start=?, quiet_hours_end=?, updated_at=NOW()
         WHERE user_id=? AND event_type=?

    # [2] 清除Redis缓存，下次读取时重新加载
    [REDIS] del f"push_config:{user_id}:{event_type}"

    # [3] 如果关闭了某事件推送，取消队列中该类型的pending通知
    if not updates.get("is_enabled", True):
        pending_ids = get_pending_notification_ids(user_id, event_type)
        for pid in pending_ids:
            [DB] UPDATE notifications SET push_status='dead', updated_at=NOW()
                 WHERE id=? AND push_status='pending'

    # [4] 通过Redis pub/sub通知其他服务实例
    [REDIS] publish "config:push:updated" json.dumps({
        "user_id": user_id,
        "event_type": event_type,
        "updated_at": NOW().isoformat()
    })
```

### 4.8 免打扰期结束批量发送

```pseudocode
async def process_snoozed_notifications():
    """定时任务：处理免打扰期积压的通知"""

    # 每分钟检查一次
    now = localtime()
    if not is_business_morning(now):  # 08:00后
        return

    # 查找所有因免打扰而snooze的通知
    snoozed = [DB] SELECT * FROM notifications
              WHERE push_status='pending' AND is_snoozed=TRUE
              AND event_type NOT IN (SELECT event_type FROM push_config WHERE priority='critical')

    if not snoozed:
        return

    # 聚合同类型通知
    grouped = group_by(snoozed, key=lambda n: n.event_type)
    for event_type, notifications in grouped.items():
        if len(notifications) > 3:
            # 超过3条同类通知，聚合为一条摘要
            summary = format_snoozed_summary(event_type, notifications)
            await send_notification(
                event_type=event_type,
                user_id=notifications[0].user_id,
                title=f"📋 免打扰期积压通知({len(notifications)}条)",
                content=summary,
                confirm_type="none"
            )
            # 标记原始通知为已聚合
            for ntf in notifications:
                [DB] UPDATE notifications SET push_status='dead', updated_at=NOW() WHERE id=?
        else:
            # 少量通知，逐条补发
            for ntf in notifications:
                [DB] UPDATE notifications SET is_snoozed=FALSE, updated_at=NOW() WHERE id=?
                await dispatch_push_worker(ntf)
```

---

## 5. 状态机与转换规则

### 5.1 推送状态完整转换表

| 当前状态 | 事件 | 目标状态 | 条件 | 动作 |
|:---------|:-----|:---------|:-----|:-----|
| pending | dispatch | sending | Hermes可用 | 调用send_message |
| pending | degrade | degraded | Hermes不可用 | 转系统内通知+注册补发 |
| pending | cancel | dead | 用户关闭推送开关 | 标记取消 |
| sending | success | sent | Hermes返回成功 | 记录msg_id |
| sending | fail | failed | Hermes返回错误 | 判断重试 |
| failed | retry | retrying | retry_count < max_retry | 指数退避等待 |
| failed | dead | dead | retry_count >= max_retry | 创建失败通知 |
| retrying | dispatch | sending | 退避时间到 | 重新调用send_message |
| degraded | compensate | pending | Hermes恢复 | 推入正常队列 |

### 5.2 确认状态完整转换表

| 当前状态 | 事件 | 目标状态 | 条件 | 动作 |
|:---------|:-----|:---------|:-----|:-----|
| none | — | none | 无需确认 | — |
| pending | confirm | confirmed | 未超时 | 执行确认逻辑 |
| pending | reject | rejected | 未超时 | 执行拒绝逻辑 |
| pending | expire | expired | 超时 | 自动取消/保持原值 |
| confirmed | — | confirmed | 终态 | — |
| rejected | — | rejected | 终态 | — |
| expired | — | expired | 终态 | — |

---

## 6. 异常处理

### 6.1 错误码定义

| 错误码 | HTTP | 说明 | 处理建议 |
|:-------|:-----|:-----|:---------|
| 40001 | 400 | 推送事件类型无效 | 检查event_type枚举 |
| 40002 | 400 | 推送通道无效 | 检查push_channel枚举 |
| 40003 | 400 | 免打扰时间格式错误 | 必须HH:MM格式且成对 |
| 40101 | 410 | 确认已过期 | 重新发起操作 |
| 40102 | 409 | 通知已处理 | 查询当前状态 |
| 40103 | 409 | 确认类型不匹配 | 检查confirm_type |
| 50001 | 500 | Hermes连接失败 | 自动降级，稍后补发 |
| 50002 | 500 | Hermes返回错误 | 自动重试，指数退避 |
| 50003 | 503 | 推送队列过载 | 告警风暴聚合 |

### 6.2 Hermes不可用降级策略

```
Hermes不可用检测:
  ├── 健康检查: 每30秒调用 Hermes /api/v1/health
  ├── 连续3次失败 → 标记 Hermes 不可用
  │   ├── 新推送 → 降级为系统内通知(in_app)
  │   ├── 需确认推送 → 降级但前端弹窗替代确认
  │   └── 已降级推送 → 注册到 hermes_pending_compensate
  ├── 恢复检测: 每60秒尝试调用 /api/v1/health
  │   └── 成功 → 标记恢复，触发 hermes_recovery_compensate()
  └── 超过1小时未恢复 → 推送系统级告警给管理员
```

### 6.3 推送限流保护

```python
# Hermes API 限流规则（按用户）
RATE_LIMITS = {
    "per_minute": 20,     # 每用户每分钟最多20条
    "per_hour": 100,      # 每用户每小时最多100条
    "burst": 5,           # 突发允许5条
}

# 限流实现
async def check_rate_limit(user_id: int) -> bool:
    key = f"push_ratelimit:{user_id}"
    current = [REDIS] incr key
    if current == 1:
        [REDIS] expire key 60

    if current > RATE_LIMITS["per_minute"]:
        # 触发限流，非critical消息延迟发送
        return False
    return True
```

---

## 7. 与其他模块的交互

### 7.1 模块调用关系

```
DD-03 策略引擎 ──────────┐
DD-04 AI-Agent ──────────┤
DD-05 交易执行 ──────────┤──▶ DD-09 Hermes ──▶ Hermes服务 ──▶ 微信
DD-06 风险监控 ──────────┤         │
DD-07 经验库 ────────────┘         ▼
                              DD-08 前端
                           (通知页面/WebSocket)
```

### 7.2 各模块调用Hermes的场景

| 调用方模块 | 事件类型 | 触发时机 | confirm_type | 数据来源 |
|:-----------|:---------|:---------|:-------------|:---------|
| DD-03 | agent_pick | 策略运行完成 | none | stock_pool + agent_decisions |
| DD-05 | trade_open | 订单成交 | trade_confirm | trade_orders |
| DD-05 | trade_close | 止盈/止损触发 | none | positions + stop_loss_conditions |
| DD-05 | trade_add | 加仓成交 | trade_confirm | trade_orders |
| DD-06 | risk_alert | 风控规则触发 | none | risk_events |
| DD-02 | sentiment_event | 舆情检测 | none | news + sentiment分析 |
| DD-09 | daily_review | 收盘后定时 | none | 汇总多表 |
| DD-03 | strategy_anomaly | 策略异常检测 | none | 策略运行时指标 |
| DD-07 | param_approve | 调参建议生成 | param_approve | param_change_log |

### 7.3 确认回调流程

```
微信用户回复"确认"
  │
  ▼
Hermes回调 → POST /api/v1/push/_internal/wechat-callback
  │
  ├── trade_confirm → DD-05 trade_orders.status: pending_confirm → pending_submit
  │                   → Redis pub/sub "trade:order:confirmed"
  │
  └── param_approve → DD-07 param_change_log.approved_by='wechat'
                      → DD-03 触发7天回测验证
                      → 回测通过 → 参数生效
                      → 回测不通过 → 自动回滚，推送回滚通知
```

### 7.4 定时任务

| 任务 | 频率 | 说明 |
|:-----|:-----|:-----|
| push_queue_consumer | 持续运行 | 消费优先级队列，发送推送 |
| push_retry_processor | 每30秒 | 处理重试队列中到期的通知 |
| hermes_health_check | 每30秒 | 检查Hermes可用性 |
| hermes_compensate | 每60秒 | Hermes恢复后补发降级通知 |
| confirm_expiry_scanner | 每60秒 | 扫描超时的确认通知 |
| snooze_processor | 每分钟 | 免打扰期结束后发送积压通知 |
| daily_review_sender | 每日15:30 | 收盘后30分钟生成并推送每日复盘 |
| alert_storm_reset | 每5分钟 | 重置告警风暴计数器 |
| push_stats_aggregate | 每日00:05 | 聚合推送统计写入日报 |

---

## 8. 测试要点

### 8.1 功能测试

| # | 场景 | 预期 |
|:--|:-----|:-----|
| 1 | 正常推送发送 | Hermes返回成功，notifications状态sent |
| 2 | 推送开关关闭 | 通知不发送，DB不创建记录 |
| 3 | 免打扰期推送 | 非critical通知snooze，critical正常发送 |
| 4 | 重复事件去重 | dedup_key相同的通知5分钟内只发1条 |
| 5 | 告警风暴聚合 | 5分钟内5条同类型告警聚合为1条摘要 |
| 6 | Hermes不可用降级 | 推送转为in_app，注册补发 |
| 7 | Hermes恢复补发 | 降级通知重新发送到微信 |
| 8 | 推送失败重试 | 指数退避30s→60s→120s，3次后dead |
| 9 | 交易确认-全部确认 | 订单pending_confirm→pending_submit |
| 10 | 交易确认-部分确认 | 只确认指定订单，其余取消 |
| 11 | 交易确认-修改后确认 | 修改价格/数量后订单更新 |
| 12 | 交易确认-超时 | 30分钟后自动取消订单 |
| 13 | 参数审批-确认 | param_change_log记录审批，触发回测 |
| 14 | 参数审批-拒绝 | 变更不生效 |
| 15 | 参数审批-超时 | 24小时后自动保持原值 |

### 8.2 性能测试

| # | 场景 | 目标 |
|:--|:-----|:-----|
| 1 | 单条推送延迟 | 从事件触发到微信收到 < 3秒 |
| 2 | 批量推送(10条) | 全部发送完成 < 5秒 |
| 3 | 告警风暴(20条/5min) | 聚合为1条，延迟 < 10秒 |
| 4 | 通知历史查询 | 10万条记录分页查询 < 200ms |
| 5 | 推送配置热更新 | 从修改到生效 < 1秒 |

### 8.3 异常测试

| # | 场景 | 预期 |
|:--|:-----|:-----|
| 1 | Hermes宕机 | 所有推送降级为in_app，不丢通知 |
| 2 | Hermes超时(10s) | 视为失败，触发重试 |
| 3 | Hermes限流 | 降速发送，不丢弃 |
| 4 | 数据库写入失败 | 推送不发送，记录错误日志 |
| 5 | Redis连接断开 | 回退到DB查询配置 |
| 6 | 确认回调乱序 | 以最新状态为准，幂等处理 |

---

## 附录A：Hermes接口对接规范

### A.1 Hermes send_message API

```
POST {HERMES_BASE_URL}/api/v1/send
Content-Type: application/json

Request:
{
    "user_id": 1,
    "message": "消息内容",
    "msg_type": "plain",           // plain / interactive
    "buttons": [                   // 仅 interactive 类型
        {"label": "确认", "action": "confirm", "value": "101"},
        {"label": "拒绝", "action": "reject", "value": "101"}
    ],
    "expire_at": "2026-05-01T11:00:00+08:00",  // 可选
    "callback_url": "/api/v1/push/_internal/wechat-callback"  // 确认回调
}

Response:
{
    "code": 0,
    "msg_id": "wx_msg_xxx",       // 微信消息ID
    "status": "sent"
}
```

### A.2 Hermes 回调接口

```
POST /api/v1/push/_internal/wechat-callback
Content-Type: application/json
X-Hermes-Signature: sha256=xxx   // 验签

Request:
{
    "msg_id": "wx_msg_xxx",
    "user_id": 1,
    "action": "confirm",          // confirm / reject / expired
    "value": "101",               // notification_id
    "reply": "确认",              // 用户回复原文（可选）
    "timestamp": "2026-05-01T10:15:00+08:00"
}
```

### A.3 Hermes 健康检查

```
GET {HERMES_BASE_URL}/api/v1/health

Response:
{
    "status": "ok",
    "wechat_connected": true,
    "uptime_seconds": 86400
}
```

---

## 附录B：配置参数清单

| 参数 | 默认值 | 说明 | 来源 |
|:-----|:-------|:-----|:-----|
| HERMES_BASE_URL | — | Hermes服务地址 | 环境变量 |
| PUSH_MAX_RETRY | 3 | 最大重试次数 | system_config |
| PUSH_RETRY_BASE_INTERVAL | 30 | 重试基础间隔(秒) | system_config |
| PUSH_DEDUP_WINDOW | 300 | 去重窗口(秒) | system_config |
| ALERT_STORM_THRESHOLD | 5 | 告警风暴阈值(5分钟内) | system_config |
| ALERT_STORM_WINDOW | 300 | 告警风暴窗口(秒) | system_config |
| PUSH_RATE_LIMIT_PER_MIN | 20 | 每分钟限流 | system_config |
| TRADE_CONFIRM_EXPIRE_MIN | 30 | 交易确认超时(分钟) | push_config |
| PARAM_APPROVE_EXPIRE_MIN | 1440 | 参数审批超时(分钟) | push_config |
| HERMES_HEALTH_CHECK_INTERVAL | 30 | 健康检查间隔(秒) | system_config |
| HERMES_TIMEOUT | 10 | API调用超时(秒) | system_config |
| DAILY_REVIEW_CRON | "30 15 * * 1-5" | 复盘推送cron | system_config |
