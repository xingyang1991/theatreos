# TheatreOS 端到端体验闭环 - 开发计划

**版本**: 1.0  
**日期**: 2025-12-25

---

本文档根据《TheatreOS_E2E闭环_开放项清单_v1.0.docx》制定详细的开发计划，旨在分阶段、可落地地完成核心体验闭环。

## 总体计划

我们将按照以下主要阶段推进开发，每个阶段都包含前后端任务和明确的交付目标。

| 阶段 | 核心模块 | 目标 | 对应文档章节 |
|---|---|---|---|
| **P3** | Slot 节拍与场景播放 | 实现准点开演、多舞台并行、门厅倒计时 | 3.1 |
| **P4** | Gate 门投票结算系统 | 实现投票/下注、证物提交、准点结算、Explain Card生成 | 3.2 |
| **P5** | Evidence 证物系统 | 实现证物生成、持有、提交、验证 | 3.3 |
| **P6** | Explain Card 与 Archive | 实现结算卡详情、历史追溯、证物柜 | 3.4 |
| **P7** | 实时通知系统 | 实现关键状态的实时推送，增强“准点感” | 3.5 |

---

## P3: Slot 节拍与场景播放流程

**目标**: 建立统一的时间节拍，实现多舞台并行播放，并在正确的时间点提示用户门厅开启。

### 后端任务

1.  **`scheduler` 服务增强**:
    *   `generate_hour_plan` 方法需为每个舞台生成独立的 `scene_config`，包含媒体包信息和挂载的 `gate_template_id`。
    *   确保 `HourPlan` 包含明确的 `slot_start_at`, `gate_open_at`, `gate_close_at`, `resolve_at` 时间戳。

2.  **`gateway` API 扩展**:
    *   **`GET /v1/theatres/{theatre_id}/showbill`**: 
        *   返回未来N小时（如2小时）的 `Slot` 列表。
        *   每个 `Slot` 包含 `slot_id`, `start_at`, `phase` (看戏/门厅/结算), `countdown_to_next_phase`。
        *   每个 `Slot` 内包含 `Stage` 列表，每个 `Stage` 卡片显示舞台名、当前场景、Ring等级。
    *   **`GET /v1/slots/{slot_id}/details`**: 
        *   返回该 `Slot` 下所有舞台的详细场景信息和 Gate 挂载信息。
        *   提供到门厅/结算的精确倒计时。

3.  **媒体降级逻辑**:
    *   在 `SceneDeliveryService` 中，当主媒体包生成失败或拉取超时，自动切换到由 `theme_pack` 提供的“图+音+字幕卡”静态降级素材。
    *   确保媒体降级不影响 `Gate` 的正常实例化和结算。

### 前端任务

1.  **Showbill 页面 (`/showbill`)**:
    *   调用 `GET /showbill` API，渲染未来2小时的 Slot 列表。
    *   实现每小时分组，并显示全局的“下一场开始倒计时”。
    *   每个 Slot 内的舞台卡片可点击，进入 `StageLive` 页面。

2.  **StageLive 页面 (`/stages/{stage_id}/live`)**:
    *   根据服务器返回的 `phase` 和倒计时，显示当前状态（“正在上演”、“门厅即将开启”等）。
    *   在“看戏”阶段，播放媒体包（视频/音频）。
    *   在 T+10 分钟时，根据服务器推送或轮询结果，自动弹出“门厅已开启，点击参与”的提示，并引导至 `GateLobby` 页面。

### 验收标准

- [ ] 戏单页能按小时展示未来演出，并有倒计时。
- [ ] 播放页能在正确时间播放场景，并在门厅开启时给出明确提示。
- [ ] 任何媒体播放失败，页面会自动展示降级内容（如静态图片和文字），且不影响后续流程。

---

## P4: Gate 门投票结算系统

**目标**: 实现完整的门（Gate）生命周期，包括投票、下注、提交证物、准点结算和生成 Explain Card。

### 后端任务

1.  **`gate` 服务完善**:
    *   **`create_gate_instance`**: 确保能根据 `scheduler` 传来的 `gate_config` 正确创建 `GateInstance`，包含选项、风险、证物槽位等。
    *   **`submit_vote` / `submit_stake`**: 
        *   实现完整的投票/下注逻辑，支持幂等性（`idempotency_key`）。
        *   增加参与限制：每用户每小时只能参与一个门。
        *   与 `wallet` 服务（如果独立）或 `gate` 内的账本交互，锁定/扣除代币。
    *   **`submit_evidence`**: 实现证物提交接口，记录提交的证物，并将其与用户的投票关联。
    *   **`resolve_gate`**: 
        *   在 `resolve_at` 时间点准时触发结算。
        *   根据投票、下注、证物影响，计算出最终获胜选项。
        *   调用 `kernel` 服务写入 `WorldState` 变化。
        *   生成 `ExplainCard` JSON 对象并存储。
        *   结算用户收益，更新钱包余额。

2.  **`gateway` API**:
    *   **`POST /v1/gates/{gate_instance_id}/vote`**: 提交投票。
    *   **`POST /v1/gates/{gate_instance_id}/stake`**: 提交下注。
    *   **`POST /v1/gates/{gate_instance_id}/evidence`**: 提交证物。
    *   **`GET /v1/gates/{gate_instance_id}/explain`**: 拉取结算后的 Explain Card。

### 前端任务

