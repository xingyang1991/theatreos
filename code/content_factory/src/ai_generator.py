"""
TheatreOS AI Content Generator
AI内容生成器 - 集成OpenAI API进行真实的内容生成
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

# OpenAI客户端
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


class GenerationMode(str, Enum):
    AI = "ai"
    TEMPLATE = "template"
    FALLBACK = "fallback"


# 配置
AI_CONFIG = {
    "model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    "max_tokens": 2000,
    "temperature": 0.8,
    "timeout": 30,
    "retry_count": 3,
}

# 提示词模板
PROMPT_TEMPLATES = {
    "scene_generation": """你是TheatreOS的剧本生成引擎，负责生成沉浸式城市剧场的场景内容。

## 世界观背景
{world_context}

## 当前世界状态
- 紧张度: {tension_level}/100
- 当前时间: {current_time}
- 活跃线索: {active_threads}

## 生成要求
- 场景类型: {scene_type}
- 目标舞台: {stage_id}
- 关联角色: {characters}
- 情绪基调: {mood}

## 输出格式
请生成一个完整的场景，包含以下JSON结构：
```json
{{
    "title": "场景标题",
    "description": "场景描述（50-100字）",
    "dialogue": [
        {{"character": "角色名", "line": "台词内容"}}
    ],
    "evidence_hints": ["可能获得的证物线索"],
    "choice_hooks": ["可能的选择点"],
    "atmosphere": "氛围描述",
    "duration_minutes": 预计持续时间
}}
```

请确保内容符合世界观设定，与当前紧张度匹配，并为后续剧情留下伏笔。""",

    "dialogue_generation": """你是TheatreOS的对话生成引擎。

## 角色信息
{character_info}

## 对话场景
{scene_context}

## 生成要求
- 对话轮数: {turn_count}
- 情绪: {emotion}
- 关键信息点: {key_points}

请生成自然、符合角色性格的对话内容。输出JSON数组格式。""",

    "evidence_description": """你是TheatreOS的证物描述生成器。

## 证物基本信息
- 名称: {evidence_name}
- 类型: {evidence_type}
- 等级: {grade}
- 来源场景: {source_scene}

## 生成要求
请生成一段引人入胜的证物描述（50-80字），包含：
1. 外观描述
2. 可能的线索暗示
3. 神秘感或紧张感

输出纯文本描述。""",

    "rumor_expansion": """你是TheatreOS的谣言扩展引擎。

## 原始谣言
{original_rumor}

## 传播上下文
- 传播者类型: {spreader_type}
- 传播地点: {location}
- 当前可信度: {credibility}

## 生成要求
请生成一个变异后的谣言版本（30-50字），要求：
1. 保留核心信息但有所变形
2. 添加传播者可能的主观臆测
3. 增加或减少某些细节

