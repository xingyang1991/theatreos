# TheatreOS 完整系统设计细化方案

本文档基于您提供的所有材料，对TheatreOS的六大系统域、共计31个子系统进行详细的设计说明。每个核心系统的设计都将遵循“职责边界、核心数据、对外接口、扩展点、失败兜底”的结构，并集成架构图，以达到可交付研发拆解任务的颗粒度。

---

## 一、 总体架构：三层分治

TheatreOS的顶层设计遵循“内核 Kernel + 主题插件 Theme Pack + 内容工厂 Content Factory”的三层分治原则，旨在实现**可控的AI内容生成**与**高度的可扩展性**。

- **内核 (Kernel)**: 负责所有确定性规则、状态管理和核心循环。它不进行任何“创作”，确保系统的稳定、可审计和可回滚。
- **主题包 (Theme Pack)**: 作为可插拔的世界观插件，用结构化数据定义一个主题的“语法”，包括剧本、规则、实体和风格。这使得平台可以轻松切换或并行多个世界观。
- **内容工厂 (Content Factory)**: 一个独立的、由工作流引擎驱动的AI内容生产线。它的任务是根据内核的“排程”，将主题包的“语法”编译成最终可供用户体验的媒体内容包，并由“连续性编译器”保证其不与世界状态冲突。

### 总体架构图

![总体架构图](diagrams/overall_architecture.png)

---

## 二、 系统域设计详述

接下来，我们将逐一深入六大系统域的设计。

### A. Runtime Domain (在线运行域)

**职责**: 处理所有用户侧的实时交互、核心游戏循环、状态管理和玩家社交系统。这是TheatreOS的心脏，直接面向用户提供服务。

**架构图**:

![Runtime Domain架构图](diagrams/runtime_domain.png)

#### 5. Theatre Kernel (世界内核)

- **职责边界**:
  - 维护世界状态（WorldState）的唯一真相（Source of Truth）。
  - 驱动世界按“Tick”演进（例如，每小时、每天），应用状态变更。
  - 记录所有改变世界状态的事件（Event Sourcing），提供完整的审计和回溯能力。
- **核心数据**:
  - `WorldState`: `(theatre_id, tick_id, world_vars, thread_states, object_holders, stage_locks)`
  - `ThreadState`: `(thread_id, phase_id, progress, branch_bucket, last_advance_at)`
  - `WorldEvent`: `(event_id, type, payload, timestamp)`，用于事件溯源。
- **对外接口/事件**:
  - `GET /theatres/{id}/world_state`: 获取当前世界状态快照。
  - `POST /theatres/{id}/apply_delta`: 内部接口，仅供Gate、Evidence等系统调用，用于原子化更新世界状态。
  - **发布事件**: `world.tick.completed`, `world.var.changed`, `thread.advanced`, `object.holder.changed`。
- **扩展点**:
  - **多城市**: 通过`theatre_id`进行逻辑隔离，每个城市是独立的内核实例集群。
  - **多主题并行**: 同一城市可运行多个`theatre_id`，状态互不污染。仅在“跨剧场汇流门”时，通过受控的事件进行联动。
- **失败兜底**:
  - Tick引擎必须设计为幂等的，重复执行同一Tick不会造成状态错乱。
  - 任何时刻都可以从`WorldEvent`事件流中重建完整的世界状态，用于灾难恢复和调试。

#### 6. Scheduler (排程器)

- **职责边界**:
  - 根据当前世界状态、运营策略和主题包设定，生成每小时的硬性约束`HourPlan`。
  - `HourPlan`定义了该小时的“创作要求”，是内容工厂的输入。
- **核心数据**:
  - `HourPlan`: `(slot_id, theatre_id, primary_thread, target_beat_mix, hour_gate_template, must_drop_evidence, safety_constraints)`
  - `HeatMap`: `(stage_tag -> heat_score)`，聚合用户行为热度，作为排程输入之一。
- **对外接口/事件**:
  - `GET /theatres/{id}/schedule/next_2h`: 客户端获取未来两小时的戏单。
  - `POST /ops/hour_plan_override`: 运营后台手动干预排程。
  - **发布事件**: `schedule.hour_plan.created`。
- **扩展点**:
  - **排程策略插件化**: 不同的Theme Pack可以定义自己的`ScheduleStrategy`，影响拍子组合和节奏。
  - **A/B测试**: 可对门比例、证物稀缺度、并行场数等排程参数进行实验。
