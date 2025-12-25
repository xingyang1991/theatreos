"""
TheatreOS Content Factory Orchestrator
内容生成编排器 - 将 HourPlan 编译成可上线的 SlotBundle

工作流程:
1. BeatPicker - 选择拍子模板
2. SlotFiller - 填充舞台/镜头/道具
3. SceneWriter - 生成场景草稿 (AI)
4. EvidenceInstantiator - 实例化证物
5. GatePlanner - 生成门厅文案
6. CanonGuard Compile - 连续性/安全检查
7. Render Pipeline - 媒体生成
8. Moderation - 审核
9. Publish - 发布
"""
import logging
import uuid
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from decimal import Decimal

from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.orm import Session, relationship
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kernel.src.database import Base, engine

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================
class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DEGRADED = "DEGRADED"  # 成功但降级


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class DegradeLevel(str, Enum):
    L0_NORMAL = "L0"      # 正常：视频+图+音+文本
    L1_LIGHT = "L1"       # 轻降级：图+音+文本（无视频）
    L2_HEAVY = "L2"       # 强降级：剪影图+音轨+证物卡
    L3_RESCUE = "L3"      # 救援拍子
    L4_SILENT = "L4"      # 静默slot


class CompilerResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"


# =============================================================================
# Database Models
# =============================================================================
class GenerationJob(Base):
    """生成任务"""
    __tablename__ = "generation_job"
    
    job_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    theatre_id = Column(String(36), nullable=False, index=True)
    slot_id = Column(String(50), nullable=False, index=True)
    status = Column(String(20), default=JobStatus.PENDING.value)
    degrade_level = Column(String(10), default=DegradeLevel.L0_NORMAL.value)
    deadline_at = Column(DateTime, nullable=False)
    attempt = Column(Integer, default=1)
    plan_hash = Column(String(64))  # HourPlan 的 hash，用于追溯
    fail_reason = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class GenerationStepLog(Base):
    """生成步骤日志"""
    __tablename__ = "generation_step_log"
    
    log_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("generation_job.job_id"), nullable=False, index=True)
    step_name = Column(String(50), nullable=False)
    step_order = Column(Integer, nullable=False)
    status = Column(String(20), default=StepStatus.PENDING.value)
    input_hash = Column(String(64))
    output_hash = Column(String(64))
    error_message = Column(Text)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_ms = Column(Integer)
    metadata_jsonb = Column(SQLiteJSON, default=dict)


