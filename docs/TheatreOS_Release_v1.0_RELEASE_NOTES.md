# TheatreOS v1.0 发布说明

**发布日期**: 2025年12月25日  
**版本号**: 1.0.0

---

## 概述

TheatreOS v1.0 是城市剧场操作系统的首个完整可用版本，包含完整的前后端代码、设计文档和部署配置。

## 包含内容

### 1. 后端代码 (`backend/`)

| 模块 | 说明 |
|------|------|
| `gateway/` | API网关，统一入口 |
| `kernel/` | 核心引擎，世界状态管理 |
| `scheduler/` | 时段调度器 |
| `gate/` | 门系统（投票/下注/结算） |
| `location/` | 位置服务（Ring评估/围栏） |
| `evidence/` | 证物系统 |
| `crew/` | 剧团系统 |
| `trace/` | 追踪系统 |
| `rumor/` | 谣言系统 |
| `auth/` | 认证系统 |
| `storage/` | 存储服务 |
| `content_factory/` | 内容工厂（AI生成） |
| `theme_pack/` | 主题包系统 |
| `test_mode/` | 测试模式 |
| `analytics/` | 数据分析 |
| `liveops/` | 运营工具 |
| `safety/` | 安全审核 |
| `admin/` | 管理后台 |
| `config/` | 配置文件 |
| `db/` | 数据库脚本 |

### 2. 前端代码 (`frontend/`)

| 目录/文件 | 说明 |
|-----------|------|
| `src/pages/` | 页面组件 |
| `src/components/` | 通用组件 |
| `src/services/` | API服务 |
| `src/stores/` | 状态管理 |
| `src/types/` | 类型定义 |
| `dist/` | 构建产物（可直接部署） |

### 3. 文档 (`docs/`)

| 文档 | 说明 |
|------|------|
| `EXPERIENCE_LOOP_DESIGN.md` | 体验闭环设计文档 |
| `TEST_MODE_DESIGN.md` | 测试模式设计文档 |
| `TheatreOS_Deployment_Report.md` | 部署报告 |
| `Theme_Pack_Development_Report.md` | 主题包开发报告 |
| `TheatreOS_Experience_Loop_Development_Report.md` | 体验闭环开发报告 |

### 4. 部署配置 (`deploy/`)

| 文件 | 说明 |
|------|------|
| `backend.env` | 后端环境变量模板 |
| `theatreos-backend.service` | Systemd服务配置 |
| `theatreos.nginx.conf` | Nginx配置 |

## 核心功能

### 已实现功能

- ✅ **戏单系统**: 今日戏单展示，多舞台并行
- ✅ **舞台观看**: 实时场景内容推送
- ✅ **门厅投票**: 投票/下注/押门机制
- ✅ **结算系统**: 整点结算，ExplainCard展示
- ✅ **回声归档**: 历史记录，证物收集
- ✅ **剧团系统**: 剧团创建，成员管理
- ✅ **追证任务**: 追证任务分配与完成
- ✅ **城市地图**: 舞台地图，区域筛选
- ✅ **测试模式**: 时间快进，手动结算
- ✅ **主题包**: 哈利波特主题包

### 体验闭环

```
看戏 → 押门 → 结算 → 回声归档 → 追证 → 复访
```

## 部署指南

### 快速部署

1. **解压文件**
   ```bash
   tar -xzvf TheatreOS_Release_v1.0.tar.gz
   cd TheatreOS_Release_v1.0
   ```

2. **部署前端**
   ```bash
   cp -r frontend/dist/* /var/www/html/
   ```

3. **部署后端**
   ```bash
   # 安装依赖
   pip install -r backend/requirements.txt
   
   # 配置环境变量
   cp deploy/backend.env /opt/theatreos/.env
   
   # 启动服务
   cp deploy/theatreos-backend.service /etc/systemd/system/
   systemctl enable theatreos-backend
   systemctl start theatreos-backend
   ```

4. **配置Nginx**
   ```bash
   cp deploy/theatreos.nginx.conf /etc/nginx/sites-available/theatreos
   ln -s /etc/nginx/sites-available/theatreos /etc/nginx/sites-enabled/
   systemctl restart nginx
   ```

### 开发环境

```bash
# 前端开发
cd frontend
npm install
npm run dev

# 后端开发
cd backend
pip install -r requirements.txt
uvicorn gateway.src.main:app --reload
```

## 当前部署

- **服务器**: 阿里云ECS (120.55.162.182)
- **访问地址**: http://120.55.162.182/

## 技术栈

- **前端**: React 18 + TypeScript + Vite + TailwindCSS
- **后端**: FastAPI + SQLAlchemy + MySQL
- **部署**: Nginx + Systemd

## 联系方式

如有问题，请联系 TheatreOS 开发团队。

---

*TheatreOS - 让城市成为你的剧场*
