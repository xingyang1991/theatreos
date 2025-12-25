# TheatreOS 端到端体验闭环开发报告

**版本**: 1.0  
**日期**: 2025-12-25  
**作者**: Manus AI

---

## 执行摘要

本报告记录了根据《TheatreOS_E2E闭环_开放项清单_v1.0》完成的核心体验闭环开发工作。我们成功实现了从"看戏"到"追证复访"的完整后端API体系，为前端提供了全面的数据支持。

### 开发成果概览

| 模块 | 新增API数量 | 状态 | 说明 |
|------|-------------|------|------|
| **Slot节拍系统** | 4 | ✅ 已部署 | 戏单、Slot详情、阶段时间线 |
| **Gate门系统** | 7 | ✅ 已部署 | 门厅、投票、下注、证物提交、结算 |
| **Evidence证物系统** | 5 | ✅ 已部署 | 证物列表、详情、验证、发放 |
| **Archive归档系统** | 4 | ✅ 已部署 | 历史记录、详情、统计、故事线 |
| **实时通知系统** | 增强 | ✅ 已部署 | E2E闭环事件推送 |

---

## 一、Slot节拍与场景播放系统

### 1.1 新增API端点

#### `GET /v1/theatres/{theatre_id}/showbill`
**功能**: 获取戏单 - 展示未来N小时的演出安排

**响应示例**:
```json
{
  "theatre_id": "xxx",
  "current_time": "2025-12-25T10:00:00Z",
  "timezone": "Asia/Shanghai",
  "lookahead_hours": 2,
  "slots": [
    {
      "slot_id": "slot_20251225_1000",
      "start_at": "2025-12-25T10:00:00Z",
      "phase": "watching",
      "phase_label": "正在上演",
      "countdown_seconds": 420,
      "stages": [...]
    }
  ],
  "current_slot_id": "slot_20251225_1000"
}
```

#### `GET /v1/slots/{slot_id}/details`
**功能**: 获取Slot详情，包含所有舞台和门信息

#### `GET /v1/slots/{slot_id}/phase`
**功能**: 获取Slot阶段时间线，用于前端倒计时

#### `GET /v1/theatres/{theatre_id}/current-slot`
**功能**: 获取当前正在进行的Slot

### 1.2 阶段流转设计

Slot的生命周期分为以下阶段，每个阶段都有明确的时间边界：

| 阶段 | 时间范围 | 说明 |
|------|----------|------|
| `upcoming` | T-∞ ~ T+0 | 即将开始 |
| `watching` | T+0 ~ T+10 | 看戏阶段 |
| `gate_open` | T+10 ~ T+12 | 门厅开放 |
| `resolving` | T+12 ~ T+12:30 | 结算中 |
| `echo` | T+12:30 ~ T+15 | 回声时刻 |
| `completed` | T+15 ~ | 已结束 |

---

## 二、Gate门投票结算系统

### 2.1 新增API端点

#### `GET /v1/gates/{gate_instance_id}/lobby`
**功能**: 获取门厅信息，展示选项、状态和用户参与情况

#### `POST /v1/gates/{gate_instance_id}/vote`
**功能**: 提交投票（幂等）

**请求体**:
```json
{
  "option_id": "opt_a",
  "ring_level": "C",
  "idempotency_key": "unique_key"
}
```

#### `POST /v1/gates/{gate_instance_id}/stake`
**功能**: 提交下注（幂等）

#### `POST /v1/gates/{gate_instance_id}/evidence`
**功能**: 提交证物

#### `GET /v1/gates/{gate_instance_id}/explain`
**功能**: 获取Explain Card结算详情

**响应示例**:
```json
{
  "gate_instance_id": "xxx",
  "winner_option_id": "opt_a",
  "winner_label": "选项A",
  "result_summary": "选项A获胜",
  "why_explanation": "根据投票和证物综合判定",
  "vote_distribution": {"opt_a": 15, "opt_b": 8},
  "stake_distribution": {"opt_a": 1500.0, "opt_b": 800.0},
  "echo_hints": [...]
}
```

#### `GET /v1/gates/{gate_instance_id}/participation`
**功能**: 获取用户在该门的参与情况

#### `POST /v1/gates/{gate_instance_id}/resolve`
**功能**: 触发门结算（内部/调度器调用）

---

## 三、Evidence证物系统

### 3.1 新增API端点

#### `GET /v1/me/evidence`
**功能**: 获取我的证物列表（证物柜）

**查询参数**:
- `status`: 筛选状态 (ACTIVE/SUBMITTED/EXPIRED)
- `tier`: 筛选等级 (A/B/C/D)
- `limit`, `offset`: 分页

#### `GET /v1/evidence/{instance_id}`
**功能**: 获取证物详情

#### `POST /v1/evidence/{instance_id}/verify`
**功能**: 验证证物真伪

#### `GET /v1/me/evidence/summary`
**功能**: 获取证物摘要统计

#### `POST /v1/evidence/grant`
**功能**: 发放证物（内部API）

### 3.2 证物等级体系

| 等级 | 名称 | 说明 |
|------|------|------|
| A | 硬证物 | 关键门前置，稀缺，通常来自RingB/A或高风险场 |
| B | 可信线索 | 用于读底概率与验证传闻 |
| C | 噪声线索 | 可误读，推动讨论与交易 |
| D | 碎片与环境 | 用于氛围与考古，不强推结算 |

---

## 四、Archive归档系统

### 4.1 新增API端点

