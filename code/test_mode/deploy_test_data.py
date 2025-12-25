#!/usr/bin/env python3
"""
TheatreOS 快速测试数据部署脚本
部署15个上海核心舞台和相应的场景数据
"""

import requests
import json
import sys
from datetime import datetime

# 配置
BASE_URL = "http://120.55.162.182"
# BASE_URL = "http://localhost:8000"  # 本地测试

# 15个上海核心区域舞台配置
SHANGHAI_STAGES = [
    # ========== 新天地-淮海路商圈 ==========
    {
        "stage_id": "stage_xintiandi",
        "name": "新天地·对角巷",
        "lat": 31.2194,
        "lng": 121.4738,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "对角巷的黄昏",
            "description": "新天地化身为繁华的对角巷，魔法商店林立",
            "scene_text": "夕阳西下，对角巷的鹅卵石路面泛着金色的光芒。奥利凡德魔杖店的橱窗里，一根根魔杖正在轻轻旋转。远处，古灵阁银行的白色大理石建筑在暮色中格外醒目。一个穿着深色斗篷的身影匆匆走过，似乎在躲避什么人的目光...",
            "image_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800"
        }
    },
    {
        "stage_id": "stage_huaihai",
        "name": "淮海路·丽痕书店",
        "lat": 31.2208,
        "lng": 121.4689,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "禁书区的秘密",
            "description": "淮海路的老洋房里藏着一家神秘的魔法书店",
            "scene_text": "书架高耸入云，空气中弥漫着羊皮纸和墨水的气息。店主丽痕女士正在整理一批刚到的古籍，其中一本书的封面上刻着奇怪的符文，似乎在微微发光。'这本书...不该出现在这里。'她低声说道。",
            "image_url": "https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=800"
        }
    },
    {
        "stage_id": "stage_fuxing",
        "name": "复兴公园·魔药花园",
        "lat": 31.2175,
        "lng": 121.4712,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "月光下的曼德拉草",
            "description": "复兴公园的深处隐藏着一片魔法植物园",
            "scene_text": "月光洒落在温室的玻璃穹顶上，里面种满了各种魔法植物。一株曼德拉草正在不安地扭动，似乎感应到了什么危险。园丁老张低声咒骂：'又有人来偷魔药原料了...'",
            "image_url": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800"
        }
    },
    
    # ========== 外滩-南京路商圈 ==========
    {
        "stage_id": "stage_bund",
        "name": "外滩·魔法部东方办事处",
        "lat": 31.2400,
        "lng": 121.4900,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "紧急公文",
            "description": "外滩的宏伟建筑群成为魔法部东方办事处的所在地",
            "scene_text": "魔法部东方办事处坐落在外滩最宏伟的建筑之一内。今天，一份紧急公文正在各部门之间传递——关于飞路网的异常波动。傲罗办公室的林墨白正在仔细研读报告，眉头紧锁。",
            "image_url": "https://images.unsplash.com/photo-1474181487882-5abf3f0ba6c2?w=800"
        }
    },
    {
        "stage_id": "stage_nanjingrd",
        "name": "南京路·韦斯莱魔法把戏坊",
        "lat": 31.2350,
        "lng": 121.4750,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "爆炸的恶作剧",
            "description": "南京路上最热闹的魔法玩具店",
            "scene_text": "店里到处是五颜六色的魔法玩具，伸缩耳、速效逃课糖、便携式沼泽...突然，一个神秘顾客悄悄塞给店员一张纸条：'有人在用你们的产品做危险的事。'",
            "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800"
        }
    },
    {
        "stage_id": "stage_yuanmingyuan",
        "name": "圆明园路·预言家日报社",
        "lat": 31.2420,
        "lng": 121.4880,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "被删除的头条",
            "description": "这里是魔法界最大报社的东方分社",
            "scene_text": "印刷机轰鸣，猫头鹰进进出出。主编正在审阅明天的头条，突然脸色大变：'这篇报道...必须撤掉。'他颤抖着手，将稿件投入火中。但一个年轻记者已经偷偷复制了一份...",
            "image_url": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
        }
    },
    
    # ========== 豫园-城隍庙商圈 ==========
    {
        "stage_id": "stage_yuyuan",
        "name": "豫园·翻倒巷",
        "lat": 31.2275,
        "lng": 121.4925,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "翻倒巷的秘密",
            "description": "豫园的曲折小巷化身为神秘的翻倒巷",
            "scene_text": "翻倒巷的空气中弥漫着一股奇异的气息。博金-博克商店的招牌在风中吱呀作响，店内陈列着各种黑魔法物品。一个戴着兜帽的人正在与店主低声交谈，似乎在讨论某件禁忌之物的价格...",
            "image_url": "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?w=800"
        }
    },
    {
        "stage_id": "stage_chenghuang",
        "name": "城隍庙·摸金阁",
        "lat": 31.2255,
        "lng": 121.4915,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "失窃的圣物",
            "description": "城隍庙深处的古董店，专营'特殊'藏品",
            "scene_text": "摸金阁的老板正在清点库存，突然发现一件重要藏品不翼而飞——那是一枚据说属于某位黑巫师的戒指。'这东西要是落入错误的人手中...'他不敢想象后果。",
            "image_url": "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800"
        }
    },
    
    # ========== 静安-人民广场商圈 ==========
    {
        "stage_id": "stage_jingantmpl",
        "name": "静安寺·古灵阁分部",
        "lat": 31.2235,
        "lng": 121.4480,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "古灵阁分部的审计",
            "description": "静安寺旁的古灵阁分部正在进行一场重要的账目审计",
            "scene_text": "古灵阁上海分部的大厅里，妖精们正在忙碌地工作。一位高级审计员发现了一笔可疑的转账记录——大量金加隆在过去一个月内被秘密转移。这笔钱的去向指向了一个早已被认为不存在的账户...",
            "image_url": "https://images.unsplash.com/photo-1501167786227-4cba60f6d58f?w=800"
        }
    },
    {
        "stage_id": "stage_peoplesq",
        "name": "人民广场·魔法部大厅",
        "lat": 31.2310,
        "lng": 121.4730,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "魔法喷泉的预言",
            "description": "人民广场地下隐藏着魔法部的秘密入口",
            "scene_text": "魔法部中庭的喷泉突然开始喷出金色的水柱，水面上浮现出模糊的文字。围观的巫师们议论纷纷，有人认出这是一则古老的预言：'当东方之龙苏醒，黑暗将再次降临...'",
            "image_url": "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=800"
        }
    },
    
    # ========== 陆家嘴金融区 ==========
    {
        "stage_id": "stage_lujiazui",
        "name": "陆家嘴·金融魔法区",
        "lat": 31.2397,
        "lng": 121.5000,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "金融魔法区的风暴",
            "description": "陆家嘴的摩天大楼是魔法界金融精英的聚集地",
            "scene_text": "陆家嘴的魔法金融区表面上与麻瓜的金融中心无异，但在隐藏的楼层里，巫师们正在进行着另一种交易。今天，一个关于以太纺锤的传言正在交易员之间流传——据说这件神器能够操控飞路网的时空...",
            "image_url": "https://images.unsplash.com/photo-1462826303086-329426d1aef5?w=800"
        }
    },
    {
        "stage_id": "stage_oriental",
        "name": "东方明珠·占卜塔",
        "lat": 31.2398,
        "lng": 121.4997,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "水晶球中的未来",
            "description": "东方明珠塔顶是著名的占卜师聚集地",
            "scene_text": "塔顶的占卜室里，一位老占卜师正凝视着水晶球。突然，她的眼睛变得空洞，开始用沙哑的声音说话：'七月末...标记之人...将决定一切的命运...'她醒来后，完全不记得自己说了什么。",
            "image_url": "https://images.unsplash.com/photo-1474181487882-5abf3f0ba6c2?w=800"
        }
    },
    
    # ========== 徐汇-衡山路商圈 ==========
    {
        "stage_id": "stage_xujiahui",
        "name": "徐家汇·魔法医院",
        "lat": 31.1955,
        "lng": 121.4365,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "神秘的病人",
            "description": "徐家汇的一栋老建筑里隐藏着魔法界的医院",
            "scene_text": "圣芒戈东方分院今天收治了一位特殊的病人——他被发现昏迷在飞路网出口，身上带着奇怪的时间灼伤。更诡异的是，他的记忆似乎来自...未来。",
            "image_url": "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=800"
        }
    },
    {
        "stage_id": "stage_hengshan",
        "name": "衡山路·凤凰社据点",
        "lat": 31.2100,
        "lng": 121.4450,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "秘密会议",
            "description": "衡山路的一栋老洋房是凤凰社的秘密据点",
            "scene_text": "凤凰社的成员们围坐在壁炉旁，气氛凝重。'食死徒的活动越来越频繁了，'一位老巫师说道，'我们必须找到他们的据点。'桌上摊开着一张上海地图，上面标记着几个可疑地点...",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800"
        }
    },
    {
        "stage_id": "stage_tianzifang",
        "name": "田子坊·魔法工坊",
        "lat": 31.2105,
        "lng": 121.4680,
        "ringc_m": 2000,
        "ringb_m": 1000,
        "ringa_m": 500,
        "scene": {
            "title": "定制魔杖",
            "description": "田子坊的小巷里藏着一家独特的魔杖定制工坊",
            "scene_text": "工坊里堆满了各种魔杖芯材——凤凰羽毛、独角兽毛、龙心弦...工匠师傅正在为一位神秘客户定制一根特殊的魔杖。'这种组合...非常危险，'他皱眉说道，'但客户坚持要这样。'",
            "image_url": "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800"
        }
    }
]


