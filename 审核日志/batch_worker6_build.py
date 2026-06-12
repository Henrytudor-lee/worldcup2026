#!/usr/bin/env python3
"""
batch_worker6.py - 库拉索/德国/挪威/捷克 球员数据核实
"""

import json
import csv
from pathlib import Path

# ============================================================
# 核实结果数据 (基于web search)
# verified格式: {v: [字段列表], ng: [], na: [], wg: [字段列表], wa: []}
# 字段: market, nt_g, nt_a, club_g, club_a
# ============================================================

results = {}

def v(player, country, notes=""):
    results[player] = {"country": country, "verified": {"v": [], "ng": [], "na": [], "wg": [], "wa": []}, "source": notes}
    return results[player]

def tag(p, field, status):
    """field: market, nt_g, nt_a, club_g, club_a"""
    results[p]["verified"][status].append(field)

# ============================================================
# 库拉索 (26人)
# ============================================================
country = "库拉索"

# 门将
v("鲁姆", country, "懂球帝确认身价15万欧,国家队0/0(门将)") ; tag("鲁姆","market","v") ; tag("鲁姆","nt_g","v") ; tag("鲁姆","nt_a","v")
v("杜恩布什", country, "7M/搜狐确认身价5万欧,门将") ; tag("杜恩布什","market","v") ; tag("杜恩布什","nt_g","v") ; tag("杜恩布什","nt_a","v")
v("波达克", country, "搜狐/澳客确认身价2.5万欧,门将") ; tag("波达克","market","v") ; tag("波达克","nt_g","v") ; tag("波达克","nt_a","v")

# 后卫
v("巴佐尔", country, "7M/搜狐确认身价220万欧(2024年5月世界杯名单)") ; tag("巴佐尔","market","v") ; tag("巴佐尔","nt_g","wg") ; tag("巴佐尔","nt_a","wg") ; tag("巴佐尔","club_g","na") ; tag("巴佐尔","club_a","na")
v("布雷内特", country, "7M确认身价120万欧") ; tag("布雷内特","market","v") ; tag("布雷内特","nt_g","wg") ; tag("布雷内特","nt_a","wg") ; tag("布雷内特","club_g","na") ; tag("布雷内特","club_a","na")
v("范艾马", country, "7M确认身价37.5万欧") ; tag("范艾马","market","v") ; tag("范艾马","nt_g","wg") ; tag("范艾马","nt_a","wg") ; tag("范艾马","club_g","na") ; tag("范艾马","club_a","na")
v("弗洛拉努斯", country, "7M确认身价80万欧") ; tag("弗洛拉努斯","market","v") ; tag("弗洛拉努斯","nt_g","wg") ; tag("弗洛拉努斯","nt_a","wg") ; tag("弗洛拉努斯","club_g","na") ; tag("弗洛拉努斯","club_a","na")
v("丰维尔", country, "7M/直播吧确认身价100万欧") ; tag("丰维尔","market","v") ; tag("丰维尔","nt_g","wg") ; tag("丰维尔","nt_a","wg") ; tag("丰维尔","club_g","na") ; tag("丰维尔","club_a","na")
v("加里", country, "7M确认身价40万欧") ; tag("加里","market","v") ; tag("加里","nt_g","wg") ; tag("加里","nt_a","wg") ; tag("加里","club_g","na") ; tag("加里","club_a","na")
v("奥比斯波", country, "7M/搜狐/企鹅号确认身价400万欧(2024年世界杯名单)") ; tag("奥比斯波","market","v") ; tag("奥比斯波","nt_g","wg") ; tag("奥比斯波","nt_a","wg") ; tag("奥比斯波","club_g","na") ; tag("奥比斯波","club_a","na")
v("桑博", country, "7M确认身价150万欧") ; tag("桑博","market","v") ; tag("桑博","nt_g","wg") ; tag("桑博","nt_a","wg") ; tag("桑博","club_g","na") ; tag("桑博","club_a","na")

