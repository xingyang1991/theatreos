# TheatreOS M3 验收文档：Evidence System & Rumor System

本文档详细说明 Evidence System（证物系统）和 Rumor System（谣言系统）的核心接口设计（OpenAPI 规范）和数据模型，供验收使用。

---

## 第一部分：Evidence System（证物系统）

### 1.1 系统概述

Evidence System 管理玩家获取、持有、验证、交易和使用证物的全生命周期。证物是玩家进行推理、博弈和影响世界的核心道具。

**核心设计理念**：
- **分层稀缺性**：证物分为 A/B/C/D 四个等级，等级越高越稀有
- **时效性**：证物有过期时间，增加紧迫感和决策压力
- **可验证性**：证物可能是伪造的，需要花费成本验证
- **可流通性**：证物可以在玩家间交易

---

### 1.2 数据模型

#### 1.2.1 核心枚举类型

```python
class EvidenceTier(str, Enum):
    """证物等级"""
    A = "A"  # 最高级 - 关键证据，极稀有
    B = "B"  # 高级 - 重要线索
    C = "C"  # 中级 - 普通线索
    D = "D"  # 低级 - 背景信息

class EvidenceSource(str, Enum):
    """证物来源"""
    SCENE = "SCENE"           # 场景观看获得
    GATE_REWARD = "GATE_REWARD"  # 门结算奖励
    TRADE = "TRADE"           # 交易获得
    CREW_SHARE = "CREW_SHARE" # 剧团共享
    SYSTEM = "SYSTEM"         # 系统发放

class EvidenceStatus(str, Enum):
    """证物状态"""
    ACTIVE = "ACTIVE"       # 活跃可用
    SUBMITTED = "SUBMITTED" # 已提交到门
    EXPIRED = "EXPIRED"     # 已过期
    CONSUMED = "CONSUMED"   # 已消耗
    TRADED = "TRADED"       # 已交易出去
    FORGED = "FORGED"       # 被标记为伪造

class VerificationStatus(str, Enum):
    """验证状态"""
    UNVERIFIED = "UNVERIFIED"   # 未验证
    VERIFIED = "VERIFIED"       # 已验证为真
    FORGED = "FORGED"           # 已验证为假
    SUSPICIOUS = "SUSPICIOUS"   # 可疑
```

#### 1.2.2 核心数据结构

**EvidenceType（证物类型定义）**
```json
{
  "type_id": "ev_signal",
  "name": "信号痕迹",
  "description": "检测到的异常信号记录",
  "category": "TRACE",
  "default_tier": "C",
  "base_value": 10,
  "expiry_hours": 72,
  "forgery_difficulty": 0.3,
  "verification_cost": 5,
  "icon_url": "https://..."
}
```

**EvidenceInstance（证物实例）**
```json
{
  "instance_id": "uuid-xxx",
  "type_id": "ev_signal",
  "tier": "B",
  "owner_id": "user_001",
  "theatre_id": "theatre_xxx",
  "source": "SCENE",
  "source_scene_id": "scene_001",
  "source_slot_id": "slot_001",
  "source_stage_id": "stage_bund",
  "status": "ACTIVE",
  "verification_status": "UNVERIFIED",
  "credibility_score": null,
  "is_forged": false,
  "forger_id": null,
  "created_at": "2025-12-25T01:00:00Z",
  "expires_at": "2025-12-28T01:00:00Z",
  "submitted_at": null,
  "submitted_to_gate": null,
  "metadata": {}
}
```

**TradeOffer（交易挂单）**
```json
{
  "offer_id": "uuid-xxx",
  "seller_id": "user_001",
  "evidence_instance_id": "uuid-xxx",
  "asking_price": 50.0,
  "currency": "SHARD",
  "status": "OPEN",
  "created_at": "2025-12-25T01:00:00Z",
  "expires_at": "2025-12-26T01:00:00Z",
  "buyer_id": null,
  "completed_at": null
}
```

**EvidenceSubmission（证物提交记录）**
```json
{
  "submission_id": "uuid-xxx",
  "evidence_instance_id": "uuid-xxx",
  "gate_instance_id": "gate_xxx",
  "user_id": "user_001",
  "submitted_at": "2025-12-25T02:00:00Z",
  "impact_score": 0.8,
  "outcome": null
}
```

