# TheatreOS 体验闭环设计

## 一、完整体验流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TheatreOS 体验闭环                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Showbill │───▶│StageLive │───▶│GateLobby │───▶│ExplainCard│          │
│  │  戏单    │    │ 看戏     │    │ 押门     │    │ 结算     │          │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘          │
│       ▲                                               │                 │
│       │                                               ▼                 │
│  ┌────┴─────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │   Map    │◀───│   Crew   │◀───│ Archive  │◀───│  回声    │          │
│  │  导航    │    │ 追证     │    │ 归档     │    │ 生成     │          │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 二、各页面功能定义

### 1. ExplainCard（结算展示页）

**触发时机**: 门结算完成后自动跳转或从Archive进入

**核心功能**:
- 展示门的最终结果（哪个选项胜出）
- 显示用户的投票/下注结果
- 计算并展示收益/损失
- 生成"回声"（Echo）记录
- 提供证物奖励预览
- 引导进入Archive归档

**数据结构**:
```typescript
interface ExplainCardData {
  gate_id: string;
  gate_title: string;
  gate_type: 'plot' | 'lore' | 'meta';
  
  // 结果
  winning_option: {
    option_id: string;
    text: string;
    final_odds: number;
  };
  
  // 用户参与
  user_participation: {
    voted_option: string | null;
    bet_option: string | null;
    bet_amount: number;
    submitted_evidences: string[];
  };
  
  // 收益
  rewards: {
    tickets_won: number;
    tickets_lost: number;
    net_change: number;
    evidence_bonus: number;
    new_evidences: Evidence[];
  };
  
  // 回声
  echo: {
    echo_id: string;
    summary: string;
    impact_description: string;
    world_state_changes: Record<string, number>;
  };
}
```

### 2. Archive（回声归档页）

**核心功能**:
- 展示用户参与过的所有门的历史记录
- 按时间线/故事线分类展示
- 证物收集进度
- 故事线完成度
- 世界观变化追踪

**数据结构**:
```typescript
interface ArchiveData {
  // 回声历史
  echoes: {
    echo_id: string;
    gate_title: string;
    timestamp: Date;
    result: 'win' | 'lose' | 'neutral';
    summary: string;
    thread_id: string;
  }[];
  
  // 证物收集
  evidence_collection: {
    total_collected: number;
    by_type: Record<string, number>;
    rare_count: number;
    completion_rate: number;
  };
  
  // 故事线进度
  thread_progress: {
    thread_id: string;
    thread_name: string;
    progress: number; // 0-100
    key_moments: string[];
  }[];
  
  // 统计
  stats: {
    total_gates_participated: number;
    win_rate: number;
    total_tickets_earned: number;
    favorite_thread: string;
  };
}
```

### 3. Crew（剧团/追证页）

**核心功能**:
- 剧团（小队）管理
- 证物追踪任务
- 协作投票
- 复访引导（基于未完成的证物线索）

**数据结构**:
```typescript
interface CrewData {
  // 我的剧团
  my_crew: {
    crew_id: string;
    name: string;
    members: {
      user_id: string;
      username: string;
      ring: RingLevel;
      role: 'leader' | 'member';
    }[];
    active_missions: string[];
  } | null;
  
  // 追证任务
  evidence_hunts: {
    hunt_id: string;
    target_evidence_type: string;
    hint: string;
    related_stage: string;
    related_thread: string;
    progress: number;
    expires_at: Date;
  }[];
  
  // 复访建议
  revisit_suggestions: {
    stage_id: string;
    stage_name: string;
    reason: string; // "有未收集的证物" | "故事线有新发展" | "限时事件"
    priority: 'high' | 'medium' | 'low';
  }[];
}
```

### 4. Map（地图页）

**核心功能**:
- 显示所有舞台位置
- 当前位置标记
- 舞台状态（活跃/休息）
- 导航功能
- 区域热度显示

**数据结构**:
```typescript
interface MapData {
  stages: {
    stage_id: string;
    name: string;
    location: {
      lat: number;
      lng: number;
      address: string;
    };
    status: 'active' | 'upcoming' | 'ended';
    current_scene: string | null;
    heat_level: number; // 0-100 热度
    distance: number; // 距离用户的米数
  }[];
  
  user_location: {
    lat: number;
    lng: number;
  } | null;
  
  regions: {
    name: string;
    stage_count: number;
    center: { lat: number; lng: number };
  }[];
}
```

## 三、后端API设计

### ExplainCard API
```
GET /v1/gates/{gate_id}/explain
Response: ExplainCardData

POST /v1/gates/{gate_id}/claim-rewards
Response: { success: boolean, rewards: Rewards }
```

### Archive API
```
GET /v1/users/me/archive
Query: ?page=1&limit=20&thread_id=xxx
Response: ArchiveData

GET /v1/users/me/archive/stats
Response: ArchiveStats

GET /v1/users/me/archive/echoes/{echo_id}
Response: EchoDetail
```

### Crew API
```
GET /v1/crews/my
Response: CrewData

POST /v1/crews
Body: { name: string }
Response: Crew

POST /v1/crews/{crew_id}/invite
Body: { user_id: string }

GET /v1/evidence-hunts/active
Response: EvidenceHunt[]

GET /v1/revisit-suggestions
Response: RevisitSuggestion[]
```

### Map API
```
GET /v1/map/stages
Query: ?lat=xxx&lng=xxx&radius=5000
Response: MapData

GET /v1/map/regions
Response: Region[]
```

## 四、页面跳转逻辑

```
GateLobby (门结算触发)
    │
    ▼
ExplainCard (展示结果)
    │
    ├──▶ "查看档案" ──▶ Archive
    │
    └──▶ "继续探索" ──▶ Showbill
    
Archive
    │
    ├──▶ "查看回声详情" ──▶ ExplainCard (历史)
    │
    ├──▶ "追踪证物" ──▶ Crew
    │
    └──▶ "前往舞台" ──▶ Map ──▶ StageLive

Crew
    │
    ├──▶ "接受任务" ──▶ Map (导航到目标舞台)
    │
    └──▶ "查看进度" ──▶ Archive
```

## 五、测试模式支持

为支持快速测试，需要在测试模式下：
1. 加速门结算（可配置的结算时间）
2. 模拟门结果（手动触发胜负）
3. 快速生成回声
4. 模拟证物掉落
5. 重置用户档案数据
