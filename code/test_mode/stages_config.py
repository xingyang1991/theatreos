"""
TheatreOS 快速测试版 - 15个上海核心区域舞台配置
所有舞台位于上海市中心3公里范围内，方便快速测试
"""

# 15个上海核心区域舞台配置
SHANGHAI_STAGES = [
    # ========== 新天地-淮海路商圈 ==========
    {
        "stage_id": "stage_xintiandi",
        "name": "新天地·对角巷",
        "lat": 31.2194,
        "lng": 121.4738,
        "location_desc": "新天地石库门",
        "hp_mapping": "对角巷",
        "scene": {
            "title": "对角巷的黄昏",
            "description": "新天地化身为繁华的对角巷，魔法商店林立，巫师们穿梭其间。",
            "scene_text": "夕阳西下，对角巷的鹅卵石路面泛着金色的光芒。奥利凡德魔杖店的橱窗里，一根根魔杖正在轻轻旋转。远处，古灵阁银行的白色大理石建筑在暮色中格外醒目。一个穿着深色斗篷的身影匆匆走过，似乎在躲避什么人的目光...",
            "npc": "奥利凡德先生",
            "thread": "飞路错拍线",
            "evidence": "神秘魔杖碎片"
        }
    },
    {
        "stage_id": "stage_huaihai",
        "name": "淮海路·丽痕书店",
        "lat": 31.2208,
        "lng": 121.4689,
        "location_desc": "淮海中路",
        "hp_mapping": "丽痕书店",
        "scene": {
            "title": "禁书区的秘密",
            "description": "淮海路的老洋房里藏着一家神秘的魔法书店。",
            "scene_text": "书架高耸入云，空气中弥漫着羊皮纸和墨水的气息。店主丽痕女士正在整理一批刚到的古籍，其中一本书的封面上刻着奇怪的符文，似乎在微微发光。'这本书...不该出现在这里。'她低声说道。",
            "npc": "丽痕女士",
            "thread": "封口令线",
            "evidence": "禁书残页"
        }
    },
    {
        "stage_id": "stage_fuxing",
        "name": "复兴公园·魔药花园",
        "lat": 31.2175,
        "lng": 121.4712,
        "location_desc": "复兴公园",
        "hp_mapping": "霍格沃茨草药园",
        "scene": {
            "title": "月光下的曼德拉草",
            "description": "复兴公园的深处隐藏着一片魔法植物园。",
            "scene_text": "月光洒落在温室的玻璃穹顶上，里面种满了各种魔法植物。一株曼德拉草正在不安地扭动，似乎感应到了什么危险。园丁老张低声咒骂：'又有人来偷魔药原料了...'",
            "npc": "园丁老张",
            "thread": "黑市走私线",
            "evidence": "魔药配方残片"
        }
    },
    
    # ========== 外滩-南京路商圈 ==========
    {
        "stage_id": "stage_bund",
        "name": "外滩·魔法部东方办事处",
        "lat": 31.2400,
        "lng": 121.4900,
        "location_desc": "外滩万国建筑群",
        "hp_mapping": "魔法部",
        "scene": {
            "title": "紧急公文",
            "description": "外滩的宏伟建筑群成为魔法部东方办事处的所在地。",
            "scene_text": "魔法部东方办事处坐落在外滩最宏伟的建筑之一内。今天，一份紧急公文正在各部门之间传递——关于飞路网的异常波动。傲罗办公室的林墨白正在仔细研读报告，眉头紧锁。",
            "npc": "傲罗林墨白",
            "thread": "飞路错拍线",
            "evidence": "魔法部内部备忘录"
        }
    },
    {
        "stage_id": "stage_nanjingrd",
        "name": "南京路·韦斯莱魔法把戏坊",
        "lat": 31.2350,
        "lng": 121.4750,
        "location_desc": "南京路步行街",
        "hp_mapping": "韦斯莱魔法把戏坊",
        "scene": {
            "title": "爆炸的恶作剧",
            "description": "南京路上最热闹的魔法玩具店。",
            "scene_text": "店里到处是五颜六色的魔法玩具，伸缩耳、速效逃课糖、便携式沼泽...突然，一个神秘顾客悄悄塞给店员一张纸条：'有人在用你们的产品做危险的事。'",
            "npc": "店员小韦",
            "thread": "黑市走私线",
            "evidence": "可疑订单清单"
        }
    },
    {
        "stage_id": "stage_yuanmingyuan",
        "name": "圆明园路·预言家日报社",
        "lat": 31.2420,
        "lng": 121.4880,
        "location_desc": "圆明园路",
        "hp_mapping": "预言家日报",
        "scene": {
            "title": "被删除的头条",
            "description": "这里是魔法界最大报社的东方分社。",
            "scene_text": "印刷机轰鸣，猫头鹰进进出出。主编正在审阅明天的头条，突然脸色大变：'这篇报道...必须撤掉。'他颤抖着手，将稿件投入火中。但一个年轻记者已经偷偷复制了一份...",
            "npc": "记者小苏",
            "thread": "封口令线",
            "evidence": "被删除的新闻稿"
        }
    },
    
    # ========== 豫园-城隍庙商圈 ==========
    {
        "stage_id": "stage_yuyuan",
        "name": "豫园·翻倒巷",
        "lat": 31.2275,
        "lng": 121.4925,
        "location_desc": "豫园老街",
        "hp_mapping": "翻倒巷",
        "scene": {
            "title": "翻倒巷的秘密",
            "description": "豫园的曲折小巷化身为神秘的翻倒巷。",
            "scene_text": "翻倒巷的空气中弥漫着一股奇异的气息。博金-博克商店的招牌在风中吱呀作响，店内陈列着各种黑魔法物品。一个戴着兜帽的人正在与店主低声交谈，似乎在讨论某件禁忌之物的价格...",
            "npc": "博金先生",
            "thread": "黑市走私线",
            "evidence": "黑市交易账本"
        }
    },
    {
        "stage_id": "stage_chenghuang",
        "name": "城隍庙·摸金阁",
        "lat": 31.2255,
        "lng": 121.4915,
        "location_desc": "城隍庙",
        "hp_mapping": "博金-博克商店",
        "scene": {
            "title": "失窃的圣物",
            "description": "城隍庙深处的古董店，专营'特殊'藏品。",
            "scene_text": "摸金阁的老板正在清点库存，突然发现一件重要藏品不翼而飞——那是一枚据说属于某位黑巫师的戒指。'这东西要是落入错误的人手中...'他不敢想象后果。",
            "npc": "摸金阁老板",
            "thread": "黑市走私线",
            "evidence": "失窃物品清单"
        }
    },
    
    # ========== 静安-人民广场商圈 ==========
    {
        "stage_id": "stage_jingantmpl",
        "name": "静安寺·古灵阁分部",
        "lat": 31.2235,
        "lng": 121.4480,
        "location_desc": "静安寺",
        "hp_mapping": "古灵阁银行",
        "scene": {
            "title": "古灵阁分部的审计",
            "description": "静安寺旁的古灵阁分部正在进行一场重要的账目审计。",
            "scene_text": "古灵阁上海分部的大厅里，妖精们正在忙碌地工作。一位高级审计员发现了一笔可疑的转账记录——大量金加隆在过去一个月内被秘密转移。这笔钱的去向指向了一个早已被认为不存在的账户...",
            "npc": "妖精审计员格里普",
            "thread": "古灵阁审计线",
            "evidence": "可疑转账记录"
        }
    },
    {
        "stage_id": "stage_peoplesq",
        "name": "人民广场·魔法部大厅",
        "lat": 31.2310,
        "lng": 121.4730,
        "location_desc": "人民广场",
        "hp_mapping": "魔法部中庭",
        "scene": {
            "title": "魔法喷泉的预言",
            "description": "人民广场地下隐藏着魔法部的秘密入口。",
            "scene_text": "魔法部中庭的喷泉突然开始喷出金色的水柱，水面上浮现出模糊的文字。围观的巫师们议论纷纷，有人认出这是一则古老的预言：'当东方之龙苏醒，黑暗将再次降临...'",
            "npc": "神秘事务司官员",
            "thread": "飞路错拍线",
            "evidence": "预言碎片"
        }
    },
    
    # ========== 陆家嘴金融区 ==========
    {
        "stage_id": "stage_lujiazui",
        "name": "陆家嘴·金融魔法区",
        "lat": 31.2397,
        "lng": 121.5000,
        "location_desc": "陆家嘴金融中心",
        "hp_mapping": "古灵阁总部",
        "scene": {
            "title": "金融魔法区的风暴",
            "description": "陆家嘴的摩天大楼是魔法界金融精英的聚集地。",
            "scene_text": "陆家嘴的魔法金融区表面上与麻瓜的金融中心无异，但在隐藏的楼层里，巫师们正在进行着另一种交易。今天，一个关于以太纺锤的传言正在交易员之间流传——据说这件神器能够操控飞路网的时空...",
            "npc": "金融巫师陈总",
            "thread": "古灵阁审计线",
            "evidence": "以太纺锤情报"
        }
    },
    {
        "stage_id": "stage_oriental",
        "name": "东方明珠·占卜塔",
        "lat": 31.2398,
        "lng": 121.4997,
        "location_desc": "东方明珠塔",
        "hp_mapping": "占卜塔",
        "scene": {
            "title": "水晶球中的未来",
            "description": "东方明珠塔顶是著名的占卜师聚集地。",
            "scene_text": "塔顶的占卜室里，一位老占卜师正凝视着水晶球。突然，她的眼睛变得空洞，开始用沙哑的声音说话：'七月末...标记之人...将决定一切的命运...'她醒来后，完全不记得自己说了什么。",
            "npc": "占卜师特里劳妮",
            "thread": "霍格沃茨外勤线",
            "evidence": "预言记录"
        }
    },
    
    # ========== 徐汇-衡山路商圈 ==========
    {
        "stage_id": "stage_xujiahui",
        "name": "徐家汇·魔法医院",
        "lat": 31.1955,
        "lng": 121.4365,
        "location_desc": "徐家汇",
        "hp_mapping": "圣芒戈医院",
        "scene": {
            "title": "神秘的病人",
            "description": "徐家汇的一栋老建筑里隐藏着魔法界的医院。",
            "scene_text": "圣芒戈东方分院今天收治了一位特殊的病人——他被发现昏迷在飞路网出口，身上带着奇怪的时间灼伤。更诡异的是，他的记忆似乎来自...未来。",
            "npc": "治疗师王医生",
            "thread": "飞路错拍线",
            "evidence": "病历档案"
        }
    },
    {
        "stage_id": "stage_hengshan",
        "name": "衡山路·凤凰社据点",
        "lat": 31.2100,
        "lng": 121.4450,
        "location_desc": "衡山路",
        "hp_mapping": "凤凰社总部",
        "scene": {
            "title": "秘密会议",
            "description": "衡山路的一栋老洋房是凤凰社的秘密据点。",
            "scene_text": "凤凰社的成员们围坐在壁炉旁，气氛凝重。'食死徒的活动越来越频繁了，'一位老巫师说道，'我们必须找到他们的据点。'桌上摊开着一张上海地图，上面标记着几个可疑地点...",
            "npc": "凤凰社联络人",
            "thread": "霍格沃茨外勤线",
            "evidence": "凤凰社情报"
        }
    },
    {
        "stage_id": "stage_tianzifang",
        "name": "田子坊·魔法工坊",
        "lat": 31.2105,
        "lng": 121.4680,
        "location_desc": "田子坊",
        "hp_mapping": "魔杖工坊",
        "scene": {
            "title": "定制魔杖",
            "description": "田子坊的小巷里藏着一家独特的魔杖定制工坊。",
            "scene_text": "工坊里堆满了各种魔杖芯材——凤凰羽毛、独角兽毛、龙心弦...工匠师傅正在为一位神秘客户定制一根特殊的魔杖。'这种组合...非常危险，'他皱眉说道，'但客户坚持要这样。'",
            "npc": "魔杖工匠老李",
            "thread": "黑市走私线",
            "evidence": "魔杖订单"
        }
    }
]

