"""
TheatreOS Render Pipeline
媒体生成管线 - 将场景草稿渲染为可发布的媒体资产

降级梯子:
- L0: 正常 - 短视频+图+音+文本
- L1: 轻降级 - 图+音+文本（无视频）
- L2: 强降级 - 剪影图+音轨+证物卡
- L3: 救援拍子 - Rescue Beat 模板
- L4: 静默slot - 只有门+Explain
"""
import logging
import uuid
import json
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================
class DegradeLevel(str, Enum):
    L0_NORMAL = "L0"      # 正常：视频+图+音+文本
    L1_LIGHT = "L1"       # 轻降级：图+音+文本（无视频）
    L2_HEAVY = "L2"       # 强降级：剪影图+音轨+证物卡
    L3_RESCUE = "L3"      # 救援拍子
    L4_SILENT = "L4"      # 静默slot


class AssetType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
    TEXT = "text"
    SILHOUETTE = "silhouette"
    EVIDENCE_CARD = "evidence_card"


class AssetStatus(str, Enum):
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ProviderType(str, Enum):
    OPENAI = "openai"
    STABILITY = "stability"
    ELEVENLABS = "elevenlabs"
    LOCAL = "local"
    TEMPLATE = "template"


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class RenderAsset:
    """渲染资产"""
    asset_id: str
    scene_id: str
    asset_type: AssetType
    provider: ProviderType
    status: AssetStatus
    url: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict:
        return {
            "asset_id": self.asset_id,
            "scene_id": self.scene_id,
            "asset_type": self.asset_type.value,
            "provider": self.provider.value,
            "status": self.status.value,
            "url": self.url,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class RenderResult:
    """渲染结果"""
    scene_id: str
    degrade_level: DegradeLevel
    assets: List[RenderAsset]
    success: bool
    error_message: Optional[str] = None
    render_time_ms: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "scene_id": self.scene_id,
            "degrade_level": self.degrade_level.value,
            "assets": [a.to_dict() for a in self.assets],
            "success": self.success,
            "error_message": self.error_message,
            "render_time_ms": self.render_time_ms
        }


@dataclass
class RenderConfig:
    """渲染配置"""
    video_enabled: bool = True
    image_enabled: bool = True
    audio_enabled: bool = True
    max_video_duration_sec: int = 30
    image_resolution: str = "1024x1024"
    audio_voice: str = "alloy"
    timeout_sec: int = 60
    max_retries: int = 2


# =============================================================================
# Asset Generators (Abstract)
# =============================================================================
class AssetGenerator(ABC):
    """资产生成器基类"""
    
    @abstractmethod
    def generate(self, scene: Dict, config: RenderConfig) -> RenderAsset:
        pass
    
    @abstractmethod
    def can_generate(self, scene: Dict) -> bool:
        pass


class VideoGenerator(AssetGenerator):
    """视频生成器"""
    
    def __init__(self):
        self.provider = ProviderType.OPENAI
    
    def can_generate(self, scene: Dict) -> bool:
        # 检查场景是否适合生成视频
        return len(scene.get("scene_text", "")) >= 50
    
    def generate(self, scene: Dict, config: RenderConfig) -> RenderAsset:
        """生成视频"""
        asset = RenderAsset(
            asset_id=str(uuid.uuid4()),
            scene_id=scene.get("scene_id", ""),
            asset_type=AssetType.VIDEO,
            provider=self.provider,
            status=AssetStatus.GENERATING
        )
        
        try:
            # 实际实现需要调用视频生成 API
            # 这里使用模拟实现
            
            # 构建视频生成 prompt
            prompt = self._build_video_prompt(scene)
            
            # 模拟视频生成
            # 实际可以使用 OpenAI Sora 或其他视频生成服务
            video_url = self._generate_video_mock(prompt, config)
            
            asset.status = AssetStatus.SUCCESS
            asset.url = video_url
            asset.content_hash = hashlib.md5(prompt.encode()).hexdigest()
            asset.metadata = {
                "prompt": prompt[:200],
                "duration_sec": config.max_video_duration_sec,
                "resolution": "1080p"
            }
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            asset.status = AssetStatus.FAILED
            asset.error_message = str(e)
        
        return asset
    
    def _build_video_prompt(self, scene: Dict) -> str:
        """构建视频生成 prompt"""
        camera_style = scene.get("camera_style", "cctv")
        mood = scene.get("mood", "neutral")
        scene_text = scene.get("scene_text", "")
        
        prompt = f"""
Camera Style: {camera_style}
Mood: {mood}
Scene Description: {scene_text[:300]}

Generate a cinematic video clip that captures this scene with the specified camera style and mood.
The video should be atmospheric and mysterious, suitable for an urban mystery narrative.
"""
        return prompt.strip()
    
    def _generate_video_mock(self, prompt: str, config: RenderConfig) -> str:
        """模拟视频生成"""
        # 返回占位符 URL
        return f"https://storage.theatreos.com/videos/{uuid.uuid4()}.mp4"