---

### 1.3 API 接口规范

#### 1.3.1 创建证物

**POST** `/v1/theatres/{theatre_id}/evidence`

创建一个新的证物实例（通常由系统在场景观看后自动调用）。

**请求体**
```json
{
  "type_id": "ev_signal",
  "tier": "B",
  "owner_id": "user_001",
  "source": "SCENE",
  "source_scene_id": "scene_001",
  "source_slot_id": "slot_001",
  "source_stage_id": "stage_bund",
  "metadata": {}
}
```

**响应** `200 OK`
```json
{
  "instance_id": "1cd06f86-b0b5-4351-b983-a642e890ca69",
  "type_id": "ev_signal",
  "tier": "B",
  "owner_id": "user_001",
  "theatre_id": "bf15fc5a-b9fa-4a73-8b62-17ecd4af0a48",
  "source": "SCENE",
  "status": "ACTIVE",
  "verification_status": "UNVERIFIED",
  "credibility_score": null,
  "created_at": "2025-12-25T01:07:10.457886+00:00",
  "expires_at": "2025-12-28T01:07:10.457775+00:00",
  "is_forged": false
}
```

---

#### 1.3.2 获取证物详情

**GET** `/v1/evidence/{instance_id}`

获取指定证物实例的详细信息。

**响应** `200 OK`
```json
{
  "instance_id": "1cd06f86-b0b5-4351-b983-a642e890ca69",
  "type_id": "ev_signal",
  "tier": "B",
  "owner_id": "user_001",
  "theatre_id": "bf15fc5a-b9fa-4a73-8b62-17ecd4af0a48",
  "source": "SCENE",
  "status": "ACTIVE",
  "verification_status": "UNVERIFIED",
  "credibility_score": null,
  "created_at": "2025-12-25T01:07:10.457886+00:00",
  "expires_at": "2025-12-28T01:07:10.457775+00:00",
  "is_forged": false
}
```

---

#### 1.3.3 获取用户证物列表

**GET** `/v1/users/{user_id}/evidence`

获取指定用户持有的所有证物。

**查询参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `include_expired` | boolean | 否 | 是否包含已过期证物，默认 `false` |
| `tier` | string | 否 | 按等级筛选 (A/B/C/D) |

**响应** `200 OK`
```json
[
  {
    "instance_id": "uuid-1",
    "type_id": "ev_signal",
    "tier": "B",
    "owner_id": "user_001",
    "theatre_id": "theatre_xxx",
    "source": "SCENE",
    "status": "ACTIVE",
    "verification_status": "UNVERIFIED",
    "created_at": "2025-12-25T01:00:00Z",
    "expires_at": "2025-12-28T01:00:00Z",
    "is_forged": false
  }
]
```

---

#### 1.3.4 验证证物

**POST** `/v1/evidence/{instance_id}/verify`

验证证物的真伪，需要支付验证成本。

**请求头**
| 头部 | 说明 |
|------|------|
| `X-User-ID` | 验证者用户ID |

**请求体**
```json
{
  "pay_cost": true
}
```

**响应** `200 OK`
```json
{
  "success": true,
  "is_authentic": true,
  "confidence": 0.95,
  "cost_paid": 5,
  "message": "证物验证完成，确认为真品",
  "detected_forgery": false
}
```

---

#### 1.3.5 提交证物到门

**POST** `/v1/evidence/{instance_id}/submit`

将证物提交到指定的门（Gate），用于影响门的结算结果。

**请求头**
| 头部 | 说明 |
|------|------|
| `X-User-ID` | 提交者用户ID |

**请求体**
```json
{
  "gate_instance_id": "gate_xxx"
}
```

**响应** `200 OK`
```json
{
  "submission_id": "uuid-xxx",
  "evidence_instance_id": "uuid-xxx",
  "gate_instance_id": "gate_xxx",
  "submitted_at": "2025-12-25T02:00:00Z",
  "message": "Evidence submitted successfully"
}
```

---

#### 1.3.6 创建交易挂单

**POST** `/v1/evidence/trade/offers`

创建一个证物出售挂单。

**请求头**
| 头部 | 说明 |
|------|------|
| `X-User-ID` | 卖家用户ID |

