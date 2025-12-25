# TheatreOS 测试模式控制面板设计

## 架构概述

```
┌─────────────────────────────────────────────────────────────┐
│                    前端测试控制面板                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 模式切换    │  │ 参数调整    │  │ 快捷预设    │         │
│  │ (开关)      │  │ (滑块/输入) │  │ (一键按钮)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    后端测试模式API                           │
│  GET  /v1/test-mode/status     - 获取当前状态               │
│  PUT  /v1/test-mode/toggle     - 切换测试模式               │
│  PUT  /v1/test-mode/config     - 更新配置参数               │
│  POST /v1/test-mode/preset     - 应用预设配置               │
│  POST /v1/test-mode/reset      - 重置测试数据               │
│  POST /v1/test-mode/trigger    - 手动触发事件               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    测试模式配置存储                          │
│  - 内存存储 (快速访问)                                       │
│  - 文件持久化 (可选)                                         │
│  - 预设模板库                                                │
└─────────────────────────────────────────────────────────────┘
```

## 功能模块

### 1. 模式切换
- 一键开启/关闭测试模式
- 显示当前模式状态
- 模式切换时自动应用对应配置

### 2. 参数调整
- 时间参数：场景切换、事件触发、投票时长
- 游戏参数：积分倍率、掉落率、升级门槛
- 位置参数：Ring范围、位置检查开关

### 3. 快捷预设
- 快速测试：最短时间间隔
- 演示模式：适合展示的参数
- 压力测试：高频事件触发
- 生产模式：正式运营参数

### 4. 扩展接口
- 自定义预设保存/加载
- 事件手动触发
- 数据重置与导出

## 预设配置

### 快速测试 (quick_test)
```json
{
  "scene_switch_interval": 15,
  "event_trigger_interval": 10,
  "vote_duration": 30,
  "skip_location_check": true,
  "fast_ring_upgrade": true
}
```

### 演示模式 (demo)
```json
{
  "scene_switch_interval": 60,
  "event_trigger_interval": 30,
  "vote_duration": 90,
  "skip_location_check": true,
  "auto_events_enabled": true
}
```

### 压力测试 (stress_test)
```json
{
  "scene_switch_interval": 5,
  "event_trigger_interval": 3,
  "vote_duration": 15,
  "world_var_change_multiplier": 10.0
}
```

### 生产模式 (production)
```json
{
  "scene_switch_interval": 300,
  "event_trigger_interval": 120,
  "vote_duration": 180,
  "skip_location_check": false,
  "test_mode_enabled": false
}
```
