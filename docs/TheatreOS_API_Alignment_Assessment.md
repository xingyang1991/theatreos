# TheatreOS API 对齐评估报告

**日期**: 2025-12-25  
**版本**: v1.2 → v1.3

---

## 一、补丁评估结论

**总体评价**: ✅ **补丁可用，建议直接应用**

提供的 `api.ts` 补丁文件质量较高，已经完成了以下关键工作：

1. **P0闭环API全部对齐** - Showbill、StageLive、GateLobby、证物选择
2. **字段适配器完整** - 包含 BE→FE 的类型映射函数
3. **兼容性设计** - 保留原有函数签名，内部实现改为调用新端点

---

## 二、后端已有端点 vs 前端补丁调用

### Slot系统

| 前端补丁调用 | 后端端点 | 状态 |
|-------------|---------|------|
| `GET /theatres/{id}/showbill` | ✅ 已有 | 匹配 |
| `GET /slots/{id}/details` | ✅ 已有 | 匹配 |
| `GET /slots/{id}/phase` | ✅ 已有 | 匹配 |
| `GET /theatres/{id}/current-slot` | ✅ 已有 | 匹配 |
| `GET /slots/{id}/gate` | ✅ 已有 | 匹配 |

### Gate系统

| 前端补丁调用 | 后端端点 | 状态 |
|-------------|---------|------|
| `GET /gates/{id}/lobby` | ✅ 已有 | 匹配 |
| `POST /gates/{id}/vote` | ✅ 已有 | 匹配 |
| `POST /gates/{id}/stake` | ✅ 已有 | 匹配 |
| `POST /gates/{id}/evidence` | ✅ 已有 | 匹配 |
| `GET /gates/{id}/explain` | ✅ 已有 | 匹配 |
| `GET /gates/{id}/participation` | ✅ 已有 | 匹配 |
| `POST /gates/{id}/claim-rewards` | ❌ 缺失 | 需补充 |

### Evidence系统

| 前端补丁调用 | 后端端点 | 状态 |
|-------------|---------|------|
| `GET /me/evidence` | ✅ 已有 | 匹配 |
| `GET /evidence/{id}` | ✅ 已有 | 匹配 |
| `POST /evidence/{id}/verify` | ✅ 已有 | 匹配 |

---

## 三、仍需后端补充的端点

### P0 必须（阻塞闭环）

| 端点 | 说明 | 优先级 |
|------|------|--------|
| `POST /gates/{id}/claim-rewards` | 领取奖励 | P0 |

### P1 近期功能

| 端点 | 说明 | 优先级 |
|------|------|--------|
| `POST /scenes/{id}/collect-evidence` | 场景收集证物 | P1 |
| `GET /users/me/archive` | 归档历史 | P1 |
| `GET /users/me/archive/stats` | 归档统计 | P1 |
| `GET /crews/mine` | 我的剧团 | P1 |
| `GET /storylines/mine` | 我的故事线 | P1 |

### P2 后续功能

| 端点 | 说明 | 优先级 |
|------|------|--------|
| WebSocket URL格式统一 | 前端用 `/ws/{theatreId}`，后端用 `?user_id=&theatre_id=` | P2 |
| Map相关API | `/map/stages`, `/map/regions` | P2 |

---

## 四、执行计划

### 步骤1: 后端补充缺失端点

需要在 `gate_routes.py` 中添加：
- `POST /gates/{id}/claim-rewards` - 领取奖励

### 步骤2: 应用前端补丁

将 `api_patch/TheatreOS_P0_api_ts_patch/frontend/src/services/api.ts` 覆盖到项目中。

### 步骤3: 部署并验证

1. 重新构建前端
2. 同步到服务器
3. 验证P0闭环

---

## 五、补丁亮点

### 适配器设计

补丁中的适配器函数设计合理：

```typescript
// 阶段映射
mapSlotPhaseFromBE(phase) -> 'watching' | 'gate_lobby' | 'settling' | 'echo'

// Gate类型映射
mapGateTypeFromBE(type) -> 'public' | 'fate' | 'council'

// 证物等级映射
mapEvidenceGradeFromBE(tier) -> 'A' | 'B' | 'C'
```

### 兼容性处理

- `gateApi.bet()` 内部调用 `/stake` 端点
- `gateApi.submitEvidence()` 支持批量提交（逐条调用后端）
- `evidenceApi.getMyEvidences()` 返回 `PaginatedResponse` 格式

### 错误处理

- 空数据时返回合理默认值
- 网络错误时不阻塞页面渲染

---

## 六、结论

**建议直接执行以下操作**：

1. ✅ 后端添加 `claim-rewards` 端点（约10分钟）
2. ✅ 应用前端 `api.ts` 补丁
3. ✅ 重新构建并部署
4. ✅ 验证P0闭环

补丁质量高，与后端v1.2路由高度匹配，可直接使用。