**请求体**
```json
{
  "evidence_instance_id": "uuid-xxx",
  "asking_price": 50.0,
  "currency": "SHARD",
  "duration_hours": 24
}
```

**响应** `200 OK`
```json
{
  "offer_id": "uuid-xxx",
  "seller_id": "user_001",
  "evidence_instance_id": "uuid-xxx",
  "asking_price": 50.0,
  "currency": "SHARD",
  "status": "OPEN",
  "created_at": "2025-12-25T01:00:00Z",
  "expires_at": "2025-12-26T01:00:00Z"
}
```

---

#### 1.3.7 获取交易挂单列表

**GET** `/v1/evidence/trade/offers`

获取当前开放的交易挂单。

**查询参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `theatre_id` | string | 否 | 按剧场筛选 |
| `tier` | string | 否 | 按证物等级筛选 |

**响应** `200 OK`
```json
[
  {
    "offer_id": "uuid-xxx",
    "seller_id": "user_001",
    "evidence_instance_id": "uuid-xxx",
    "asking_price": 50.0,
    "currency": "SHARD",
    "status": "OPEN",
    "created_at": "2025-12-25T01:00:00Z",
    "expires_at": "2025-12-26T01:00:00Z"
  }
]
```

---

#### 1.3.8 接受交易挂单

**POST** `/v1/evidence/trade/offers/{offer_id}/accept`

买家接受一个交易挂单，完成交易。

**请求体**
```json
{
  "buyer_id": "user_002"
}
```

**响应** `200 OK`
```json
{
  "success": true,
  "message": "交易完成，证物已转移"
}
```

---

#### 1.3.9 获取证物系统统计

**GET** `/v1/theatres/{theatre_id}/evidence/stats`

获取指定剧场的证物系统统计数据。

**响应** `200 OK`
```json
{
  "total_instances": 156,
  "by_tier": {
    "A": 5,
    "B": 23,
    "C": 78,
    "D": 50
  },
  "by_status": {
    "ACTIVE": 120,
    "SUBMITTED": 15,
    "EXPIRED": 10,
    "CONSUMED": 8,
    "TRADED": 3,
    "FORGED": 0
  },
  "active_offers": 12,
  "total_submissions": 45
}
```

---

## 第二部分：Rumor System（谣言系统）

### 2.1 系统概述

Rumor System 允许玩家创建、传播和验证"谣言"（UGC内容），这些谣言会影响舞台热度，进而影响排程器和内容工厂的决策。

**核心设计理念**：
- **UGC驱动**：玩家是信息的创造者，而非仅仅是接收者
- **信息博弈**：谣言有可信度评分，玩家需要判断真伪
- **世界影响**：广播的谣言会改变舞台热度，影响后续剧情
- **误读不是失败**：错误的谣言会产生"回声"，成为世界历史的一部分

---

### 2.2 数据模型

#### 2.2.1 核心枚举类型

```python
class RumorSource(str, Enum):
    """传闻来源类型"""
    EYEWITNESS = "EYEWITNESS"   # 目击 - 亲眼所见
    SECONDHAND = "SECONDHAND"   # 二手 - 从他人处获得
    INFERENCE = "INFERENCE"     # 推测 - 基于证物推断
    HEARSAY = "HEARSAY"         # 道听途说 - 未经证实

class RumorTone(str, Enum):
    """传闻语气/意图"""
    WARNING = "WARNING"         # 警告 - 提醒危险
    LURE = "LURE"               # 引诱 - 吸引前往
    INQUIRY = "INQUIRY"         # 求证 - 寻求确认
    REPORT = "REPORT"           # 报告 - 中性陈述
    SPECULATION = "SPECULATION" # 猜测 - 不确定推测

class RumorStatus(str, Enum):
    """传闻状态"""
    PRIVATE = "PRIVATE"         # 私藏
    SHARED = "SHARED"           # 已分享（给特定人/剧团）
    BROADCAST = "BROADCAST"     # 已广播（公开）
    VERIFIED_TRUE = "VERIFIED_TRUE"     # 已验证为真
    VERIFIED_FALSE = "VERIFIED_FALSE"   # 已验证为假（误读）
    EXPIRED = "EXPIRED"         # 已过期
    RETRACTED = "RETRACTED"     # 已撤回

class RumorCategory(str, Enum):
    """传闻类别"""
    LOCATION = "LOCATION"       # 地点相关
    CHARACTER = "CHARACTER"     # 人物相关
    EVENT = "EVENT"             # 事件相关
    OBJECT = "OBJECT"           # 物品相关
    PREDICTION = "PREDICTION"   # 预测类

class VerificationOutcome(str, Enum):
    """验证结果"""
    ACCURATE = "ACCURATE"       # 准确
    PARTIAL = "PARTIAL"         # 部分准确
    INACCURATE = "INACCURATE"   # 不准确
    MISLEADING = "MISLEADING"   # 误导性
    UNVERIFIABLE = "UNVERIFIABLE"  # 无法验证
```