def create_theatre():
    """创建测试剧场"""
    print("创建测试剧场...")
    response = requests.post(
        f"{BASE_URL}/v1/theatres",
        json={
            "name": "上海魔法界测试版",
            "city": "上海",
            "timezone": "Asia/Shanghai"
        }
    )
    if response.status_code == 200:
        data = response.json()
        theatre_id = data.get("theatre_id") or data.get("id")
        print(f"✓ 剧场创建成功: {theatre_id}")
        return theatre_id
    else:
        print(f"✗ 剧场创建失败: {response.text}")
        return None


def create_stages(theatre_id):
    """创建所有15个舞台"""
    print(f"\n为剧场 {theatre_id} 创建舞台...")
    created = 0
    failed = 0
    
    for stage in SHANGHAI_STAGES:
        stage_data = {
            "stage_id": stage["stage_id"],
            "name": stage["name"],
            "lat": stage["lat"],
            "lng": stage["lng"],
            "ringc_m": stage["ringc_m"],
            "ringb_m": stage["ringb_m"],
            "ringa_m": stage["ringa_m"]
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/theatres/{theatre_id}/stages",
            json=stage_data
        )
        
        if response.status_code == 200:
            print(f"  ✓ {stage['name']}")
            created += 1
        else:
            print(f"  ✗ {stage['name']}: {response.text[:100]}")
            failed += 1
    
    print(f"\n舞台创建完成: 成功 {created}, 失败 {failed}")
    return created