class ImageGenerator(AssetGenerator):
    """图片生成器"""
    
    def __init__(self):
        self.provider = ProviderType.OPENAI
        self.client = None
        self._init_client()
    
    def _init_client(self):
        try:
            from openai import OpenAI
            self.client = OpenAI()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    def can_generate(self, scene: Dict) -> bool:
        return True
    
    def generate(self, scene: Dict, config: RenderConfig) -> RenderAsset:
        """生成图片"""
        asset = RenderAsset(
            asset_id=str(uuid.uuid4()),
            scene_id=scene.get("scene_id", ""),
            asset_type=AssetType.IMAGE,
            provider=self.provider,
            status=AssetStatus.GENERATING
        )
        
        try:
            prompt = self._build_image_prompt(scene)
            
            if self.client:
                # 使用 OpenAI DALL-E
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size=config.image_resolution,
                    quality="standard",
                    n=1
                )
                image_url = response.data[0].url
            else:
                # 模拟生成
                image_url = f"https://storage.theatreos.com/images/{uuid.uuid4()}.png"
            
            asset.status = AssetStatus.SUCCESS
            asset.url = image_url
            asset.content_hash = hashlib.md5(prompt.encode()).hexdigest()
            asset.metadata = {
                "prompt": prompt[:200],
                "resolution": config.image_resolution
            }
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            asset.status = AssetStatus.FAILED
            asset.error_message = str(e)
        
        return asset
    
    def _build_image_prompt(self, scene: Dict) -> str:
        """构建图片生成 prompt"""
        camera_style = scene.get("camera_style", "cctv")
        mood = scene.get("mood", "neutral")
        scene_text = scene.get("scene_text", "")
        stage_id = scene.get("stage_id", "")
        
        style_mapping = {
            "cctv": "surveillance camera footage, grainy, night vision",
            "drone": "aerial view, bird's eye perspective, cinematic",
            "pov": "first person view, immersive, eye level",
            "static": "static shot, fixed camera, documentary style"
        }
        
        mood_mapping = {
            "ominous": "dark, foreboding, shadows, tension",
            "tense": "high contrast, dramatic lighting, suspense",
            "calm": "soft lighting, peaceful, serene",
            "mysterious": "fog, mist, enigmatic atmosphere",
            "neutral": "balanced lighting, natural colors"
        }
        
        style_desc = style_mapping.get(camera_style, style_mapping["static"])
        mood_desc = mood_mapping.get(mood, mood_mapping["neutral"])
        
        prompt = f"""
Urban mystery scene in Shanghai at night.
Style: {style_desc}
Atmosphere: {mood_desc}
Scene: {scene_text[:200]}

Cinematic, atmospheric, no text or watermarks.
"""
        return prompt.strip()


