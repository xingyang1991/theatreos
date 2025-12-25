"""
测试主题包加载和管理功能
"""
import sys
sys.path.insert(0, '/home/ubuntu/theatreos')

from theme_pack.src.loader import ThemePackLoader
from theme_pack.src.manager import ThemePackManager, get_theme_pack_manager
from theme_pack.src.models import ThemePack


def test_loader():
    """测试主题包加载器"""
    print("=" * 60)
    print("Testing ThemePackLoader")
    print("=" * 60)
    
    loader = ThemePackLoader("/home/ubuntu/theatreos/theme_pack/packs")
    
    # 列出可用主题包
    packs = loader.list_available_packs()
    print(f"\nAvailable packs: {packs}")
    
    # 加载主题包
    pack = loader.load_pack("hp_shanghai_s1")
    print(f"\nLoaded pack: {pack.metadata.name}")
    print(f"  Version: {pack.metadata.version}")
    print(f"  Season: {pack.metadata.season_id}")
    print(f"  Description: {pack.metadata.description[:80]}...")
    
    # 统计
    print(f"\nPack Statistics:")
    print(f"  Characters: {len(pack.characters)}")
    print(f"  Threads: {len(pack.threads)}")
    print(f"  Beat Templates: {len(pack.beat_templates)}")
    print(f"  Gate Templates: {len(pack.gate_templates)}")
    print(f"  Evidence Types: {len(pack.evidence_types)}")
    print(f"  Rescue Beats: {len(pack.rescue_beats)}")
    print(f"  World Variables: {len(pack.world_variables)}")
    print(f"  Key Objects: {len(pack.key_objects)}")
    print(f"  Factions: {len(pack.factions)}")
    
    return pack


def test_manager():
    """测试主题包管理器"""
    print("\n" + "=" * 60)
    print("Testing ThemePackManager")
    print("=" * 60)
    
    manager = get_theme_pack_manager("/home/ubuntu/theatreos/theme_pack/packs")
    
    # 列出可用主题包
    packs = manager.list_available_packs()
    print(f"\nAvailable packs: {len(packs)}")
    for p in packs:
        print(f"  - {p.get('pack_id')}: {p.get('name')} v{p.get('version')}")
    
    # 绑定剧场
    theatre_id = "test_theatre_001"
    pack = manager.bind_theatre(theatre_id, "hp_shanghai_s1")
    print(f"\nBound theatre {theatre_id} to pack {pack.metadata.pack_id}")
    
    # 查询角色
    print("\nCharacters:")
    characters = manager.list_characters(theatre_id)
    for c in characters[:5]:
        print(f"  - {c['character_id']}: {c['name_cn']} ({c['faction']})")
    print(f"  ... and {len(characters) - 5} more")
    
    # 查询故事线
    print("\nThreads:")
    threads = manager.list_threads(theatre_id)
    for t in threads:
        print(f"  - {t['thread_id']}: {t['name']}")
    
    # 查询世界变量
    print("\nWorld Variables:")
    variables = manager.list_world_variables(theatre_id)
    for v in variables:
        print(f"  - {v['id']}: {v['name_cn']} (default: {v['default_value']})")
    
    # 获取默认世界状态
    print("\nDefault World State:")
    defaults = manager.get_default_world_state(theatre_id)
    for var_id, value in defaults.items():
        print(f"  - {var_id}: {value}")
    
    # 验证主题包
    print("\nValidating pack...")
    result = manager.validate_pack("hp_shanghai_s1")
    print(f"  Valid: {result['valid']}")
    if result['errors']:
        print(f"  Errors: {result['errors']}")
    if result['warnings']:
        print(f"  Warnings: {result['warnings']}")
    
    return manager


def test_queries():
    """测试查询功能"""
    print("\n" + "=" * 60)
    print("Testing Query Functions")
    print("=" * 60)
    
    manager = get_theme_pack_manager("/home/ubuntu/theatreos/theme_pack/packs")
    theatre_id = "test_theatre_001"
    
    # 按阵营查询角色
    print("\nCharacters by faction 'aurors':")
    aurors = manager.get_characters_by_faction(theatre_id, "aurors")
    for c in aurors:
        print(f"  - {c.name_cn}: {c.role}")
    
    # 按故事线查询拍子
    print("\nBeats for thread 'thread_floo_fracture' (first 5):")
    beats = manager.get_beats_by_thread(theatre_id, "thread_floo_fracture")
    for b in beats[:5]:
        print(f"  - {b.beat_id}: {b.beat_type}")
    print(f"  ... total {len(beats)} beats")
    
    # 按类型查询拍子
    print("\nBeats of type 'REVEAL' (first 5):")
    reveal_beats = manager.get_beats_by_type(theatre_id, "REVEAL")
    for b in reveal_beats[:5]:
        print(f"  - {b.beat_id}: {b.thread_id}")
    print(f"  ... total {len(reveal_beats)} REVEAL beats")
    
    # 获取特定角色
    print("\nCharacter detail - char_cassia_wren:")
    cassia = manager.get_character(theatre_id, "char_cassia_wren")
    if cassia:
        print(f"  Name: {cassia.name_cn}")
        print(f"  Role: {cassia.role}")
        print(f"  Goal: {cassia.public_goal}")
        print(f"  Allowed beats: {cassia.allowed_beat_types}")
    
    # 获取统计信息
    print("\nPack Stats:")
    stats = manager.get_pack_stats(theatre_id)
    print(f"  Pack: {stats['name']} v{stats['version']}")
    for key, value in stats['stats'].items():
        print(f"  {key}: {value}")


def main():
    print("TheatreOS Theme Pack System Test")
    print("=" * 60)
    
    try:
        test_loader()
        test_manager()
        test_queries()
        
        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