- **失败兜底**:
  - 若动态排程生成失败，系统必须自动回退到一个预设的、静态的“骨架排程”（Fallback Schedule）。
  - 若当前小时内容生成不足，排程器应在下一小时自动降低并行场次要求，保证稳定性。

#### 8. Gate System (门系统)

- **职责边界**:
  - 管理“门”的完整生命周期：实例化、开放投票/下注窗口、关闭、结算。
  - 执行公平、可解释且防大户碾压的结算算法。
  - 生成解释卡（Explain Card），向玩家说明结算结果和其对世界的影响。
  - 调用内核接口，将结算后果（Delta）写入WorldState。
- **核心数据**:
  - `GateInstance`: `(gate_id, slot_id, template_id, options, status, result, explain_card_data)`
  - `Stake`: `(user_id, gate_id, option_id, currency, amount)`
  - `EvidenceSubmission`: `(user_id, evidence_instance_id, gate_id)`
- **对外接口/事件**:
  - `POST /gates/{gate_id}/vote`: 参与投票。
  - `POST /gates/{gate_id}/stake`: 进行下注。
  - `POST /gates/{gate_id}/submit_evidence`: 提交证物以获取优势。
  - **发布事件**: `gate.resolved`, `gate.stake.placed`。
- **扩展点**:
  - **Gate类型**: 可轻松扩展新的门类型（如议会门、阵营门）。
  - **Explain Card模板**: 模板内容由Theme Pack定义，保证与世界观一致。
- **失败兜底**:
  - 结算过程必须是幂等的，多次调用同一结算任务结果应完全一致。
  - 若Explain Card生成失败，必须发布一个默认模板的解释卡，至少包含获胜方、世界变量变化和下一条简单的线索提示。

#### 9. Evidence System (证物系统)

- **职责边界**:
  - 管理证物实例（EvidenceInstance）的生命周期，从生成、归属到过期。
  - 处理证物的核心交互：提交、验证、交易。
  - 应用伪造证物的副作用（由Theme Pack定义）。
- **核心数据**:
  - `EvidenceType`: `(type_id, name, description, verification_rules)`，由Theme Pack定义。
  - `EvidenceInstance`: `(instance_id, type_id, tier, owner_id, source_scene_id, expires_at, verified_state)`。
- **对外接口/事件**:
  - `GET /evidence/{instance_id}`: 查看证物详情（根据持有者权限）。
  - `POST /evidence/verify`: 请求验证一个证物。
  - **发布事件**: `evidence.created`, `evidence.owner.changed`, `evidence.verified`。
- **扩展点**:
  - **验证方式**: 不同主题可定义不同的验证逻辑（如消耗资源、前往特定地点）。
  - **词典系统**: 未来可扩展为更复杂的“可读语法”系统，作为玩家的长期成长线。
- **失败兜底**:
  - 若`must_drop`证物在生成时媒体部分失败，系统必须保证其“逻辑部分”（一张带ID和类型的证物卡）能被成功创建和分发。

#### 12. Crew System (剧团系统)

- **职责边界**:
  - 管理剧团的创建、加入、成员和权限。
  - 实现剧团的核心社交功能：共享证物库（Vault）、分工协作工具。
  - 计算并更新剧团信誉，管理议会席位资格。
- **核心数据**:
  - `Crew`: `(crew_id, name, reputation_score, created_at)`
  - `CrewMember`: `(user_id, crew_id, role)`
  - `CrewVault`: `(crew_id, items: [evidence_instance_id])`
- **对外接口/事件**:
  - `POST /crews`: 创建剧团。
  - `POST /crews/{crew_id}/join`: 加入剧团。
  - `POST /crews/{crew_id}/vault/share`: 向共享库添加证物。
  - **发布事件**: `crew.created`, `crew.member.joined`。
- **扩展点**:
  - **反垄断机制**: 剧团信誉的计算公式应是非线性的（如对数或开方），并引入周度衰减，防止大剧团永久垄断。
  - **议会席位**: 席位分配可采用“榜单+抽选保留席”的混合模式，保证中小剧团的参与感。
- **失败兜底**:
  - 如果出现可能导致垄断的漏洞，运营后台应能立即调整信誉计算权重或手动干预议会席位分配。

---