class SilhouetteGenerator(AssetGenerator):
    """剪影图生成器（降级模式）"""
    
    def __init__(self):
        self.provider = ProviderType.LOCAL
    
    def can_generate(self, scene: Dict) -> bool:
        return True
    
    def generate(self, scene: Dict, config: RenderConfig) -> RenderAsset:
        """生成剪影图"""
        asset = RenderAsset(
            asset_id=str(uuid.uuid4()),
            scene_id=scene.get("scene_id", ""),
            asset_type=AssetType.SILHOUETTE,
            provider=self.provider,
            status=AssetStatus.SUCCESS
        )
        
        # 剪影图使用预制模板
        mood = scene.get("mood", "neutral")
        template_id = self._select_template(mood)
        
        asset.url = f"https://storage.theatreos.com/templates/silhouettes/{template_id}.png"
        asset.metadata = {
            "template_id": template_id,
            "mood": mood
        }
        
        return asset
    
    def _select_template(self, mood: str) -> str:
        """选择剪影模板"""
        templates = {
            "ominous": "silhouette_dark_01",
            "tense": "silhouette_tension_01",
            "calm": "silhouette_calm_01",
            "mysterious": "silhouette_mystery_01",
            "neutral": "silhouette_default_01"
        }
        return templates.get(mood, "silhouette_default_01")


class AudioGenerator(AssetGenerator):
    """音频生成器"""
    
    def __init__(self):
        self.provider = ProviderType.OPENAI
        self.client = None
        self._init_client()
    
    def _init_client(self):
        try:
            from openai import OpenAI
            self.client = OpenAI()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    def can_generate(self, scene: Dict) -> bool:
        # 有对白或场景描述时生成音频
        return bool(scene.get("dialogue")) or bool(scene.get("scene_text"))
    
    def generate(self, scene: Dict, config: RenderConfig) -> RenderAsset:
        """生成音频"""
        asset = RenderAsset(
            asset_id=str(uuid.uuid4()),
            scene_id=scene.get("scene_id", ""),
            asset_type=AssetType.AUDIO,
            provider=self.provider,
            status=AssetStatus.GENERATING
        )
        
        try:
            # 构建要朗读的文本
            text = self._build_narration_text(scene)
            
            if self.client and text:
                # 使用 OpenAI TTS
                response = self.client.audio.speech.create(
                    model="tts-1",
                    voice=config.audio_voice,
                    input=text[:4096]  # TTS 有长度限制
                )
                
                # 保存音频文件
                audio_path = f"/tmp/audio_{asset.asset_id}.mp3"
                response.stream_to_file(audio_path)
                
                # 实际应上传到存储服务
                audio_url = f"https://storage.theatreos.com/audio/{asset.asset_id}.mp3"
            else:
                # 模拟生成
                audio_url = f"https://storage.theatreos.com/audio/{uuid.uuid4()}.mp3"
            
            asset.status = AssetStatus.SUCCESS
            asset.url = audio_url
            asset.metadata = {
                "text_length": len(text),
                "voice": config.audio_voice
            }
            
        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            asset.status = AssetStatus.FAILED
            asset.error_message = str(e)
        
        return asset
    
    def _build_narration_text(self, scene: Dict) -> str:
        """构建旁白文本"""
        parts = []
        
        # 场景描述
        scene_text = scene.get("scene_text", "")
        if scene_text:
            parts.append(scene_text)
        
        # 对白
        dialogue = scene.get("dialogue", [])
        for line in dialogue:
            if isinstance(line, list) and len(line) >= 2:
                speaker, text = line[0], line[1]
                parts.append(f"{speaker}说：{text}")
        
        return "\n".join(parts)


class EvidenceCardGenerator(AssetGenerator):
    """证物卡生成器"""
    
    def __init__(self):
        self.provider = ProviderType.TEMPLATE
    
    def can_generate(self, scene: Dict) -> bool:
        return bool(scene.get("evidence_outputs"))
    
    def generate(self, scene: Dict, config: RenderConfig) -> RenderAsset:
        """生成证物卡"""
        asset = RenderAsset(
            asset_id=str(uuid.uuid4()),
            scene_id=scene.get("scene_id", ""),
            asset_type=AssetType.EVIDENCE_CARD,
            provider=self.provider,
            status=AssetStatus.SUCCESS
        )
        
        evidence_outputs = scene.get("evidence_outputs", [])
        
        # 使用模板生成证物卡
        cards = []
        for ev in evidence_outputs:
            card = {
                "evidence_type_id": ev.get("evidence_type_id"),
                "tier": ev.get("tier", "C"),
                "template_url": f"https://storage.theatreos.com/templates/evidence/{ev.get('tier', 'C')}_card.png"
            }
            cards.append(card)
        
        asset.url = f"https://storage.theatreos.com/evidence_cards/{asset.asset_id}.json"
        asset.metadata = {"cards": cards}
        
        return asset


