# TheatreOS · HP 上海 200 Node 数据包 v1.0

本数据包用于把「上海城市舞台 Node」扩展到 **200 个 Stage**，并提供一套与 TheatreOS 内容生成兼容的“舞台语义层”（Tag Lexicon + Cluster Catalog），以保证：
- **极度贴合哈利波特原作世界观**（对角巷/翻倒巷/魔法部/古灵阁/圣芒戈/凤凰社/禁林等语义）
- **贴合上海真实地理语境**（以城市中心热点区域为主，按区域簇生成）
- **完全匹配当前后端 CreateStageRequest 的字段格式**（可直接用于批量导入/部署脚本）

---

## 目录结构

- `stages/`
  - `shanghai_hp_stages_200.json`：**200 个 Stage Seed**（字段严格匹配 CreateStageRequest）
  - `shanghai_hp_stages_200.csv`：同上，便于表格查看
  - `shanghai_hp_stage_meta_200.json`：扩展元数据（区、簇、原作映射、推荐 Thread、提示词种子）
  - `shanghai_hp_stage_meta_200.csv`：同上

- `lexicon/`
  - `shanghai_hp_stage_clusters.json`：20 个城市簇（每簇 10 个节点）+ 推荐 Thread + base tags
  - `shanghai_hp_stage_tag_lexicon.json`：Stage Tag 语义词典（HP映射、氛围提示、推荐镜头/情绪）

---

## Stage 字段说明（与后端一致）

每个 Stage 对象字段：
- `stage_id`：舞台唯一 ID
- `name`：显示名（格式：`上海真实地点·哈利波特映射别名`）
- `lat` / `lng`：WGS84 坐标（用于 Ring 计算）
- `ringc_m` / `ringb_m` / `ringa_m`：圈层半径（米）
- `tags`：舞台标签（必须来自主题包 beat_templates 使用的 stage_tag_taxonomy）
- `safe_only`：是否允许 RingA（`false` 表示该点位不开放 RingA）

---

## 推荐导入方式（示例）

> 下面仅给出“导入策略”，具体脚本可复用你们现有的 `deploy_scripts/deploy_test_data.py`/`deploy_test_data_v2.py`。

1. **先部署 Theme Pack**（hp_shanghai_s1）
2. **创建 Theatre**
3. **批量创建 Stages**
   - 读 `shanghai_hp_stages_200.json`
   - 对每条记录调用：
     - `POST /v1/theatres/{theatre_id}/stages`
4. 运行 `scheduler` 生成 slot/scene 即可看到 200 个舞台参与排片。

---

## 说明与注意

- 坐标为“基于中心热点簇 + 轻微散点”的工程化坐标（用于产品/系统联调与 Ring 规则验证）；如需要 **完全对齐地图 POI 精度**，建议用高德/OSM POI 数据源进行二次校准。
- 本包不包含 UI、技术选型或代码实现；只提供可直接喂给系统的结构化数据。
- `prompt_seed` 中明确加入“不暴露精确地址/不出现可识别真人”的约束，便于内容生成与隐私安全一致。


---

## Meta 字段补充（用于内容/AI生成，可选）

`shanghai_hp_stage_meta_200.json` 额外提供：
- `wizarding_zone` / `canon_ref`
- `recommended_threads`
- `prompt_seed`
- `story_hook`：每个点位 1 句剧情钩子
- `npc_hint`：适配该点位的 NPC 风格建议