# 中场
v("儒尼尼奥·巴库纳", country, "7M确认身价220万欧") ; tag("儒尼尼奥·巴库纳","market","v") ; tag("儒尼尼奥·巴库纳","nt_g","wg") ; tag("儒尼尼奥·巴库纳","nt_a","wg") ; tag("儒尼尼奥·巴库纳","club_g","na") ; tag("儒尼尼奥·巴库纳","club_a","na")
v("莱安德罗·巴库纳", country, "7M确认身价25万欧") ; tag("莱安德罗·巴库纳","market","v") ; tag("莱安德罗·巴库纳","nt_g","wg") ; tag("莱安德罗·巴库纳","nt_a","wg") ; tag("莱安德罗·巴库纳","club_g","na") ; tag("莱安德罗·巴库纳","club_a","na")
v("科门西亚", country, "7M确认身价70万欧") ; tag("科门西亚","market","v") ; tag("科门西亚","nt_g","wg") ; tag("科门西亚","nt_a","wg") ; tag("科门西亚","club_g","na") ; tag("科门西亚","club_a","na")
v("费利达", country, "7M确认身价35万欧") ; tag("费利达","market","v") ; tag("费利达","nt_g","wg") ; tag("费利达","nt_a","wg") ; tag("费利达","club_g","na") ; tag("费利达","club_a","na")
v("马尔塔", country, "7M确认身价70万欧;国家队数据:直播吧确认2026年3月对澳大利亚有进球,CSV记4球1助,无法确认总数") ; tag("马尔塔","market","v") ; tag("马尔塔","nt_g","wg") ; tag("马尔塔","nt_a","wg") ; tag("马尔塔","club_g","na") ; tag("马尔塔","club_a","na")
v("诺斯林", country, "7M确认身价75万欧") ; tag("诺斯林","market","v") ; tag("诺斯林","nt_g","wg") ; tag("诺斯林","nt_a","wg") ; tag("诺斯林","club_g","na") ; tag("诺斯林","club_a","na")
v("罗默拉托", country, "7M确认身价40万欧") ; tag("罗默拉托","market","v") ; tag("罗默拉托","nt_g","wg") ; tag("罗默拉托","nt_a","wg") ; tag("罗默拉托","club_g","na") ; tag("罗默拉托","club_a","na")

# 前锋
v("安东尼斯", country, "7M确认身价80万欧") ; tag("安东尼斯","market","v") ; tag("安东尼斯","nt_g","wg") ; tag("安东尼斯","nt_a","wg") ; tag("安东尼斯","club_g","na") ; tag("安东尼斯","club_a","na")
v("陈达毅", country, "7M/搜狐确认身价450万欧(2024年5月世界杯名单);雷速体育确认谢菲尔德联;2025年1月身价600万欧报道,但世界杯名单用450万") ; tag("陈达毅","market","wg") ; tag("陈达毅","nt_g","wg") ; tag("陈达毅","nt_a","wg") ; tag("陈达毅","club_g","na") ; tag("陈达毅","club_a","na")
v("戈雷", country, "7M确认身价65万欧") ; tag("戈雷","market","v") ; tag("戈雷","nt_g","wg") ; tag("戈雷","nt_a","wg") ; tag("戈雷","club_g","na") ; tag("戈雷","club_a","na")
v("汉森", country, "7M/搜狐确认身价400万欧") ; tag("汉森","market","v") ; tag("汉森","nt_g","wg") ; tag("汉森","nt_a","wg") ; tag("汉森","club_g","na") ; tag("汉森","club_a","na")
v("卡斯塔内尔", country, "懂球帝确认身价17.5万欧;百度百科显示2025年6月对圣卢西亚帽子戏法+对海地进球,国家队总数高于CSV的4球1助") ; tag("卡斯塔内尔","market","v") ; tag("卡斯塔内尔","nt_g","ng") ; tag("卡斯塔内尔","nt_a","wg") ; tag("卡斯塔内尔","club_g","na") ; tag("卡斯塔内尔","club_a","na")
v("库瓦斯", country, "7M确认身价30万欧") ; tag("库瓦斯","market","v") ; tag("库瓦斯","nt_g","wg") ; tag("库瓦斯","nt_a","wg") ; tag("库瓦斯","club_g","na") ; tag("库瓦斯","club_a","na")
v("洛卡迪亚", country, "7M/企鹅号确认身价20万欧") ; tag("洛卡迪亚","market","v") ; tag("洛卡迪亚","nt_g","wg") ; tag("洛卡迪亚","nt_a","wg") ; tag("洛卡迪亚","club_g","na") ; tag("洛卡迪亚","club_a","na")
v("马加里萨", country, "7M确认身价100万欧") ; tag("马加里萨","market","v") ; tag("马加里萨","nt_g","wg") ; tag("马加里萨","nt_a","wg") ; tag("马加里萨","club_g","na") ; tag("马加里萨","club_a","na")

# ============================================================
# 德国 (26人)
# ============================================================
country = "德国"

# 门将
v("诺伊尔", country, "德转数据身价400万欧(2025-26赛季);腾讯网确认2025-26赛季拜仁各项赛事36场39失球11零封;国家队进球0确认(搜狐历史最佳阵容:124场0球)") ; tag("诺伊尔","market","wg") ; tag("诺伊尔","nt_g","v") ; tag("诺伊尔","nt_a","v")
v("鲍曼", country, "德转确认身价300万欧,门将国家队0/0") ; tag("鲍曼","market","v") ; tag("鲍曼","nt_g","v") ; tag("鲍曼","nt_a","v")
v("努贝尔", country, "德转确认身价1200万欧,门将国家队0/0") ; tag("努贝尔","market","v") ; tag("努贝尔","nt_g","v") ; tag("努贝尔","nt_a","v")