# =============================================================================
# Render Pipeline
# =============================================================================
class RenderPipeline:
    """渲染管线"""
    
    def __init__(self, config: RenderConfig = None):
        self.config = config or RenderConfig()
        
        # 初始化生成器
        self.video_generator = VideoGenerator()
        self.image_generator = ImageGenerator()
        self.silhouette_generator = SilhouetteGenerator()
        self.audio_generator = AudioGenerator()
        self.evidence_card_generator = EvidenceCardGenerator()
    
    def render(
        self,
        scenes: List[Dict],
        target_level: DegradeLevel = DegradeLevel.L0_NORMAL
    ) -> Tuple[List[RenderResult], DegradeLevel]:
        """
        渲染场景列表
        
        Args:
            scenes: 场景列表
            target_level: 目标降级级别
        
        Returns:
            (渲染结果列表, 最终降级级别)
        """
        results = []
        final_level = target_level
        
        for scene in scenes:
            result = self._render_scene(scene, target_level)
            results.append(result)
            
            # 如果渲染失败，可能需要进一步降级
            if not result.success and result.degrade_level.value > final_level.value:
                final_level = result.degrade_level
        
        return results, final_level
    
    def _render_scene(self, scene: Dict, target_level: DegradeLevel) -> RenderResult:
        """渲染单个场景"""
        start_time = datetime.now(timezone.utc)
        assets = []
        current_level = target_level
        
        try:
            if target_level == DegradeLevel.L0_NORMAL:
                # L0: 尝试生成完整资产
                assets.extend(self._render_l0(scene))
                
                # 检查是否有失败，需要降级
                failed_video = any(
                    a.asset_type == AssetType.VIDEO and a.status == AssetStatus.FAILED
                    for a in assets
                )
                if failed_video:
                    current_level = DegradeLevel.L1_LIGHT
                    logger.info(f"Video failed, degrading to L1 for scene {scene.get('scene_id')}")
            
            elif target_level == DegradeLevel.L1_LIGHT:
                # L1: 图+音+文本（无视频）
                assets.extend(self._render_l1(scene))
            
            elif target_level == DegradeLevel.L2_HEAVY:
                # L2: 剪影图+音轨+证物卡
                assets.extend(self._render_l2(scene))
            
            elif target_level == DegradeLevel.L3_RESCUE:
                # L3: 救援拍子模板
                assets.extend(self._render_l3(scene))
            
            else:
                # L4: 静默 slot
                assets.extend(self._render_l4(scene))
            
            # 检查是否全部成功
            all_success = all(a.status == AssetStatus.SUCCESS for a in assets)
            
            end_time = datetime.now(timezone.utc)
            render_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return RenderResult(
                scene_id=scene.get("scene_id", ""),
                degrade_level=current_level,
                assets=assets,
                success=all_success,
                render_time_ms=render_time_ms
            )
            
        except Exception as e:
            logger.error(f"Render failed for scene {scene.get('scene_id')}: {e}")
            
            # 降级到 L4
            return RenderResult(
                scene_id=scene.get("scene_id", ""),
                degrade_level=DegradeLevel.L4_SILENT,
                assets=self._render_l4(scene),
                success=False,
                error_message=str(e)
            )
    
    def _render_l0(self, scene: Dict) -> List[RenderAsset]:
        """L0: 完整渲染"""
        assets = []
        
        # 视频
        if self.config.video_enabled and self.video_generator.can_generate(scene):
            assets.append(self.video_generator.generate(scene, self.config))
        
        # 图片
        if self.config.image_enabled and self.image_generator.can_generate(scene):
            assets.append(self.image_generator.generate(scene, self.config))
        
        # 音频
        if self.config.audio_enabled and self.audio_generator.can_generate(scene):
            assets.append(self.audio_generator.generate(scene, self.config))
        
        # 证物卡
        if self.evidence_card_generator.can_generate(scene):
            assets.append(self.evidence_card_generator.generate(scene, self.config))
        
        return assets
    
    def _render_l1(self, scene: Dict) -> List[RenderAsset]:
        """L1: 轻降级（无视频）"""
        assets = []
        
        # 图片
        if self.image_generator.can_generate(scene):
            assets.append(self.image_generator.generate(scene, self.config))
        
        # 音频
        if self.audio_generator.can_generate(scene):
            assets.append(self.audio_generator.generate(scene, self.config))
        
        # 证物卡
        if self.evidence_card_generator.can_generate(scene):
            assets.append(self.evidence_card_generator.generate(scene, self.config))
        
        return assets
    
    def _render_l2(self, scene: Dict) -> List[RenderAsset]:
        """L2: 强降级（剪影模式）"""
        assets = []
        
        # 剪影图
        assets.append(self.silhouette_generator.generate(scene, self.config))
        
        # 音频
        if self.audio_generator.can_generate(scene):
            assets.append(self.audio_generator.generate(scene, self.config))
        
        # 证物卡
        if self.evidence_card_generator.can_generate(scene):
            assets.append(self.evidence_card_generator.generate(scene, self.config))
        
        return assets
    
    def _render_l3(self, scene: Dict) -> List[RenderAsset]:
        """L3: 救援拍子"""
        assets = []
        
        # 使用预制的救援模板
        rescue_asset = RenderAsset(
            asset_id=str(uuid.uuid4()),
            scene_id=scene.get("scene_id", ""),
            asset_type=AssetType.IMAGE,
            provider=ProviderType.TEMPLATE,
            status=AssetStatus.SUCCESS,
            url="https://storage.theatreos.com/templates/rescue/rescue_beat_01.png",
            metadata={"template": "rescue_beat_01"}
        )
        assets.append(rescue_asset)
        
        return assets
    
    def _render_l4(self, scene: Dict) -> List[RenderAsset]:
        """L4: 静默 slot"""
        assets = []
        
        # 只有基础占位图
        silent_asset = RenderAsset(
            asset_id=str(uuid.uuid4()),
            scene_id=scene.get("scene_id", ""),
            asset_type=AssetType.IMAGE,
            provider=ProviderType.TEMPLATE,
            status=AssetStatus.SUCCESS,
            url="https://storage.theatreos.com/templates/silent/signal_lost.png",
            metadata={"template": "signal_lost"}
        )
        assets.append(silent_asset)
        
        return assets


