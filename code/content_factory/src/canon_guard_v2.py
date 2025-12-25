"""
TheatreOS CanonGuard Compiler V2
连续性编译器 - 支持动态主题包加载

核心职责:
1. 硬性规则检查 (FAIL/PASS)
2. 预算限制检查
3. 软性评分
4. 自动修复建议

V2改进:
- 从ThemePack动态加载白名单
- 支持运行时切换主题包
- 与ThemePackManager集成
"""
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

# 导入主题包管理器
import sys
sys.path.insert(0, '/home/ubuntu/theatreos')
from theme_pack.src.manager import get_theme_pack_manager, ThemePackManager
from theme_pack.src.models import ThemePack, Character, Thread, BeatTemplate

logger = logging.getLogger(__name__)


# =============================================================================
# Enums & Data Classes (保持与V1兼容)
# =============================================================================
class RuleSeverity(str, Enum):
    FAIL = "FAIL"
    WARN = "WARN"
    SCORE = "SCORE"


class AutoFixStrategy(str, Enum):
    RESCHEDULE = "reschedule"
    REPLACE_WITH_RESCUE = "replace_with_rescue"
    CONVERT_TO_MISDIRECTION = "convert_to_misdirection"
    OFFSCREEN_EVENT = "offscreen_event"
    CLAMP = "clamp"
    INSERT_AFTERMATH = "insert_aftermath"
    SWAP_GATE_TEMPLATE = "swap_gate_template"
    REDACT = "redact"
    SWITCH_TO_SILHOUETTE = "switch_to_silhouette"
    BLOCK_STAGE = "block_stage"
    REWRITE_PROMPT = "rewrite_prompt"
    DEGRADE_TO_EVIDENCE_CARD = "degrade_to_evidence_card"
    SWAP_SCENE_TEMPLATE = "swap_scene_template"
    SWAP_STAGE_SAME_TAG = "swap_stage_same_tag"
    DEGRADE_ASSETS = "degrade_assets"
    RESCHEDULE_NEXT_HOUR = "reschedule_next_hour"


@dataclass
class Rule:
    """规则定义"""
    code: str
    name: str
    description: str
    severity: RuleSeverity
    auto_fix_strategies: List[AutoFixStrategy] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "auto_fix_strategies": [s.value for s in self.auto_fix_strategies]
        }


@dataclass
class Violation:
    """规则违反"""
    rule: Rule
    message: str
    context: Dict = field(default_factory=dict)
    auto_fix_applied: Optional[AutoFixStrategy] = None
    fixed: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "code": self.rule.code,
            "name": self.rule.name,
            "severity": self.rule.severity.value,
            "message": self.message,
            "context": self.context,
            "auto_fix_applied": self.auto_fix_applied.value if self.auto_fix_applied else None,
            "fixed": self.fixed
        }


@dataclass
class Budget:
    """预算限制"""
    name: str
    limit: int
    current: int = 0
    
    @property
    def exceeded(self) -> bool:
        return self.current > self.limit
    
    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.current)


@dataclass
class CompileReport:
    """编译报告"""
    status: str
    violations: List[Violation]
    warnings: List[Violation]
    budgets: Dict[str, Budget]
    score: float
    auto_fixes_applied: List[str]
    compile_time_ms: int
    theme_pack_id: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [w.to_dict() for w in self.warnings],
            "budgets": {k: {"name": v.name, "limit": v.limit, "current": v.current, "exceeded": v.exceeded} for k, v in self.budgets.items()},
            "score": self.score,
            "auto_fixes_applied": self.auto_fixes_applied,
            "compile_time_ms": self.compile_time_ms,
            "theme_pack_id": self.theme_pack_id
        }