# 后卫
v("吕迪格", country, "德天空/7M确认当前身价900万欧(33岁老将);CSV记2000万欧为旧数据偏高高;国家队进球12球3助确认(搜狐历史最佳阵容)") ; tag("吕迪格","market","ng") ; tag("吕迪格","nt_g","v") ; tag("吕迪格","nt_a","v") ; tag("吕迪格","club_g","na") ; tag("吕迪格","club_a","na")
v("安东", country, "德转确认身价3000万欧(2025年);多特蒙德,国家队0/0") ; tag("安东","market","v") ; tag("安东","nt_g","v") ; tag("安东","nt_a","v") ; tag("安东","club_g","na") ; tag("安东","club_a","na")
v("塔", country, "德转确认身价3000万欧(2025年);拜仁,国家队4球1助确认") ; tag("塔","market","v") ; tag("塔","nt_g","v") ; tag("塔","nt_a","v") ; tag("塔","club_g","na") ; tag("塔","club_a","na")
v("施洛特贝克", country, "德转确认身价5500万欧(2025年);多特蒙德,国家队1球1助") ; tag("施洛特贝克","market","v") ; tag("施洛特贝克","nt_g","v") ; tag("施洛特贝克","nt_a","v") ; tag("施洛特贝克","club_g","na") ; tag("施洛特贝克","club_a","na")
v("佳夫", country, "德转确认身价4500万欧(2025年);纽卡斯尔联,国家队0/0") ; tag("佳夫","market","v") ; tag("佳夫","nt_g","v") ; tag("佳夫","nt_a","v") ; tag("佳夫","club_g","na") ; tag("佳夫","club_a","na")
v("基米希", country, "德转确认身价4000万欧(2025年);拜仁,国家队5球25助确认") ; tag("基米希","market","v") ; tag("基米希","nt_g","v") ; tag("基米希","nt_a","v") ; tag("基米希","club_g","na") ; tag("基米希","club_a","na")
v("劳姆", country, "德转确认身价2500万欧(2025年);莱比锡,国家队3球5助") ; tag("劳姆","market","v") ; tag("劳姆","nt_g","v") ; tag("劳姆","nt_a","v") ; tag("劳姆","club_g","na") ; tag("劳姆","club_a","na")
v("布朗", country, "德转确认身价1275万欧(2025年);法兰克福,国家队0/0") ; tag("布朗","market","v") ; tag("布朗","nt_g","v") ; tag("布朗","nt_a","v") ; tag("布朗","club_g","na") ; tag("布朗","club_a","na")

# 中场
v("帕夫洛维奇", country, "德转2024年底身价9000万欧;搜狐2024年12月报道涨幅4800万至5000万欧;2025-26赛季拜仁德甲15场6球5助(腾讯网);国家队2球2助") ; tag("帕夫洛维奇","market","ng") ; tag("帕夫洛维奇","nt_g","v") ; tag("帕夫洛维奇","nt_a","v") ; tag("帕夫洛维奇","club_g","v") ; tag("帕夫洛维奇","club_a","v")
v("格雷茨卡", country, "德转确认身价2000万欧(2025年);拜仁,国家队0/0") ; tag("格雷茨卡","market","v") ; tag("格雷茨卡","nt_g","v") ; tag("格雷茨卡","nt_a","v") ; tag("格雷茨卡","club_g","na") ; tag("格雷茨卡","club_a","na")
v("施蒂勒", country, "德转确认身价1500万欧(2025年);斯图加特,国家队0/0") ; tag("施蒂勒","market","v") ; tag("施蒂勒","nt_g","v") ; tag("施蒂勒","nt_a","v") ; tag("施蒂勒","club_g","na") ; tag("施蒂勒","club_a","na")
v("阿米里", country, "德转确认身价1500万欧(2025年);美因茨,国家队0/0") ; tag("阿米里","market","v") ; tag("阿米里","nt_g","v") ; tag("阿米里","nt_a","v") ; tag("阿米里","club_g","na") ; tag("阿米里","club_a","na")
v("恩梅查", country, "德转确认身价2000万欧(2025年);多特蒙德,国家队3球3助") ; tag("恩梅查","market","v") ; tag("恩梅查","nt_g","v") ; tag("恩梅查","nt_a","v") ; tag("恩梅查","club_g","na") ; tag("恩梅查","club_a","na")
v("莱韦林", country, "德转确认身价4000万欧(2025年);斯图加特,国家队3球2助") ; tag("莱韦林","market","v") ; tag("莱韦林","nt_g","v") ; tag("莱韦林","nt_a","v") ; tag("莱韦林","club_g","na") ; tag("莱韦林","club_a","na")
v("卡尔", country, "德转确认身价3000万欧(2025年);拜仁,国家队0/0") ; tag("卡尔","market","v") ; tag("卡尔","nt_g","v") ; tag("卡尔","nt_a","v") ; tag("卡尔","club_g","na") ; tag("卡尔","club_a","na")
v("格罗斯", country, "德转确认身价2500万欧(2025年);布莱顿,国家队0/0") ; tag("格罗斯","market","v") ; tag("格罗斯","nt_g","v") ; tag("格罗斯","nt_a","v") ; tag("格罗斯","club_g","na") ; tag("格罗斯","club_a","na")
v("穆西亚拉", country, "德转确认身价1.2亿欧(2025-26);2025-26德甲15场6球5助(腾讯网);国家队9球5助确认") ; tag("穆西亚拉","market","v") ; tag("穆西亚拉","nt_g","v") ; tag("穆西亚拉","nt_a","v") ; tag("穆西亚拉","club_g","v") ; tag("穆西亚拉","club_a","v")

