# TheatreOS - 城市剧场操作系统

**版本**: 1.0.0  
**更新日期**: 2025年12月25日

## 项目概述

TheatreOS 是一个创新的城市实景互动剧场平台，将真实城市空间转化为多舞台虚拟剧场。玩家可以在城市中的各个"舞台"（真实地点）参与剧情演绎、投票押门、收集证物，体验沉浸式的城市探索游戏。

### 核心特性

- **多舞台并行**: 城市中的多个地点同时运行不同剧情
- **准点结算**: 每小时整点进行剧情门结算
- **Ring分级**: 基于地理位置的参与权限（Ring A/B/C）
- **证物系统**: 收集、验证、交易游戏内证物
- **剧团协作**: 玩家组建剧团，协作追证
- **回声归档**: 完整的剧情历史和个人档案

## 目录结构

```
theatreos/
├── frontend/                 # React前端应用
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   │   ├── Showbill.tsx     # 戏单页面
│   │   │   ├── StageLive.tsx    # 舞台观看
│   │   │   ├── GateLobby.tsx    # 门厅投票
│   │   │   ├── ExplainCard.tsx  # 结算展示
│   │   │   ├── Archive.tsx      # 回声归档
│   │   │   ├── Crew.tsx         # 剧团管理
│   │   │   ├── Map.tsx          # 城市地图
│   │   │   └── Profile.tsx      # 个人中心
│   │   ├── components/      # 通用组件
│   │   ├── services/        # API服务
│   │   ├── stores/          # 状态管理
│   │   └── types/           # 类型定义
│   └── dist/                # 构建产物
│
├── gateway/                  # API网关
│   └── src/
│       ├── main.py              # 主入口
│       ├── auth_routes.py       # 认证路由
│       ├── realtime_routes.py   # 实时推送
│       ├── storage_routes.py    # 存储服务
│       └── experience_loop_routes.py  # 体验闭环API
│
├── kernel/                   # 核心引擎
│   └── src/
│       ├── kernel_service.py    # 世界状态管理
│       ├── database.py          # 数据库模型
│       └── models.py            # 数据模型
│
├── scheduler/                # 调度器
│   └── src/
│       └── scheduler_service.py # 时段调度
│
├── gate/                     # 门系统
│   └── src/
│       └── gate_service.py      # 投票/下注/结算
│
├── location/                 # 位置服务
│   └── src/
│       └── location_service.py  # Ring评估/围栏
│
├── evidence/                 # 证物系统
│   └── src/
│       └── evidence_service.py  # 证物管理
│
├── crew/                     # 剧团系统
│   └── src/
│       └── crew_service.py      # 剧团管理
│
├── trace/                    # 追踪系统
│   └── src/
│       └── trace_service.py     # 用户行为追踪
│
├── rumor/                    # 谣言系统
│   └── src/
│       └── rumor_service.py     # 谣言传播
│
├── auth/                     # 认证系统
│   └── src/
│       ├── auth_service.py      # 用户认证
│       └── middleware.py        # 认证中间件
│
├── content_factory/          # 内容工厂
│   └── src/
│       ├── orchestrator.py      # 内容编排
│       ├── ai_generator.py      # AI生成
│       └── canon_guard.py       # 世界观守护
│
├── theme_pack/               # 主题包
│   ├── packs/                   # 主题包数据
│   └── src/                     # 主题包服务
│
├── test_mode/                # 测试模式
│   ├── api_routes.py            # 测试API
│   ├── test_config.py           # 测试配置
│   └── stages_config.py         # 舞台配置
│
├── config/                   # 配置文件
│   ├── settings.py              # 全局设置
│   └── service_registry.py      # 服务注册
│
├── db/                       # 数据库脚本
│   ├── 01_kernel.sql
│   ├── 02_scheduler.sql
│   └── ...
│
└── docs/                     # 文档
    └── EXPERIENCE_LOOP_DESIGN.md
```

## 技术栈

### 前端
- **React 18** + TypeScript
- **Vite** 构建工具
- **TailwindCSS** 样式框架
- **Framer Motion** 动画库
- **Zustand** 状态管理
- **Axios** HTTP客户端

### 后端
- **FastAPI** Web框架
- **SQLAlchemy** ORM
- **MySQL/TiDB** 数据库
- **Redis** 缓存（可选）
- **WebSocket** 实时通信

## 快速开始

### 环境要求
- Node.js 18+
- Python 3.10+
- MySQL 8.0+ 或 TiDB

### 前端开发
```bash
cd frontend
npm install
npm run dev
```

### 后端开发
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
cd backend
uvicorn gateway.src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 生产部署
```bash
# 构建前端
cd frontend && npm run build

# 部署到Nginx
cp -r dist/* /var/www/html/

# 启动后端服务
systemctl start theatreos-backend
```

## API文档

启动后端服务后，访问以下地址查看API文档：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 核心API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/theatres` | POST | 创建剧场 |
| `/v1/theatres/{id}/slots/next` | GET | 获取戏单 |
| `/v1/slots/{id}` | GET | 获取时段详情 |
| `/v1/gates/{id}` | GET | 获取门详情 |
| `/v1/gates/{id}/vote` | POST | 投票 |
| `/v1/gates/{id}/explain` | GET | 获取结算卡 |
| `/v1/users/me/archive` | GET | 获取用户档案 |
| `/v1/evidence-hunts/active` | GET | 获取追证任务 |
| `/v1/map/stages` | GET | 获取地图数据 |

## 体验闭环

TheatreOS 的核心体验闭环：

```
看戏 → 押门 → 结算 → 回声归档 → 追证 → 复访
  ↑                                      ↓
  └──────────────────────────────────────┘
```

1. **看戏**: 在戏单中选择舞台，观看当前场景
2. **押门**: 在门厅中投票或下注预测剧情走向
3. **结算**: 整点结算，查看ExplainCard了解结果
4. **回声归档**: 在档案中回顾历史，收集证物
5. **追证**: 参与追证任务，获取稀有证物
6. **复访**: 根据建议重访舞台，继续探索

## 测试模式

项目内置测试模式，可快速体验完整功能：

1. 点击右下角齿轮图标打开测试面板
2. 使用"快进时间"模拟时间流逝
3. 使用"触发结算"手动触发门结算
4. 使用"生成数据"创建测试场景

## 部署信息

当前生产环境：
- **服务器**: 阿里云ECS (120.55.162.182)
- **前端**: Nginx静态托管
- **后端**: Systemd管理的FastAPI服务
- **数据库**: 阿里云RDS MySQL

## 相关文档

- [体验闭环设计文档](docs/EXPERIENCE_LOOP_DESIGN.md)
- [测试模式设计文档](test_mode/TEST_MODE_DESIGN.md)
- [部署报告](TheatreOS_Deployment_Report.md)
- [主题包开发报告](Theme_Pack_Development_Report.md)
- [体验闭环开发报告](TheatreOS_Experience_Loop_Development_Report.md)

## 许可证

Copyright © 2025 TheatreOS Team. All rights reserved.
