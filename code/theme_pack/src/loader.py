"""
TheatreOS Theme Pack Loader
主题包加载器 - 负责从文件系统加载和解析主题包

支持的加载方式：
1. 从单个JSON文件加载完整主题包
2. 从目录结构加载分散的主题包文件
3. 从数据库加载已注册的主题包
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone

from .models import (
    ThemePack, ThemePackMetadata,
    WorldVariable, KeyObject, Faction, Character,
    Thread, ThreadPhase,
    BeatTemplate, BeatPreconditions, BeatSlots, BeatEffects, EvidenceOutput,
    GateTemplate, GateOption, GateStake,
    EvidenceType
)

logger = logging.getLogger(__name__)


class ThemePackLoader:
    """主题包加载器"""
    
    def __init__(self, packs_directory: str = None):
        """
        初始化加载器
        
        Args:
            packs_directory: 主题包存储目录，默认为 theme_pack/packs/
        """
        if packs_directory is None:
            # 默认目录
            base_dir = Path(__file__).parent.parent
            packs_directory = base_dir / "packs"
        
        self.packs_directory = Path(packs_directory)
        self._cache: Dict[str, ThemePack] = {}
        
        logger.info(f"ThemePackLoader initialized with packs directory: {self.packs_directory}")
    
    def load_pack(self, pack_id: str, force_reload: bool = False) -> ThemePack:
        """
        加载指定的主题包
        
        Args:
            pack_id: 主题包ID (如 "hp_shanghai_s1")
            force_reload: 是否强制重新加载（忽略缓存）
        
        Returns:
            ThemePack: 加载的主题包对象
        
        Raises:
            FileNotFoundError: 主题包不存在
            ValueError: 主题包格式错误
        """
        # 检查缓存
        if not force_reload and pack_id in self._cache:
            logger.debug(f"Loading pack {pack_id} from cache")
            return self._cache[pack_id]
        
        pack_path = self.packs_directory / pack_id
        
        if not pack_path.exists():
            raise FileNotFoundError(f"Theme pack not found: {pack_id}")
        
        # 尝试加载
        if (pack_path / "manifest.json").exists():
            # 从目录结构加载
            theme_pack = self._load_from_directory(pack_path)
        elif pack_path.suffix == ".json":
            # 从单个JSON文件加载
            theme_pack = self._load_from_json(pack_path)
        else:
            raise ValueError(f"Invalid theme pack format: {pack_id}")
        
        # 缓存
        self._cache[pack_id] = theme_pack
        logger.info(f"Theme pack loaded: {pack_id} (v{theme_pack.metadata.version})")
        
        return theme_pack
    
    def _load_from_directory(self, pack_path: Path) -> ThemePack:
        """从目录结构加载主题包"""
        
        # 加载清单文件
        manifest_path = pack_path / "manifest.json"
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # 解析元数据
        metadata = ThemePackMetadata(
            pack_id=manifest.get("pack_id", pack_path.name),
            name=manifest.get("name", ""),
            version=manifest.get("version", "1.0.0"),
            description=manifest.get("description", ""),
            season_id=manifest.get("season_id", ""),
            city=manifest.get("city", "shanghai"),
            created_at=manifest.get("created_at", ""),
            updated_at=manifest.get("updated_at", datetime.now(timezone.utc).isoformat())
        )
        
        # 加载各组件
        world_variables = self._load_world_variables(pack_path)
        key_objects = self._load_key_objects(pack_path)
        factions = self._load_factions(pack_path)
        characters = self._load_characters(pack_path)
        threads = self._load_threads(pack_path)
        beat_templates = self._load_beat_templates(pack_path)
        gate_templates = self._load_gate_templates(pack_path)
        evidence_types = self._load_evidence_types(pack_path)
        rescue_beats = self._load_rescue_beats(pack_path)
        
        return ThemePack(
            metadata=metadata,
            world_variables=world_variables,
            key_objects=key_objects,
            factions=factions,
            characters=characters,
            threads=threads,
            beat_templates=beat_templates,
            gate_templates=gate_templates,
            evidence_types=evidence_types,
            rescue_beats=rescue_beats
        )
    
    def _load_from_json(self, json_path: Path) -> ThemePack:
        """从单个JSON文件加载主题包"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self._parse_theme_pack_data(data)
    
    def _parse_theme_pack_data(self, data: Dict) -> ThemePack:
        """解析主题包数据"""
        
        # 元数据
        meta = data.get("metadata", {})
        metadata = ThemePackMetadata(
            pack_id=meta.get("pack_id", "unknown"),
            name=meta.get("name", ""),
            version=meta.get("version", "1.0.0"),
            description=meta.get("description", ""),
            season_id=meta.get("season_id", ""),
            city=meta.get("city", "shanghai"),
            created_at=meta.get("created_at", ""),
            updated_at=meta.get("updated_at", "")
        )
        
        # 世界变量
        world_variables = [
            WorldVariable(
                id=w.get("id"),
                name_cn=w.get("name_cn", w.get("cn", "")),
                description=w.get("description", w.get("desc", "")),
                default_value=w.get("default_value", 0.5),
                min_value=w.get("min_value", 0.0),
                max_value=w.get("max_value", 1.0),
                max_change_per_hour=w.get("max_change_per_hour", 0.15)
            )
            for w in data.get("world_variables", [])
        ]
        
        # 关键物品
        key_objects = [
            KeyObject(
                object_id=o.get("object_id"),
                name=o.get("name"),
                description=o.get("description", o.get("desc", "")),
                related_threads=o.get("related_threads", [])
            )
            for o in data.get("key_objects", data.get("objects", []))
        ]
        
        # 阵营
        factions = [
            Faction(
                faction_id=f.get("faction_id"),
                name=f.get("name"),
                style=f.get("style", ""),
                related_characters=f.get("related_characters", [])
            )
            for f in data.get("factions", [])
        ]
        
        # 角色
        characters = [
            Character(
                character_id=c.get("character_id"),
                name=c.get("name"),
                name_cn=c.get("name_cn", ""),
                faction=c.get("faction"),
                role=c.get("role", ""),
                public_goal=c.get("public_goal", ""),
                hidden_secret=c.get("hidden_secret", ""),
                voice_style=c.get("voice_style", ""),
                visual_style=c.get("visual_style", ""),
                forbidden_content=c.get("forbidden_content", []),
                allowed_beat_types=c.get("allowed_beat_types", [])
            )
            for c in data.get("characters", [])
        ]
        
        # 故事线
        threads = []
        for t in data.get("threads", []):
            phases = [
                ThreadPhase(
                    phase=p.get("phase"),
                    name_cn=p.get("name_cn", p.get("cn", "")),
                    goal=p.get("goal", ""),
                    allowed_beat_types=p.get("allowed_beat_types", [])
                )
                for p in t.get("phases", [])
            ]
            threads.append(Thread(
                thread_id=t.get("thread_id"),
                name=t.get("name"),
                logline=t.get("logline", ""),
                key_objects=t.get("key_objects", []),
                key_stages=t.get("key_stages", []),
                world_vars=t.get("world_vars", []),
                phases=phases,
                crosslinks=t.get("crosslinks", [])
            ))
        
        # 拍子模板
        beat_templates = self._parse_beat_templates(data.get("beat_templates", []))
        
        # 门模板
        gate_templates = self._parse_gate_templates(data.get("gate_templates", []))
        
        # 证物类型
        evidence_types = [
            EvidenceType(
                evidence_type_id=e.get("evidence_type_id"),
                name=e.get("name"),
                category=e.get("category", ""),
                description=e.get("description", ""),
                default_tier=e.get("default_tier", "B"),
                provenance_default=e.get("provenance_default", "onsite"),
                used_for=e.get("used_for", []),
                forgeability=e.get("forgeability", "medium"),
                expiry=e.get("expiry", "48h"),
                notes=e.get("notes", "")
            )
            for e in data.get("evidence_types", [])
        ]
        
        # 救援拍子
        rescue_beats = self._parse_beat_templates(data.get("rescue_beats", []))
        
        return ThemePack(
            metadata=metadata,
            world_variables=world_variables,
            key_objects=key_objects,
            factions=factions,
            characters=characters,
            threads=threads,
            beat_templates=beat_templates,
            gate_templates=gate_templates,
            evidence_types=evidence_types,
            rescue_beats=rescue_beats
        )
    
    def _parse_beat_templates(self, beats_data: List[Dict]) -> List[BeatTemplate]:
        """解析拍子模板列表"""
        templates = []
        for b in beats_data:
            # 前置条件
            pre = b.get("preconditions", {})
            preconditions = BeatPreconditions(
                thread_phase_in=pre.get("thread_phase_in", []),
                world_conditions=pre.get("world", {})
            )
            
            # 槽位
            slots_data = b.get("slots", {})
            slots = BeatSlots(
                stage_tag_any=slots_data.get("stage_tag_any", []),
                camera_style_any=slots_data.get("camera_style_any", []),
                mood_any=slots_data.get("mood_any", []),
                prop_any=slots_data.get("prop_any", [])
            )
            
            # 效果
            effects_data = b.get("effects", {})
            thread_effects = effects_data.get("thread", {})
            world_effects = effects_data.get("world", {})
            effects = BeatEffects(
                thread_progress_add=thread_effects.get("progress_add", 0),
                world_var_changes=world_effects
            )
            
            # 证物产出
            evidence_outputs = [
                EvidenceOutput(
                    evidence_type=e.get("type"),
                    tier=e.get("tier", "B"),
                    tags=e.get("tags", [])
                )
                for e in b.get("evidence_outputs", [])
            ]
            
            templates.append(BeatTemplate(
                beat_id=b.get("beat_id"),
                beat_type=b.get("type", ""),
                thread_id=b.get("thread_id", ""),
                cast_roles=b.get("cast_roles", []),
                preconditions=preconditions,
                slots=slots,
                effects=effects,
                evidence_outputs=evidence_outputs,
                optional_gate=b.get("optional_gate"),
                fallbacks=b.get("fallbacks", [])
            ))
        
        return templates
    
    def _parse_gate_templates(self, gates_data: List[Dict]) -> List[GateTemplate]:
        """解析门模板列表"""
        templates = []
        for g in gates_data:
            # 选项
            options = [
                GateOption(
                    option_id=o.get("id"),
                    label=o.get("label", "")
                )
                for o in g.get("options", [])
            ]
            
            # 下注配置
            stake_data = g.get("stake", {})
            stake = GateStake(
                currency=stake_data.get("currency", "ticket"),
                weight_rule=stake_data.get("weight_rule", "sqrt"),
                cap_by_cred=stake_data.get("cap_by_cred", True)
            )
            
            # 解释卡
            explain = g.get("explain_card", {})
            
            # 后果
            consequences = g.get("consequences", {})
            
            templates.append(GateTemplate(
                gate_id=g.get("gate_id"),
                gate_type=g.get("type", "public_vote"),
                title=g.get("title", ""),
                tags=g.get("tags", []),
                options=options,
                stake=stake,
                world_factors=g.get("world_factors", []),
                resolve_algorithm=g.get("resolve", {}).get("algorithm", "public_max_weight"),
                consequences_win=consequences.get("win", []),
                consequences_lose=consequences.get("lose", []),
                explain_card_title=explain.get("title", ""),
                explain_card_bullets=explain.get("bullets", [])
            ))
        
        return templates
    
    # 从目录加载各组件的辅助方法
    def _load_world_variables(self, pack_path: Path) -> List[WorldVariable]:
        """加载世界变量"""
        file_path = pack_path / "world_variables.json"
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [
            WorldVariable(
                id=w.get("id"),
                name_cn=w.get("name_cn", w.get("cn", "")),
                description=w.get("description", w.get("desc", "")),
                default_value=w.get("default_value", 0.5)
            )
            for w in data.get("world_vars", data)
        ]
    
    def _load_key_objects(self, pack_path: Path) -> List[KeyObject]:
        """加载关键物品"""
        file_path = pack_path / "objects.json"
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [
            KeyObject(
                object_id=o.get("object_id"),
                name=o.get("name"),
                description=o.get("description", o.get("desc", ""))
            )
            for o in data.get("objects", data)
        ]
    
    def _load_factions(self, pack_path: Path) -> List[Faction]:
        """加载阵营"""
        file_path = pack_path / "factions.json"
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [
            Faction(
                faction_id=f.get("faction_id"),
                name=f.get("name"),
                style=f.get("style", "")
            )
            for f in data.get("factions", data)
        ]
    
    def _load_characters(self, pack_path: Path) -> List[Character]:
        """加载角色"""
        file_path = pack_path / "characters.json"
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [
            Character(
                character_id=c.get("character_id"),
                name=c.get("name"),
                name_cn=c.get("name_cn", ""),
                faction=c.get("faction"),
                role=c.get("role", ""),
                public_goal=c.get("public_goal", ""),
                hidden_secret=c.get("hidden_secret", ""),
                voice_style=c.get("voice_style", ""),
                visual_style=c.get("visual_style", ""),
                forbidden_content=c.get("forbidden_content", []),
                allowed_beat_types=c.get("allowed_beat_types", [])
            )
            for c in data.get("characters", data)
        ]
    
    def _load_threads(self, pack_path: Path) -> List[Thread]:
        """加载故事线"""
        file_path = pack_path / "threads.json"
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        threads = []
        for t in data.get("threads", data):
            phases = [
                ThreadPhase(
                    phase=p.get("phase"),
                    name_cn=p.get("name_cn", p.get("cn", "")),
                    goal=p.get("goal", ""),
                    allowed_beat_types=p.get("allowed_beat_types", [])
                )
                for p in t.get("phases", [])
            ]
            threads.append(Thread(
                thread_id=t.get("thread_id"),
                name=t.get("name"),
                logline=t.get("logline", ""),
                key_objects=t.get("key_objects", []),
                key_stages=t.get("key_stages", []),
                world_vars=t.get("world_vars", []),
                phases=phases,
                crosslinks=t.get("crosslinks", [])
            ))
        return threads
    
    def _load_beat_templates(self, pack_path: Path) -> List[BeatTemplate]:
        """加载拍子模板"""
        file_path = pack_path / "beats.json"
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self._parse_beat_templates(data.get("beat_templates", data))
    
    def _load_gate_templates(self, pack_path: Path) -> List[GateTemplate]:
        """加载门模板"""
        file_path = pack_path / "gates.json"
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self._parse_gate_templates(data.get("gate_templates", data))
    
    def _load_evidence_types(self, pack_path: Path) -> List[EvidenceType]:
        """加载证物类型"""
        file_path = pack_path / "evidence.json"
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [
            EvidenceType(
                evidence_type_id=e.get("evidence_type_id"),
                name=e.get("name"),
                category=e.get("category", ""),
                description=e.get("description", ""),
                default_tier=e.get("default_tier", "B"),
                provenance_default=e.get("provenance_default", "onsite"),
                used_for=e.get("used_for", []),
                forgeability=e.get("forgeability", "medium"),
                expiry=e.get("expiry", "48h"),
                notes=e.get("notes", "")
            )
            for e in data.get("evidence_types", data)
        ]
    
    def _load_rescue_beats(self, pack_path: Path) -> List[BeatTemplate]:
        """加载救援拍子"""
        file_path = pack_path / "rescue_beats.json"
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self._parse_beat_templates(data.get("rescue_beats", data))
    
    def list_available_packs(self) -> List[str]:
        """列出所有可用的主题包"""
        if not self.packs_directory.exists():
            return []
        
        packs = []
        for item in self.packs_directory.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                packs.append(item.name)
            elif item.suffix == ".json":
                packs.append(item.stem)
        
        return packs
    
    def clear_cache(self, pack_id: str = None):
        """清除缓存"""
        if pack_id:
            self._cache.pop(pack_id, None)
        else:
            self._cache.clear()
        logger.info(f"Cache cleared: {pack_id or 'all'}")