#### 2.2.2 核心数据结构

**Rumor（谣言实例）**
```json
{
  "rumor_id": "uuid-xxx",
  "creator_id": "user_001",
  "theatre_id": "theatre_xxx",
  "content": "有人在外滩附近看到了神秘的闪光",
  "category": "LOCATION",
  "source": "EYEWITNESS",
  "tone": "WARNING",
  "based_on_evidence_ids": ["ev_001", "ev_002"],
  "based_on_scene_id": "scene_001",
  "related_stage_tags": ["bund", "pudong"],
  "status": "PRIVATE",
  "credibility_score": 0.7,
  "spread_count": 0,
  "view_count": 0,
  "influence_score": 0.0,
  "created_at": "2025-12-25T01:00:00Z",
  "expires_at": "2025-12-27T01:00:00Z",
  "broadcast_at": null,
  "verified_at": null,
  "verification_outcome": null,
  "is_misread": false,
  "misread_consequence": null,
  "echo_id": null
}
```

**RumorShare（分享记录）**
```json
{
  "share_id": "uuid-xxx",
  "rumor_id": "uuid-xxx",
  "from_user_id": "user_001",
  "to_user_id": "user_002",
  "to_crew_id": null,
  "shared_at": "2025-12-25T02:00:00Z",
  "is_broadcast": false
}
```

**MisreadEcho（误读回声）**
```json
{
  "echo_id": "uuid-xxx",
  "rumor_id": "uuid-xxx",
  "theatre_id": "theatre_xxx",
  "original_claim": "有人在外滩附近看到了神秘的闪光",
  "actual_truth": "那是一场烟火表演的测试",
  "deviation_type": "IDENTITY",
  "affected_stage_tags": ["bund", "pudong"],
  "consequence_description": "虚假警告导致区域被过度回避，资源开始积累",
  "world_var_changes": {
    "area_activity": -0.2,
    "resource_density": 0.1
  },
  "created_at": "2025-12-25T03:00:00Z",
  "resolved_at": null
}
```

**StageHeat（舞台热度）**
```json
{
  "stage_tag": "bund",
  "total_heat": 2.5,
  "contribution_count": 8,
  "tone_breakdown": {
    "WARNING": 1.2,
    "LURE": 0.8,
    "INQUIRY": 0.5
  }
}
```

---

### 2.3 API 接口规范

#### 2.3.1 创建谣言

**POST** `/v1/theatres/{theatre_id}/rumors`

创建一个新的谣言。

**请求头**
| 头部 | 说明 |
|------|------|
| `X-User-ID` | 创建者用户ID |

**请求体**
```json
{
  "content": "有人在外滩附近看到了神秘的闪光",
  "category": "LOCATION",
  "source": "EYEWITNESS",
  "tone": "WARNING",
  "based_on_evidence_ids": ["ev_001"],
  "based_on_scene_id": "scene_001",
  "related_stage_tags": ["bund", "pudong"],
  "expiry_hours": 48
}
```

**响应** `200 OK`
```json
{
  "rumor_id": "1f95d879-e3b6-4d3a-a0e5-09f9a5fe65c3",
  "creator_id": "test_user_001",
  "theatre_id": "bf15fc5a-b9fa-4a73-8b62-17ecd4af0a48",
  "content": "有人在外滩附近看到了神秘的闪光",
  "category": "LOCATION",
  "source": "EYEWITNESS",
  "tone": "WARNING",
  "status": "PRIVATE",
  "credibility_score": 0.7,
  "spread_count": 0,
  "view_count": 0,
  "influence_score": 0.0,
  "created_at": "2025-12-25T01:07:21.662746+00:00",
  "expires_at": "2025-12-27T01:07:21.662698+00:00",
  "is_misread": false,
  "verification_outcome": null
}
```

