"""
TheatreOS Theme Pack Manager
主题包管理服务 - 提供主题包的注册、查询、切换等功能

核心功能：
1. 主题包注册与管理
2. 剧场与主题包的绑定
3. 运行时主题包切换
4. 主题包内容查询接口
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path

from .models import ThemePack, Character, Thread, BeatTemplate, GateTemplate, EvidenceType
from .loader import ThemePackLoader

logger = logging.getLogger(__name__)


class ThemePackManager:
    """主题包管理器 - 单例模式"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, packs_directory: str = None):
        if self._initialized:
            return
        
        self._loader = ThemePackLoader(packs_directory)
        self._active_packs: Dict[str, ThemePack] = {}  # theatre_id -> ThemePack
        self._default_pack_id: str = "hp_shanghai_s1"
        self._initialized = True
        
        logger.info("ThemePackManager initialized")
    
    # =========================================================================
    # 主题包加载与管理
    # =========================================================================
    
    def load_pack(self, pack_id: str, force_reload: bool = False) -> ThemePack:
        """
        加载主题包
        
        Args:
            pack_id: 主题包ID
            force_reload: 是否强制重新加载
        
        Returns:
            ThemePack: 加载的主题包
        """
        return self._loader.load_pack(pack_id, force_reload)
    
    def list_available_packs(self) -> List[Dict]:
        """
        列出所有可用的主题包
        
        Returns:
            List[Dict]: 主题包信息列表
        """
        pack_ids = self._loader.list_available_packs()
        result = []
        
        for pack_id in pack_ids:
            try:
                pack = self._loader.load_pack(pack_id)
                result.append({
                    "pack_id": pack_id,
                    "name": pack.metadata.name,
                    "version": pack.metadata.version,
                    "description": pack.metadata.description,
                    "season_id": pack.metadata.season_id,
                    "city": pack.metadata.city,
                    "stats": {
                        "characters": len(pack.characters),
                        "threads": len(pack.threads),
                        "beat_templates": len(pack.beat_templates),
                        "gate_templates": len(pack.gate_templates),
                        "evidence_types": len(pack.evidence_types),
                        "rescue_beats": len(pack.rescue_beats)
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to load pack {pack_id}: {e}")
                result.append({
                    "pack_id": pack_id,
                    "error": str(e)
                })
        
        return result
    
    def set_default_pack(self, pack_id: str):
        """设置默认主题包"""
        # 验证主题包存在
        self._loader.load_pack(pack_id)
        self._default_pack_id = pack_id
        logger.info(f"Default pack set to: {pack_id}")
    
    # =========================================================================
    # 剧场主题包绑定
    # =========================================================================
    
    def bind_theatre(self, theatre_id: str, pack_id: str = None) -> ThemePack:
        """
        为剧场绑定主题包
        
        Args:
            theatre_id: 剧场ID
            pack_id: 主题包ID，为None时使用默认主题包
        
        Returns:
            ThemePack: 绑定的主题包
        """
        pack_id = pack_id or self._default_pack_id
        pack = self._loader.load_pack(pack_id)
        self._active_packs[theatre_id] = pack
        
        logger.info(f"Theatre {theatre_id} bound to pack {pack_id}")
        return pack
    
    def get_theatre_pack(self, theatre_id: str) -> ThemePack:
        """
        获取剧场的主题包
        
        Args:
            theatre_id: 剧场ID
        
        Returns:
            ThemePack: 剧场的主题包
        
        Raises:
            KeyError: 剧场未绑定主题包
        """
        if theatre_id not in self._active_packs:
            # 自动绑定默认主题包
            return self.bind_theatre(theatre_id)
        
        return self._active_packs[theatre_id]
    
    def switch_theatre_pack(self, theatre_id: str, new_pack_id: str) -> ThemePack:
        """
        切换剧场的主题包
        
        Args:
            theatre_id: 剧场ID
            new_pack_id: 新主题包ID
        
        Returns:
            ThemePack: 新的主题包
        """
        pack = self._loader.load_pack(new_pack_id)
        self._active_packs[theatre_id] = pack
        
        logger.info(f"Theatre {theatre_id} switched to pack {new_pack_id}")
        return pack
    
    def unbind_theatre(self, theatre_id: str):
        """解除剧场的主题包绑定"""
        if theatre_id in self._active_packs:
            del self._active_packs[theatre_id]
            logger.info(f"Theatre {theatre_id} unbound from pack")
    
    # =========================================================================
    # 内容查询接口 - 角色
    # =========================================================================
    
    def get_character(self, theatre_id: str, character_id: str) -> Optional[Character]:
        """获取角色"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_character(character_id)
    
    def get_characters_by_faction(self, theatre_id: str, faction_id: str) -> List[Character]:
        """获取阵营的所有角色"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_characters_by_faction(faction_id)
    
    def list_characters(self, theatre_id: str) -> List[Dict]:
        """列出所有角色"""
        pack = self.get_theatre_pack(theatre_id)
        return [c.to_dict() for c in pack.characters]
    
    def is_valid_character(self, theatre_id: str, character_id: str) -> bool:
        """检查角色是否有效（白名单检查）"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_character(character_id) is not None
    
    # =========================================================================
    # 内容查询接口 - 故事线
    # =========================================================================
    
    def get_thread(self, theatre_id: str, thread_id: str) -> Optional[Thread]:
        """获取故事线"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_thread(thread_id)
    
    def list_threads(self, theatre_id: str) -> List[Dict]:
        """列出所有故事线"""
        pack = self.get_theatre_pack(theatre_id)
        return [t.to_dict() for t in pack.threads]
    
    def is_valid_thread(self, theatre_id: str, thread_id: str) -> bool:
        """检查故事线是否有效"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_thread(thread_id) is not None
    
    # =========================================================================
    # 内容查询接口 - 拍子模板
    # =========================================================================
    
    def get_beat_template(self, theatre_id: str, beat_id: str) -> Optional[BeatTemplate]:
        """获取拍子模板"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_beat_template(beat_id)
    
    def get_beats_by_thread(self, theatre_id: str, thread_id: str) -> List[BeatTemplate]:
        """获取故事线的所有拍子"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_beats_by_thread(thread_id)
    
    def get_beats_by_type(self, theatre_id: str, beat_type: str) -> List[BeatTemplate]:
        """获取指定类型的所有拍子"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_beats_by_type(beat_type)
    
    def list_beat_templates(self, theatre_id: str) -> List[Dict]:
        """列出所有拍子模板"""
        pack = self.get_theatre_pack(theatre_id)
        return [b.to_dict() for b in pack.beat_templates]
    
    def get_rescue_beats(self, theatre_id: str) -> List[BeatTemplate]:
        """获取救援拍子列表"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.rescue_beats
    
    # =========================================================================
    # 内容查询接口 - 门模板
    # =========================================================================
    
    def get_gate_template(self, theatre_id: str, gate_id: str) -> Optional[GateTemplate]:
        """获取门模板"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_gate_template(gate_id)
    
    def list_gate_templates(self, theatre_id: str) -> List[Dict]:
        """列出所有门模板"""
        pack = self.get_theatre_pack(theatre_id)
        return [g.to_dict() for g in pack.gate_templates]
    
    def is_valid_gate_template(self, theatre_id: str, gate_id: str) -> bool:
        """检查门模板是否有效"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_gate_template(gate_id) is not None
    
    # =========================================================================
    # 内容查询接口 - 证物类型
    # =========================================================================
    
    def get_evidence_type(self, theatre_id: str, evidence_type_id: str) -> Optional[EvidenceType]:
        """获取证物类型"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_evidence_type(evidence_type_id)
    
    def list_evidence_types(self, theatre_id: str) -> List[Dict]:
        """列出所有证物类型"""
        pack = self.get_theatre_pack(theatre_id)
        return [e.to_dict() for e in pack.evidence_types]
    
    def is_valid_evidence_type(self, theatre_id: str, evidence_type_id: str) -> bool:
        """检查证物类型是否有效"""
        pack = self.get_theatre_pack(theatre_id)
        return pack.get_evidence_type(evidence_type_id) is not None
    
    # =========================================================================
    # 内容查询接口 - 世界变量
    # =========================================================================
    
    def get_world_variable(self, theatre_id: str, var_id: str) -> Optional[Dict]:
        """获取世界变量定义"""
        pack = self.get_theatre_pack(theatre_id)
        var = pack.get_world_variable(var_id)
        return var.to_dict() if var else None
    
    def list_world_variables(self, theatre_id: str) -> List[Dict]:
        """列出所有世界变量"""
        pack = self.get_theatre_pack(theatre_id)
        return [w.to_dict() for w in pack.world_variables]
    
    def get_default_world_state(self, theatre_id: str) -> Dict[str, float]:
        """获取默认世界状态"""
        pack = self.get_theatre_pack(theatre_id)
        return {w.id: w.default_value for w in pack.world_variables}
    
    # =========================================================================
    # 内容查询接口 - 关键物品
    # =========================================================================
    
    def get_key_object(self, theatre_id: str, object_id: str) -> Optional[Dict]:
        """获取关键物品"""
        pack = self.get_theatre_pack(theatre_id)
        for obj in pack.key_objects:
            if obj.object_id == object_id:
                return obj.to_dict()
        return None
    
    def list_key_objects(self, theatre_id: str) -> List[Dict]:
        """列出所有关键物品"""
        pack = self.get_theatre_pack(theatre_id)
        return [o.to_dict() for o in pack.key_objects]
    
    def is_valid_object(self, theatre_id: str, object_id: str) -> bool:
        """检查物品是否有效（白名单检查）"""
        pack = self.get_theatre_pack(theatre_id)
        for obj in pack.key_objects:
            if obj.object_id == object_id:
                return True
        return False
    
    # =========================================================================
    # 内容查询接口 - 阵营
    # =========================================================================
    
    def list_factions(self, theatre_id: str) -> List[Dict]:
        """列出所有阵营"""
        pack = self.get_theatre_pack(theatre_id)
        return [f.to_dict() for f in pack.factions]
    
    # =========================================================================
    # 统计与诊断
    # =========================================================================
    
    def get_pack_stats(self, theatre_id: str) -> Dict:
        """获取主题包统计信息"""
        pack = self.get_theatre_pack(theatre_id)
        return {
            "pack_id": pack.metadata.pack_id,
            "name": pack.metadata.name,
            "version": pack.metadata.version,
            "stats": {
                "world_variables": len(pack.world_variables),
                "key_objects": len(pack.key_objects),
                "factions": len(pack.factions),
                "characters": len(pack.characters),
                "threads": len(pack.threads),
                "beat_templates": len(pack.beat_templates),
                "gate_templates": len(pack.gate_templates),
                "evidence_types": len(pack.evidence_types),
                "rescue_beats": len(pack.rescue_beats)
            }
        }
    
    def validate_pack(self, pack_id: str) -> Dict:
        """
        验证主题包完整性
        
        Returns:
            Dict: 验证结果，包含错误和警告
        """
        try:
            pack = self._loader.load_pack(pack_id)
        except Exception as e:
            return {"valid": False, "error": str(e)}
        
        errors = []
        warnings = []
        
        # 检查必要组件
        if not pack.characters:
            errors.append("No characters defined")
        if not pack.threads:
            errors.append("No threads defined")
        if not pack.beat_templates:
            errors.append("No beat templates defined")
        if not pack.gate_templates:
            warnings.append("No gate templates defined")
        if not pack.evidence_types:
            warnings.append("No evidence types defined")
        if not pack.rescue_beats:
            warnings.append("No rescue beats defined (fallback may fail)")
        
        # 检查引用完整性
        for beat in pack.beat_templates:
            if beat.thread_id and not pack.get_thread(beat.thread_id):
                errors.append(f"Beat {beat.beat_id} references unknown thread {beat.thread_id}")
            
            if beat.optional_gate:
                gate_id = beat.optional_gate.get("gate_template_id")
                if gate_id and not pack.get_gate_template(gate_id):
                    warnings.append(f"Beat {beat.beat_id} references unknown gate {gate_id}")
        
        return {
            "valid": len(errors) == 0,
            "pack_id": pack_id,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "characters": len(pack.characters),
                "threads": len(pack.threads),
                "beat_templates": len(pack.beat_templates),
                "gate_templates": len(pack.gate_templates),
                "evidence_types": len(pack.evidence_types),
                "rescue_beats": len(pack.rescue_beats)
            }
        }


# 全局单例
_manager_instance: Optional[ThemePackManager] = None


def get_theme_pack_manager(packs_directory: str = None) -> ThemePackManager:
    """获取主题包管理器单例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ThemePackManager(packs_directory)
    return _manager_instance