class SceneDraft(Base):
    """场景草稿"""
    __tablename__ = "scene_draft"
    
    scene_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("generation_job.job_id"), nullable=False, index=True)
    slot_id = Column(String(50), nullable=False)
    stage_id = Column(String(50), nullable=False)
    thread_id = Column(String(50))
    beat_id = Column(String(50))
    ring_min = Column(String(1), default="C")
    draft_jsonb = Column(SQLiteJSON, default=dict)
    compiler_status = Column(String(20))
    compiler_errors = Column(SQLiteJSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RenderAsset(Base):
    """渲染资产"""
    __tablename__ = "render_asset"
    
    asset_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scene_id = Column(String(36), ForeignKey("scene_draft.scene_id"), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)  # video, image, audio, text
    provider = Column(String(50))  # openai, stability, local
    url = Column(Text)
    status = Column(String(20), default="PENDING")
    content_hash = Column(String(64))
    metadata_jsonb = Column(SQLiteJSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RescueBundle(Base):
    """救援包模板"""
    __tablename__ = "rescue_bundle"
    
    rescue_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    theatre_id = Column(String(36), nullable=False, index=True)
    rescue_type = Column(String(20), nullable=False)  # silent, aftermath, broadcast
    payload_jsonb = Column(SQLiteJSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Create tables
Base.metadata.create_all(engine)


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class BeatTemplate:
    """拍子模板"""
    beat_id: str
    beat_type: str  # reveal, confrontation, discovery, breath, aftermath
    intensity: str  # high, medium, low
    required_elements: List[str] = field(default_factory=list)
    camera_styles: List[str] = field(default_factory=list)
    mood_tags: List[str] = field(default_factory=list)


@dataclass
class SceneDraftData:
    """场景草稿数据"""
    scene_id: str
    stage_id: str
    thread_id: str
    beat_id: str
    camera_style: str
    mood: str
    scene_text: str
    dialogue: List[List[str]]
    evidence_outputs: List[Dict]
    gate_lobby_copy: str
    ring_min: str = "C"
    media_level: str = "L0"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SlotBundle:
    """场次发布包"""
    slot_id: str
    theatre_id: str
    scenes: List[SceneDraftData]
    gate_instance_id: str
    gate_config: Dict
    must_drop_evidence: List[Dict]
    degrade_level: str
    source_job_id: str
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "slot_id": self.slot_id,
            "theatre_id": self.theatre_id,
            "scenes": [s.to_dict() for s in self.scenes],
            "gate_instance_id": self.gate_instance_id,
            "gate_config": self.gate_config,
            "must_drop_evidence": self.must_drop_evidence,
            "degrade_level": self.degrade_level,
            "source_job_id": self.source_job_id,
            "notes": self.notes
        }


@dataclass
class CompileError:
    """编译错误"""
    code: str
    name: str
    severity: str
    message: str
    auto_fix_applied: Optional[str] = None


@dataclass
class CompileResult:
    """编译结果"""
    status: CompilerResult
    errors: List[CompileError]
    warnings: List[CompileError]
    score: float
    auto_fixes_applied: List[str]


# =============================================================================
# Content Factory Orchestrator
# =============================================================================
class ContentFactoryOrchestrator:
    """内容工厂编排器"""
    
    WORKFLOW_STEPS = [
        "beat_picker",
        "slot_filler",
        "scene_writer",
        "evidence_instantiator",
        "gate_planner",
        "canon_guard_compile",
        "render_pipeline",
        "moderation",
        "publish"
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self.canon_guard = CanonGuardCompiler(db)
        self.scene_writer = AISceneWriter()
        self.render_pipeline = RenderPipeline()
    
    def create_job(
        self,
        theatre_id: str,
        slot_id: str,
        hour_plan: Any,
        deadline_minutes_before: int = 5
    ) -> GenerationJob:
        """创建生成任务"""
        # 计算 deadline（开演前 N 分钟）
        slot_start = hour_plan.start_at
        deadline = slot_start - timedelta(minutes=deadline_minutes_before)
        
        # 计算 plan hash
        plan_data = {
            "slot_id": slot_id,
            "theatre_id": theatre_id,
            "primary_thread": hour_plan.primary_thread,
            "scenes_parallel": hour_plan.scenes_parallel,
            "hour_gate": hour_plan.hour_gate_jsonb
        }
        plan_hash = hashlib.sha256(json.dumps(plan_data, sort_keys=True).encode()).hexdigest()[:16]
        
        job = GenerationJob(
            theatre_id=theatre_id,
            slot_id=slot_id,
            deadline_at=deadline,
            plan_hash=plan_hash
        )
        self.db.add(job)
        self.db.commit()
        
        logger.info(f"Created generation job {job.job_id} for slot {slot_id}")
        return job
    
    def run_workflow(
        self,
        job_id: str,
        hour_plan: Any,
        world_state: Dict
    ) -> Tuple[SlotBundle, DegradeLevel]:
        """
        运行完整的生成工作流
        
        返回: (SlotBundle, DegradeLevel)
        """
        job = self.db.query(GenerationJob).filter(GenerationJob.job_id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = JobStatus.RUNNING.value
        self.db.commit()
        
        current_degrade = DegradeLevel.L0_NORMAL
        scenes: List[SceneDraftData] = []
        
        try:
            # Step 1: Beat Picker
            self._log_step_start(job_id, "beat_picker", 1)
            beats = self._pick_beats(hour_plan, world_state)
            self._log_step_end(job_id, "beat_picker", StepStatus.SUCCESS)
            
            # Step 2: Slot Filler
            self._log_step_start(job_id, "slot_filler", 2)
            filled_slots = self._fill_slots(beats, hour_plan)
            self._log_step_end(job_id, "slot_filler", StepStatus.SUCCESS)
            
            # Step 3: Scene Writer (AI)
            self._log_step_start(job_id, "scene_writer", 3)
            scene_drafts = self._write_scenes(filled_slots, world_state, job_id)
            self._log_step_end(job_id, "scene_writer", StepStatus.SUCCESS)
            
            # Step 4: Evidence Instantiator
            self._log_step_start(job_id, "evidence_instantiator", 4)
            evidence_list = self._instantiate_evidence(scene_drafts, hour_plan)
            self._log_step_end(job_id, "evidence_instantiator", StepStatus.SUCCESS)
            
            # Step 5: Gate Planner
            self._log_step_start(job_id, "gate_planner", 5)
            gate_config = self._plan_gate(hour_plan, scene_drafts)
            self._log_step_end(job_id, "gate_planner", StepStatus.SUCCESS)
            
            # Step 6: CanonGuard Compile
            self._log_step_start(job_id, "canon_guard_compile", 6)
            compile_result = self.canon_guard.compile(
                scene_drafts=scene_drafts,
                evidence_list=evidence_list,
                gate_config=gate_config,
                world_state=world_state,
                hour_plan=hour_plan
            )
            
            if compile_result.status == CompilerResult.FAIL:
                # 尝试自动修复
                scene_drafts, compile_result = self._auto_fix(
                    scene_drafts, compile_result, world_state, hour_plan
                )
                if compile_result.status == CompilerResult.FAIL:
                    # 自动修复失败，使用救援拍子
                    current_degrade = DegradeLevel.L3_RESCUE
                    scene_drafts = self._get_rescue_scenes(job.theatre_id, hour_plan)
            
            self._log_step_end(job_id, "canon_guard_compile", StepStatus.SUCCESS, {
                "compile_status": compile_result.status.value,
                "score": compile_result.score
            })
            
            # Step 7: Render Pipeline
            self._log_step_start(job_id, "render_pipeline", 7)
            rendered_scenes, render_degrade = self.render_pipeline.render(
                scene_drafts, current_degrade
            )
            if render_degrade.value > current_degrade.value:
                current_degrade = render_degrade
            self._log_step_end(job_id, "render_pipeline", StepStatus.SUCCESS, {
                "degrade_level": current_degrade.value
            })
            
            # Step 8: Moderation
            self._log_step_start(job_id, "moderation", 8)
            moderated_scenes = self._moderate(rendered_scenes)
            self._log_step_end(job_id, "moderation", StepStatus.SUCCESS)
            
            scenes = moderated_scenes
            
            # Step 9: Publish
            self._log_step_start(job_id, "publish", 9)
            slot_bundle = SlotBundle(
                slot_id=hour_plan.slot_id,
                theatre_id=job.theatre_id,
                scenes=scenes,
                gate_instance_id=str(uuid.uuid4()),
                gate_config=gate_config,
                must_drop_evidence=evidence_list,
                degrade_level=current_degrade.value,
                source_job_id=job_id
            )
            self._log_step_end(job_id, "publish", StepStatus.SUCCESS)
            
            # 更新任务状态
            job.status = JobStatus.SUCCESS.value if current_degrade == DegradeLevel.L0_NORMAL else JobStatus.DEGRADED.value
            job.degrade_level = current_degrade.value
            self.db.commit()
            
            logger.info(f"Workflow completed for job {job_id}, degrade_level={current_degrade.value}")
            return slot_bundle, current_degrade
            
        except Exception as e:
            logger.error(f"Workflow failed for job {job_id}: {e}")
            job.status = JobStatus.FAILED.value
            job.fail_reason = str(e)
            self.db.commit()
            
            # 返回静默 slot 作为最终兜底
            return self._create_silent_slot(job, hour_plan), DegradeLevel.L4_SILENT
    
    def _log_step_start(self, job_id: str, step_name: str, step_order: int):
        """记录步骤开始"""
        log = GenerationStepLog(
            job_id=job_id,
            step_name=step_name,
            step_order=step_order,
            status=StepStatus.RUNNING.value,
            started_at=datetime.now(timezone.utc)
        )
        self.db.add(log)
        self.db.commit()
    
    def _log_step_end(
        self,
        job_id: str,
        step_name: str,
        status: StepStatus,
        metadata: Dict = None
    ):
        """记录步骤结束"""
        log = self.db.query(GenerationStepLog).filter(
            GenerationStepLog.job_id == job_id,
            GenerationStepLog.step_name == step_name
        ).first()
        
        if log:
            log.status = status.value
            log.ended_at = datetime.now(timezone.utc)
            if log.started_at:
                log.duration_ms = int((log.ended_at - log.started_at).total_seconds() * 1000)
            if metadata:
                log.metadata_jsonb = metadata
            self.db.commit()
    
    def _pick_beats(self, hour_plan: Any, world_state: Dict) -> List[BeatTemplate]:
        """选择拍子模板"""
        # 根据 hour_plan 的 target_beat_mix 选择拍子
        beat_mix = hour_plan.beat_mix_jsonb or {"reveal": 2, "breath": 1, "confrontation": 1}
        
        beats = []
        for beat_type, count in beat_mix.items():
            for i in range(count):
                beat = BeatTemplate(
                    beat_id=f"bt_{beat_type}_{i+1:03d}",
                    beat_type=beat_type,
                    intensity="high" if beat_type in ["reveal", "confrontation"] else "low",
                    camera_styles=["cctv", "drone", "pov"],
                    mood_tags=["ominous", "tense"] if beat_type == "reveal" else ["calm", "reflective"]
                )
                beats.append(beat)
        
        return beats
    
    def _fill_slots(self, beats: List[BeatTemplate], hour_plan: Any) -> List[Dict]:
        """填充场次槽位"""
        filled = []
        stages = ["stg_001", "stg_002", "stg_003"]  # 从 hour_plan 或配置获取
        
        for i, beat in enumerate(beats):
            filled.append({
                "beat": beat,
                "stage_id": stages[i % len(stages)],
                "camera_style": beat.camera_styles[0] if beat.camera_styles else "cctv",
                "thread_id": hour_plan.primary_thread or "thread_01"
            })
        
        return filled
    
    def _write_scenes(
        self,
        filled_slots: List[Dict],
        world_state: Dict,
        job_id: str
    ) -> List[SceneDraftData]:
        """使用 AI 生成场景"""
        scenes = []
        
        for slot in filled_slots:
            beat = slot["beat"]
            
            # 调用 AI 生成
            draft = self.scene_writer.write_scene(
                beat_template=beat,
                stage_id=slot["stage_id"],
                thread_id=slot["thread_id"],
                world_state=world_state
            )
            
            # 保存到数据库
            scene_record = SceneDraft(
                scene_id=draft.scene_id,
                job_id=job_id,
                slot_id=slot.get("slot_id", ""),
                stage_id=draft.stage_id,
                thread_id=draft.thread_id,
                beat_id=draft.beat_id,
                ring_min=draft.ring_min,
                draft_jsonb=draft.to_dict()
            )
            self.db.add(scene_record)
            scenes.append(draft)
        
        self.db.commit()
        return scenes
    
    def _instantiate_evidence(
        self,
        scene_drafts: List[SceneDraftData],
        hour_plan: Any
    ) -> List[Dict]:
        """实例化证物"""
        evidence_list = []
        
        for scene in scene_drafts:
            for ev in scene.evidence_outputs:
                evidence_instance = {
                    "evidence_id": str(uuid.uuid4()),
                    "evidence_type_id": ev.get("evidence_type_id", "ev_generic"),
                    "tier": ev.get("tier", "C"),
                    "source_scene_id": scene.scene_id,
                    "ttl_hours": ev.get("ttl_hours", 24),
                    "must_drop": ev.get("must_drop", False)
                }
                evidence_list.append(evidence_instance)
        
        return evidence_list
    
    def _plan_gate(self, hour_plan: Any, scene_drafts: List[SceneDraftData]) -> Dict:
        """规划门厅"""
        gate_config = hour_plan.hour_gate_jsonb or {
            "type": "Public",
            "title": f"Gate for {hour_plan.slot_id}",
            "options": [
                {"option_id": "opt_a", "label": "选项A：追查线索"},
                {"option_id": "opt_b", "label": "选项B：静观其变"}
            ]
        }
        
        # 从场景中提取门厅文案
        if scene_drafts:
            gate_config["lobby_copy"] = scene_drafts[0].gate_lobby_copy or "命运的天平正在倾斜..."
        
        return gate_config
    
    def _auto_fix(
        self,
        scene_drafts: List[SceneDraftData],
        compile_result: CompileResult,
        world_state: Dict,
        hour_plan: Any
    ) -> Tuple[List[SceneDraftData], CompileResult]:
        """自动修复编译错误"""
        max_attempts = 2
        
        for attempt in range(max_attempts):
            # 应用自动修复策略
            for error in compile_result.errors:
                if error.code == "CG001":  # 角色时空冲突
                    # 重新调度场景
                    pass
                elif error.code == "CG006":  # 越权生成实体
                    # 重写 prompt
                    pass
            
            # 重新编译
            new_result = self.canon_guard.compile(
                scene_drafts=scene_drafts,
                evidence_list=[],
                gate_config={},
                world_state=world_state,
                hour_plan=hour_plan
            )
            
            if new_result.status != CompilerResult.FAIL:
                return scene_drafts, new_result
        
        return scene_drafts, compile_result
    
    def _get_rescue_scenes(self, theatre_id: str, hour_plan: Any) -> List[SceneDraftData]:
        """获取救援场景"""
        # 查找预生成的救援包
        rescue = self.db.query(RescueBundle).filter(
            RescueBundle.theatre_id == theatre_id
        ).first()
        
        if rescue:
            return [SceneDraftData(**s) for s in rescue.payload_jsonb.get("scenes", [])]
        
        # 生成默认救援场景
        return [SceneDraftData(
            scene_id=str(uuid.uuid4()),
            stage_id="stg_rescue",
            thread_id="thread_rescue",
            beat_id="bt_rescue_001",
            camera_style="static",
            mood="mysterious",
            scene_text="信号在迷雾中若隐若现，真相仍在等待被揭示...",
            dialogue=[],
            evidence_outputs=[],
            gate_lobby_copy="迷雾笼罩，请稍后再试",
            ring_min="C",
            media_level="L3"
        )]
    
    def _moderate(self, scenes: List[SceneDraftData]) -> List[SceneDraftData]:
        """内容审核"""
        # P0 阶段只做基础关键词过滤
        moderated = []
        
        for scene in scenes:
            # 简单的关键词检查
            text = scene.scene_text.lower()
            if any(word in text for word in ["暴力", "血腥", "政治"]):
                # 降级为剪影模式
                scene.media_level = "L2"
            moderated.append(scene)
        
        return moderated
    
    def _create_silent_slot(self, job: GenerationJob, hour_plan: Any) -> SlotBundle:
        """创建静默 slot（最终兜底）"""
        silent_scene = SceneDraftData(
            scene_id=str(uuid.uuid4()),
            stage_id="stg_silent",
            thread_id="thread_silent",
            beat_id="bt_silent_001",
            camera_style="static",
            mood="mysterious",
            scene_text="信号被迷雾吞没，世界暂时沉寂...",
            dialogue=[],
            evidence_outputs=[],
            gate_lobby_copy="信号中断，门厅仍可结算",
            ring_min="C",
            media_level="L4"
        )
        
        return SlotBundle(
            slot_id=hour_plan.slot_id,
            theatre_id=job.theatre_id,
            scenes=[silent_scene],
            gate_instance_id=str(uuid.uuid4()),
            gate_config=hour_plan.hour_gate_jsonb or {"type": "Public"},
            must_drop_evidence=[],
            degrade_level=DegradeLevel.L4_SILENT.value,
            source_job_id=job.job_id,
            notes="Silent slot due to generation failure"
        )


# =============================================================================
# CanonGuard Compiler
# =============================================================================
class CanonGuardCompiler:
    """连续性编译器"""
    
    # 硬性规则
    HARD_RULES = {
        "CG001": {"name": "角色时空冲突", "severity": "FAIL"},
        "CG002": {"name": "物件归属冲突", "severity": "FAIL"},
        "CG003": {"name": "世界变量越界", "severity": "FAIL"},
        "CG004": {"name": "门非法", "severity": "FAIL"},
        "CG005": {"name": "隐私/安全违规", "severity": "FAIL"},
        "CG006": {"name": "越权生成实体", "severity": "FAIL"},
        "CG007": {"name": "must_drop未满足", "severity": "FAIL"},
    }
    
    # 预算限制
    BUDGETS = {
        "per_hour": {
            "max_high_intensity_beats": 4,
            "min_breath_beats": 1,
            "max_gates_total": 3,
            "max_A_tier_evidence": 2,
            "max_repeat_same_stage": 3
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def compile(
        self,
        scene_drafts: List[SceneDraftData],
        evidence_list: List[Dict],
        gate_config: Dict,
        world_state: Dict,
        hour_plan: Any
    ) -> CompileResult:
        """编译场景草稿"""
        errors = []
        warnings = []
        auto_fixes = []
        
        # 检查硬性规则
        errors.extend(self._check_character_conflicts(scene_drafts))
        errors.extend(self._check_entity_whitelist(scene_drafts))
        errors.extend(self._check_safety(scene_drafts))
        errors.extend(self._check_world_var_bounds(scene_drafts, world_state))
        errors.extend(self._check_gate_validity(gate_config))
        errors.extend(self._check_must_drop(evidence_list, hour_plan))
        
        # 检查预算
        warnings.extend(self._check_budgets(scene_drafts, evidence_list))
        
        # 计算质量分数
        score = self._calculate_score(scene_drafts, warnings)
        
        # 确定编译状态
        if any(e.severity == "FAIL" for e in errors):
            status = CompilerResult.FAIL
        elif warnings:
            status = CompilerResult.WARN
        else:
            status = CompilerResult.PASS
        
        return CompileResult(
            status=status,
            errors=errors,
            warnings=warnings,
            score=score,
            auto_fixes_applied=auto_fixes
        )
    
    def _check_character_conflicts(self, scenes: List[SceneDraftData]) -> List[CompileError]:
        """检查角色时空冲突"""
        errors = []
        # 简化实现：检查同一角色是否同时出现在多个场景
        # 实际需要解析 dialogue 中的角色
        return errors
    
    def _check_entity_whitelist(self, scenes: List[SceneDraftData]) -> List[CompileError]:
        """检查实体白名单"""
        errors = []
        # 检查是否引用了白名单之外的实体
        # 实际需要加载 EntityRegistry
        return errors
    
    def _check_safety(self, scenes: List[SceneDraftData]) -> List[CompileError]:
        """检查安全违规"""
        errors = []
        
        dangerous_patterns = [
            "真实地址", "身份证", "电话号码", "银行卡",
            "制作炸弹", "自杀方法", "毒品配方"
        ]
        
        for scene in scenes:
            text = scene.scene_text
            for pattern in dangerous_patterns:
                if pattern in text:
                    errors.append(CompileError(
                        code="CG005",
                        name="隐私/安全违规",
                        severity="FAIL",
                        message=f"场景 {scene.scene_id} 包含危险内容: {pattern}"
                    ))
        
        return errors
    
    def _check_world_var_bounds(
        self,
        scenes: List[SceneDraftData],
        world_state: Dict
    ) -> List[CompileError]:
        """检查世界变量边界"""
        errors = []
        # 检查变量是否在 [0, 1] 范围内
        # 检查每小时变化是否 <= 0.15
        return errors
    
    def _check_gate_validity(self, gate_config: Dict) -> List[CompileError]:
        """检查门有效性"""
        errors = []
        
        if not gate_config.get("options"):
            errors.append(CompileError(
                code="CG004",
                name="门非法",
                severity="FAIL",
                message="门配置缺少选项"
            ))
        
        return errors
    
    def _check_must_drop(
        self,
        evidence_list: List[Dict],
        hour_plan: Any
    ) -> List[CompileError]:
        """检查必须掉落的证物"""
        errors = []
        # 检查 hour_plan 中的 must_drop 是否都有对应的证物实例
        return errors
    
    def _check_budgets(
        self,
        scenes: List[SceneDraftData],
        evidence_list: List[Dict]
    ) -> List[CompileError]:
        """检查预算限制"""
        warnings = []
        
        # 统计高强度拍子
        high_intensity_count = sum(
            1 for s in scenes if s.mood in ["ominous", "tense", "confrontational"]
        )
        
        if high_intensity_count > self.BUDGETS["per_hour"]["max_high_intensity_beats"]:
            warnings.append(CompileError(
                code="CB001",
                name="高强度拍子超限",
                severity="WARN",
                message=f"高强度拍子数量 {high_intensity_count} 超过限制 {self.BUDGETS['per_hour']['max_high_intensity_beats']}"
            ))
        
        # 统计 A 级证物
        a_tier_count = sum(1 for e in evidence_list if e.get("tier") == "A")
        if a_tier_count > self.BUDGETS["per_hour"]["max_A_tier_evidence"]:
            warnings.append(CompileError(
                code="CB002",
                name="A级证物超限",
                severity="WARN",
                message=f"A级证物数量 {a_tier_count} 超过限制 {self.BUDGETS['per_hour']['max_A_tier_evidence']}"
            ))
        
        return warnings
    
    def _calculate_score(
        self,
        scenes: List[SceneDraftData],
        warnings: List[CompileError]
    ) -> float:
        """计算质量分数"""
        base_score = 1.0
        
        # 每个警告扣分
        warning_penalty = len(warnings) * 0.05
        
        # 场景多样性加分
        unique_stages = len(set(s.stage_id for s in scenes))
        diversity_bonus = min(unique_stages * 0.02, 0.1)
        
        score = max(0, min(1, base_score - warning_penalty + diversity_bonus))
        return round(score, 2)


# =============================================================================
# AI Scene Writer
# =============================================================================
class AISceneWriter:
    """AI 场景生成器"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化 OpenAI 客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    def write_scene(
        self,
        beat_template: BeatTemplate,
        stage_id: str,
        thread_id: str,
        world_state: Dict
    ) -> SceneDraftData:
        """生成场景"""
        
        if self.client:
            try:
                return self._write_with_ai(beat_template, stage_id, thread_id, world_state)
            except Exception as e:
                logger.warning(f"AI generation failed, using fallback: {e}")
        
        # Fallback: 使用模板生成
        return self._write_with_template(beat_template, stage_id, thread_id)
    
    def _write_with_ai(
        self,
        beat_template: BeatTemplate,
        stage_id: str,
        thread_id: str,
        world_state: Dict
    ) -> SceneDraftData:
        """使用 AI 生成场景"""
        
        prompt = f"""你是 TheatreOS 的剧本生成器。请根据以下信息生成一个场景：

拍子类型: {beat_template.beat_type}
强度: {beat_template.intensity}
舞台: {stage_id}
叙事线: {thread_id}
世界状态: 紧张度={world_state.get('vars', {}).get('tension', 0.5)}

请生成一个 200-500 字的镜头化场景描述，包含：
1. 场景文本（scene_text）：镜头化描述，像电影剧本
2. 对白（dialogue）：每句 <= 16 字
3. 证物提示（evidence_hints）：可能掉落的证物类型
4. 门厅文案（gate_lobby_copy）：<= 80 字

输出 JSON 格式：
{{
  "scene_text": "...",
  "dialogue": [["角色A", "台词1"], ["角色B", "台词2"]],
  "evidence_hints": ["信号碎片", "神秘便条"],
  "gate_lobby_copy": "..."
}}
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1000
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return SceneDraftData(
            scene_id=str(uuid.uuid4()),
            stage_id=stage_id,
            thread_id=thread_id,
            beat_id=beat_template.beat_id,
            camera_style=beat_template.camera_styles[0] if beat_template.camera_styles else "cctv",
            mood=beat_template.mood_tags[0] if beat_template.mood_tags else "neutral",
            scene_text=result.get("scene_text", ""),
            dialogue=result.get("dialogue", []),
            evidence_outputs=[
                {"evidence_type_id": f"ev_{hint.replace(' ', '_')}", "tier": "C"}
                for hint in result.get("evidence_hints", [])
            ],
            gate_lobby_copy=result.get("gate_lobby_copy", "")
        )
    
    def _write_with_template(
        self,
        beat_template: BeatTemplate,
        stage_id: str,
        thread_id: str
    ) -> SceneDraftData:
        """使用模板生成场景（Fallback）"""
        
        templates = {
            "reveal": {
                "scene_text": "监控画面闪烁，一个模糊的身影出现在画面边缘。镜头缓缓推进，揭示出一个被遗忘的角落。空气中弥漫着紧张的气息，仿佛有什么即将发生...",
                "dialogue": [["神秘人", "真相从不会被永远掩埋"], ["旁白", "信号开始不稳定"]],
                "evidence_hints": ["信号碎片", "模糊影像"],
                "gate_lobby_copy": "真相的碎片正在浮现，你准备好了吗？"
            },
            "confrontation": {
                "scene_text": "两个身影在昏暗的灯光下对峙。空气凝固，时间仿佛停滞。每一个细微的动作都可能改变局势的走向...",
                "dialogue": [["人物A", "你知道得太多了"], ["人物B", "这才刚刚开始"]],
                "evidence_hints": ["对话录音", "紧张气氛"],
                "gate_lobby_copy": "对峙已经开始，选择你的立场"
            },
            "breath": {
                "scene_text": "城市的喧嚣渐渐远去，镜头定格在一个宁静的角落。短暂的平静中，隐藏着下一场风暴的预兆...",
                "dialogue": [],
                "evidence_hints": ["环境线索"],
                "gate_lobby_copy": "暴风雨前的宁静..."
            }
        }
        
        template = templates.get(beat_template.beat_type, templates["breath"])
        
        return SceneDraftData(
            scene_id=str(uuid.uuid4()),
            stage_id=stage_id,
            thread_id=thread_id,
            beat_id=beat_template.beat_id,
            camera_style=beat_template.camera_styles[0] if beat_template.camera_styles else "cctv",
            mood=beat_template.mood_tags[0] if beat_template.mood_tags else "neutral",
            scene_text=template["scene_text"],
            dialogue=template["dialogue"],
            evidence_outputs=[
                {"evidence_type_id": f"ev_{hint.replace(' ', '_')}", "tier": "C"}
                for hint in template["evidence_hints"]
            ],
            gate_lobby_copy=template["gate_lobby_copy"]
        )


# =============================================================================
# Render Pipeline
# =============================================================================
class RenderPipeline:
    """渲染管线"""
    
    def render(
        self,
        scenes: List[SceneDraftData],
        current_degrade: DegradeLevel
    ) -> Tuple[List[SceneDraftData], DegradeLevel]:
        """渲染场景资产"""
        
        rendered_scenes = []
        final_degrade = current_degrade
        
        for scene in scenes:
            try:
                if current_degrade == DegradeLevel.L0_NORMAL:
                    # 尝试生成完整资产
                    # 实际实现需要调用视频/图片/音频生成 API
                    scene.media_level = "L0"
                elif current_degrade == DegradeLevel.L1_LIGHT:
                    scene.media_level = "L1"
                elif current_degrade == DegradeLevel.L2_HEAVY:
                    scene.media_level = "L2"
                else:
                    scene.media_level = current_degrade.value
                
                rendered_scenes.append(scene)
                
            except Exception as e:
                logger.warning(f"Render failed for scene {scene.scene_id}: {e}")
                # 降级
                if final_degrade == DegradeLevel.L0_NORMAL:
                    final_degrade = DegradeLevel.L1_LIGHT
                scene.media_level = final_degrade.value
                rendered_scenes.append(scene)
        
        return rendered_scenes, final_degrade


# =============================================================================
# Service Interface
# =============================================================================
class ContentFactoryService:
    """Content Factory 服务接口"""
    
    def __init__(self, db: Session):
        self.db = db
        self.orchestrator = ContentFactoryOrchestrator(db)
    
    def generate_slot(
        self,
        theatre_id: str,
        slot_id: str,
        hour_plan: Any,
        world_state: Dict
    ) -> SlotBundle:
        """生成 slot 内容"""
        
        # 创建任务
        job = self.orchestrator.create_job(theatre_id, slot_id, hour_plan)
        
        # 运行工作流
        slot_bundle, degrade_level = self.orchestrator.run_workflow(
            job.job_id, hour_plan, world_state
        )
        
        return slot_bundle
    
    def get_job_status(self, job_id: str) -> Dict:
        """获取任务状态"""
        job = self.db.query(GenerationJob).filter(GenerationJob.job_id == job_id).first()
        
        if not job:
            return {"error": "Job not found"}
        
        steps = self.db.query(GenerationStepLog).filter(
            GenerationStepLog.job_id == job_id
        ).order_by(GenerationStepLog.step_order).all()
        
        return {
            "job_id": job.job_id,
            "theatre_id": job.theatre_id,
            "slot_id": job.slot_id,
            "status": job.status,
            "degrade_level": job.degrade_level,
            "attempt": job.attempt,
            "deadline_at": job.deadline_at.isoformat() if job.deadline_at else None,
            "fail_reason": job.fail_reason,
            "steps": [
                {
                    "step_name": s.step_name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error_message
                }
                for s in steps
            ]
        }