#### `GET /v1/me/archive`
**功能**: 获取我的参与历史归档

**查询参数**:
- `action_type`: 筛选行为类型
- `outcome`: 筛选结果 (WIN/LOSE/NEUTRAL)
- `start_date`, `end_date`: 日期范围

#### `GET /v1/me/archive/{entry_id}`
**功能**: 获取归档详情，包含完整Explain Card

#### `GET /v1/me/archive/stats`
**功能**: 获取归档统计

**响应示例**:
```json
{
  "total_participations": 25,
  "wins": 12,
  "losses": 8,
  "neutral": 5,
  "win_rate": 0.6,
  "total_stake_amount": 5000.0,
  "total_payout": 6200.0,
  "net_profit": 1200.0
}
```

#### `GET /v1/me/storylines`
**功能**: 获取我参与的故事线

---

## 五、实时通知系统增强

### 5.1 新增E2E闭环事件类型

| 事件类型 | 触发时机 | 用途 |
|----------|----------|------|
| `slot.phase.changed` | Slot阶段变更 | 前端自动更新状态 |
| `slot.countdown` | 倒计时更新 | 同步显示倒计时 |
| `gate.state.changed` | 门状态变更 | 提示用户参与 |
| `gate.vote.update` | 投票更新 | 实时显示投票分布 |
| `explain.ready` | Explain Card就绪 | 自动跳转结算页 |
| `evidence.received` | 获得证物 | 弹窗提示 |
| `evidence.expiring_soon` | 证物即将过期 | 提醒使用 |

### 5.2 推送服务便捷函数

```python
# 通知Slot阶段变更
await notify_slot_phase_changed(theatre_id, slot_id, "watching", "gate_open", 120)

# 通知门开启
await notify_gate_opened(theatre_id, gate_instance_id, countdown_to_close=120)

# 通知Explain Card准备就绪
await notify_explain_ready(theatre_id, gate_instance_id, "opt_a", "选项A", "选项A获胜")

# 通知获得证物
await notify_evidence_received(user_id, evidence_id, "神秘信件", "B", "SCENE")
```

---

## 六、部署状态

### 6.1 服务器信息

| 项目 | 值 |
|------|-----|
| 服务器IP | 120.55.162.182 |
| 后端端口 | 8000 |
| 服务状态 | ✅ 运行中 |

### 6.2 路由注册确认

所有新路由已成功注册：

```
✅ Data pack routes registered successfully
✅ Slot routes registered successfully
✅ Gate routes registered successfully
✅ Evidence routes registered successfully
✅ Archive routes registered successfully
✅ Test mode routes registered successfully
```

### 6.3 API文档访问

Swagger UI: http://120.55.162.182/docs

---

## 七、前端集成指南

### 7.1 戏单页面集成

```typescript
// 获取戏单
const showbill = await api.get(`/v1/theatres/${theatreId}/showbill?lookahead_hours=2`);

// 监听阶段变更
realtime.on('slot.phase.changed', (data) => {
  if (data.new_phase === 'gate_open') {
    showNotification('门厅已开启，快来参与！');
  }
});
```

### 7.2 门厅页面集成

```typescript
// 获取门厅信息
const lobby = await api.get(`/v1/gates/${gateId}/lobby`);

// 提交投票
await api.post(`/v1/gates/${gateId}/vote`, {
  option_id: selectedOption,
  idempotency_key: generateKey()
});

// 监听结算完成
realtime.on('explain.ready', (data) => {
  router.push(`/explains/${data.gate_instance_id}`);
});
```

### 7.3 证物柜集成

```typescript
// 获取证物列表
const evidence = await api.get('/v1/me/evidence?status=ACTIVE');

// 监听获得证物
realtime.on('evidence.received', (data) => {
  showToast(`获得新证物: ${data.evidence_name}`);
});
```

---

## 八、后续开发建议

### 8.1 P1优先级

1. **前端页面实现**: 根据本报告的API规范，实现对应的前端页面
2. **调度器集成**: 将Slot阶段变更和Gate结算与调度器联动
3. **证物掉落规则**: 实现场景播放时的证物掉落逻辑

### 8.2 P2优先级

1. **故事线追溯**: 完善Archive中的故事线关联
2. **证物交易**: 实现用户间的证物交易功能
3. **成就系统**: 基于Archive统计实现成就徽章

### 8.3 P3优先级

1. **数据分析**: 基于Archive数据的用户行为分析
2. **推荐系统**: 基于参与历史的个性化推荐
3. **社交功能**: 剧团内的证物共享和协作

---

## 九、文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| slot_routes.py | gateway/src/ | Slot节拍API |
| gate_routes.py | gateway/src/ | Gate门系统API |
| evidence_routes.py | gateway/src/ | Evidence证物API |
| archive_routes.py | gateway/src/ | Archive归档API |
| realtime_enhanced.py | gateway/src/ | 增强实时推送 |
| main.py | gateway/src/ | 更新的主入口 |
| E2E_Loop_Development_Plan.md | 项目根目录 | 开发计划文档 |

---

## 十、结论

本次开发工作成功实现了TheatreOS端到端体验闭环的核心后端API体系。所有API均已部署到生产服务器并通过基础验证。前端团队现在可以基于这些API开始页面开发工作，实现完整的用户体验闭环。

**核心闭环路径已打通**:
```
看戏 → 获得证物 → 进入门厅 → 投票/下注/提交证物 → 结算 → 查看Explain Card → 归档 → 追证复访
```
