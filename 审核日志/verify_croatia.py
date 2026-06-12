#!/usr/bin/env python3
import json
import os
from datetime import datetime

LOG_FILE = "/Users/garcia/Desktop/WorldCup2026/审核日志/batch_supplement5.json"

def load_log():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_log(data):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_player(name, country, v, ng, na, wg, wa, source):
    log = load_log()
    log[name] = {
        "country": country,
        "verified": {
            "v": v,
            "ng": ng,
            "na": na,
            "wg": wg,
            "wa": wa
        },
        "source": source
    }
    save_log(log)
    print(f"  ✓ 已写入: {name}")

# 5个关键球员
# 1. 卢卡·莫德里奇
add_player(
    "卢卡·莫德里奇",
    "克罗地亚",
    "350万欧",
    "28(待核实，实际生涯约26球)",
    "25(待核实)",
    "待核实(已离开皇马，25-26在AC米兰)",
    "待核实",
    "转会市场/懂球帝:25年7月自由身加盟AC米兰，24-25赛季皇马4球8助攻，身价350万欧"
)

# 2. 伊万·佩里西奇
add_player(
    "伊万·佩里西奇",
    "克罗地亚",
    "2300万欧(网易)/120万欧(腾讯存疑)",
    "38(待核实，网易显示此数据但可能含预选赛)",
    "30(待核实)",
    "7球12助攻(网易:25-26赛季PSV埃因霍温31场)",
    "12",
    "网易/腾讯:25-26赛季PSV埃因霍温，身价2300万欧(另有120万欧说，待核实)"
)

# 3. 安德雷·克拉马里奇
add_player(
    "安德雷·克拉马里奇",
    "克罗地亚",
    "300万欧",
    "36(待核实，实际生涯约26球)",
    "15(待核实)",
    "约11球7助攻(雷速体育:25-26霍芬海姆31场11球7助攻;2月德甲8球)",
    "7",
    "雷速体育/腾讯:25-26霍芬海姆31场11球7助攻，身价300万欧，国家队26球(部分来源)"
)

# 4. 安特·布迪米尔
add_player(
    "安特·布迪米尔",
    "克罗地亚",
    "500万欧",
    "0(存疑，布迪米尔已为国家队出场约28次，应有进球)",
    "0(待核实)",
    "2球(雷速体育:25-26西甲7场2球;另来源21球赛季)，另奥萨苏纳21球赛季",
    "0",
    "雷速体育/腾讯:25-26奥萨苏纳7场2球，身价500万欧；24-25赛季18球"
)

# 5. 约什科·格瓦迪奥尔
add_player(
    "约什科·格瓦迪奥尔",
    "克罗地亚",
    "7000万欧",
    "3(待核实，实际应为5+球)",
    "0",
    "2球4助攻(雷速体育:25-26曼城23场2球4助攻；1月骨折赛季报销)",
    "4",
    "雷速体育/斯基拉:25-26曼城23场2球4助攻，1月胫骨骨折赛季报销，身价7000万欧"
)

print("\n5个关键球员已写入。")
print(f"文件路径: {LOG_FILE}")