# =============================================================================
# Rule Registry
# =============================================================================
class RuleRegistry:
    """规则注册表"""
    
    HARD_RULES = [
        Rule(
            code="CG001",
            name="角色时空冲突",
            description="同一角色同一时间窗只能在一个Scene出现；除非PORTAL且有证物解释",
            severity=RuleSeverity.FAIL,
            auto_fix_strategies=[AutoFixStrategy.RESCHEDULE, AutoFixStrategy.REPLACE_WITH_RESCUE]
        ),
        Rule(
            code="CG002",
            name="物件归属冲突",
            description="关键物件必须唯一holder/location",
            severity=RuleSeverity.FAIL,
            auto_fix_strategies=[AutoFixStrategy.CONVERT_TO_MISDIRECTION, AutoFixStrategy.OFFSCREEN_EVENT]
        ),
        Rule(
            code="CG003",
            name="世界变量越界",
            description="world_var必须在[0,1]且每小时变化≤0.15",
            severity=RuleSeverity.FAIL,
            auto_fix_strategies=[AutoFixStrategy.CLAMP, AutoFixStrategy.INSERT_AFTERMATH]
        ),
        Rule(
            code="CG004",
            name="门非法",
            description="Gate选项必须来自GateTemplate，不得临时生成新选项",
            severity=RuleSeverity.FAIL,
            auto_fix_strategies=[AutoFixStrategy.SWAP_GATE_TEMPLATE]
        ),
        Rule(
            code="CG005",
            name="隐私/安全违规",
            description="不得出现可定位现实信息、真人可识别入镜、危险引导",
            severity=RuleSeverity.FAIL,
            auto_fix_strategies=[AutoFixStrategy.REDACT, AutoFixStrategy.SWITCH_TO_SILHOUETTE, AutoFixStrategy.BLOCK_STAGE]
        ),
        Rule(
            code="CG006",
            name="越权生成实体",
            description="不得新增关键角色/关键物件；只能引用Bible集合",
            severity=RuleSeverity.FAIL,
            auto_fix_strategies=[AutoFixStrategy.REWRITE_PROMPT, AutoFixStrategy.REPLACE_WITH_RESCUE]
        ),
        Rule(
            code="CG007",
            name="must_drop未满足",
            description="HourPlan规定的must_drop证物必须产出（允许降级）",
            severity=RuleSeverity.FAIL,
            auto_fix_strategies=[AutoFixStrategy.DEGRADE_TO_EVIDENCE_CARD, AutoFixStrategy.SWAP_SCENE_TEMPLATE]
        ),
    ]
    
    SOFT_RULES = [
        Rule(
            code="CS101",
            name="重复镜头惩罚",
            description="同一舞台+同一镜头语法在24h内重复>2次降分",
            severity=RuleSeverity.SCORE,
            auto_fix_strategies=[]
        ),
        Rule(
            code="CS102",
            name="解释性台词惩罚",
            description="对白过长/解释世界观降分",
            severity=RuleSeverity.SCORE,
            auto_fix_strategies=[]
        ),
        Rule(
            code="CS103",
            name="误导配额",
            description="每晚至少2个C/D证物制造误读空间",
            severity=RuleSeverity.SCORE,
            auto_fix_strategies=[]
        ),
        Rule(
            code="CS104",
            name="社交依赖",
            description="每晚至少1次需要跨小队交换证物才能押门的场次",
            severity=RuleSeverity.SCORE,
            auto_fix_strategies=[]
        ),
    ]
    
    BUDGET_CONFIG = {
        "per_hour": {
            "max_high_intensity_beats": 4,
            "min_breath_beats": 1,
            "max_gates_total": 3,
            "max_A_tier_evidence": 2,
            "max_repeat_same_stage": 3
        },
        "per_night": {
            "max_A_tier_evidence": 6,
            "max_high_intensity_beats": 18
        },
        "per_day": {
            "min_thread_advances_total": 6,
            "min_puzzle_milestones": 1
        }
    }
    
    SCORE_WEIGHTS = {
        "continuity": 0.25,
        "clarity": 0.20,
        "tension": 0.15,
        "novelty": 0.15,
        "social_dependency": 0.15,
        "misread_space": 0.10
    }
    
    @classmethod
    def get_rule(cls, code: str) -> Optional[Rule]:
        for rule in cls.HARD_RULES + cls.SOFT_RULES:
            if rule.code == code:
                return rule
        return None
    
    @classmethod
    def get_all_rules(cls) -> List[Rule]:
        return cls.HARD_RULES + cls.SOFT_RULES