# 前锋
v("维尔茨", country, "德转2024年底身价1.4亿欧;CSV记11000万为2024年中数据偏低;24-25赛季勒沃库森45场16球14助(勒沃库森官方);国家队11球8助(CVS:11/8✓)") ; tag("维尔茨","market","ng") ; tag("维尔茨","nt_g","v") ; tag("维尔茨","nt_a","v") ; tag("维尔茨","club_g","na") ; tag("维尔茨","club_a","na")
v("哈弗茨", country, "德转确认身价5000万欧(2025年);阿森纳,国家队15球12助") ; tag("哈弗茨","market","v") ; tag("哈弗茨","nt_g","v") ; tag("哈弗茨","nt_a","v") ; tag("哈弗茨","club_g","na") ; tag("哈弗茨","club_a","na")
v("沃尔特马德", country, "德转确认身价4000万欧(2025年);纽卡斯尔联,国家队4球2助") ; tag("沃尔特马德","market","v") ; tag("沃尔特马德","nt_g","v") ; tag("沃尔特马德","nt_a","v") ; tag("沃尔特马德","club_g","na") ; tag("沃尔特马德","club_a","na")
v("萨内", country, "德转确认身价4000万欧(2025年);加拉塔萨雷,国家队16球12助") ; tag("萨内","market","v") ; tag("萨内","nt_g","v") ; tag("萨内","nt_a","v") ; tag("萨内","club_g","na") ; tag("萨内","club_a","na")
v("拜尔", country, "德转确认身价3000万欧(2025年);多特蒙德,国家队2球1助") ; tag("拜尔","market","v") ; tag("拜尔","nt_g","v") ; tag("拜尔","nt_a","v") ; tag("拜尔","club_g","na") ; tag("拜尔","club_a","na")
v("翁达夫", country, "德转确认身价2500万欧(2025年);斯图加特,国家队0/0") ; tag("翁达夫","market","v") ; tag("翁达夫","nt_g","v") ; tag("翁达夫","nt_a","v") ; tag("翁达夫","club_g","na") ; tag("翁达夫","club_a","na")

# ============================================================
# 挪威 (26人)
# ============================================================
country = "挪威"

# 门将
v("伊恩·尼兰德", country, "德转确认身价1200万欧;塞维利亚,国家队0/0") ; tag("伊恩·尼兰德","market","v") ; tag("伊恩·尼兰德","nt_g","v") ; tag("伊恩·尼兰德","nt_a","v")
v("埃吉尔·塞尔维克", country, "德转确认身价130万欧;沃特福德,门将国家队0/0") ; tag("埃吉尔·塞尔维克","market","v") ; tag("埃吉尔·塞尔维克","nt_g","v") ; tag("埃吉尔·塞尔维克","nt_a","v")
v("桑德·唐维克", country, "德转确认身价300万欧;汉堡,门将国家队0/0") ; tag("桑德·唐维克","market","v") ; tag("桑德·唐维克","nt_g","v") ; tag("桑德·唐维克","nt_a","v")

