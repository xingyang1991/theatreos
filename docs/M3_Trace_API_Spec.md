# Trace System API 验收文档

**版本：** 1.0

**负责人：** Manus AI

---

## 1. 系统概述

Trace System (痕迹系统) 负责记录玩家在游戏世界中的关键行为，并将其转化为可被其他玩家发现的“痕迹”。这些痕迹是动态的，会随时间衰减，并能影响区域的氛围。

## 2. 数据模型 (Data Models)

### Trace (痕迹)

```json
{
  "trace_id": "uuid",
  "theatre_id": "uuid",
  "creator_id": "string",
  "trace_type": "TraceType (Enum)",
  "stage_id": "string",
  "stage_tag": "string",
  "status": "TraceStatus (Enum)",
  "visibility": "TraceVisibility (Enum)",
  "intensity": "float (0.0-1.0)",
  "decay_rate": "float (0.0-1.0)",
  "discovery_difficulty": "float (0.0-1.0)",
  "discovery_count": "integer",
  "description": "string",
  "created_at": "datetime",
  "expires_at": "datetime"
}
```

### Enums

-   `TraceType`: `VISIT`, `OBSERVE`, `VOTE`, `TRADE`, `RUMOR`, `DISCOVER`, `SUBMIT`, `CREW_ACTION`
-   `TraceStatus`: `ACTIVE`, `FADED`, `DISCOVERED`
-   `TraceVisibility`: `PUBLIC`, `RING_A`, `RING_B`, `CREW_ONLY`

## 3. API 接口规范 (OpenAPI)

### `POST /v1/theatres/{theatre_id}/traces`

-   **说明**: 留下一个痕迹。
-   **请求体**: `{"trace_type": "...", "stage_id": "...", ...}`
-   **响应**: `200 OK` - 返回创建的 `Trace` 对象。

### `GET /v1/traces/{trace_id}`

-   **说明**: 获取痕迹详情。
-   **响应**: `200 OK` - 返回 `Trace` 对象。

### `POST /v1/traces/{trace_id}/discover`

-   **说明**: 尝试发现一个痕迹。
-   **请求体**: `{"method": "...", "discoverer_ring": "..."}`
-   **响应**: `200 OK` - 返回 `Discovery` 对象，并可能附带生成的 `Evidence` 信息。

### `GET /v1/stages/{stage_id}/density`

-   **说明**: 获取一个舞台的痕迹密度。
-   **响应**: `200 OK` - 返回 `StageDensity` 对象。

### `GET /v1/users/{user_id}/trace-profile`

-   **说明**: 获取用户的痕迹档案。
-   **响应**: `200 OK` - 返回 `UserTraceProfile` 对象。

## 4. 验收检查清单

| 接口 | 状态 | 测试用例 |
|---|---|---|
| `POST /v1/theatres/{theatre_id}/traces` | ✅ 已实现 | 创建一个 `VOTE` 类型的痕迹 |
| `GET /v1/traces/{trace_id}` | ✅ 已实现 | 获取刚刚创建的痕迹详情 |
| `POST /v1/traces/{trace_id}/discover` | ✅ 已实现 | 另一个用户尝试发现该痕迹 |
| `GET /v1/stages/{stage_id}/density` | ✅ 已实现 | 检查舞台的痕迹密度是否增加 |
| `GET /v1/users/{user_id}/trace-profile` | ✅ 已实现 | 检查两个用户的痕迹档案是否更新 |