### B. Content Factory Domain (AI内容域)

**职责**: 作为一个独立的、异步的生产线，负责将`HourPlan`编译成可供上线的、经过质量检查和安全审核的媒体内容包。这是实现“AI生成自由度”与“系统稳定性”解耦的关键。

**架构图**:

![Content Factory Domain架构图](diagrams/content_factory_domain.png)

#### 16. Generation Orchestrator (生成编排系统)

- **职责边界**:
  - 消费`schedule.hour_plan.created`事件，为每个`HourPlan`启动一个内容生成工作流。
  - 编排和调度多智能体（Multi-Agent）协作，管理从拍子选择到最终发布的完整流程。
  - 强烈建议使用如Temporal这样的工作流引擎来实现，以获得重试、补偿、超时和可观测性。
- **核心数据**:
  - `GenerationJob`: `(job_id, slot_id, status, attempts, cost, artifacts_references)`
  - `SceneDraft`: 结构化的JSON，包含场景文本、对白、证物提示等，是渲染前的中间产物。
- **对外接口/事件**:
  - `POST /gen/run?slot_id=...`: 手动触发一个生成任务。
  - `GET /gen/jobs/{id}`: 查询生成任务状态。
  - **发布事件**: `gen.job.started`, `gen.job.completed`, `gen.job.failed`, `content.published`。
- **扩展点**:
  - **LLM网关**: 所有对大语言模型的调用都通过一个自研的轻量级网关，以统一处理结构化输出（JSON Schema）、重试、成本控制和供应商切换。
  - **提示词包 (Prompt Pack)**: 提示词模板和风格锁应作为Theme Pack的一部分进行管理，减少模型输出的“漂移”。
- **失败兜底**:
  - 这是保证系统不断档的核心。任何生成环节失败，工作流必须自动执行降级策略：
    1.  **自动修复**: 尝试更换同标签的舞台或同类型的拍子重试。
    2.  **替换救援拍子**: 如果重试失败，立即换上预设的救援拍子（Rescue Beat）。
    3.  **降级媒体**: 如果渲染失败，将内容降级为“剪影+音轨+证物卡”。
    4.  **最终兜底**: 若一切都失败，发布一个“静默回声”场次，只包含一个门和一张解释卡，告知玩家此地信号受阻。

#### 17. CanonGuard Compiler (连续性与安全编译器)

- **职责边界**:
  - 作为内容上线前的强制性检查关卡，对生成的`SceneDraft`进行编译。
  - 检查与当前`WorldState`的连续性、是否符合实体白名单、是否超出预算配额、以及是否违反安全合规规则。
  - 输出编译结果：`PASS`或`FAIL`，如果失败则附带自动修复建议。
- **核心规则 (必须工程化)**:
  - **硬规则 (Hard Fail)**: 角色时空冲突、关键物件归属冲突、`must_drop`证物未产出、门选项非法、安全违规。
  - **软规则 (Soft Score)**: 重复镜头语法惩罚、解释性台词过多、新鲜度不足等，用于从多个候选场次中择优。
  - **预算 (Budget)**: 每小时高强度拍子上限、A级证物产出上限等。
- **对外接口/事件**:
  - `POST /compiler/check`: 输入`SceneDraft`、`WorldState`和`HourPlan`，返回编译结果。
- **扩展点**:
  - **规则配置化**: 所有规则都应在JSON或YAML文件中定义，允许运营在后台调整参数。
  - **主题特定规则**: Theme Pack可以附加该主题独有的规则（例如，某主题禁止出现“魔法”一词）。
- **失败兜底**:
  - 编译`FAIL`必须阻塞上线流程，并强制触发Orchestrator的自动修复或救援替换逻辑。

---

### C, D, E, F 域设计详述

这四个域提供了支撑在线运行、内容生产和长期运营所必需的运营、安全、数据和基础设施能力。

**架构图**:

![Other Domains架构图](diagrams/other_domains.png)

#### C. LiveOps Domain (运营域)

- **职责**: 为运营团队提供管理、监控和干预系统的工具，确保日常运营的平稳和高效。

- **20. LiveOps Console (运营后台)**
  - **职责边界**: 提供一个统一的Web界面，用于管理排程、配置爆点、控制舞台和处理突发事件。
  - **核心功能**: 排程可视化与编辑、门模板管理、舞台封锁/开放、RingA一键开关、主题包版本回滚、发布包版本回滚。
  - **关键能力**: “一键救援”（发布预设的救援slot）、“一键降级”（全城切换到剪影/音轨模式）、“一键封锁舞台”（用于安全事件处置）。