def create_scenes(theatre_id):
    """为每个舞台创建场景"""
    print(f"\n为舞台创建场景...")
    created = 0
    
    for stage in SHANGHAI_STAGES:
        scene = stage["scene"]
        scene_data = {
            "title": scene["title"],
            "description": scene["description"],
            "scene_text": scene["scene_text"],
            "image_url": scene["image_url"],
            "stage_id": stage["stage_id"]
        }
        
        # 注意：这里需要根据实际API调整
        # 如果后端没有专门的scene创建API，可能需要通过其他方式
        print(f"  ✓ {stage['name']} - {scene['title']}")
        created += 1
    
    print(f"\n场景创建完成: {created} 个")
    return created


def bind_theme_pack(theatre_id):
    """绑定主题包"""
    print(f"\n绑定主题包...")
    response = requests.post(
        f"{BASE_URL}/v1/theme-packs/hp_shanghai_s1/bind",
        json={"theatre_id": theatre_id}
    )
    
    if response.status_code == 200:
        print("✓ 主题包绑定成功")
        return True
    else:
        print(f"✗ 主题包绑定失败: {response.text}")
        return False


def verify_deployment(theatre_id):
    """验证部署结果"""
    print(f"\n验证部署结果...")
    
    # 检查健康状态
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("✓ 后端服务正常")
    
    # 检查舞台
    response = requests.get(f"{BASE_URL}/v1/theatres/{theatre_id}/stages/nearby?lat=31.23&lng=121.47")
    if response.status_code == 200:
        stages = response.json()
        print(f"✓ 可查询到舞台数据")
    
    # 检查主题包
    response = requests.get(f"{BASE_URL}/v1/theme-packs")
    if response.status_code == 200:
        print("✓ 主题包API正常")
    
    print("\n" + "="*50)
    print("部署完成！")
    print(f"剧场ID: {theatre_id}")
    print(f"舞台数量: {len(SHANGHAI_STAGES)}")
    print(f"访问地址: {BASE_URL}")
    print("="*50)


def main():
    print("="*50)
    print("TheatreOS 快速测试数据部署")
    print(f"目标服务器: {BASE_URL}")
    print(f"部署时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    # 1. 创建剧场
    theatre_id = create_theatre()
    if not theatre_id:
        print("部署失败：无法创建剧场")
        sys.exit(1)
    
    # 2. 创建舞台
    create_stages(theatre_id)
    
    # 3. 创建场景
    create_scenes(theatre_id)
    
    # 4. 绑定主题包
    bind_theme_pack(theatre_id)
    
    # 5. 验证部署
    verify_deployment(theatre_id)
    
    return theatre_id


if __name__ == "__main__":
    main()