**可信度计算规则**：
- 基础可信度基于来源类型：
  - `EYEWITNESS`（目击）: 0.7
  - `INFERENCE`（推测）: 0.6
  - `SECONDHAND`（二手）: 0.5
  - `HEARSAY`（道听途说）: 0.3
- 每关联一个证物，可信度 +0.1（上限 +0.3）

---

#### 2.3.2 基于模板创建谣言

**POST** `/v1/theatres/{theatre_id}/rumors/from-template`

使用预定义模板创建谣言。

**请求头**
| 头部 | 说明 |
|------|------|
| `X-User-ID` | 创建者用户ID |

**请求体**
```json
{
  "template_id": "tmpl_location_sighting",
  "fill_values": {
    "location": "外滩",
    "subject": "神秘人影"
  },
  "source": "EYEWITNESS",
  "tone": "WARNING",
  "based_on_evidence_ids": ["ev_001"]
}
```

**可用模板**：
| 模板ID | 类别 | 模式 |
|--------|------|------|
| `tmpl_location_sighting` | LOCATION | "有人在{location}附近看到了{subject}" |
| `tmpl_event_prediction` | PREDICTION | "据说{time}会在{location}发生{event}" |
| `tmpl_character_action` | CHARACTER | "{character}似乎正在{action}" |
| `tmpl_object_discovery` | OBJECT | "在{location}发现了{object}的踪迹" |
| `tmpl_warning` | EVENT | "警告：{location}区域可能存在{danger}" |

---

#### 2.3.3 获取谣言详情

**GET** `/v1/rumors/{rumor_id}`

获取指定谣言的详细信息。每次访问会增加 `view_count`。

**响应** `200 OK`
```json
{
  "rumor_id": "uuid-xxx",
  "creator_id": "user_001",
  "theatre_id": "theatre_xxx",
  "content": "有人在外滩附近看到了神秘的闪光",
  "category": "LOCATION",
  "source": "EYEWITNESS",
  "tone": "WARNING",
  "status": "BROADCAST",
  "credibility_score": 0.65,
  "spread_count": 15,
  "view_count": 42,
  "influence_score": 0.58,
  "created_at": "2025-12-25T01:00:00Z",
  "expires_at": "2025-12-27T01:00:00Z",
  "is_misread": false,
  "verification_outcome": null
}
```

---

#### 2.3.4 获取广播谣言列表

**GET** `/v1/theatres/{theatre_id}/rumors/broadcast`

获取指定剧场的公开广播谣言，按影响力排序。

**查询参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `stage_tag` | string | 否 | 按舞台标签筛选 |
| `limit` | integer | 否 | 返回数量上限，默认 20 |

**响应** `200 OK`
```json
[
  {
    "rumor_id": "uuid-1",
    "creator_id": "user_001",
    "theatre_id": "theatre_xxx",
    "content": "有人在外滩附近看到了神秘的闪光",
    "category": "LOCATION",
    "source": "EYEWITNESS",
    "tone": "WARNING",
    "status": "BROADCAST",
    "credibility_score": 0.65,
    "spread_count": 15,
    "view_count": 42,
    "influence_score": 0.58,
    "created_at": "2025-12-25T01:00:00Z",
    "expires_at": "2025-12-27T01:00:00Z",
    "is_misread": false
  }
]
```

---

#### 2.3.5 获取用户创建的谣言

**GET** `/v1/users/{user_id}/rumors`

获取指定用户创建的所有谣言。

**查询参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `include_expired` | boolean | 否 | 是否包含已过期谣言，默认 `false` |

---

#### 2.3.6 分享谣言

**POST** `/v1/rumors/{rumor_id}/share`

将谣言分享给特定用户或剧团。

**请求头**
| 头部 | 说明 |
|------|------|
| `X-User-ID` | 分享者用户ID |

**请求体**
```json
{
  "to_user_id": "user_002",
  "to_crew_id": null
}
```