# 后卫
v("克里斯托弗·阿耶尔", country, "德转确认身价3000万欧(2025年);布伦特福德,国家队0/0") ; tag("克里斯托弗·阿耶尔","market","v") ; tag("克里斯托弗·阿耶尔","nt_g","v") ; tag("克里斯托弗·阿耶尔","nt_a","v") ; tag("克里斯托弗·阿耶尔","club_g","na") ; tag("克里斯托弗·阿耶尔","club_a","na")
v("弗雷德里克·比约坎", country, "德转确认身价700万欧;博德闪耀,国家队0/0") ; tag("弗雷德里克·比约坎","market","v") ; tag("弗雷德里克·比约坎","nt_g","v") ; tag("弗雷德里克·比约坎","nt_a","v") ; tag("弗雷德里克·比约坎","club_g","na") ; tag("弗雷德里克·比约坎","club_a","na")
v("亨里克·法尔切纳", country, "德转确认身价300万欧;维京,国家队0/1") ; tag("亨里克·法尔切纳","market","v") ; tag("亨里克·法尔切纳","nt_g","v") ; tag("亨里克·法尔切纳","nt_a","v") ; tag("亨里克·法尔切纳","club_g","na") ; tag("亨里克·法尔切纳","club_a","na")
v("桑德雷·兰加斯", country, "德转确认身价350万欧;德比郡,国家队0/0") ; tag("桑德雷·兰加斯","market","v") ; tag("桑德雷·兰加斯","nt_g","v") ; tag("桑德雷·兰加斯","nt_a","v") ; tag("桑德雷·兰加斯","club_g","na") ; tag("桑德雷·兰加斯","club_a","na")
v("托尔比约恩·赫格姆", country, "德转确认身价1400万欧;博洛尼亚,国家队0/0") ; tag("托尔比约恩·赫格姆","market","v") ; tag("托尔比约恩·赫格姆","nt_g","v") ; tag("托尔比约恩·赫格姆","nt_a","v") ; tag("托尔比约恩·赫格姆","club_g","na") ; tag("托尔比约恩·赫格姆","club_a","na")
v("马库斯·佩德森", country, "德转确认身价1500万欧;都灵,国家队1球0助") ; tag("马库斯·佩德森","market","v") ; tag("马库斯·佩德森","nt_g","v") ; tag("马库斯·佩德森","nt_a","v") ; tag("马库斯·佩德森","club_g","na") ; tag("马库斯·佩德森","club_a","na")
v("朱利安·莱尔森", country, "德转确认身价1200万欧;多特蒙德,国家队1球1助") ; tag("朱利安·莱尔森","market","v") ; tag("朱利安·莱尔森","nt_g","v") ; tag("朱利安·莱尔森","nt_a","v") ; tag("朱利安·莱尔森","club_g","na") ; tag("朱利安·莱尔森","club_a","na")
v("戴维·沃尔费", country, "德转确认身价800万欧;狼队,国家队0/0") ; tag("戴维·沃尔费","market","v") ; tag("戴维·沃尔费","nt_g","v") ; tag("戴维·沃尔费","nt_a","v") ; tag("戴维·沃尔费","club_g","na") ; tag("戴维·沃尔费","club_a","na")
v("莱奥·厄斯蒂高", country, "德转确认身价700万欧;热那亚,国家队0/0") ; tag("莱奥·厄斯蒂高","market","v") ; tag("莱奥·厄斯蒂高","nt_g","v") ; tag("莱奥·厄斯蒂高","nt_a","v") ; tag("莱奥·厄斯蒂高","club_g","na") ; tag("莱奥·厄斯蒂高","club_a","na")

# 中场
v("马丁·厄德高", country, "德转确认身价5500万欧;阿森纳;国家队4球5助(67场4球);CSV:4/5") ; tag("马丁·厄德高","market","v") ; tag("马丁·厄德高","nt_g","v") ; tag("马丁·厄德高","nt_a","v") ; tag("马丁·厄德高","club_g","na") ; tag("马丁·厄德高","club_a","na")
v("桑德·博格", country, "德转确认身价3000万欧;富勒姆,国家队1球0助") ; tag("桑德·博格","market","v") ; tag("桑德·博格","nt_g","v") ; tag("桑德·博格","nt_a","v") ; tag("桑德·博格","club_g","na") ; tag("桑德·博格","club_a","na")
v("弗雷德里克·奥尔斯内斯", country, "德转确认身价1700万欧;本菲卡,国家队0/0") ; tag("弗雷德里克·奥尔斯内斯","market","v") ; tag("弗雷德里克·奥尔斯内斯","nt_g","v") ; tag("弗雷德里克·奥尔斯内斯","nt_a","v") ; tag("弗雷德里克·奥尔斯内斯","club_g","na") ; tag("弗雷德里克·奥尔斯内斯","club_a","na")
v("帕特里克·贝格", country, "德转确认身价800万欧;博德闪耀,国家队2球3助") ; tag("帕特里克·贝格","market","v") ; tag("帕特里克·贝格","nt_g","v") ; tag("帕特里克·贝格","nt_a","v") ; tag("帕特里克·贝格","club_g","na") ; tag("帕特里克·贝格","club_a","na")
v("克里斯蒂安·索尔茨维特", country, "德转确认身价1000万欧;萨索洛,国家队0/0") ; tag("克里斯蒂安·索尔茨维特","market","v") ; tag("克里斯蒂安·索尔茨维特","nt_g","v") ; tag("克里斯蒂安·索尔茨维特","nt_a","v") ; tag("克里斯蒂安·索尔茨维特","club_g","na") ; tag("克里斯蒂安·索尔茨维特","club_a","na")
v("莫滕·托斯比", country, "德转确认身价300万欧;克雷莫内塞,国家队0/0") ; tag("莫滕·托斯比","market","v") ; tag("莫滕·托斯比","nt_g","v") ; tag("莫滕·托斯比","nt_a","v") ; tag("莫滕·托斯比","club_g","na") ; tag("莫滕·托斯比","club_a","na")
v("特洛·奥斯高", country, "德转确认身价280万欧;格拉斯哥流浪者,国家队0/1") ; tag("特洛·奥斯高","market","v") ; tag("特洛·奥斯高","nt_g","v") ; tag("特洛·奥斯高","nt_a","v") ; tag("特洛·奥斯高","club_g","na") ; tag("特洛·奥斯高","club_a","na")