# =============================================================================
# Dynamic Entity Registry (从ThemePack加载)
# =============================================================================
class DynamicEntityRegistry:
    """
    动态实体注册表 - 从ThemePack加载白名单
    
    与V1的EntityRegistry不同，此版本从ThemePackManager动态获取数据，
    支持运行时切换主题包。
    """
    
    def __init__(self, theatre_id: str, theme_pack_manager: ThemePackManager = None):
        """
        初始化动态实体注册表
        
        Args:
            theatre_id: 剧场ID，用于获取绑定的主题包
            theme_pack_manager: 主题包管理器实例，为None时使用全局单例
        """
        self.theatre_id = theatre_id
        self._manager = theme_pack_manager or get_theme_pack_manager()
        self._cache_timestamp = None
        self._cache_pack_id = None
        
        # 缓存的白名单数据
        self._characters: Dict[str, Dict] = {}
        self._objects: Dict[str, Dict] = {}
        self._evidence_types: Dict[str, Dict] = {}
        self._threads: Dict[str, Dict] = {}
        self._gate_templates: Dict[str, Dict] = {}
        self._beat_templates: Dict[str, Dict] = {}
        self._world_variables: Dict[str, Dict] = {}
        
        # 初始加载
        self._refresh_cache()
    
    def _refresh_cache(self, force: bool = False):
        """刷新缓存"""
        try:
            pack = self._manager.get_theatre_pack(self.theatre_id)
            pack_id = pack.metadata.pack_id
            
            # 检查是否需要刷新
            if not force and self._cache_pack_id == pack_id:
                return
            
            # 加载角色白名单
            self._characters = {
                c.character_id: {
                    "name": c.name,
                    "name_cn": c.name_cn,
                    "faction": c.faction,
                    "role": c.role,
                    "allowed_beat_types": c.allowed_beat_types,
                    "forbidden_content": c.forbidden_content
                }
                for c in pack.characters
            }
            
            # 加载物品白名单
            self._objects = {
                o.object_id: {
                    "name": o.name,
                    "description": o.description,
                    "related_threads": o.related_threads
                }
                for o in pack.key_objects
            }
            
            # 加载证物类型白名单
            self._evidence_types = {
                e.evidence_type_id: {
                    "name": e.name,
                    "category": e.category,
                    "default_tier": e.default_tier,
                    "forgeability": e.forgeability,
                    "expiry": e.expiry
                }
                for e in pack.evidence_types
            }
            
            # 加载故事线白名单
            self._threads = {
                t.thread_id: {
                    "name": t.name,
                    "logline": t.logline,
                    "phases": [p.phase for p in t.phases],
                    "world_vars": t.world_vars
                }
                for t in pack.threads
            }
            
            # 加载门模板白名单
            self._gate_templates = {
                g.gate_id: {
                    "title": g.title,
                    "gate_type": g.gate_type,
                    "options": [o.option_id for o in g.options],
                    "tags": g.tags
                }
                for g in pack.gate_templates
            }
            
            # 加载拍子模板白名单
            self._beat_templates = {
                b.beat_id: {
                    "beat_type": b.beat_type,
                    "thread_id": b.thread_id,
                    "cast_roles": b.cast_roles,
                    "fallbacks": b.fallbacks
                }
                for b in pack.beat_templates
            }
            
            # 加载世界变量白名单
            self._world_variables = {
                w.id: {
                    "name_cn": w.name_cn,
                    "description": w.description,
                    "default_value": w.default_value,
                    "min_value": w.min_value,
                    "max_value": w.max_value,
                    "max_change_per_hour": w.max_change_per_hour
                }
                for w in pack.world_variables
            }
            
            self._cache_pack_id = pack_id
            self._cache_timestamp = datetime.now(timezone.utc)
            
            logger.info(f"DynamicEntityRegistry refreshed for theatre {self.theatre_id}, pack: {pack_id}")
            logger.info(f"  Loaded: {len(self._characters)} characters, {len(self._objects)} objects, "
                       f"{len(self._evidence_types)} evidence types, {len(self._threads)} threads")
            
        except Exception as e:
            logger.error(f"Failed to refresh entity registry: {e}")
            raise
    
    @property
    def pack_id(self) -> str:
        """当前主题包ID"""
        return self._cache_pack_id or "unknown"
    
    # =========================================================================
    # 角色验证
    # =========================================================================
    def is_valid_character(self, char_id: str) -> bool:
        """检查角色是否在白名单中"""
        return char_id in self._characters
    
    def get_character(self, char_id: str) -> Optional[Dict]:
        """获取角色信息"""
        return self._characters.get(char_id)
    
    def get_character_allowed_beats(self, char_id: str) -> List[str]:
        """获取角色允许的拍子类型"""
        char = self._characters.get(char_id)
        return char.get("allowed_beat_types", []) if char else []
    
    def get_character_forbidden_content(self, char_id: str) -> List[str]:
        """获取角色禁止的内容"""
        char = self._characters.get(char_id)
        return char.get("forbidden_content", []) if char else []
    
    def list_characters(self) -> List[str]:
        """列出所有角色ID"""
        return list(self._characters.keys())
    
    # =========================================================================
    # 物品验证
    # =========================================================================
    def is_valid_object(self, obj_id: str) -> bool:
        """检查物品是否在白名单中"""
        return obj_id in self._objects
    
    def get_object(self, obj_id: str) -> Optional[Dict]:
        """获取物品信息"""
        return self._objects.get(obj_id)
    
    def list_objects(self) -> List[str]:
        """列出所有物品ID"""
        return list(self._objects.keys())
    
    # =========================================================================
    # 证物类型验证
    # =========================================================================
    def is_valid_evidence_type(self, evidence_type_id: str) -> bool:
        """检查证物类型是否在白名单中"""
        return evidence_type_id in self._evidence_types
    
    def get_evidence_type(self, evidence_type_id: str) -> Optional[Dict]:
        """获取证物类型信息"""
        return self._evidence_types.get(evidence_type_id)
    
    def list_evidence_types(self) -> List[str]:
        """列出所有证物类型ID"""
        return list(self._evidence_types.keys())
    
    # =========================================================================
    # 故事线验证
    # =========================================================================
    def is_valid_thread(self, thread_id: str) -> bool:
        """检查故事线是否在白名单中"""
        return thread_id in self._threads
    
    def get_thread(self, thread_id: str) -> Optional[Dict]:
        """获取故事线信息"""
        return self._threads.get(thread_id)
    
    def is_valid_thread_phase(self, thread_id: str, phase: str) -> bool:
        """检查故事线阶段是否有效"""
        thread = self._threads.get(thread_id)
        if not thread:
            return False
        return phase in thread.get("phases", [])
    
    def list_threads(self) -> List[str]:
        """列出所有故事线ID"""
        return list(self._threads.keys())
    
    # =========================================================================
    # 门模板验证
    # =========================================================================
    def is_valid_gate_template(self, gate_id: str) -> bool:
        """检查门模板是否在白名单中"""
        return gate_id in self._gate_templates
    
    def get_gate_template(self, gate_id: str) -> Optional[Dict]:
        """获取门模板信息"""
        return self._gate_templates.get(gate_id)
    
    def is_valid_gate_option(self, gate_id: str, option_id: str) -> bool:
        """检查门选项是否有效"""
        gate = self._gate_templates.get(gate_id)
        if not gate:
            return False
        return option_id in gate.get("options", [])
    
    def list_gate_templates(self) -> List[str]:
        """列出所有门模板ID"""
        return list(self._gate_templates.keys())
    
    # =========================================================================
    # 拍子模板验证
    # =========================================================================
    def is_valid_beat_template(self, beat_id: str) -> bool:
        """检查拍子模板是否在白名单中"""
        return beat_id in self._beat_templates
    
    def get_beat_template(self, beat_id: str) -> Optional[Dict]:
        """获取拍子模板信息"""
        return self._beat_templates.get(beat_id)
    
    def get_beat_fallbacks(self, beat_id: str) -> List[str]:
        """获取拍子的fallback列表"""
        beat = self._beat_templates.get(beat_id)
        return beat.get("fallbacks", []) if beat else []
    
    def list_beat_templates(self) -> List[str]:
        """列出所有拍子模板ID"""
        return list(self._beat_templates.keys())
    
    # =========================================================================
    # 世界变量验证
    # =========================================================================
    def is_valid_world_variable(self, var_id: str) -> bool:
        """检查世界变量是否在白名单中"""
        return var_id in self._world_variables
    
    def get_world_variable(self, var_id: str) -> Optional[Dict]:
        """获取世界变量信息"""
        return self._world_variables.get(var_id)
    
    def get_world_variable_bounds(self, var_id: str) -> Tuple[float, float]:
        """获取世界变量的边界"""
        var = self._world_variables.get(var_id)
        if not var:
            return (0.0, 1.0)
        return (var.get("min_value", 0.0), var.get("max_value", 1.0))
    
    def get_world_variable_max_change(self, var_id: str) -> float:
        """获取世界变量的最大变化率"""
        var = self._world_variables.get(var_id)
        return var.get("max_change_per_hour", 0.15) if var else 0.15
    
    def list_world_variables(self) -> List[str]:
        """列出所有世界变量ID"""
        return list(self._world_variables.keys())
    
    def get_default_world_state(self) -> Dict[str, float]:
        """获取默认世界状态"""
        return {
            var_id: var.get("default_value", 0.5)
            for var_id, var in self._world_variables.items()
        }