**响应** `200 OK`
```json
{
  "share_id": "uuid-xxx",
  "rumor_id": "uuid-xxx",
  "from_user_id": "user_001",
  "to_user_id": "user_002",
  "to_crew_id": null,
  "is_broadcast": false,
  "shared_at": "2025-12-25T02:00:00Z"
}
```

**副作用**：
- 谣言状态从 `PRIVATE` 变为 `SHARED`
- `spread_count` +1
- `credibility_score` -0.05（每次传播略微降低可信度）

---

#### 2.3.7 广播谣言

**POST** `/v1/rumors/{rumor_id}/broadcast`

将谣言公开广播（只有创建者可以广播）。

**请求头**
| 头部 | 说明 |
|------|------|
| `X-User-ID` | 广播者用户ID（必须是创建者） |

**响应** `200 OK`
```json
{
  "share_id": "uuid-xxx",
  "rumor_id": "uuid-xxx",
  "from_user_id": "user_001",
  "to_user_id": null,
  "to_crew_id": null,
  "is_broadcast": true,
  "shared_at": "2025-12-25T02:00:00Z"
}
```

**副作用**：
- 谣言状态变为 `BROADCAST`
- `spread_count` +10
- 更新关联舞台的热度

---

#### 2.3.8 验证谣言

**POST** `/v1/rumors/{rumor_id}/verify`

验证谣言的真实性（通常由系统或管理员调用）。

**请求头**
| 头部 | 说明 |
|------|------|
| `X-User-ID` | 验证者用户ID |

**请求体**
```json
{
  "actual_truth": "那是一场烟火表演的测试",
  "is_accurate": false,
  "deviation_type": "IDENTITY"
}
```

**响应** `200 OK`
```json
{
  "outcome": "INACCURATE",
  "echo_id": "uuid-xxx",
  "consequence": "虚假警告导致区域被过度回避，资源开始积累"
}
```

**误读后果计算**：
根据谣言的语气（tone）和传播程度计算后果：

| 语气 | 后果描述 | 世界变量影响 |
|------|----------|--------------|
| WARNING | 虚假警告导致区域被过度回避 | `area_activity` -0.2, `resource_density` +0.1 |
| LURE | 虚假引诱导致大量玩家涌入 | `area_activity` +0.3, `patrol_intensity` +0.2 |
| INQUIRY | 错误求证引发连锁调查 | `community_trust` -0.1 |
| REPORT | 错误报告被记录 | `information_noise` +0.1 |
| SPECULATION | 错误猜测成为流行观点 | `narrative_drift` +0.15 |

---

#### 2.3.9 添加反应

**POST** `/v1/rumors/{rumor_id}/reactions`

对谣言添加反应。

**请求头**
| 头部 | 说明 |
|------|------|
| `X-User-ID` | 用户ID |

**请求体**
```json
{
  "reaction_type": "BELIEVE",
  "comment": "我也看到了类似的情况"
}
```

**可用反应类型**：
| 类型 | 说明 | 可信度影响 |
|------|------|------------|
| `BELIEVE` | 相信 | +0.02 |
| `DOUBT` | 怀疑 | -0.02 |
| `INVESTIGATE` | 调查 | +0.01 |
| `SPREAD` | 传播 | +0.01 |
| `DEBUNK` | 辟谣 | -0.05 |

---

#### 2.3.10 获取舞台热度

**GET** `/v1/stages/{stage_tag}/heat`

获取指定舞台的热度详情。

**响应** `200 OK`
```json
{
  "stage_tag": "bund",
  "total_heat": 2.5,
  "contribution_count": 8,
  "tone_breakdown": {
    "WARNING": 1.2,
    "LURE": 0.8,
    "INQUIRY": 0.5
  }
}
```

---

#### 2.3.11 获取热度地图

**GET** `/v1/theatres/{theatre_id}/heat-map`

获取剧场的整体热度地图。

**响应** `200 OK`
```json
{
  "bund": 2.5,
  "pudong": 1.8,
  "jing_an": 0.5,
  "french_concession": 3.2
}
```

---

#### 2.3.12 获取谣言系统统计

**GET** `/v1/theatres/{theatre_id}/rumors/stats`

获取指定剧场的谣言系统统计数据。

