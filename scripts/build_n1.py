# -*- coding: utf-8 -*-
"""
Builder for Kanji Master N1 dataset (30 chapters + special readings).
"""

import os
import json
import sys
sys.path.append(os.path.dirname(__file__))
from fetcher import fetch_batch_mazii, format_kanji_record

N1_CURRICULUM = [
    {
        "chapter": 1,
        "name": "1章 行為-1 (Hành vi & Hành động 1)",
        "page": 12,
        "sections": [
            ("行為1", ["為", "扱", "披", "抑", "抵", "抗", "掲", "拭"]),
            ("行為2", ["跳", "躍", "踏", "駆", "伏", "弾", "裂", "塗"]),
            ("行為3", ["叱", "黙", "唱", "聴", "眺", "隠", "添", "排"]),
            ("行為4", ["挑", "操", "磨", "奪", "妨", "遮", "伴", "揺"]),
            ("行為5", ["尽", "諦", "誓", "悟", "避", "耐", "焦", "慌"])
        ]
    },
    {
        "chapter": 2,
        "name": "2章 行為-2 (Hành vi & Hành động 2)",
        "page": 18,
        "sections": [
            ("行為6", ["尋", "促", "惑", "譲", "陥", "迫", "遂", "抽"]),
            ("行為7", ["覆", "偽", "輝", "控", "砕", "削", "挟", "挿"]),
            ("行為8", ["及", "紛", "免", "慎", "併", "劣", "隔", "抹"]),
            ("行為9", ["惜", "嘆", "驚", "憩", "粘", "奮", "歓", "諭"]),
            ("行為10", ["忍", "狂", "奔", "貪", "侮", "辱", "褒", "慰"])
        ]
    },
    {
        "chapter": 3,
        "name": "3章 人間関係 (Quan hệ con người)",
        "page": 28,
        "sections": [
            ("家族・親族", ["嫁", "婿", "縁", "戚", "系", "姻", "叔", "伯"]),
            ("人生", ["恩", "涯", "継", "婆", "紳", "淑", "嬢"]),
            ("敬意・礼儀", ["貴", "威", "仰", "謹", "賀", "奉", "忠", "孝"]),
            ("自己・他者", ["貞", "徳", "称", "郎", "俺", "己", "孤", "匿"]),
            ("死・追悼", ["遺", "逝", "葬", "忌", "棺", "墓", "故", "魂"])
        ]
    },
    {
        "chapter": 4,
        "name": "4章 食・住 (Ẩm thực & Nhà ở)",
        "page": 34,
        "sections": [
            ("食材", ["桃", "柿", "芋", "栗", "腐", "昆", "漬", "藻"]),
            ("調理", ["沸", "騰", "煮", "炊", "揚", "炒", "蒸", "鍋"]),
            ("建物", ["舎", "塔", "垣", "邸", "亭", "房", "棟", "倉"]),
            ("道具", ["縄", "綱", "網", "絞", "盆", "鉢", "刃", "栓"]),
            ("住居設備", ["扉", "棚", "卓", "斎", "堀", "炉", "芳", "臭"])
        ]
    },
    {
        "chapter": 5,
        "name": "5章 状態-1 (Trạng thái & Tính chất 1)",
        "page": 44,
        "sections": [
            ("状態1", ["穏", "暇", "滑", "雰", "朝", "裕", "乏", "微"]),
            ("状態2", ["愚", "稚", "猛", "烈", "卑", "壮", "陰", "膨"]),
            ("状態3", ["奇", "妙", "徹", "魅", "凡", "甲", "乙", "恒"]),
            ("時間・頻度", ["至", "瞬", "旬", "頃", "徐", "頻", "逐", "斉"]),
            ("程度・性質", ["唯", "疎", "剰", "緩", "街", "殊", "偏", "宜"])
        ]
    },
    {
        "chapter": 6,
        "name": "6章 状態-2 (Trạng thái & Tâm lý 2)",
        "page": 50,
        "sections": [
            ("感情1", ["慈", "慕", "悦", "愉", "哀", "情", "閑", "慮"]),
            ("感情2", ["愁", "憂", "憤", "慨", "惨", "寂", "剛", "敢"]),
            ("性格・性質", ["俊", "敏", "迅", "豪", "巧", "粋", "粗", "丈"]),
            ("心理", ["懐", "悔", "怪", "妄", "恨", "羨", "煩", "憧"]),
            ("容姿・様子", ["飽", "錯", "瞭", "寛", "悠", "醜", "麗"])
        ]
    },
    {
        "chapter": 7,
        "name": "7章 自然-1 (Thiên nhiên & Sinh thái 1)",
        "page": 60,
        "sections": [
            ("植物", ["幹", "茎", "芽", "苗", "芝", "茂", "郊", "樹"]),
            ("動物", ["獲", "尾", "雄", "雌", "滅", "獣", "狩", "猟"]),
            ("物質・鉱物", ["窒", "素", "亜", "鉛", "硫", "酸", "磁", "晶"]),
            ("水辺", ["潮", "浦", "泊", "清", "潔", "没", "濁", "澄"]),
            ("気象", ["霧", "霜", "露", "曇", "虹", "圏", "緯"])
        ]
    },
    {
        "chapter": 8,
        "name": "8章 自然-2 (Thiên nhiên & Động thực vật 2)",
        "page": 66,
        "sections": [
            ("昆虫・爬虫類", ["蝶", "蚊", "蜂", "蜜", "蛍", "亀", "蛇", "餌"]),
            ("鳥類", ["雀", "鳩", "鴨", "烏", "鶴", "翼", "牙"]),
            ("獣類", ["猿", "狼", "猪", "熊", "虎", "鯨", "竜", "籠"]),
            ("樹木・地形", ["繭", "蚕", "桑", "柳", "峰", "岳", "峠", "漠"]),
            ("水域・地形", ["堤", "隆", "峡", "岬", "渓", "渦", "潤", "郡"])
        ]
    },
    {
        "chapter": 9,
        "name": "9章 仕事 (Nghề nghiệp & Thương mại)",
        "page": 76,
        "sections": [
            ("交通・流通", ["汽", "舶", "搬", "運", "貫", "献", "繁", "拓"]),
            ("農業・生産", ["刈", "稲", "穂", "耕", "穫", "穀", "栽", "培"]),
            ("交渉・事務", ["渉", "提", "摘", "択", "把", "妥", "佐", "請"]),
            ("組織・人事", ["派", "遣", "宣", "卸", "属", "軸", "軌", "還"]),
            ("経営・管理", ["遇", "蓄", "勘", "託", "障", "社", "枢", "顧"])
        ]
    },
    {
        "chapter": 10,
        "name": "10章 教育 (Giáo dục & Học thuật)",
        "page": 82,
        "sections": [
            ("学習・研究", ["礎", "践", "模", "範", "釈", "拠", "克", "奨"]),
            ("徳育・評価", ["哲", "倫", "志", "功", "佳", "秀", "推", "薦"]),
            ("出版・執筆", ["訂", "項", "索", "稿", "翻", "欄", "載", "啓"]),
            ("指導・組織", ["監", "督", "矛", "盾", "浸", "透", "諸", "班"]),
            ("態度・姿勢", ["怠", "誠", "誇", "墜", "繰", "析", "熟", "揮"])
        ]
    },
    {
        "chapter": 11,
        "name": "11章 文化-1 (Văn hóa & Nghệ thuật 1)",
        "page": 92,
        "sections": [
            ("娯楽・芸術", ["庶", "娯", "興", "趣", "釣", "撮", "彫", "創"]),
            ("絵画・工芸", ["俗", "描", "肖", "漫", "陶", "墨", "朱", "淡"]),
            ("音楽", ["琴", "弦", "鼓", "笛", "雅", "奏", "譜", "鑑"]),
            ("宗教・信仰", ["仁", "僧", "尼", "尚", "禅", "鐘", "典"]),
            ("武芸・武器", ["弓", "矢", "硝", "剣", "刀", "鎖", "侍", "騎"])
        ]
    },
    {
        "chapter": 12,
        "name": "12章 文化-2 (Văn hóa, Lịch sử & Hoàng gia 2)",
        "page": 98,
        "sections": [
            ("皇室・貴族", ["宮", "廷", "皇", "帝", "后", "陛", "妃", "姫"]),
            ("表彰・栄誉", ["奨", "彰", "傑", "賜", "勲", "誉", "呈", "冠"]),
            ("神話・霊怪", ["幻", "仙", "聖", "廃", "吉", "凶", "厄", "鬼"]),
            ("歴史・暦", ["幕", "藩", "紀", "暦", "崇", "祥"]),
            ("遺跡・記念", ["碑", "墳", "郷", "旗", "搭", "織", "染"])
        ]
    },
    {
        "chapter": 13,
        "name": "13章 体 (Cơ thể & Y tế)",
        "page": 108,
        "sections": [
            ("顔・頭部", ["瞳", "眉", "頬", "唇", "爪", "喉", "掌", "癖"]),
            ("四肢・体幹", ["裸", "膚", "肢", "膝", "肘", "腕", "脇", "尻"]),
            ("内臓", ["肺", "腸", "肝", "胆", "腹", "腎", "尿", "盲"]),
            ("病気・症状", ["慢", "疾", "疫", "痢", "痛", "胎", "矯", "耗"]),
            ("健康・医療", ["鍛", "錬", "頑", "摂", "肥", "凝", "衰"])
        ]
    },
    {
        "chapter": 14,
        "name": "14章 司法・行政 (Tư pháp & Hành chính)",
        "page": 114,
        "sections": [
            ("法執行", ["秘", "密", "摩", "擦", "締", "施", "衝"]),
            ("裁判・訴訟", ["弁", "訴", "訟", "審", "債", "執", "是", "憲"]),
            ("処分・賠償", ["廃", "棄", "却", "陳", "貫", "賠"]),
            ("犯罪・捜査", ["犠", "牲", "脅", "襲", "逮", "闘", "詐", "欺"]),
            ("治安・防衛", ["邦", "陣", "轄", "拘", "偵", "阻", "斥"])
        ]
    },
    {
        "chapter": 15,
        "name": "15章 付き合い (Giao tiếp & Nghi lễ)",
        "page": 128,
        "sections": [
            ("礼儀・作法", ["儀", "寧", "挨", "拶", "謙", "遜", "汰", "畏"]),
            ("慶弔", ["寿", "恭", "慶", "弔", "旦", "詣", "訃", "喪"])
        ]
    },
    {
        "chapter": 16,
        "name": "16章 仕事・役所 (Công vụ & Công sở)",
        "page": 130,
        "sections": [
            ("財政・給与", ["累", "幣", "俸", "酬", "倹", "廉", "租", "賦"]),
            ("業務・指示", ["采", "逸", "赴", "諮", "唆", "抄", "庸", "憾"]),
            ("連携・委託", ["該", "旋", "扶", "媒", "嘱", "懇", "弊", "綻"]),
            ("規定・閲覧", ["措", "准", "款", "遵", "頒", "閲", "抄", "謄"]),
            ("官職・異動", ["枢", "閑", "宰", "吏", "迭", "諮", "還", "罷"])
        ]
    },
    {
        "chapter": 17,
        "name": "17章 時間・数学・形状・接続詞 (Thời gian, Toán học & Hình học)",
        "page": 138,
        "sections": [
            ("時間", ["睦", "如", "弥", "暁", "宵", "暫", "漸", "刹"]),
            ("数学・数字", ["零", "壱", "弐", "桁", "幾", "箇", "括", "弧"]),
            ("形状・幾何", ["凹", "凸", "垂", "塊", "径", "岐"]),
            ("接続・関係", ["又", "既", "且", "但"])
        ]
    },
    {
        "chapter": 18,
        "name": "18章 文化-3 (Văn hóa, Văn học & Trò chơi)",
        "page": 142,
        "sections": [
            ("文学・詩歌", ["謡", "唄", "吟", "詠", "叙", "随", "韻", "諧"]),
            ("遊戯・娯楽", ["碁", "棋", "駒", "玩", "戯", "稽", "瑠"]),
            ("伝承・妖怪", ["架", "謡", "幽", "霊", "獄", "冥", "妖", "閻"]),
            ("職人・学問", ["旨", "匠", "伎", "儒"])
        ]
    },
    {
        "chapter": 19,
        "name": "19章 着物 (Trang phục & May mặc)",
        "page": 152,
        "sections": [
            ("紡績・織物", ["織", "維", "麻", "絹", "紡", "縫", "繕"]),
            ("服飾・寸法", ["呉", "絞", "珠", "扇", "巾", "寸", "尺"]),
            ("染色・装飾", ["藤", "藍", "漆", "褐", "丹", "錦", "鈴", "唐"]),
            ("和装・履物", ["袖", "裾", "襟", "芯", "履", "駄", "紐", "縛"])
        ]
    },
    {
        "chapter": 20,
        "name": "20章 犯罪・戦争 (Tội phạm & Chiến tranh)",
        "page": 156,
        "sections": [
            ("犯罪・不正", ["賄", "賂", "痴", "窃", "拐", "虐", "喝", "賭"]),
            ("暴力・侵略", ["拉", "拷", "搾", "謀", "懲", "菌", "征", "覇"]),
            ("処罰・戒告", ["懲", "戒", "猶", "陥", "糾", "勅", "勃"]),
            ("戦乱・災禍", ["賊", "邪", "虚", "禍", "堕", "虜", "殉", "誅"]),
            ("拘束・従属", ["奴", "隷", "囚", "屯"])
        ]
    },
    {
        "chapter": 21,
        "name": "21章 建物 (Kiến trúc & Xây dựng)",
        "page": 164,
        "sections": [
            ("構造物", ["栈", "壇", "塀", "坪", "陵", "郭", "楼", "朽"]),
            ("建材・間取り", ["舗", "隙", "構", "瓦", "硝"])
        ]
    },
    {
        "chapter": 22,
        "name": "22章 生活 (Đời sống & Sinh hoạt hàng ngày)",
        "page": 166,
        "sections": [
            ("日用品・食器", ["箸", "椀", "串", "椅", "鞄", "籠", "箋", "銭"]),
            ("醸造・計量", ["醸", "酵", "薫", "殻", "俵", "斗", "升", "斤"]),
            ("食品・調理具", ["麺", "煎", "餅", "釜", "蓋", "耐", "膳", "衷"]),
            ("寝具・設備", ["枕", "鍵", "錠", "呂", "頓", "稽", "糧", "窯"])
        ]
    },
    {
        "chapter": 23,
        "name": "23章 行為・感情・思考 (Tâm lý, Cảm xúc & Hành động sâu sắc)",
        "page": 176,
        "sections": [
            ("動作・攻撃", ["貼", "剥", "据", "斬", "蹴", "狙", "旨", "臨"]),
            ("対応・境遇", ["傍", "鎮", "窮", "堪", "撤", "喚", "享"]),
            ("感覚・表現", ["喚", "匂", "乞", "傲", "漏", "擦", "詮"]),
            ("心理・追究", ["遡", "惧", "悼", "捉", "銘", "葛", "萎"]),
            ("悪意・罵倒", ["嫉", "妬", "嘲", "怨", "呪", "蔑", "罵", "潰"])
        ]
    },
    {
        "chapter": 24,
        "name": "24章 海・山 (Địa hình Biển & Núi rừng)",
        "page": 182,
        "sections": [
            ("海洋・航海", ["氾", "濫", "礁", "潟", "浪", "潜", "帆", "隻"]),
            ("船舶・遭難", ["艦", "艇", "羅", "盤", "遭", "墜", "飢", "餓"]),
            ("山岳・洞窟", ["湧", "崖", "麓", "窟", "坑", "勾", "畔", "堆"]),
            ("開墾・林業", ["伐", "填", "墾", "薪", "斧", "酪"])
        ]
    },
    {
        "chapter": 25,
        "name": "25章 人・様子 (Diện mạo & Tính cách)",
        "page": 188,
        "sections": [
            ("風貌・気質", ["朴", "艶", "淫", "爽", "蜜", "摯", "傲", "聰"]),
            ("曖昧・拙劣", ["曖", "遜", "曖", "昧", "恣", "苛", "庸", "拙"]),
            ("極端・状態", ["顕", "泰", "蛮", "凄", "甚", "僅", "旺", "寡"])
        ]
    },
    {
        "chapter": 26,
        "name": "26章 体 (Cơ thể & Bệnh lý chuyên sâu)",
        "page": 192,
        "sections": [
            ("解剖・組織", ["貌", "痩", "泌", "髄", "脊", "椎", "胞"]),
            ("器官・部位", ["孔", "顎", "咽", "唾", "拳", "股", "腺"]),
            ("医療・治癒", ["癒", "篤", "剖", "醒", "骸", "麻", "痺"]),
            ("外傷・疾患", ["梗", "塞", "臼", "撲", "捻", "挫", "腰", "痛"])
        ]
    },
    {
        "chapter": 27,
        "name": "27章 地名 (Địa danh Nhật Bản)",
        "page": 202,
        "sections": [
            ("地名", ["鎌", "潟", "岐", "滋", "那", "須", "曽"])
        ]
    },
    {
        "chapter": 28,
        "name": "28章 言葉で覚える (Ghi nhớ qua từ vựng)",
        "page": 204,
        "sections": [
            (" từ vựng 1", ["汎", "沙", "茎", "韓", "厘", "附", "彙", "逓"]),
            (" từ vựng 2", ["某", "羞", "赦", "丙", "唸", "哺"])
        ]
    },
    {
        "chapter": 29,
        "name": "29章 身分 (Địa vị & Tước vị)",
        "page": 206,
        "sections": [
            ("thân phận 1", ["侶", "戴", "貢", "帥", "曹", "尉", "躬", "嫡"]),
            ("tước vị 2", ["爵", "侯", "勅", "詔", "謁", "朕"])
        ]
    },
    {
        "chapter": 30,
        "name": "30章 難読編 (Chữ Hán khó đọc & Hiếm gặp)",
        "page": 214,
        "sections": [
            ("khó đọc 1", ["填", "斑", "慄", "弄", "憬", "毀", "蔽", "鬱"]),
            ("khó đọc 2", ["沃", "辣", "触", "冶", "瑠", "璃", "鎧", "璽"]),
            ("khó đọc 3", ["鋳", "墾", "虜", "胴", "敏"])
        ]
    }
]

