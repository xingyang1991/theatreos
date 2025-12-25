# Crew System API 验收文档

**版本：** 1.0

**负责人：** Manus AI

---

## 1. 系统概述

Crew System (剧团系统) 允许玩家组建团队，进行协作、资源共享和集体行动，是 TheatreOS 社交和组织玩法的核心。

## 2. 数据模型 (Data Models)

### Crew (剧团)

```json
{
  "crew_id": "uuid",
  "theatre_id": "uuid",
  "name": "string",
  "tag": "string (3-5 chars)",
  "tier": "integer (1-5)",
  "reputation": "integer",
  "member_count": "integer",
  "is_public": "boolean",
  "created_at": "datetime"
}
```

### CrewMember (剧团成员)

```json
{
  "member_id": "uuid",
  "crew_id": "uuid",
  "user_id": "string",
  "role": "CrewRole (Enum)",
  "status": "MemberStatus (Enum)",
  "contribution": "integer",
  "joined_at": "datetime"
}
```

### Enums

-   `CrewRole`: `LEADER`, `OFFICER`, `MEMBER`, `RECRUIT`
-   `MemberStatus`: `ACTIVE`, `INACTIVE`, `BANNED`

## 3. API 接口规范 (OpenAPI)

### `POST /v1/theatres/{theatre_id}/crews`

-   **说明**: 创建一个新的剧团。
-   **请求体**: `{"name": "...", "tag": "..."}`
-   **响应**: `200 OK` - 返回创建的 `Crew` 对象。

### `GET /v1/crews/{crew_id}`

-   **说明**: 获取剧团详情。
-   **响应**: `200 OK` - 返回 `Crew` 对象。

### `POST /v1/crews/{crew_id}/invite`

-   **说明**: 邀请一个用户加入剧团。
-   **Query**: `?invitee_id=...`
-   **响应**: `200 OK` - 返回新的 `CrewMember` 对象。

### `GET /v1/crews/{crew_id}/members`

-   **说明**: 获取剧团成员列表。
-   **响应**: `200 OK` - 返回 `CrewMember` 对象列表。

### `POST /v1/crews/{crew_id}/actions`

-   **说明**: 发起一个集体行动。
-   **请求体**: `{"action_type": "...", "title": "..."}`
-   **响应**: `200 OK` - 返回创建的 `CrewAction` 对象。

### `POST /v1/crews/{crew_id}/shares`

-   **说明**: 在剧团内共享一个资源（如证物）。
-   **请求体**: `{"share_type": "...", "resource_id": "..."}`
-   **响应**: `200 OK` - 返回创建的 `CrewShare` 对象。

## 4. 验收检查清单

| 接口 | 状态 | 测试用例 |
|---|---|---|
| `POST /v1/theatres/{theatre_id}/crews` | ✅ 已实现 | 用户A创建一个剧团 |
| `GET /v1/crews/{crew_id}` | ✅ 已实现 | 获取该剧团的详情 |
| `POST /v1/crews/{crew_id}/invite` | ✅ 已实现 | 用户A邀请用户B加入 |
| `GET /v1/crews/{crew_id}/members` | ✅ 已实现 | 检查成员列表是否包含用户A和B |
| `POST /v1/crews/{crew_id}/actions` | ✅ 已实现 | 用户A发起一个“共享”行动 |
| `POST /v1/crews/{crew_id}/shares` | ✅ 已实现 | 用户B共享一个证物 |
| `POST /v1/crews/shares/{share_id}/claim` | ✅ 已实现 | 用户A领取该证物 |
| `GET /v1/crews/{crew_id}/stats` | ✅ 已实现 | 检查剧团统计数据是否更新 |