**响应** `200 OK`
```json
{
  "total_rumors": 89,
  "by_status": {
    "PRIVATE": 23,
    "SHARED": 18,
    "BROADCAST": 35,
    "VERIFIED_TRUE": 8,
    "VERIFIED_FALSE": 3,
    "EXPIRED": 2,
    "RETRACTED": 0
  },
  "by_category": {
    "LOCATION": 32,
    "CHARACTER": 21,
    "EVENT": 18,
    "OBJECT": 12,
    "PREDICTION": 6
  },
  "total_spread": 456,
  "total_views": 2340,
  "misread_count": 3,
  "active_echoes": 3
}
```

---

## 第三部分：系统交互流程

### 3.1 证物获取与使用流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  观看场景    │────▶│  获得证物    │────▶│  持有证物    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
            │  验证证物    │            │  交易证物    │            │  提交到门    │
            └──────┬──────┘            └──────┬──────┘            └──────┬──────┘
                   │                          │                          │
                   ▼                          ▼                          ▼
            ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
            │ 确认真伪     │            │ 获得货币     │            │ 影响结算     │
            └─────────────┘            └─────────────┘            └─────────────┘
```

### 3.2 谣言传播与影响流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  创建谣言    │────▶│  私藏状态    │────▶│  分享/广播   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  更新热度    │
                                        └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
            │ 影响排程器   │            │ 影响内容工厂 │            │ 被验证       │
            └─────────────┘            └─────────────┘            └──────┬──────┘
                                                                         │
                                                        ┌────────────────┴────────────────┐
                                                        │                                 │
                                                        ▼                                 ▼
                                                 ┌─────────────┐                  ┌─────────────┐
                                                 │ 验证为真     │                  │ 验证为假     │
                                                 │ 可信度+0.2   │                  │ 产生回声     │
                                                 └─────────────┘                  └─────────────┘
```

---

## 第四部分：验收检查清单

### 4.1 Evidence System 检查项

| 功能 | 接口 | 状态 |
|------|------|------|
| 创建证物 | `POST /v1/theatres/{id}/evidence` | ✅ 已实现 |
| 获取证物详情 | `GET /v1/evidence/{id}` | ✅ 已实现 |
| 获取用户证物列表 | `GET /v1/users/{id}/evidence` | ✅ 已实现 |
| 验证证物 | `POST /v1/evidence/{id}/verify` | ✅ 已实现 |
| 提交证物到门 | `POST /v1/evidence/{id}/submit` | ✅ 已实现 |
| 创建交易挂单 | `POST /v1/evidence/trade/offers` | ✅ 已实现 |
| 获取交易挂单列表 | `GET /v1/evidence/trade/offers` | ✅ 已实现 |
| 接受交易挂单 | `POST /v1/evidence/trade/offers/{id}/accept` | ✅ 已实现 |
| 获取统计数据 | `GET /v1/theatres/{id}/evidence/stats` | ✅ 已实现 |

### 4.2 Rumor System 检查项

| 功能 | 接口 | 状态 |
|------|------|------|
| 创建谣言 | `POST /v1/theatres/{id}/rumors` | ✅ 已实现 |
| 基于模板创建谣言 | `POST /v1/theatres/{id}/rumors/from-template` | ✅ 已实现 |
| 获取谣言详情 | `GET /v1/rumors/{id}` | ✅ 已实现 |
| 获取广播谣言列表 | `GET /v1/theatres/{id}/rumors/broadcast` | ✅ 已实现 |
| 获取用户谣言列表 | `GET /v1/users/{id}/rumors` | ✅ 已实现 |
| 分享谣言 | `POST /v1/rumors/{id}/share` | ✅ 已实现 |
| 广播谣言 | `POST /v1/rumors/{id}/broadcast` | ✅ 已实现 |
| 验证谣言 | `POST /v1/rumors/{id}/verify` | ✅ 已实现 |
| 添加反应 | `POST /v1/rumors/{id}/reactions` | ✅ 已实现 |
| 获取舞台热度 | `GET /v1/stages/{tag}/heat` | ✅ 已实现 |
| 获取热度地图 | `GET /v1/theatres/{id}/heat-map` | ✅ 已实现 |
| 获取统计数据 | `GET /v1/theatres/{id}/rumors/stats` | ✅ 已实现 |

---

**文档版本**: v1.0  
**最后更新**: 2025-12-25  
**作者**: Manus AI