SPECIAL_READINGS_N1 = [
    {"word": "明日", "reading": "あす", "meaning": "ngày mai (trang trọng)"},
    {"word": "小豆", "reading": "あずき", "meaning": "đậu đỏ nhỏ"},
    {"word": "海女", "reading": "あま", "meaning": "nữ thợ lặn mò ngọc trai"},
    {"word": "硫黄", "reading": "いおう", "meaning": "lưu huỳnh"},
    {"word": "意気地", "reading": "いくじ", "meaning": "nghị lực, dũng khí, khí phách"},
    {"word": "田舎", "reading": "いなか", "meaning": "nông thôn, vùng quê"},
    {"word": "息吹", "reading": "いぶき", "meaning": "hơi thở, luồng sinh khí (mùa xuân)"},
    {"word": "海原", "reading": "うなばら", "meaning": "biển rộng bao la"},
    {"word": "乳母", "reading": "うば", "meaning": "vú em, mẹ nuôi"},
    {"word": "浮気", "reading": "うわき", "meaning": "ngoại tình, lăng nhăng"},
    {"word": "浮つく", "reading": "うわつく", "meaning": "nông nổi, bồng bột, lơ lửng"},
    {"word": "笑顔", "reading": "えがお", "meaning": "nụ cười rạng rỡ"},
    {"word": "叔父", "reading": "おじ", "meaning": "chú, cậu"},
    {"word": "大人", "reading": "おとな", "meaning": "người lớn"},
    {"word": "乙女", "reading": "おとめ", "meaning": "thiếu nữ, trinh nữ"},
    {"word": "叔母", "reading": "おば", "meaning": "cô, dì"},
    {"word": "お神酒", "reading": "おみき", "meaning": "rượu cúng thần linh Thần đạo"},
    {"word": "母屋", "reading": "おもや", "meaning": "nhà chính, gian nhà lớn"},
    {"word": "神楽", "reading": "かぐら", "meaning": "điệu múa tế thần cổ truyền"},
    {"word": "河岸", "reading": "かし", "meaning": "bờ sông, chợ cá bên sông"},
    {"word": "鍛冶", "reading": "かじ", "meaning": "thợ rèn kim loại"},
    {"word": "風邪", "reading": "かぜ", "meaning": "cảm lạnh"},
    {"word": "固唾", "reading": "かたず", "meaning": "nước bọt (nuốt nước bọt nín thở)"},
    {"word": "仮名", "reading": "かな", "meaning": "chữ kana"},
    {"word": "蚊帳", "reading": "かや", "meaning": "màn ngủ chống muỗi"},
    {"word": "為替", "reading": "かわせ", "meaning": "hối đoái ngoại tệ, ngân phiếu"},
    {"word": "河原", "reading": "かわら", "meaning": "bãi sông cát sỏi"},
    {"word": "昨日", "reading": "きのう", "meaning": "hôm qua"},
    {"word": "今日", "reading": "きょう", "meaning": "hôm nay"},
    {"word": "果物", "reading": "くだもの", "meaning": "hoa quả, trái cây"},
    {"word": "玄人", "reading": "くろうと", "meaning": "chuyên gia lão luyện, nhà nghề"},
    {"word": "今朝", "reading": "けさ", "meaning": "sáng nay"},
    {"word": "景色", "reading": "けしき", "meaning": "cảnh sắc, phong cảnh"},
    {"word": "心地", "reading": "ここち", "meaning": "cảm giác trong lòng (dễ chịu...)"},
    {"word": "居士", "reading": "こじ", "meaning": "cư sĩ, người ẩn dật"},
    {"word": "今年", "reading": "ことし", "meaning": "năm nay"},
    {"word": "早乙女", "reading": "さおとめ", "meaning": "cô gái cấy lúa non"},
    {"word": "雑魚", "reading": "ざこ", "meaning": "cá tạp nhỏ, kẻ tép riu vô danh"},
    {"word": "桟敷", "reading": "さじき", "meaning": "khán đài bằng gỗ kê cao"},
    {"word": "差し支える", "reading": "さしつかえる", "meaning": "cản trở, phiền hà"},
    {"word": "五月", "reading": "さつき", "meaning": "tháng 5 âm lịch"},
    {"word": "早苗", "reading": "さなえ", "meaning": "mạ non vừa nhổ cấy"},
    {"word": "五月雨", "reading": "さみだれ", "meaning": "mưa dầm rả rích đầu hè"},
    {"word": "時雨", "reading": "しぐれ", "meaning": "mưa rào thoáng qua mùa thu đông"},
    {"word": "竹刀", "reading": "しない", "meaning": "kiếm tre tập Kendo"},
    {"word": "老舗", "reading": "しにせ", "meaning": "cửa hàng truyền thống lâu đời"},
    {"word": "芝生", "reading": "しばふ", "meaning": "bãi cỏ, thảm cỏ xanh"},
    {"word": "清水", "reading": "しみず", "meaning": "dòng nước suối trong lành"},
    {"word": "三味線", "reading": "しゃみせん", "meaning": "đàn 3 dây shamisen của Nhật"},
    {"word": "砂利", "reading": "じゃり", "meaning": "sỏi đá răm trải đường"},
    {"word": "数珠", "reading": "じゅず", "meaning": "tràng hạt niệm Phật"},
    {"word": "上手", "reading": "じょうず", "meaning": "giỏi, khéo léo"},
    {"word": "白髪", "reading": "しらが", "meaning": "tóc bạc"},
    {"word": "素人", "reading": "しろうと", "meaning": "người nghiệp dư, không chuyên"},
    {"word": "師走", "reading": "しわす", "meaning": "tháng 12 âm lịch chạp"},
    {"word": "数寄屋", "reading": "すきや", "meaning": "nhà trà đạo thanh tịnh mộc mạc"},
    {"word": "相撲", "reading": "すもう", "meaning": "đấu vật Sumo"},
    {"word": "草履", "reading": "ぞうり", "meaning": "dép cói rơm truyền thống Nhật"},
    {"word": "山車", "reading": "だし", "meaning": "xe rước lễ hội rực rỡ"},
    {"word": "太刀", "reading": "たち", "meaning": "thanh kiếm dài Nhật Bản"},
    {"word": "立ち退く", "reading": "たちのく", "meaning": "di dời, giải tỏa khỏi nơi ở"},
    {"word": "七夕", "reading": "たなばた", "meaning": "lễ thất tịch ngưu lang chức nữ"},
    {"word": "足袋", "reading": "たび", "meaning": "tất truyền thống Nhật rẽ ngón"},
    {"word": "稚児", "reading": "ちご", "meaning": "trẻ thơ rước lễ ở đền chùa"},
    {"word": "一日", "reading": "ついたち", "meaning": "ngày mùng một đầu tháng"},
    {"word": "築山", "reading": "つきやま", "meaning": "hòn non bộ, đồi giả trong vườn"},
    {"word": "梅雨", "reading": "つゆ", "meaning": "mùa mưa Nhật Bản"},
    {"word": "凸凹", "reading": "でこぼこ", "meaning": "gồ ghề lồi lõm"},
    {"word": "手伝う", "reading": "てつだう", "meaning": "phụ giúp, giúp đỡ"},
    {"word": "伝馬船", "reading": "てんません", "meaning": "thuyền chèo tay nhỏ trung chuyển"},
    {"word": "投網", "reading": "とあみ", "meaning": "lưới quăng đánh bắt cá"},
    {"word": "十重二十重", "reading": "とえはたえ", "meaning": "trùng trùng điệp điệp nhiều lớp"},
    {"word": "読経", "reading": "どきょう", "meaning": "tụng kinh Phật giáo"},
    {"word": "時計", "reading": "とけい", "meaning": "đồng hồ"},
    {"word": "友達", "reading": "ともだち", "meaning": "bạn bè"},
    {"word": "仲人", "reading": "なこうど", "meaning": "người mai mối hôn nhân"},
    {"word": "名残", "reading": "なごり", "meaning": "dấu vết còn lại, lưu luyến"},
    {"word": "雪崩", "reading": "なだれ", "meaning": "lở tuyết ầm ầm"},
    {"word": "野良", "reading": "のら", "meaning": "đồng ruộng hoang dã (chó hoang, mèo hoang)"},
    {"word": "祝詞", "reading": "のりと", "meaning": "bài văn khấn tế Thần đạo"},
    {"word": "博士", "reading": "はかせ", "meaning": "tiến sĩ, nhà thông thái"},
    {"word": "二十", "reading": "はたち", "meaning": "hai mươi tuổi"},
    {"word": "二十日", "reading": "はつか", "meaning": "ngày hai mươi"},
    {"word": "波止場", "reading": "はとば", "meaning": "bến tàu chắn sóng"},
    {"word": "一人", "reading": "ひとり", "meaning": "một người, đơn độc"},
    {"word": "日和", "reading": "ひより", "meaning": "thời tiết đẹp, dịp tốt lành"},
    {"word": "二人", "reading": "ふたり", "meaning": "hai người"},
    {"word": "二日", "reading": "ふつか", "meaning": "ngày mùng hai, 2 ngày"},
    {"word": "吹雪", "reading": "ふぶき", "meaning": "bão tuyết gió mạnh"},
    {"word": "下手", "reading": "へた", "meaning": "kém cỏi, vụng về"},
    {"word": "部屋", "reading": "へや", "meaning": "căn phòng"},
    {"word": "迷子", "reading": "まいご", "meaning": "trẻ lạc"},
    {"word": "真面目", "reading": "まじめ", "meaning": "chăm chỉ, nghiêm túc"},
    {"word": "真っ赤", "reading": "まっか", "meaning": "đỏ tươi, đỏ bừng mặt"},
    {"word": "真っ青", "reading": "まっさお", "meaning": "xanh ngắt, tái mét mặt"},
    {"word": "土産", "reading": "みやげ", "meaning": "quà lưu niệm đặc sản"},
    {"word": "息子", "reading": "むすこ", "meaning": "con trai"},
    {"word": "眼鏡", "reading": "めがね", "meaning": "kính mắt"},
    {"word": "猛者", "reading": "もさ", "meaning": "người dũng mãnh quả cảm, tay cừ khôi"},
    {"word": "紅葉", "reading": "もみじ", "meaning": "lá phong mùa thu"},
    {"word": "木綿", "reading": "もめん", "meaning": "vải bông sợi cotton"},
    {"word": "最寄り", "reading": "もより", "meaning": "gần nhất (nhà ga gần nhất)"},
    {"word": "八百長", "reading": "やおちょう", "meaning": "trận đấu dàn xếp tỉ số, đóng kịch"},
    {"word": "八百屋", "reading": "やおや", "meaning": "cửa hàng rau củ quả"},
    {"word": "大和", "reading": "やまと", "meaning": "nước Nhật cổ, tinh thần Yamato"},
    {"word": "弥生", "reading": "やよい", "meaning": "tháng 3 âm lịch (mùa xuân sang)"},
    {"word": "浴衣", "reading": "ゆかた", "meaning": "áo kimono mùa hè bằng vải mỏng"},
    {"word": "行方", "reading": "ゆくえ", "meaning": "tung tích nơi đến"},
    {"word": "寄席", "reading": "よせ", "meaning": "nhà hát biểu diễn tấu hài Rakugo"},
    {"word": "若人", "reading": "わこうど", "meaning": "người trẻ tuổi, thanh niên"}
]

