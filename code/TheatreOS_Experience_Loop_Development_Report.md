# TheatreOS 体验闭环开发报告

**版本**: 1.0
**日期**: 2025年12月25日
**作者**: Manus AI

## 1. 项目概述

本次任务旨在完成 TheatreOS 平台的核心体验闭环。根据您的评估，平台在完成“看戏 → 押门”流程后中断，缺失了“准点结算 → 解释卡 → 回声归档 → 追证驱动复访”的关键环节。本报告将详细阐述为弥补此缺口所完成的开发工作。

## 2. 状态评估确认

我们首先对您提供的7个核心页面的实现状态进行了代码级审查，结果完全证实了您的评估。`Showbill`、`StageLive` 和 `GateLobby` 功能完整，而 `ExplainCard`、`Archive`、`Crew` 和 `Map` 页面均为占位符，`Profile` 页面功能非常基础。这明确了体验闭环的断点位于 `GateLobby` 之后。

## 3. 体验闭环设计与实现

为构建完整的体验闭环，我们设计并开发了以下四个核心页面，并为它们提供了相应的后端模拟API支持。

### 3.1. 设计文档

我们首先创建了详细的设计文档 `docs/EXPERIENCE_LOOP_DESIGN.md`，其中定义了新页面的功能、数据结构、API接口和页面跳转逻辑，为后续开发提供了清晰的蓝图。

### 3.2. 页面开发

我们从零开始，将所有占位符页面替换为功能完整的React组件，并集成了丰富的UI元素和交互动效，以提供高质量的用户体验。

| 开发页面 | 文件路径 | 功能简介 |
| :--- | :--- | :--- |
| **ExplainCard** | `frontend/src/pages/ExplainCard.tsx` | 展示门的结算结果、用户收益、新获证物和剧情“回声”。 |
| **Archive** | `frontend/src/pages/Archive.tsx` | 提供历史回声、证物收集、故事线进度和个人统计的查询。 |
| **Crew** | `frontend/src/pages/Crew.tsx` | 支持剧团创建与管理、协作追证任务和智能复访建议。 |
| **Map** | `frontend/src/pages/Map.tsx` | 以列表和地图两种模式展示所有舞台，并提供导航和状态筛选。 |

### 3.3. 后端API开发（模拟）

为支持新页面的功能，我们在后端网关中添加了新的路由文件 `gateway/src/experience_loop_routes.py`，其中包含了所有必要的API端点。**请注意，当前这些API返回的是预置的模拟数据**，以便于前端独立开发和测试。您需要根据设计文档中的数据结构，将其对接到真实的数据库和游戏逻辑中。

**新增API端点列表**:

| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `GET` | `/v1/gates/{gate_id}/explain` | 获取结算卡详情 |
| `GET` | `/v1/users/me/archive` | 获取用户完整档案 |
| `GET` | `/v1/evidence-hunts/active` | 获取活跃的追证任务 |
| `GET` | `/v1/revisit-suggestions` | 获取复访建议 |
| `GET` | `/v1/map/stages` | 获取地图舞台数据 |

### 3.4. 前后端集成

我们更新了前端的API服务文件 `frontend/src/services/api.ts`，添加了调用上述新API的方法，并确保所有新页面都通过这些服务方法获取数据。前端路由 `frontend/src/App.tsx` 也已配置正确，确保用户可以流畅地在各个页面间跳转。

## 4. 部署与测试

我们已将更新后的前端应用成功构建，并打包了所有相关产物。您可以通过以下步骤在您的服务器上部署本次更新。

### 4.1. 部署包

所有开发产物，包括前端构建文件、源代码和设计文档，都已打包在 `/home/ubuntu/theatreos_experience_loop_update.tar.gz` 中。

### 4.2. 部署步骤

1.  **解压部署包**: 在服务器上，将部署包解压到您的项目根目录。

    ```bash
    tar -xzvf /home/ubuntu/theatreos_experience_loop_update.tar.gz -C /home/ubuntu/aliyun_deploy/
    ```

2.  **更新前端文件**: 将解压后的 `frontend/dist` 目录覆盖您现有的前端部署目录。

    ```bash
    # 假设您的Nginx指向 /var/www/html
    sudo rm -rf /var/www/html/*
    sudo cp -r /home/ubuntu/aliyun_deploy/frontend/dist/* /var/www/html/
    ```

3.  **更新后端代码**: 将 `gateway/src/experience_loop_routes.py` 文件复制到您的后端源码目录，并在 `main.py` 中引入和注册这个新的路由模块。

    ```python
    # 在 main.py 中添加
    from gateway.src.experience_loop_routes import router as experience_loop_router
    
    app.include_router(experience_loop_router)
    ```

4.  **重启服务**: 重启您的后端FastAPI服务和Nginx，使更改生效。

    ```bash
    # 重启FastAPI (假设使用pm2)
    pm2 restart theatreos-backend
    
    # 重启Nginx
    sudo systemctl restart nginx
    ```

## 5. 结论与后续步骤

通过本次开发，TheatreOS平台已具备完整的核心体验闭环。用户现在可以从观看场景、参与押门，到查看结算、回顾历史、收集证物，并根据系统建议再次访问舞台，形成了一个可持续的游戏循环。

**后续建议**:

- **对接真实数据**: 将后端模拟API替换为对数据库和游戏逻辑的真实调用。
- **完善个人中心**: 开发 `Profile` 页面，增加玩家成长、票券钱包、权限管理等功能。
- **压力测试**: 对完整的体验闭环进行压力测试，确保在高并发下的稳定运行。

我们相信，这些更新将极大地提升TheatreOS的趣味性和可玩性。