1.  **GateLobby 页面 (`/gates/{gate_instance_id}/lobby`)**:
    *   展示门的标题、选项、风险提示。
    *   用户可以选择选项进行投票或下注。
    *   提供证物选择器，允许用户从“我的证物”中选择并提交。
    *   在 `gate_close_at` 之后，所有操作按钮置灰，页面变为只读。

2.  **ExplainCard 页面 (`/explains/{gate_instance_id}`)**:
    *   在收到“结算完成”通知后，前端路由到此页面。
    *   渲染 `ExplainCard` 内容：结果、原因分析、世界状态变化、回声线索。
    *   “回声线索”应为可点击链接，能跳转到下一小时相关的舞台或戏单。

### 验收标准

- [ ] 用户可以在门厅页面投票、下注、提交证物。
- [ ] 到结算时间点，Explain Card 页面能准时展示结果。
- [ ] 结算结果符合预期逻辑（投票人数、证物优势等）。
- [ ] 多次重复提交或请求结算，系统状态保持一致（幂等性）。

---

## P5: Evidence 证物系统

**目标**: 建立证物的完整生命周期管理，支持在看戏时获得证物，并在门中使用。

### 后端任务

1.  **`evidence` 服务完善**:
    *   **`create_evidence_instance`**: 
        *   提供接口供 `SceneDelivery` 或 `ContentFactory` 调用，用于在看戏时生成证物实例。
        *   支持 `must_drop` 和概率掉落规则。
        *   证物实例需包含 `owner_id`, `source_scene_id`, `tier`, `expires_at` 等关键信息。
    *   **`get_user_evidence`**: 提供接口查询用户当前持有的所有有效证物。
    *   **`update_evidence_status`**: 在证物被提交、消耗或过期时，更新其状态。

2.  **`gateway` API**:
    *   **`GET /v1/me/evidence`**: 获取当前用户的证物列表（证物柜）。
    *   **`POST /v1/evidence/{instance_id}/verify`**: （P0可简化）提供一个验证证物的入口。

### 前端任务

1.  **StageLive 页面**:
    *   在播放过程中，当收到获得证物的通知时，弹出“获得新证物：[证物名称]”的提示卡片。

2.  **Archive -> 证物柜页面 (`/archive/evidence`)**:
    *   调用 `GET /v1/me/evidence`，展示用户持有的所有证物。
    *   每个证物卡片显示名称、来源、稀有度（Tier）、过期时间、状态（已提交/可用）。

### 验收标准

- [ ] 看戏时能按规则获得证物。
- [ ] 在“我的档案-证物柜”中能看到所有持有的证物及其状态。
- [ ] 获得的证物可以在门厅页面被选择和提交。

---

## P6: Explain Card 与 Archive

**目标**: 将结算结果持久化，让用户可以随时回顾自己的参与历史和决策结果。

### 后端任务

1.  **`archive` 服务 (或在 `gate` 服务中实现)**:
    *   在 `gate` 结算完成后，创建一条 `ArchiveEntry` 记录。
    *   记录应包含 `user_id`, `slot_id`, `gate_instance_id`, 用户的选择，最终结果，以及 `ExplainCard` 的完整内容。

2.  **`gateway` API**:
    *   **`GET /v1/me/archive`**: 获取用户的参与历史记录，支持分页。
    *   返回列表，每项包含门的信息、用户的选择和最终结果。

### 前端任务

1.  **Archive 页面 (`/archive`)**:
    *   实现一个历史记录列表，按时间倒序展示用户参与过的所有门。
    *   每一项点击后可以展开，显示完整的 `ExplainCard` 内容。
    *   提供按故事线或关键词筛选的功能（P1）。

### 验收标准

- [ ] 每次参与门之后，在“我的档案”页面能找到对应的历史记录。
- [ ] 历史记录中的 Explain Card 内容与当时看到的一致。

---

## P7: 实时通知系统

**目标**: 通过实时推送，提升“准点开演/开门/结算”的仪式感和即时性。

### 后端任务

1.  **`realtime` 服务 (WebSocket/SSE)**:
    *   实现一个 SSE (Server-Sent Events) 或 WebSocket 端点。
    *   当 `scheduler`, `gate` 等服务的关键状态变更时，向该服务发送事件。
    *   **需要推送的事件**:
        *   `slot.phase.changed`: { `slot_id`, `new_phase` } (看戏 -> 门厅 -> 结算)
        *   `gate.state.changed`: { `gate_instance_id`, `new_state` } (opened -> closing -> resolved)
        *   `explain.ready`: { `gate_instance_id` }
        *   `evidence.received`: { `evidence_name`, `tier` }
        *   `system.alert`: { `message`, `level` } (如媒体降级、舞台封锁)

### 前端任务

1.  **全局实时连接**:
    *   在应用加载后，建立到后端实时通知服务的连接。
    *   监听并处理来自服务器的各类事件。
    *   根据 `slot.phase.changed` 事件更新全局倒计时和页面状态。
    *   根据 `explain.ready` 事件，自动将用户从 `GateLobby` 引导至 `ExplainCard` 页面。
    *   根据 `evidence.received` 事件，弹出获得证物的提示。

### 验收标准

- [ ] 无需刷新页面，戏单倒计时和状态能自动更新。
- [ ] 结算完成后，页面能自动跳转到 Explain Card。
- [ ] 看戏时获得证物，能立即收到弹窗提示。