def build():
    all_kanji = []
    for ch in N1_CURRICULUM:
        for sec_name, k_list in ch["sections"]:
            all_kanji.extend(k_list)
    print(f"Total N1 kanji to process: {len(all_kanji)}")

    mazii_map = fetch_batch_mazii(all_kanji)

    dataset = []
    kid = 1
    for ch in N1_CURRICULUM:
        ch_num = ch["chapter"]
        ch_name = ch["name"]
        page = ch["page"]
        for sec_name, k_list in ch["sections"]:
            for k in k_list:
                item = mazii_map.get(k, {})
                record = format_kanji_record(
                    kid=kid,
                    kanji=k,
                    chapter=ch_num,
                    chapter_name=ch_name,
                    section=sec_name,
                    page=page,
                    raw_item=item
                )
                dataset.append(record)
                kid += 1

    out_kanji_file = os.path.join(os.path.dirname(__file__), "..", "data", "kanji-n1.json")
    out_special_file = os.path.join(os.path.dirname(__file__), "..", "data", "special-n1.json")

    with open(out_kanji_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(dataset)} kanji to {out_kanji_file}")

    with open(out_special_file, "w", encoding="utf-8") as f:
        json.dump(SPECIAL_READINGS_N1, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(SPECIAL_READINGS_N1)} special readings to {out_special_file}")

if __name__ == "__main__":
    build()
