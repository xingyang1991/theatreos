# TheatreOS v1.3-alpha Release Notes

**版本:** v1.3-alpha  
**发布日期:** 2025-12-26  
**代号:** E2E 体验闭环版本

## 版本概述

TheatreOS v1.3-alpha 是一个重要的里程碑版本，实现了核心 E2E (End-to-End) 体验闭环。本版本完成了 "看戏→押门→结算" 核心流程的前后端 API 对齐，并提供了完整的演示功能。

## 主要更新

### 核心功能

1. **E2E 体验闭环**
   - 完成 Showbill (戏单) 页面与后端 API 对齐
   - 完成 StageLive (舞台直播) 页面与后端 API 对齐
   - 完成 GateLobby (门厅) 页面与后端 API 对齐
   - 完成 ExplainCard (解释卡) API 对齐

2. **Gate 系统**
   - 支持投票功能 (`/v1/gates/{id}/vote`)
   - 支持下注功能 (`/v1/gates/{id}/stake`)
   - 支持解释卡查询 (`/v1/gates/{id}/explain`)
   - 支持门状态查询 (`/v1/gates/{id}/lobby`)

3. **Demo 管理**
   - 新增 `demo-cycle` API 一键创建演示数据
   - 新增 `demo-full-cycle` API 完整演示流程
   - 支持 Test Mode 事件触发

### 前端页面

| 页面 | 状态 | 数据来源 |
|------|------|----------|
| Showbill | ✅ 完成 | 真实 API |
| StageLive | ✅ 完成 | 真实 API |
| GateLobby | ✅ 完成 | 真实 API |
| Archive | ✅ UI完成 | 模拟数据 |
| Crew | ✅ UI完成 | 模拟数据 |
| Map | ✅ UI完成 | 模拟数据 |

### 数据包

- HP Shanghai 200 数据包已集成
- 包含 8 个舞台、多条故事线
- 支持哈利波特主题内容

## 已知问题

1. Archive, Crew, Map 页面尚未与后端 API 对齐，使用模拟数据
2. `slot_id` 格式在占位数据和真实数据之间存在不一致
3. 部分 API 路径前端与后端不匹配（如 `/v1/me/crew` vs `/v1/users/{id}/crew`）

## 文件结构

```
theatreos_v1.3_release/
├── RELEASE_NOTES_v1.3.md    # 本文件
├── code/                     # 源代码
│   ├── frontend/            # 前端代码 (React + TypeScript)
│   ├── gateway/             # API 网关
│   ├── kernel/              # 核心引擎
│   ├── gate/                # 门系统
│   ├── scheduler/           # 调度器
│   ├── content_factory/     # 内容工厂
│   ├── theme_pack/          # 主题包
│   ├── data_packs/          # 数据包
│   └── ...
└── docs/                     # 文档
    ├── M1_Completion_Report.md
    ├── M2_Completion_Report.md
    ├── M3_Completion_Report.md
    ├── M4_Completion_Report.md
    ├── TheatreOS_E2E_Loop_Development_Report.md
    ├── theatreos_e2e_test_report.md
    └── ...
```

## 部署说明

### 后端部署

```bash
cd code
pip install -r requirements.txt
cd gateway/src
python main.py
```

### 前端部署

```bash
cd code/frontend
npm install
npm run build
# 将 dist 目录部署到 Web 服务器
```

## 测试验证

访问 http://120.55.162.182 可查看当前部署的版本。

### 快速测试

1. 访问首页查看戏单
2. 点击舞台卡片进入直播页面
3. 访问 `/gate-lobby/W1_D4_1700` 查看门厅
4. 使用 Admin API 创建演示数据：
   ```
   POST /v1/admin/theatres/{theatre_id}/demo-cycle
   ```

## 下一步计划

1. 完成 Archive, Crew, Map 的后端 API 对齐
2. 统一 slot_id 生成逻辑
3. 添加更多主题包和数据包
4. 优化性能和用户体验

---

**TheatreOS Team**  
2025-12-26