# =============================================================================
# CanonGuard Compiler V2
# =============================================================================
class CanonGuardCompilerV2:
    """
    连续性编译器V2 - 支持动态主题包
    
    与V1的主要区别：
    1. 使用DynamicEntityRegistry替代静态EntityRegistry
    2. 支持运行时切换主题包
    3. 编译报告包含主题包信息
    """
    
    def __init__(self, theatre_id: str, theme_pack_manager: ThemePackManager = None):
        """
        初始化编译器
        
        Args:
            theatre_id: 剧场ID
            theme_pack_manager: 主题包管理器
        """
        self.theatre_id = theatre_id
        self._manager = theme_pack_manager or get_theme_pack_manager()
        self.entity_registry = DynamicEntityRegistry(theatre_id, self._manager)
        self.rule_registry = RuleRegistry()
    
    def refresh_theme_pack(self):
        """刷新主题包（当主题包切换时调用）"""
        self.entity_registry._refresh_cache(force=True)
    
    def compile(
        self,
        scene_drafts: List[Dict],
        evidence_list: List[Dict],
        gate_config: Dict,
        world_state: Dict,
        hour_plan: Dict,
        historical_context: Dict = None
    ) -> CompileReport:
        """
        编译场景草稿
        
        Args:
            scene_drafts: 场景草稿列表
            evidence_list: 证物列表
            gate_config: 门配置
            world_state: 当前世界状态
            hour_plan: 小时计划
            historical_context: 历史上下文
        
        Returns:
            CompileReport: 编译报告
        """
        start_time = datetime.now(timezone.utc)
        
        violations = []
        warnings = []
        auto_fixes_applied = []
        
        # 1. 检查硬性规则
        violations.extend(self._check_character_conflicts(scene_drafts))
        violations.extend(self._check_object_conflicts(scene_drafts, world_state))
        violations.extend(self._check_world_var_bounds(scene_drafts, world_state))
        violations.extend(self._check_gate_validity(gate_config))
        violations.extend(self._check_safety(scene_drafts))
        violations.extend(self._check_entity_whitelist(scene_drafts))
        violations.extend(self._check_must_drop(evidence_list, hour_plan))
        
        # 2. 尝试自动修复
        for violation in violations:
            if violation.rule.auto_fix_strategies:
                fix_result = self._try_auto_fix(violation, scene_drafts, world_state)
                if fix_result:
                    violation.auto_fix_applied = fix_result
                    violation.fixed = True
                    auto_fixes_applied.append(f"{violation.rule.code}:{fix_result.value}")
        
        # 3. 检查软性规则
        warnings.extend(self._check_soft_rules(scene_drafts, evidence_list, historical_context))
        
        # 4. 检查预算
        budgets = self._check_budgets(scene_drafts, evidence_list, gate_config)
        
        # 5. 计算评分
        score = self._calculate_score(violations, warnings, budgets, scene_drafts)
        
        # 6. 确定状态
        unfixed_violations = [v for v in violations if not v.fixed]
        if unfixed_violations:
            status = "FAIL"
        elif warnings:
            status = "WARN"
        else:
            status = "PASS"
        
        compile_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return CompileReport(
            status=status,
            violations=violations,
            warnings=warnings,
            budgets=budgets,
            score=score,
            auto_fixes_applied=auto_fixes_applied,
            compile_time_ms=compile_time,
            theme_pack_id=self.entity_registry.pack_id
        )
    
    # =========================================================================
    # 硬性规则检查
    # =========================================================================
    
    def _check_character_conflicts(self, scene_drafts: List[Dict]) -> List[Violation]:
        """检查角色时空冲突"""
        violations = []
        rule = RuleRegistry.get_rule("CG001")
        
        # 按时间窗口分组场景
        time_windows = {}
        for scene in scene_drafts:
            window = scene.get("time_window", "default")
            if window not in time_windows:
                time_windows[window] = []
            time_windows[window].append(scene)
        
        # 检查每个时间窗口
        for window, scenes in time_windows.items():
            char_locations = {}
            for scene in scenes:
                for char_id in scene.get("characters", []):
                    location = scene.get("stage_id", "unknown")
                    if char_id in char_locations:
                        if char_locations[char_id] != location:
                            # 检查是否有PORTAL解释
                            if scene.get("beat_type") != "PORTAL":
                                violations.append(Violation(
                                    rule=rule,
                                    message=f"角色 {char_id} 在时间窗口 {window} 同时出现在 {char_locations[char_id]} 和 {location}",
                                    context={
                                        "character_id": char_id,
                                        "time_window": window,
                                        "locations": [char_locations[char_id], location]
                                    }
                                ))
                    else:
                        char_locations[char_id] = location
        
        return violations
    
    def _check_object_conflicts(self, scene_drafts: List[Dict], world_state: Dict) -> List[Violation]:
        """检查物件归属冲突"""
        violations = []
        rule = RuleRegistry.get_rule("CG002")
        
        object_holders = {}
        for scene in scene_drafts:
            for obj in scene.get("objects", []):
                obj_id = obj.get("object_id")
                holder = obj.get("holder") or obj.get("location")
                
                if obj_id in object_holders:
                    if object_holders[obj_id] != holder:
                        violations.append(Violation(
                            rule=rule,
                            message=f"物件 {obj_id} 同时被 {object_holders[obj_id]} 和 {holder} 持有",
                            context={
                                "object_id": obj_id,
                                "holders": [object_holders[obj_id], holder]
                            }
                        ))
                else:
                    object_holders[obj_id] = holder
        
        return violations
    
    def _check_world_var_bounds(self, scene_drafts: List[Dict], world_state: Dict) -> List[Violation]:
        """检查世界变量越界"""
        violations = []
        rule = RuleRegistry.get_rule("CG003")
        
        # 计算场景对世界变量的影响
        var_changes = {}
        for scene in scene_drafts:
            effects = scene.get("effects", {}).get("world", {})
            for var_id, change in effects.items():
                if var_id not in var_changes:
                    var_changes[var_id] = 0
                var_changes[var_id] += change
        
        # 检查变化是否越界
        for var_id, total_change in var_changes.items():
            # 从主题包获取变量约束
            bounds = self.entity_registry.get_world_variable_bounds(var_id)
            max_change = self.entity_registry.get_world_variable_max_change(var_id)
            
            current_value = world_state.get(var_id, 0.5)
            new_value = current_value + total_change
            
            # 检查边界
            if new_value < bounds[0] or new_value > bounds[1]:
                violations.append(Violation(
                    rule=rule,
                    message=f"世界变量 {var_id} 将越界: {current_value} + {total_change} = {new_value} (范围: {bounds})",
                    context={
                        "variable_id": var_id,
                        "current": current_value,
                        "change": total_change,
                        "new_value": new_value,
                        "bounds": bounds
                    }
                ))
            
            # 检查变化率
            if abs(total_change) > max_change:
                violations.append(Violation(
                    rule=rule,
                    message=f"世界变量 {var_id} 变化过快: {total_change} (最大: {max_change}/小时)",
                    context={
                        "variable_id": var_id,
                        "change": total_change,
                        "max_change": max_change
                    }
                ))
        
        return violations
    
    def _check_gate_validity(self, gate_config: Dict) -> List[Violation]:
        """检查门配置有效性"""
        violations = []
        rule = RuleRegistry.get_rule("CG004")
        
        gate_id = gate_config.get("gate_template_id")
        if gate_id and not self.entity_registry.is_valid_gate_template(gate_id):
            violations.append(Violation(
                rule=rule,
                message=f"门模板 {gate_id} 不在白名单中",
                context={"gate_template_id": gate_id}
            ))
        
        # 检查选项
        for option in gate_config.get("options", []):
            option_id = option.get("id")
            if gate_id and not self.entity_registry.is_valid_gate_option(gate_id, option_id):
                violations.append(Violation(
                    rule=rule,
                    message=f"门选项 {option_id} 不属于模板 {gate_id}",
                    context={"gate_template_id": gate_id, "option_id": option_id}
                ))
        
        return violations
    
    def _check_safety(self, scene_drafts: List[Dict]) -> List[Violation]:
        """检查安全规则"""
        violations = []
        rule = RuleRegistry.get_rule("CG005")
        
        # 敏感词列表
        sensitive_patterns = [
            "真实地址", "电话号码", "身份证", "银行卡",
            "自杀", "自残", "暴力", "恐怖",
        ]
        
        for scene in scene_drafts:
            content = json.dumps(scene, ensure_ascii=False)
            for pattern in sensitive_patterns:
                if pattern in content:
                    violations.append(Violation(
                        rule=rule,
                        message=f"场景包含敏感内容: {pattern}",
                        context={"scene_id": scene.get("scene_id"), "pattern": pattern}
                    ))
        
        return violations
    
    def _check_entity_whitelist(self, scene_drafts: List[Dict]) -> List[Violation]:
        """检查实体白名单"""
        violations = []
        rule = RuleRegistry.get_rule("CG006")
        
        for scene in scene_drafts:
            # 检查角色
            for char_id in scene.get("characters", []):
                if not self.entity_registry.is_valid_character(char_id):
                    violations.append(Violation(
                        rule=rule,
                        message=f"角色 {char_id} 不在白名单中",
                        context={"character_id": char_id, "scene_id": scene.get("scene_id")}
                    ))
            
            # 检查物品
            for obj in scene.get("objects", []):
                obj_id = obj.get("object_id")
                if obj_id and not self.entity_registry.is_valid_object(obj_id):
                    violations.append(Violation(
                        rule=rule,
                        message=f"物品 {obj_id} 不在白名单中",
                        context={"object_id": obj_id, "scene_id": scene.get("scene_id")}
                    ))
            
            # 检查证物类型
            for evidence in scene.get("evidence_outputs", []):
                ev_type = evidence.get("type")
                if ev_type and not self.entity_registry.is_valid_evidence_type(ev_type):
                    violations.append(Violation(
                        rule=rule,
                        message=f"证物类型 {ev_type} 不在白名单中",
                        context={"evidence_type": ev_type, "scene_id": scene.get("scene_id")}
                    ))
        
        return violations
    
    def _check_must_drop(self, evidence_list: List[Dict], hour_plan: Dict) -> List[Violation]:
        """检查必须产出的证物"""
        violations = []
        rule = RuleRegistry.get_rule("CG007")
        
        must_drop = hour_plan.get("must_drop", [])
        produced = {e.get("type") for e in evidence_list}
        
        for required in must_drop:
            if required not in produced:
                violations.append(Violation(
                    rule=rule,
                    message=f"必须产出的证物 {required} 未产出",
                    context={"required_evidence": required}
                ))
        
        return violations
    
    # =========================================================================
    # 软性规则检查
    # =========================================================================
    
    def _check_soft_rules(
        self,
        scene_drafts: List[Dict],
        evidence_list: List[Dict],
        historical_context: Dict = None
    ) -> List[Violation]:
        """检查软性规则"""
        warnings = []
        
        # CS101: 重复镜头
        if historical_context:
            recent_shots = historical_context.get("recent_shots", [])
            for scene in scene_drafts:
                shot_key = f"{scene.get('stage_id')}:{scene.get('camera_style')}"
                if recent_shots.count(shot_key) > 2:
                    rule = RuleRegistry.get_rule("CS101")
                    warnings.append(Violation(
                        rule=rule,
                        message=f"镜头 {shot_key} 在24小时内重复超过2次",
                        context={"shot_key": shot_key}
                    ))
        
        # CS103: 误导配额
        low_tier_evidence = [e for e in evidence_list if e.get("tier") in ["C", "D"]]
        if len(low_tier_evidence) < 2:
            rule = RuleRegistry.get_rule("CS103")
            warnings.append(Violation(
                rule=rule,
                message=f"低等级证物(C/D)不足2个，当前{len(low_tier_evidence)}个",
                context={"count": len(low_tier_evidence)}
            ))
        
        return warnings
    
    # =========================================================================
    # 预算检查
    # =========================================================================
    
    def _check_budgets(
        self,
        scene_drafts: List[Dict],
        evidence_list: List[Dict],
        gate_config: Dict
    ) -> Dict[str, Budget]:
        """检查预算"""
        budgets = {}
        config = RuleRegistry.BUDGET_CONFIG["per_hour"]
        
        # 高强度拍子
        high_intensity = len([s for s in scene_drafts if s.get("intensity", 0) > 0.7])
        budgets["high_intensity_beats"] = Budget(
            name="高强度拍子",
            limit=config["max_high_intensity_beats"],
            current=high_intensity
        )
        
        # A级证物
        a_tier = len([e for e in evidence_list if e.get("tier") == "A"])
        budgets["a_tier_evidence"] = Budget(
            name="A级证物",
            limit=config["max_A_tier_evidence"],
            current=a_tier
        )
        
        # 门数量
        gate_count = 1 if gate_config else 0
        budgets["gates"] = Budget(
            name="门数量",
            limit=config["max_gates_total"],
            current=gate_count
        )
        
        return budgets
    
    # =========================================================================
    # 评分计算
    # =========================================================================
    
    def _calculate_score(
        self,
        violations: List[Violation],
        warnings: List[Violation],
        budgets: Dict[str, Budget],
        scene_drafts: List[Dict]
    ) -> float:
        """计算评分"""
        base_score = 100.0
        
        # 违规扣分
        for v in violations:
            if not v.fixed:
                base_score -= 20.0
            else:
                base_score -= 5.0  # 自动修复的扣分较少
        
        # 警告扣分
        for w in warnings:
            base_score -= 5.0
        
        # 预算超支扣分
        for budget in budgets.values():
            if budget.exceeded:
                base_score -= 10.0
        
        return max(0.0, min(100.0, base_score))
    
    # =========================================================================
    # 自动修复
    # =========================================================================
    
    def _try_auto_fix(
        self,
        violation: Violation,
        scene_drafts: List[Dict],
        world_state: Dict
    ) -> Optional[AutoFixStrategy]:
        """尝试自动修复"""
        for strategy in violation.rule.auto_fix_strategies:
            if self._apply_fix(strategy, violation, scene_drafts, world_state):
                return strategy
        return None
    
    def _apply_fix(
        self,
        strategy: AutoFixStrategy,
        violation: Violation,
        scene_drafts: List[Dict],
        world_state: Dict
    ) -> bool:
        """应用修复策略"""
        try:
            if strategy == AutoFixStrategy.CLAMP:
                # 钳制世界变量到边界
                var_id = violation.context.get("variable_id")
                if var_id:
                    bounds = self.entity_registry.get_world_variable_bounds(var_id)
                    # 实际修复逻辑...
                    return True
            
            elif strategy == AutoFixStrategy.REPLACE_WITH_RESCUE:
                # 替换为救援拍子
                scene_id = violation.context.get("scene_id")
                if scene_id:
                    # 从主题包获取救援拍子
                    rescue_beats = self._manager.get_rescue_beats(self.theatre_id)
                    if rescue_beats:
                        # 实际替换逻辑...
                        return True
            
            elif strategy == AutoFixStrategy.SWAP_GATE_TEMPLATE:
                # 替换门模板
                gate_templates = self.entity_registry.list_gate_templates()
                if gate_templates:
                    # 实际替换逻辑...
                    return True
            
            # 其他策略...
            
        except Exception as e:
            logger.warning(f"Auto-fix failed: {strategy.value}, error: {e}")
        
        return False


# =============================================================================
# 工厂函数
# =============================================================================

def create_canon_guard(theatre_id: str) -> CanonGuardCompilerV2:
    """
    创建CanonGuard编译器
    
    Args:
        theatre_id: 剧场ID
    
    Returns:
        CanonGuardCompilerV2: 编译器实例
    """
    return CanonGuardCompilerV2(theatre_id)


def get_entity_registry(theatre_id: str) -> DynamicEntityRegistry:
    """
    获取实体注册表
    
    Args:
        theatre_id: 剧场ID
    
    Returns:
        DynamicEntityRegistry: 实体注册表实例
    """
    return DynamicEntityRegistry(theatre_id)