# 6条故事线配置
STORY_THREADS = {
    "飞路错拍线": {
        "description": "调查飞路网时空异常",
        "priority": 1,
        "key_item": "以太纺锤",
        "related_stages": ["stage_xintiandi", "stage_bund", "stage_peoplesq", "stage_xujiahui"]
    },
    "封口令线": {
        "description": "揭露魔法部的信息封锁",
        "priority": 2,
        "key_item": "封口令印玺",
        "related_stages": ["stage_huaihai", "stage_yuanmingyuan"]
    },
    "黑市走私线": {
        "description": "追踪黑魔法物品走私网络",
        "priority": 2,
        "key_item": "黑账本",
        "related_stages": ["stage_fuxing", "stage_nanjingrd", "stage_yuyuan", "stage_chenghuang", "stage_tianzifang"]
    },
    "古灵阁审计线": {
        "description": "调查古灵阁的可疑资金流向",
        "priority": 3,
        "key_item": "清算算石",
        "related_stages": ["stage_jingantmpl", "stage_lujiazui"]
    },
    "霍格沃茨外勤线": {
        "description": "协助霍格沃茨处理东方事务",
        "priority": 3,
        "key_item": "霍格沃茨徽章",
        "related_stages": ["stage_oriental", "stage_hengshan"]
    },
    "潮汐奇兽线": {
        "description": "追踪神秘的魔法生物",
        "priority": 4,
        "key_item": "潮汐符",
        "related_stages": ["stage_bund", "stage_lujiazui"]
    }
}

# 测试用的快速事件配置
QUICK_EVENTS = [
    {
        "event_id": "evt_001",
        "name": "神秘人出现",
        "type": "encounter",
        "duration_seconds": 60,
        "choices": [
            {"id": "follow", "text": "跟踪他", "points": 10},
            {"id": "ignore", "text": "装作没看见", "points": 5},
            {"id": "confront", "text": "直接质问", "points": 15}
        ]
    },
    {
        "event_id": "evt_002",
        "name": "可疑包裹",
        "type": "discovery",
        "duration_seconds": 45,
        "choices": [
            {"id": "open", "text": "打开查看", "points": 20},
            {"id": "report", "text": "上报魔法部", "points": 10},
            {"id": "leave", "text": "原地放下", "points": 0}
        ]
    },
    {
        "event_id": "evt_003",
        "name": "紧急投票",
        "type": "gate",
        "duration_seconds": 30,
        "choices": [
            {"id": "yes", "text": "支持行动", "points": 15},
            {"id": "no", "text": "反对行动", "points": 10},
            {"id": "abstain", "text": "弃权", "points": 5}
        ]
    }
]