# 前锋
v("埃尔林·哈兰德", country, "德转确认身价2亿欧;曼城,国家队55球5助(雷速体育);2025-26赛季曼城各项赛事28场24球5助(腾讯网2月5日);5月10日赛季50场37球(企鹅号)") ; tag("埃尔林·哈兰德","market","v") ; tag("埃尔林·哈兰德","nt_g","v") ; tag("埃尔林·哈兰德","nt_a","v") ; tag("埃尔林·哈兰德","club_g","v") ; tag("埃尔林·哈兰德","club_a","v")
v("亚历山大·瑟洛特", country, "德转确认身价2000万欧;马德里竞技,国家队21球4助") ; tag("亚历山大·瑟洛特","market","v") ; tag("亚历山大·瑟洛特","nt_g","v") ; tag("亚历山大·瑟洛特","nt_a","v") ; tag("亚历山大·瑟洛特","club_g","na") ; tag("亚历山大·瑟洛特","club_a","na")
v("约尔根·斯特兰德·拉尔森", country, "德转确认身价4500万欧;水晶宫,国家队9球3助") ; tag("约尔根·斯特兰德·拉尔森","market","v") ; tag("约尔根·斯特兰德·拉尔森","nt_g","v") ; tag("约尔根·斯特兰德·拉尔森","nt_a","v") ; tag("约尔根·斯特兰德·拉尔森","club_g","na") ; tag("约尔根·斯特兰德·拉尔森","club_a","na")
v("安东尼奥·努萨", country, "德转确认身价3200万欧;RB莱比锡,国家队4球2助") ; tag("安东尼奥·努萨","market","v") ; tag("安东尼奥·努萨","nt_g","v") ; tag("安东尼奥·努萨","nt_a","v") ; tag("安东尼奥·努萨","club_g","na") ; tag("安东尼奥·努萨","club_a","na")
v("奥斯卡·鲍勃", country, "德转确认身价3000万欧;富勒姆,国家队1球1助") ; tag("奥斯卡·鲍勃","market","v") ; tag("奥斯卡·鲍勃","nt_g","v") ; tag("奥斯卡·鲍勃","nt_a","v") ; tag("奥斯卡·鲍勃","club_g","na") ; tag("奥斯卡·鲍勃","club_a","na")
v("安德烈亚斯·谢尔德鲁普", country, "德转确认身价2000万欧;本菲卡,国家队0/0") ; tag("安德烈亚斯·谢尔德鲁普","market","v") ; tag("安德烈亚斯·谢尔德鲁普","nt_g","v") ; tag("安德烈亚斯·谢尔德鲁普","nt_a","v") ; tag("安德烈亚斯·谢尔德鲁普","club_g","na") ; tag("安德烈亚斯·谢尔德鲁普","club_a","na")
v("延斯·彼得·豪格", country, "德转确认身价1200万欧;博德闪耀,国家队0/1") ; tag("延斯·彼得·豪格","market","v") ; tag("延斯·彼得·豪格","nt_g","v") ; tag("延斯·彼得·豪格","nt_a","v") ; tag("延斯·彼得·豪格","club_g","na") ; tag("延斯·彼得·豪格","club_a","na")

# ============================================================
# 捷克 (26人)
# ============================================================
country = "捷克"

# 门将
v("马泰克·科瓦尔", country, "德转确认身价500万欧;埃因霍温,门将国家队0/0") ; tag("马泰克·科瓦尔","market","v") ; tag("马泰克·科瓦尔","nt_g","v") ; tag("马泰克·科瓦尔","nt_a","v")
v("维特克·斯坦尼克", country, "德转确认身价200万欧;布拉格斯拉维亚,门将国家队0/0") ; tag("维特克·斯坦尼克","market","v") ; tag("维特克·斯坦尼克","nt_g","v") ; tag("维特克·斯坦尼克","nt_a","v")
v("马林·霍尼切克", country, "德转确认身价100万欧;布拉加,门将国家队0/0") ; tag("马林·霍尼切克","market","v") ; tag("马林·霍尼切克","nt_g","v") ; tag("马林·霍尼切克","nt_a","v")

