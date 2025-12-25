# TheatreOS 主题包系统开发报告

**版本:** 1.0
**日期:** 2025年12月25日
**作者:** Manus AI

## 1. 项目概述

本次开发的核心目标是实现 TheatreOS 剧本内容的动态加载与管理能力，将原本硬编码在系统中的世界观设定（如角色、故事线、规则等）外部化、模块化，形成可随时替换的“主题包”（Theme Pack）。该功能的实现，是 TheatreOS 从单一剧本应用迈向可扩展内容平台的关键一步。

开发工作主要围绕以下几个方面展开：

- **标准化数据结构**：基于您提供的内容规划材料，设计了一套标准化的主题包数据结构。
- **开发管理模块**：构建了全新的主题包管理服务，负责主题包的加载、验证、查询和切换。
- **重构核心组件**：对内容生成的核心模块 `CanonGuard`（连续性编译器）进行了重构，使其能够从静态规则转向动态加载主题包规则。
- **创建主题包**：将现有的“哈利波特·上海魔法界”内容完整迁移至新的主题包格式。
- **提供API接口**：开放了一套完整的 RESTful API，用于管理和查询主题包内容。

## 2. 功能实现

### 2.1. 主题包结构

我们定义了一套标准化的主题包目录结构，以 `hp_shanghai_s1` 为例：

```
/opt/theatreos/theme_pack/packs/hp_shanghai_s1/
├── manifest.json         # 主题包清单文件，包含元数据和文件索引
├── characters.json       # 角色白名单
├── threads.json          # 故事线定义
├── beats.json            # 拍子模板库
├── gates.json            # 门模板库
├── evidence.json         # 证物类型库
├── world_variables.json  # 世界变量定义
├── objects.json          # 关键物品白名单
├── factions.json         # 阵营定义
└── rescue_beats.json     # 救援拍子库
```

这种结构使得每个主题包都是一个自包含的、可独立分发的单元。

### 2.2. 核心服务与模块

| 模块/服务 | 位置 | 核心职责 |
| :--- | :--- | :--- |
| **ThemePackLoader** | `theme_pack/src/loader.py` | 从文件系统加载、解析和验证主题包数据。 |
| **ThemePackManager** | `theme_pack/src/manager.py` | 管理内存中的主题包，处理剧场与主题包的绑定关系，提供数据查询接口。 |
| **ThemePack API** | `theme_pack/src/routes.py` | 提供 RESTful API，用于列出、获取、切换和验证主题包。 |
| **CanonGuardCompilerV2** | `content_factory/src/canon_guard_v2.py` | 新版连续性编译器，通过 `DynamicEntityRegistry` 动态从 `ThemePackManager` 获取世界观规则和白名单。 |

### 2.3. API 使用说明

新的主题包管理API部署在 `/v1/theme-packs/` 路径下。以下是几个核心API的用法示例：

#### 1. 列出所有可用的主题包

```bash
curl http://120.55.162.182/v1/theme-packs/
```

#### 2. 获取特定主题包的详细信息

```bash
curl http://120.55.162.182/v1/theme-packs/hp_shanghai_s1
```

#### 3. 将剧场绑定到主题包

此操作会为指定剧场加载主题包，后续所有内容生成都将基于此主题包。

```bash
curl -X POST http://120.55.162.182/v1/theme-packs/bind \
     -H "Content-Type: application/json" \
     -d '{"theatre_id": "your_theatre_id", "pack_id": "hp_shanghai_s1"}'
```

#### 4. 查询剧场当前主题包的角色列表

```bash
curl http://120.55.162.182/v1/theme-packs/theatres/your_theatre_id/characters
```

完整的API文档可以通过访问 `http://120.55.162.182/docs` 查看。

## 3. 如何创建和切换新主题

基于当前架构，您可以按照以下步骤创建并使用一个新的主题包：

1.  **创建新主题目录**：在服务器的 `/opt/theatreos/theme_pack/packs/` 目录下，创建一个新的文件夹，例如 `my_new_theme_v1`。

2.  **准备数据文件**：按照 `hp_shanghai_s1` 的结构，在新目录中创建对应的 `manifest.json` 和其他数据文件。您需要将您的世界观设定、角色、故事线等内容填充到这些标准格式的JSON文件中。

3.  **重新加载服务（可选）**：`ThemePackManager` 会在服务启动时自动扫描并加载所有可用的主题包。如果您在服务运行时添加了新的主题包，可以调用以下API来重新加载，而无需重启整个后端服务：

    ```bash
    curl -X POST http://120.55.162.182/v1/theme-packs/reload/my_new_theme_v1
    ```

4.  **切换剧场主题**：为您的剧场切换到新的主题包。

    ```bash
    curl -X POST http://120.55.162.182/v1/theme-packs/theatres/your_theatre_id/switch \
         -H "Content-Type: application/json" \
         -d '{"new_pack_id": "my_new_theme_v1"}'
    ```

完成以上步骤后，您的剧场 `your_theatre_id` 就会开始使用 `my_new_theme_v1` 主题包来生成所有内容。

## 4. 总结与后续建议

本次开发成功地将 TheatreOS 的内容系统从硬编码的静态结构升级为灵活、可扩展的动态主题包架构。这为未来的内容创作、社区贡献和商业化运营奠定了坚实的技术基础。

**后续建议：**

- **开发主题包编辑器**：可以开发一个Web界面的主题包编辑器，让内容创作者无需直接编辑JSON文件，从而降低创作门槛。
- **完善验证机制**：进一步增强主题包的验证逻辑，例如检查故事线之间的逻辑关联、资源文件的完整性等。
- **数据库存储**：考虑将主题包数据存储在数据库中，以支持更高效的查询和版本管理。

如果您有任何疑问或需要进一步的开发支持，请随时提出。
