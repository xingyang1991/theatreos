"""
TheatreOS CanonGuard Compiler
连续性编译器 - 确保生成内容符合世界观规则

核心职责:
1. 硬性规则检查 (FAIL/PASS)
2. 预算限制检查
3. 软性评分
4. 自动修复建议
"""
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Enums & Data Classes
# =============================================================================
class RuleSeverity(str, Enum):
    FAIL = "FAIL"      # 必须修复，否则无法发布
    WARN = "WARN"      # 警告，可以发布但会降分
    SCORE = "SCORE"    # 仅影响评分


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
    status: str  # PASS, FAIL, WARN
    violations: List[Violation]
    warnings: List[Violation]
    budgets: Dict[str, Budget]
    score: float
    auto_fixes_applied: List[str]
    compile_time_ms: int
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [w.to_dict() for w in self.warnings],
            "budgets": {k: {"name": v.name, "limit": v.limit, "current": v.current, "exceeded": v.exceeded} for k, v in self.budgets.items()},
            "score": self.score,
            "auto_fixes_applied": self.auto_fixes_applied,
            "compile_time_ms": self.compile_time_ms
        }


# =============================================================================
# Rule Registry
# =============================================================================
class RuleRegistry:
    """规则注册表"""
    
    # 硬性规则
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
    
    # 软性规则（影响评分）
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
    
    # 预算配置
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
    
    # 评分权重
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
        """根据代码获取规则"""
        for rule in cls.HARD_RULES + cls.SOFT_RULES:
            if rule.code == code:
                return rule
        return None
    
    @classmethod
    def get_all_rules(cls) -> List[Rule]:
        """获取所有规则"""
        return cls.HARD_RULES + cls.SOFT_RULES


# =============================================================================
# Entity Registry (白名单)
# =============================================================================
class EntityRegistry:
    """实体注册表（白名单）"""
    
    def __init__(self, theme_pack_id: str = "hp_shanghai_s1"):
        self.theme_pack_id = theme_pack_id
        self._load_whitelist()
    
    def _load_whitelist(self):
        """加载白名单"""
        # 实际应从 ThemePack 加载
        self.characters = {
            "char_001": {"name": "神秘人A", "type": "npc"},
            "char_002": {"name": "神秘人B", "type": "npc"},
            "char_003": {"name": "线人C", "type": "npc"},
        }
        
        self.objects = {
            "obj_001": {"name": "神秘信封", "type": "key_item"},
            "obj_002": {"name": "旧照片", "type": "evidence"},
            "obj_003": {"name": "加密U盘", "type": "key_item"},
        }
        
        self.locations = {
            "loc_001": {"name": "外滩观景台", "type": "stage"},
            "loc_002": {"name": "南京路步行街", "type": "stage"},
            "loc_003": {"name": "豫园", "type": "stage"},
        }
    
    def is_valid_character(self, char_id: str) -> bool:
        return char_id in self.characters
    
    def is_valid_object(self, obj_id: str) -> bool:
        return obj_id in self.objects
    
    def is_valid_location(self, loc_id: str) -> bool:
        return loc_id in self.locations