# =============================================================================
# Render Pipeline Service
# =============================================================================
class RenderPipelineService:
    """渲染管线服务"""
    
    def __init__(self, config: RenderConfig = None):
        self.pipeline = RenderPipeline(config)
    
    def render_scenes(
        self,
        scenes: List[Dict],
        target_level: str = "L0"
    ) -> Dict:
        """
        渲染场景
        
        Args:
            scenes: 场景列表
            target_level: 目标降级级别 (L0-L4)
        
        Returns:
            渲染结果
        """
        level = DegradeLevel(target_level)
        results, final_level = self.pipeline.render(scenes, level)
        
        return {
            "target_level": target_level,
            "final_level": final_level.value,
            "total_scenes": len(scenes),
            "success_count": sum(1 for r in results if r.success),
            "results": [r.to_dict() for r in results]
        }
    
    def get_degrade_ladder(self) -> List[Dict]:
        """获取降级梯子说明"""
        return [
            {
                "level": "L0",
                "name": "正常",
                "assets": ["视频", "图片", "音频", "文本", "证物卡"],
                "description": "最强代入感，完整媒体体验"
            },
            {
                "level": "L1",
                "name": "轻降级",
                "assets": ["图片", "音频", "文本", "证物卡"],
                "description": "无视频，渲染失败常见兜底"
            },
            {
                "level": "L2",
                "name": "强降级",
                "assets": ["剪影图", "音轨", "证物卡"],
                "description": "内容仍可读懂，神秘感保持"
            },
            {
                "level": "L3",
                "name": "救援拍子",
                "assets": ["救援模板"],
                "description": "保证 slot 结构完整"
            },
            {
                "level": "L4",
                "name": "静默 slot",
                "assets": ["占位图", "门", "Explain"],
                "description": "最后兜底，仍可结算与回声"
            }
        ]