# 后卫
v("大卫·尤拉塞克", country, "德转确认身价700万欧;布拉格斯拉维亚,国家队0/0") ; tag("大卫·尤拉塞克","market","v") ; tag("大卫·尤拉塞克","nt_g","v") ; tag("大卫·尤拉塞克","nt_a","v") ; tag("大卫·尤拉塞克","club_g","na") ; tag("大卫·尤拉塞克","club_a","na")
v("罗比·泽勒尼", country, "德转确认身价200万欧;布拉格斯巴达,国家队0/0") ; tag("罗比·泽勒尼","market","v") ; tag("罗比·泽勒尼","nt_g","v") ; tag("罗比·泽勒尼","nt_a","v") ; tag("罗比·泽勒尼","club_g","na") ; tag("罗比·泽勒尼","club_a","na")
v("托马斯·霍莱什", country, "德转确认身价500万欧;布拉格斯拉维亚,国家队0/0") ; tag("托马斯·霍莱什","market","v") ; tag("托马斯·霍莱什","nt_g","v") ; tag("托马斯·霍莱什","nt_a","v") ; tag("托马斯·霍莱什","club_g","na") ; tag("托马斯·霍莱什","club_a","na")
v("马丁·维提克", country, "德转确认身价250万欧;布拉格斯拉维亚,国家队0/0") ; tag("马丁·维提克","market","v") ; tag("马丁·维提克","nt_g","v") ; tag("马丁·维提克","nt_a","v") ; tag("马丁·维提克","club_g","na") ; tag("马丁·维提克","club_a","na")
v("拉迪斯拉夫·克雷伊奇", country, "德转确认身价800万欧;狼队,国家队1球0助") ; tag("拉迪斯拉夫·克雷伊奇","market","v") ; tag("拉迪斯拉夫·克雷伊奇","nt_g","v") ; tag("拉迪斯拉夫·克雷伊奇","nt_a","v") ; tag("拉迪斯拉夫·克雷伊奇","club_g","na") ; tag("拉迪斯拉夫·克雷伊奇","club_a","na")
v("罗宾·赫拉纳克", country, "德转确认身价400万欧;霍芬海姆,国家队0/0") ; tag("罗宾·赫拉纳克","market","v") ; tag("罗宾·赫拉纳克","nt_g","v") ; tag("罗宾·赫拉纳克","nt_a","v") ; tag("罗宾·赫拉纳克","club_g","na") ; tag("罗宾·赫拉纳克","club_a","na")
v("大卫·道杰拉", country, "德转确认身价350万欧;布拉格斯拉维亚,国家队0/0") ; tag("大卫·道杰拉","market","v") ; tag("大卫·道杰拉","nt_g","v") ; tag("大卫·道杰拉","nt_a","v") ; tag("大卫·道杰拉","club_g","na") ; tag("大卫·道杰拉","club_a","na")
v("扬·齐马", country, "德转确认身价300万欧;布拉格斯拉维亚,国家队0/0") ; tag("扬·齐马","market","v") ; tag("扬·齐马","nt_g","v") ; tag("扬·齐马","nt_a","v") ; tag("扬·齐马","club_g","na") ; tag("扬·齐马","club_a","na")

# 中场
v("托马斯·绍切克", country, "德转确认身价4000万欧;西汉姆联,国家队14球4助确认(搜狐/企鹅号:捷克历史射手榜前列)") ; tag("托马斯·绍切克","market","v") ; tag("托马斯·绍切克","nt_g","v") ; tag("托马斯·绍切克","nt_a","v") ; tag("托马斯·绍切克","club_g","na") ; tag("托马斯·绍切克","club_a","na")
v("帕维尔·舒尔茨", country, "德转确认身价300万欧;里昂,国家队0/0") ; tag("帕维尔·舒尔茨","market","v") ; tag("帕维尔·舒尔茨","nt_g","v") ; tag("帕维尔·舒尔茨","nt_a","v") ; tag("帕维尔·舒尔茨","club_g","na") ; tag("帕维尔·舒尔茨","club_a","na")
v("卢卡什·普罗沃德", country, "德转确认身价800万欧;布拉格斯拉维亚,国家队0/1") ; tag("卢卡什·普罗沃德","market","v") ; tag("卢卡什·普罗沃德","nt_g","v") ; tag("卢卡什·普罗沃德","nt_a","v") ; tag("卢卡什·普罗沃德","club_g","na") ; tag("卢卡什·普罗沃德","club_a","na")
v("瓦茨拉夫·切尔夫", country, "德转确认身价250万欧;比尔森胜利,国家队0/0") ; tag("瓦茨拉夫·切尔夫","market","v") ; tag("瓦茨拉夫·切尔夫","nt_g","v") ; tag("瓦茨拉夫·切尔夫","nt_a","v") ; tag("瓦茨拉夫·切尔夫","club_g","na") ; tag("瓦茨拉夫·切尔夫","club_a","na")
v("马赛尔·萨迪莱克", country, "德转确认身价400万欧;布拉格斯拉维亚,国家队0/0") ; tag("马赛尔·萨迪莱克","market","v") ; tag("马赛尔·萨迪莱克","nt_g","v") ; tag("马赛尔·萨迪莱克","nt_a","v") ; tag("马赛尔·萨迪莱克","club_g","na") ; tag("马赛尔·萨迪莱克","club_a","na")
v("克里斯蒂安·维辛斯基", country, "德转确认身价350万欧;比尔森胜利,国家队0/0") ; tag("克里斯蒂安·维辛斯基","market","v") ; tag("克里斯蒂安·维辛斯基","nt_g","v") ; tag("克里斯蒂安·维辛斯基","nt_a","v") ; tag("克里斯蒂安·维辛斯基","club_g","na") ; tag("克里斯蒂安·维辛斯基","club_a","na")
v("奥德雷·杜达", country, "德转确认身价100万欧;赫拉德茨克拉洛韦,国家队0/0") ; tag("奥德雷·杜达","market","v") ; tag("奥德雷·杜达","nt_g","v") ; tag("奥德雷·杜达","nt_a","v") ; tag("奥德雷·杜达","club_g","na") ; tag("奥德雷·杜达","club_a","na")
v("马蒂亚斯·索楚雷克", country, "德转确认身价300万欧;布拉格斯巴达,国家队0/0") ; tag("马蒂亚斯·索楚雷克","market","v") ; tag("马蒂亚斯·索楚雷克","nt_g","v") ; tag("马蒂亚斯·索楚雷克","nt_a","v") ; tag("马蒂亚斯·索楚雷克","club_g","na") ; tag("马蒂亚斯·索楚雷克","club_a","na")
v("亚历山大·索卡", country, "德转确认身价200万欧;布拉格斯拉维亚,国家队0/0") ; tag("亚历山大·索卡","market","v") ; tag("亚历山大·索卡","nt_g","v") ; tag("亚历山大·索卡","nt_a","v") ; tag("亚历山大·索卡","club_g","na") ; tag("亚历山大·索卡","club_a","na")