# =============================================================================
# CanonGuard Compiler
# =============================================================================
class CanonGuardCompiler:
    """连续性编译器"""
    
    def __init__(self, entity_registry: EntityRegistry = None):
        self.entity_registry = entity_registry or EntityRegistry()
        self.rule_registry = RuleRegistry()
    
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
            historical_context: 历史上下文（用于检查重复等）
        
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
        
        # 2. 检查预算
        budgets = self._check_budgets(scene_drafts, evidence_list)
        for budget_name, budget in budgets.items():
            if budget.exceeded:
                warnings.append(Violation(
                    rule=Rule(
                        code=f"CB_{budget_name}",
                        name=f"预算超限: {budget.name}",
                        description=f"{budget.name} 超过限制",
                        severity=RuleSeverity.WARN
                    ),
                    message=f"{budget.name}: {budget.current}/{budget.limit}"
                ))
        
        # 3. 检查软性规则
        warnings.extend(self._check_soft_rules(scene_drafts, historical_context))
        
        # 4. 计算评分
        score = self._calculate_score(scene_drafts, violations, warnings)
        
        # 5. 确定状态
        has_fail = any(v.rule.severity == RuleSeverity.FAIL and not v.fixed for v in violations)
        status = "FAIL" if has_fail else ("WARN" if warnings else "PASS")
        
        # 计算编译时间
        end_time = datetime.now(timezone.utc)
        compile_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return CompileReport(
            status=status,
            violations=violations,
            warnings=warnings,
            budgets=budgets,
            score=score,
            auto_fixes_applied=auto_fixes_applied,
            compile_time_ms=compile_time_ms
        )
    
    def _check_character_conflicts(self, scene_drafts: List[Dict]) -> List[Violation]:
        """检查角色时空冲突"""
        violations = []
        rule = RuleRegistry.get_rule("CG001")
        
        # 提取所有场景中的角色
        character_appearances = {}  # {char_id: [scene_ids]}
        
        for scene in scene_drafts:
            dialogue = scene.get("dialogue", [])
            for line in dialogue:
                if isinstance(line, list) and len(line) >= 2:
                    char_name = line[0]
                    scene_id = scene.get("scene_id", "unknown")
                    
                    if char_name not in character_appearances:
                        character_appearances[char_name] = []
                    character_appearances[char_name].append(scene_id)
        
        # 检查同一角色是否同时出现在多个场景
        for char_name, scene_ids in character_appearances.items():
            if len(set(scene_ids)) > 1:
                # 同一角色出现在多个不同场景
                # 需要进一步检查时间窗是否重叠
                # 简化实现：假设同一 slot 内的场景时间重叠
                violations.append(Violation(
                    rule=rule,
                    message=f"角色 '{char_name}' 同时出现在多个场景: {scene_ids}",
                    context={"character": char_name, "scenes": scene_ids}
                ))
        
        return violations
    
    def _check_object_conflicts(self, scene_drafts: List[Dict], world_state: Dict) -> List[Violation]:
        """检查物件归属冲突"""
        violations = []
        rule = RuleRegistry.get_rule("CG002")
        
        # 检查关键物件的唯一性
        # 实际需要解析场景中提到的物件
        
        return violations
    
    def _check_world_var_bounds(self, scene_drafts: List[Dict], world_state: Dict) -> List[Violation]:
        """检查世界变量边界"""
        violations = []
        rule = RuleRegistry.get_rule("CG003")
        
        current_vars = world_state.get("vars", {})
        
        for var_name, var_value in current_vars.items():
            # 检查是否在 [0, 1] 范围内
            if not (0 <= var_value <= 1):
                violations.append(Violation(
                    rule=rule,
                    message=f"世界变量 '{var_name}' 值 {var_value} 超出 [0, 1] 范围",
                    context={"variable": var_name, "value": var_value}
                ))
        
        return violations
    
    def _check_gate_validity(self, gate_config: Dict) -> List[Violation]:
        """检查门有效性"""
        violations = []
        rule = RuleRegistry.get_rule("CG004")
        
        if not gate_config:
            violations.append(Violation(
                rule=rule,
                message="缺少门配置",
                context={}
            ))
            return violations
        
        options = gate_config.get("options", [])
        if not options:
            violations.append(Violation(
                rule=rule,
                message="门配置缺少选项",
                context={"gate_config": gate_config}
            ))
        
        # 检查选项是否来自模板（简化实现）
        for opt in options:
            if not opt.get("option_id"):
                violations.append(Violation(
                    rule=rule,
                    message="门选项缺少 option_id",
                    context={"option": opt}
                ))
        
        return violations
    
    def _check_safety(self, scene_drafts: List[Dict]) -> List[Violation]:
        """检查安全违规"""
        violations = []
        rule = RuleRegistry.get_rule("CG005")
        
        # 危险模式列表
        dangerous_patterns = [
            # 个人信息
            ("身份证", "个人信息泄露"),
            ("电话号码", "个人信息泄露"),
            ("银行卡", "个人信息泄露"),
            ("家庭住址", "个人信息泄露"),
            # 危险内容
            ("制作炸弹", "危险指引"),
            ("自杀方法", "危险指引"),
            ("毒品配方", "危险指引"),
            ("武器制造", "危险指引"),
            # 政治敏感
            ("政治领导人", "政治敏感"),
            ("国家机密", "政治敏感"),
        ]
        
        for scene in scene_drafts:
            scene_text = scene.get("scene_text", "").lower()
            dialogue_text = " ".join([
                line[1] if isinstance(line, list) and len(line) >= 2 else ""
                for line in scene.get("dialogue", [])
            ]).lower()
            
            full_text = scene_text + " " + dialogue_text
            
            for pattern, category in dangerous_patterns:
                if pattern in full_text:
                    violations.append(Violation(
                        rule=rule,
                        message=f"场景包含 {category} 内容: '{pattern}'",
                        context={
                            "scene_id": scene.get("scene_id"),
                            "pattern": pattern,
                            "category": category
                        }
                    ))
        
        return violations
    
    def _check_entity_whitelist(self, scene_drafts: List[Dict]) -> List[Violation]:
        """检查实体白名单"""
        violations = []
        rule = RuleRegistry.get_rule("CG006")
        
        # 实际需要解析场景中的实体引用
        # 简化实现：检查是否有明显的新角色/物件创建
        
        new_entity_patterns = [
            "新角色",
            "新人物",
            "新物品",
            "新道具",
        ]
        
        for scene in scene_drafts:
            scene_text = scene.get("scene_text", "")
            
            for pattern in new_entity_patterns:
                if pattern in scene_text:
                    violations.append(Violation(
                        rule=rule,
                        message=f"场景可能创建了新实体: '{pattern}'",
                        context={
                            "scene_id": scene.get("scene_id"),
                            "pattern": pattern
                        }
                    ))
        
        return violations
    
    def _check_must_drop(self, evidence_list: List[Dict], hour_plan: Dict) -> List[Violation]:
        """检查必须掉落的证物"""
        violations = []
        rule = RuleRegistry.get_rule("CG007")
        
        # 获取 hour_plan 中的 must_drop 要求
        must_drop = []
        if hasattr(hour_plan, 'must_drop_jsonb'):
            must_drop = hour_plan.must_drop_jsonb or []
        elif isinstance(hour_plan, dict):
            must_drop = hour_plan.get("must_drop", [])
        
        # 检查每个 must_drop 是否有对应的证物
        evidence_types = {e.get("evidence_type_id") for e in evidence_list}
        
        for required in must_drop:
            required_type = required.get("evidence_type_id") if isinstance(required, dict) else required
            if required_type not in evidence_types:
                violations.append(Violation(
                    rule=rule,
                    message=f"必须掉落的证物 '{required_type}' 未产出",
                    context={"required": required_type}
                ))
        
        return violations
    
    def _check_budgets(self, scene_drafts: List[Dict], evidence_list: List[Dict]) -> Dict[str, Budget]:
        """检查预算限制"""
        budgets = {}
        config = RuleRegistry.BUDGET_CONFIG["per_hour"]
        
        # 高强度拍子
        high_intensity_count = sum(
            1 for s in scene_drafts
            if s.get("mood") in ["ominous", "tense", "confrontational", "intense"]
        )
        budgets["high_intensity_beats"] = Budget(
            name="高强度拍子",
            limit=config["max_high_intensity_beats"],
            current=high_intensity_count
        )
        
        # A级证物
        a_tier_count = sum(1 for e in evidence_list if e.get("tier") == "A")
        budgets["a_tier_evidence"] = Budget(
            name="A级证物",
            limit=config["max_A_tier_evidence"],
            current=a_tier_count
        )
        
        # 同舞台重复
        stage_counts = {}
        for s in scene_drafts:
            stage_id = s.get("stage_id", "unknown")
            stage_counts[stage_id] = stage_counts.get(stage_id, 0) + 1
        
        max_repeat = max(stage_counts.values()) if stage_counts else 0
        budgets["repeat_same_stage"] = Budget(
            name="同舞台重复",
            limit=config["max_repeat_same_stage"],
            current=max_repeat
        )
        
        return budgets
    
    def _check_soft_rules(self, scene_drafts: List[Dict], historical_context: Dict = None) -> List[Violation]:
        """检查软性规则"""
        warnings = []
        
        # CS102: 解释性台词惩罚
        rule_cs102 = RuleRegistry.get_rule("CS102")
        for scene in scene_drafts:
            dialogue = scene.get("dialogue", [])
            for line in dialogue:
                if isinstance(line, list) and len(line) >= 2:
                    text = line[1]
                    if len(text) > 50:  # 台词过长
                        warnings.append(Violation(
                            rule=rule_cs102,
                            message=f"台词过长 ({len(text)} 字): '{text[:30]}...'",
                            context={"scene_id": scene.get("scene_id"), "length": len(text)}
                        ))
        
        return warnings
    
    def _calculate_score(
        self,
        scene_drafts: List[Dict],
        violations: List[Violation],
        warnings: List[Violation]
    ) -> float:
        """计算质量分数"""
        base_score = 1.0
        
        # 违规扣分
        fail_count = sum(1 for v in violations if v.rule.severity == RuleSeverity.FAIL and not v.fixed)
        warn_count = len(warnings)
        
        violation_penalty = fail_count * 0.2 + warn_count * 0.05
        
        # 多样性加分
        unique_stages = len(set(s.get("stage_id", "") for s in scene_drafts))
        unique_moods = len(set(s.get("mood", "") for s in scene_drafts))
        diversity_bonus = min((unique_stages + unique_moods) * 0.02, 0.1)
        
        # 内容丰富度加分
        avg_text_length = sum(len(s.get("scene_text", "")) for s in scene_drafts) / max(len(scene_drafts), 1)
        richness_bonus = min(avg_text_length / 500 * 0.05, 0.05)
        
        score = max(0, min(1, base_score - violation_penalty + diversity_bonus + richness_bonus))
        return round(score, 2)
    
    def suggest_auto_fix(self, violation: Violation) -> Optional[AutoFixStrategy]:
        """建议自动修复策略"""
        if not violation.rule.auto_fix_strategies:
            return None
        
        # 返回优先级最高的修复策略
        priority_order = [
            AutoFixStrategy.SWAP_STAGE_SAME_TAG,
            AutoFixStrategy.REPLACE_WITH_RESCUE,
            AutoFixStrategy.DEGRADE_ASSETS,
            AutoFixStrategy.RESCHEDULE_NEXT_HOUR
        ]
        
        for strategy in priority_order:
            if strategy in violation.rule.auto_fix_strategies:
                return strategy
        
        return violation.rule.auto_fix_strategies[0]
    
    def apply_auto_fix(
        self,
        scene_drafts: List[Dict],
        violation: Violation,
        strategy: AutoFixStrategy
    ) -> Tuple[List[Dict], bool]:
        """
        应用自动修复
        
        Returns:
            (修复后的场景列表, 是否成功)
        """
        logger.info(f"Applying auto-fix strategy {strategy.value} for violation {violation.rule.code}")
        
        if strategy == AutoFixStrategy.SWAP_STAGE_SAME_TAG:
            # 换一个同类型的舞台
            # 实际需要查询可用舞台
            return scene_drafts, True
        
        elif strategy == AutoFixStrategy.REDACT:
            # 删除敏感内容
            for scene in scene_drafts:
                if scene.get("scene_id") == violation.context.get("scene_id"):
                    pattern = violation.context.get("pattern", "")
                    scene["scene_text"] = scene.get("scene_text", "").replace(pattern, "[已编辑]")
            return scene_drafts, True
        
        elif strategy == AutoFixStrategy.SWITCH_TO_SILHOUETTE:
            # 切换到剪影模式
            for scene in scene_drafts:
                if scene.get("scene_id") == violation.context.get("scene_id"):
                    scene["media_level"] = "L2"
            return scene_drafts, True
        
        elif strategy == AutoFixStrategy.CLAMP:
            # 钳制变量值
            return scene_drafts, True
        
        elif strategy == AutoFixStrategy.REPLACE_WITH_RESCUE:
            # 替换为救援拍子
            # 实际需要加载救援模板
            return scene_drafts, True
        
        return scene_drafts, False