输出纯文本。"""
}


@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    mode: GenerationMode
    content: Any
    tokens_used: int = 0
    latency_ms: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "mode": self.mode.value,
            "content": self.content,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "error": self.error
        }


class AIContentGenerator:
    """AI内容生成器"""
    
    def __init__(self):
        self.client = None
        self.mode = GenerationMode.FALLBACK
        
        if OPENAI_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
            try:
                self.client = OpenAI()
                self.mode = GenerationMode.AI
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
                self.mode = GenerationMode.FALLBACK
        else:
            print("OpenAI not available, using fallback mode")
            self.mode = GenerationMode.FALLBACK
    
    def _call_openai(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        """调用OpenAI API"""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = datetime.utcnow()
        
        response = self.client.chat.completions.create(
            model=AI_CONFIG["model"],
            messages=messages,
            max_tokens=AI_CONFIG["max_tokens"],
            temperature=AI_CONFIG["temperature"],
            timeout=AI_CONFIG["timeout"]
        )
        
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return {
            "content": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "latency_ms": latency_ms
        }
    
    def _parse_json_response(self, text: str) -> Any:
        """解析JSON响应"""
        # 尝试提取JSON块
        import re
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            text = json_match.group(1)
        
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试修复常见问题
            text = text.strip()
            if text.startswith('{') or text.startswith('['):
                # 可能是截断的JSON
                return {"raw_text": text, "parse_error": True}
            return {"raw_text": text}
    
    def generate_scene(
        self,
        world_context: str,
        tension_level: int,
        current_time: str,
        active_threads: List[str],
        scene_type: str,
        stage_id: str,
        characters: List[str],
        mood: str
    ) -> GenerationResult:
        """生成场景内容"""
        
        # 构建提示词
        prompt = PROMPT_TEMPLATES["scene_generation"].format(
            world_context=world_context,
            tension_level=tension_level,
            current_time=current_time,
            active_threads=", ".join(active_threads) if active_threads else "无",
            scene_type=scene_type,
            stage_id=stage_id,
            characters=", ".join(characters) if characters else "无特定角色",
            mood=mood
        )
        
        # 尝试AI生成
        if self.mode == GenerationMode.AI and self.client:
            for attempt in range(AI_CONFIG["retry_count"]):
                try:
                    result = self._call_openai(prompt)
                    content = self._parse_json_response(result["content"])
                    
                    return GenerationResult(
                        success=True,
                        mode=GenerationMode.AI,
                        content=content,
                        tokens_used=result["tokens_used"],
                        latency_ms=result["latency_ms"]
                    )
                except Exception as e:
                    if attempt == AI_CONFIG["retry_count"] - 1:
                        print(f"AI generation failed after {AI_CONFIG['retry_count']} attempts: {e}")
                    continue
        
        # Fallback: 使用模板生成
        return self._generate_scene_fallback(
            scene_type, stage_id, characters, mood, tension_level
        )
    
    def _generate_scene_fallback(
        self,
        scene_type: str,
        stage_id: str,
        characters: List[str],
        mood: str,
        tension_level: int
    ) -> GenerationResult:
        """场景生成的Fallback"""
        
        # 基于模板的场景生成
        templates = {
            "discovery": {
                "title": f"在{stage_id}的意外发现",
                "description": f"一个{mood}的时刻，某些隐藏的真相似乎即将浮出水面...",
                "dialogue": [
                    {"character": characters[0] if characters else "神秘人", "line": "你注意到了吗？这里有些不对劲..."},
                    {"character": "旁白", "line": "空气中弥漫着一种难以言喻的紧张感。"}
                ],
                "evidence_hints": ["一张褪色的照片", "一段模糊的录音"],
                "choice_hooks": ["深入调查", "暂时离开"],
                "atmosphere": f"紧张度{tension_level}%，{mood}的氛围笼罩着整个场景",
                "duration_minutes": 15
            },
            "confrontation": {
                "title": f"{stage_id}的对峙",
                "description": f"两股力量在此相遇，{mood}的气氛让人窒息...",
                "dialogue": [
                    {"character": characters[0] if characters else "角色A", "line": "我知道你在隐瞒什么。"},
                    {"character": characters[1] if len(characters) > 1 else "角色B", "line": "有些事情，知道得太多并不是好事。"}
                ],
                "evidence_hints": ["对话录音", "目击者证词"],
                "choice_hooks": ["支持一方", "保持中立", "揭露真相"],
                "atmosphere": f"紧张度{tension_level}%，冲突一触即发",
                "duration_minutes": 20
            },
            "revelation": {
                "title": f"真相大白于{stage_id}",
                "description": f"所有的线索终于汇聚，{mood}的情绪达到顶点...",
                "dialogue": [
                    {"character": "旁白", "line": "当最后一块拼图落下，一切都变得清晰起来。"}
                ],
                "evidence_hints": ["关键证据", "完整的时间线"],
                "choice_hooks": ["接受真相", "质疑结论"],
                "atmosphere": f"紧张度{tension_level}%，真相的重量让人喘不过气",
                "duration_minutes": 25
            }
        }
        
        template = templates.get(scene_type, templates["discovery"])
        
        return GenerationResult(
            success=True,
            mode=GenerationMode.FALLBACK,
            content=template,
            tokens_used=0,
            latency_ms=0
        )
    
    def generate_dialogue(
        self,
        character_info: Dict[str, Any],
        scene_context: str,
        turn_count: int = 3,
        emotion: str = "neutral",
        key_points: List[str] = None
    ) -> GenerationResult:
        """生成对话"""
        
        if self.mode == GenerationMode.AI and self.client:
            prompt = PROMPT_TEMPLATES["dialogue_generation"].format(
                character_info=json.dumps(character_info, ensure_ascii=False),
                scene_context=scene_context,
                turn_count=turn_count,
                emotion=emotion,
                key_points=", ".join(key_points) if key_points else "无"
            )
            
            try:
                result = self._call_openai(prompt)
                content = self._parse_json_response(result["content"])
                
                return GenerationResult(
                    success=True,
                    mode=GenerationMode.AI,
                    content=content,
                    tokens_used=result["tokens_used"],
                    latency_ms=result["latency_ms"]
                )
            except Exception as e:
                print(f"Dialogue generation failed: {e}")
        
        # Fallback
        character_name = character_info.get("name", "角色")
        dialogues = [
            {"character": character_name, "line": f"（{emotion}地）让我想想..."},
            {"character": character_name, "line": "这件事比我想象的要复杂。"},
            {"character": character_name, "line": "我们需要更多的信息。"}
        ][:turn_count]
        
        return GenerationResult(
            success=True,
            mode=GenerationMode.FALLBACK,
            content=dialogues,
            tokens_used=0,
            latency_ms=0
        )
    
    def generate_evidence_description(
        self,
        evidence_name: str,
        evidence_type: str,
        grade: str,
        source_scene: str = None
    ) -> GenerationResult:
        """生成证物描述"""
        
        if self.mode == GenerationMode.AI and self.client:
            prompt = PROMPT_TEMPLATES["evidence_description"].format(
                evidence_name=evidence_name,
                evidence_type=evidence_type,
                grade=grade,
                source_scene=source_scene or "未知"
            )
            
            try:
                result = self._call_openai(prompt)
                
                return GenerationResult(
                    success=True,
                    mode=GenerationMode.AI,
                    content=result["content"],
                    tokens_used=result["tokens_used"],
                    latency_ms=result["latency_ms"]
                )
            except Exception as e:
                print(f"Evidence description generation failed: {e}")
        
        # Fallback
        descriptions = {
            "A": f"这是一件极为罕见的{evidence_type}——{evidence_name}。它的存在本身就是一个谜，每一个细节都暗示着更深层的秘密。",
            "B": f"一件值得注意的{evidence_type}：{evidence_name}。仔细观察，你能发现一些不寻常的痕迹。",
            "C": f"一件普通的{evidence_type}——{evidence_name}。但在这个故事里，没有什么是真正普通的。"
        }
        
        return GenerationResult(
            success=True,
            mode=GenerationMode.FALLBACK,
            content=descriptions.get(grade, descriptions["C"]),
            tokens_used=0,
            latency_ms=0
        )
    
    def expand_rumor(
        self,
        original_rumor: str,
        spreader_type: str = "player",
        location: str = None,
        credibility: float = 0.5
    ) -> GenerationResult:
        """扩展/变异谣言"""
        
        if self.mode == GenerationMode.AI and self.client:
            prompt = PROMPT_TEMPLATES["rumor_expansion"].format(
                original_rumor=original_rumor,
                spreader_type=spreader_type,
                location=location or "未知地点",
                credibility=f"{credibility*100:.0f}%"
            )
            
            try:
                result = self._call_openai(prompt)
                
                return GenerationResult(
                    success=True,
                    mode=GenerationMode.AI,
                    content=result["content"],
                    tokens_used=result["tokens_used"],
                    latency_ms=result["latency_ms"]
                )
            except Exception as e:
                print(f"Rumor expansion failed: {e}")
        
        # Fallback: 简单变形
        mutations = [
            f"听说{original_rumor}，而且情况比想象的更严重...",
            f"有人说{original_rumor}，但我觉得这只是冰山一角。",
            f"关于{original_rumor}的事，我听到了不同的版本..."
        ]
        
        import random
        return GenerationResult(
            success=True,
            mode=GenerationMode.FALLBACK,
            content=random.choice(mutations),
            tokens_used=0,
            latency_ms=0
        )
    
    def get_status(self) -> Dict[str, Any]:
        """获取生成器状态"""
        return {
            "mode": self.mode.value,
            "openai_available": OPENAI_AVAILABLE,
            "client_initialized": self.client is not None,
            "model": AI_CONFIG["model"] if self.client else None,
            "config": {
                "max_tokens": AI_CONFIG["max_tokens"],
                "temperature": AI_CONFIG["temperature"],
                "timeout": AI_CONFIG["timeout"]
            }
        }


# 全局单例
_ai_generator_instance = None

def get_ai_generator() -> AIContentGenerator:
    """获取AI生成器单例"""
    global _ai_generator_instance
    if _ai_generator_instance is None:
        _ai_generator_instance = AIContentGenerator()
    return _ai_generator_instance