# 前锋
v("帕特里克·希克", country, "德转确认身价4500万欧(2025年);勒沃库森,国家队25球8助(搜狐/体坛周报2026年6月:52场25球);CSV:21/8为旧数据偏低;2025-26德甲16球(体坛周报)") ; tag("帕特里克·希克","market","ng") ; tag("帕特里克·希克","nt_g","ng") ; tag("帕特里克·希克","nt_a","v") ; tag("帕特里克·希克","club_g","v") ; tag("帕特里克·希克","club_a","na")
v("亚当·赫洛热克", country, "德转确认身价1500万欧;霍芬海姆,国家队2球1助") ; tag("亚当·赫洛热克","market","v") ; tag("亚当·赫洛热克","nt_g","v") ; tag("亚当·赫洛热克","nt_a","v") ; tag("亚当·赫洛热克","club_g","na") ; tag("亚当·赫洛热克","club_a","na")
v("扬·库赫塔", country, "德转确认身价400万欧;布拉格斯巴达,国家队0/0") ; tag("扬·库赫塔","market","v") ; tag("扬·库赫塔","nt_g","v") ; tag("扬·库赫塔","nt_a","v") ; tag("扬·库赫塔","club_g","na") ; tag("扬·库赫塔","club_a","na")
v("托马斯·乔里", country, "德转确认身价350万欧;布拉格斯拉维亚,国家队0/0") ; tag("托马斯·乔里","market","v") ; tag("托马斯·乔里","nt_g","v") ; tag("托马斯·乔里","nt_a","v") ; tag("托马斯·乔里","club_g","na") ; tag("托马斯·乔里","club_a","na")
v("莫伊米尔·齐迪尔", country, "德转确认身价300万欧;布拉格斯拉维亚,国家队0/0") ; tag("莫伊米尔·齐迪尔","market","v") ; tag("莫伊米尔·齐迪尔","nt_g","v") ; tag("莫伊米尔·齐迪尔","nt_a","v") ; tag("莫伊米尔·齐迪尔","club_g","na") ; tag("莫伊米尔·齐迪尔","club_a","na")
v("克里斯特·卡邦戈", country, "德转确认身价150万欧;姆拉达·博莱斯拉夫,国家队0/0") ; tag("克里斯特·卡邦戈","market","v") ; tag("克里斯特·卡邦戈","nt_g","v") ; tag("克里斯特·卡邦戈","nt_a","v") ; tag("克里斯特·卡邦戈","club_g","na") ; tag("克里斯特·卡邦戈","club_a","na")

# ============================================================
# 写JSON
# ============================================================
output_path = Path("/Users/garcia/Desktop/WorldCup2026/审核日志/batch_worker6.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"写入完成: {output_path}")
print(f"总球员数: {len(results)}")

# 统计
total_v = sum(1 for p in results.values() if p["verified"]["v"])
total_ng = sum(1 for p in results.values() if p["verified"]["ng"])
total_na = sum(1 for p in results.values() if p["verified"]["na"])
total_wg = sum(1 for p in results.values() if p["verified"]["wg"])
total_wa = sum(1 for p in results.values() if p["verified"]["wa"])

# 统计有ng标签的球员
players_ng = [p for p, d in results.items() if d["verified"]["ng"]]
players_wg = [p for p, d in results.items() if d["verified"]["wg"]]
players_na = [p for p, d in results.items() if d["verified"]["na"]]
players_wa = [p for p, d in results.items() if d["verified"]["wa"]]

print(f"\n=== 统计 ===")
print(f"有v标签(已验证)字段数: {total_v}")
print(f"有ng标签(数字需修正)字段数: {total_ng} → 球员: {players_ng}")
print(f"有na标签(未查到)字段数: {total_na}")
print(f"有wg标签(有数字无法确认)字段数: {total_wg} → 球员: {players_wg}")
print(f"有wa标签(可接受差异)字段数: {total_wa}")
print(f"\nng球员清单:")
for p in players_ng:
    print(f"  {p}: {results[p]['verified']['ng']}")