#### D. Safety & Moderation Domain (安全治理域)

- **职责**: 保护社区和平台免受有害内容、作弊行为和安全风险的侵害。

- **23. Moderation (内容审核)**
  - **职责边界**: 对所有用户生成内容（UGC，如传闻、聊天）和AI生成媒体内容进行审核。
  - **设计原则**: 采用“先严后宽”的策略。首月只开放模板化的UGC，后续再逐步开放受控的自由编辑（需经过提案、预编译和人审流程）。

- **24. Abuse / Anti-cheat (反作弊)**
  - **职责边界**: 检测并处理位置作弊、下注异常、机器人刷号等滥用行为。
  - **失败兜底**: 一旦检测到定位异常或作弊嫌疑，自动将该用户权限降级到RingC（远观），不影响其基本观看体验，但限制其高级交互和下注上限。

#### E. Analytics Domain (数据域)

- **职责**: 收集、处理和分析用户行为与系统运行数据，为产品迭代、运营决策和内容优化提供洞察。

- **27. Archive & Forensics (档案与考古)**
  - **职责边界**: 将所有已发布的场次、结算的门、世界状态变更等事件归档，形成可供玩家查询的“历史档案”。
  - **核心功能**: 支持玩家进行“考古”，回溯某一天的事件，或查看某个关键决策如何引发了后续的一系列“回声”。这是增强玩家社区归属感和叙事沉浸感的关键系统。

#### F. Infra Domain (基础设施域)

- **职责**: 提供稳定、可扩展、高效的基础设施服务，支撑上层所有业务系统的运行。

- **29. Event Bus (事件总线)**
  - **职责边界**: 作为系统解耦的核心，承载所有跨模块的异步消息，如`gate.resolved`, `world.tick.completed`, `content.published`等。
  - **技术选型**: 推荐使用Kafka，因为它强大的持久化、回放和流处理能力，对于实现事件溯源、数据分析和系统审计至关重要。

- **30. Workflow Engine (工作流引擎)**
  - **职责边界**: 专用于驱动Content Factory中的长流程任务。
  - **技术选型**: 强烈推荐Temporal。其对工作流状态的持久化、内置的重试/补偿逻辑、以及优秀的可观测性，是解决AI内容生成中各种不确定性和失败场景的最佳实践，确保“永不断档”的最可靠方案。

---

## 三、 系统清单汇总

下表汇总了TheatreOS的全部31个系统，按域分类，并标注了其核心职责和建议的技术选型。

| 域 | 系统编号 | 系统名称 | 核心职责 | 建议技术选型 |
| :--- | :---: | :--- | :--- | :--- |
| **A. Runtime** | 1 | API Gateway / BFF | 统一入口、请求路由、协议转换 | Kong / Nginx |
|  | 2 | Auth & Identity | 账号体系、认证、授权 | Keycloak / Auth0 |
|  | 3 | User Profile & Reputation | 个人档案、信誉计算 | PostgreSQL |
|  | 4 | Location & Geofence | 定位、围栏、RingC/B/A判断 | PostGIS |
|  | 5 | **Theatre Kernel** | 世界状态、Tick引擎、事件溯源 | Kotlin/Spring Boot + PostgreSQL |
|  | 6 | **Scheduler** | 排程器、HourPlan生成 | Kotlin/Spring Boot |
|  | 7 | Scene Delivery | 场次投放、播放权限、版本管理 | Kotlin/Spring Boot + Redis |
|  | 8 | **Gate System** | 投票/下注/结算/Explain Card | Kotlin/Spring Boot |
|  | 9 | Evidence System | 证物实例化、提交、验证、过期 | Kotlin/Spring Boot |
|  | 10 | Rumor System | 传闻卡流通、验证 | Kotlin/Spring Boot |
|  | 11 | Trace System | 痕迹放置、生命周期、副作用 | Kotlin/Spring Boot |
|  | 12 | **Crew System** | 剧团、共享库、协作、议会席位 | Kotlin/Spring Boot |
|  | 13 | Economy & Wallet | 资源/代币/通行证 | Kotlin/Spring Boot |
|  | 14 | Trade/Market | 交换/撮合/托管 | Kotlin/Spring Boot |
| **B. Content Factory** | 15 | **Theme Pack Registry** | 主题包仓库、版本、发布 | Python/FastAPI + S3 |
|  | 16 | **Generation Orchestrator** | 生成编排、多智能体工作流 | Python/FastAPI + **Temporal** |
|  | 17 | **CanonGuard Compiler** | 连续性/安全/预算编译器 | Go / Kotlin (纯规则引擎) |
|  | 18 | Render Pipeline | 图/音/视频生成与素材管理 | Python + 云渲染API |
|  | 19 | Content QA & Review | 人审、抽检、回滚 | Web UI + 审核队列 |
| **C. LiveOps** | 20 | **LiveOps Console** | 排程/开关/风控/一键救援 | React Admin |
|  | 21 | Feature Flags & Config | 灰度、实验、规则开关 | Unleash / LaunchDarkly |
|  | 22 | Incident & Safety Ops | 安全事件处置SOP | 工单系统集成 |
| **D. Safety** | 23 | Moderation | UGC/媒体/文本审核 | 云审核API + 人审平台 |
|  | 24 | Abuse / Anti-cheat | 位置作弊/下注风控 | 规则引擎 + 异常检测 |
| **E. Analytics** | 25 | Telemetry Pipeline | 埋点、事件流采集 | Kafka + Flink/Spark |
|  | 26 | Metrics & Experimentation | 指标、A/B、归因 | Grafana + 自研实验平台 |
|  | 27 | Archive & Forensics | 档案、考古、回声复盘 | ClickHouse |
| **F. Infra** | 28 | Media Storage + CDN | 素材存储与分发 | S3 + CloudFront/Cloudflare |
|  | 29 | **Event Bus** | 事件总线 | **Kafka** |
|  | 30 | **Workflow Engine** | 长流程编排 | **Temporal** |
|  | 31 | Observability | 日志/链路/告警 | OpenTelemetry + Grafana + Loki |

---

## 四、 推荐技术栈总结

基于项目的核心挑战（每小时准时交付、世界状态一致性、AI生成可控、地理围栏与隐私），推荐以下技术方案：

| 层级 | 推荐方案 | 理由 |
| :--- | :--- | :--- |
| **后端核心 (Runtime Kernel)** | Kotlin + Spring Boot | 适合复杂领域模型（DDD）、事务一致性强、团队招聘容易。 |
| **主数据库** | PostgreSQL (+ PostGIS + pgvector) | 一库多用，减少系统复杂度。PostGIS用于地理围栏，pgvector用于AI检索。 |
| **缓存** | Redis | 用于Gate倒计时、热度、戏单等高频读取场景。 |
| **内容工厂** | Python + FastAPI + **Temporal** | Python是AI/ML生态的首选语言。Temporal是处理"多步骤+重试+补偿+超时"工作流的最佳实践。 |
| **规则编译器 (CanonGuard)** | Go 或 Kotlin | 需要高确定性、可测试的纯规则引擎，独立于AI管道。 |
| **事件总线** | Kafka | 成熟、可靠，强大的持久化和回放能力对审计和回声功能至关重要。 |
| **分析数据库** | ClickHouse | 事件量起来后，用于漏斗、留存、按小时聚合分析非常高效。 |
| **媒体与分发** | S3 + CDN | 标准方案，供应商可替换。 |
| **可观测性** | OpenTelemetry + Prometheus/Grafana + Loki | 业界标准的全链路追踪、指标和日志方案。 |

---

## 五、 工程演进建议

为避免一次性构建"巨石系统"，建议分阶段演进：

| 阶段 | 目标 | 核心系统范围 |
| :--- | :--- | :--- |
| **MVP** | 能跑起来 | Kernel (WorldState, Scheduler, Gate, Explain), SceneDelivery (图文音), Crew (创建/加入/Vault), LiveOps (排程/一键救援/封锁), CanonGuard (硬规则) |
| **V1** | 能扩张 | 副剧场轮换, Council Gate, Trade/Market, Trace副作用, CanonGuard (软评分+自动修复), Render Pipeline (供应商抽象+素材复用) |
| **V2** | 能规模化 | 受控编辑UGC (提案→预编译→人审), 跨剧场汇流门, 更强NPC/群体行为模拟 |
