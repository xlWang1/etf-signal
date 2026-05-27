"""
ETF 筛选（纯 akshare · 同一指数只留一只 · 并筛选原池中不存在的）
"""

import akshare as ak
import pandas as pd

# =========================
# 原始 ETF 池子（你提供的）
# =========================
ORIGINAL_POOL = {
    "sh.510300": "沪深300ETF",
    "sh.515030": "新能源车ETF",
    "sh.515790": "光伏产业ETF",
    "sh.512170": "医疗ETF",
    "sz.159865": "养殖ETF",
    "sh.562500": "机器人ETF",
    "sz.159996": "家电ETF",
    "sh.563300": "中证2000ETF",
    "sh.518880": "黄金ETF",
    "sz.159985": "豆粕ETF",
    "sz.159740": "恒生科技ETF",
    "sz.159998": "计算机ETF",
    "sz.159870": "化工ETF",
    "sh.513850": "美国50ETF",
    "sh.513520": "日经ETF",
    "sz.159561": "德国ETF",
    "sz.159131": "港股通信息技术ETF",
    "sz.159381": "创业板人工智能ETF",
    "sh.512800": "银行ETF",
    "sz.159566": "储能电池ETF",
    "sz.159570": "港股通创新药ETF汇添富",
    "sh.588000": "科创50ETF华夏",
    "sh.512000": "券商ETF华宝",
    # "sz.159516": "半导体设备ETF国泰",
    "sh.560780": "半导体设备ETF广发",
    "sh.512400": "有色金属ETF南方",
    "sz.159928": "消费ETF汇添富",
    "sh.515220": "煤炭ETF国泰",
    "sh.512710": "军工龙头ETF富国",
    "sz.159611": "电力ETF广发",
    "sz.159869": "游戏ETF华夏"
}

# =========================
# 参数
# =========================
MIN_FUND_SIZE = 10           # 流通市值≥2亿元
MIN_TODAY_AMOUNT = 1e8      # 当日成交额≥5000万元
MAX_ETF_COUNT = 300

# =========================
# 指数关键词映射
# =========================
INDEX_KEYWORDS = [
    "沪深300", "上证50", "中证500", "中证1000", "中证2000",
    "科创50", "科创100", "创业板", "创业板50",
    "证券", "券商", "证券保险",
    "黄金", "黄金ETF",
    "恒生", "恒生科技", "恒生互联网",
    "纳指", "纳斯达克", "标普",
    "日经", "德国", "法国", "东南亚",
    "医药", "医疗", "创新药",
    "消费", "白酒", "食品",
    "新能源", "光伏", "储能", "电池",
    "芯片", "半导体", "集成电路",
    "人工智能", "AI", "计算机", "软件",
    "机器人", "工业母机",
    "军工", "国防",
    "红利", "低波", "现金流",
    "电力", "煤炭", "钢铁", "有色",
    "化工", "稀土",
    "豆粕", "商品"
]

def extract_index_keyword(name: str) -> str:
    """从 ETF 名称中提取指数关键词"""
    for kw in INDEX_KEYWORDS:
        if kw in name:
            return kw
    return "其他"

def filter_new_etfs(new_pool_df, original_pool):
    """
    筛选出原池中不存在的 ETF

    Args:
        new_pool_df: 新筛选出的 ETF DataFrame
        original_pool: 原始 ETF 池子（字典）

    Returns:
        DataFrame: 原池中不存在的新 ETF
    """
    # 提取原池中的所有代码
    original_codes = set(original_pool.keys())

    # 筛选出原池中不存在的 ETF
    new_etfs = new_pool_df[~new_pool_df["jq_code"].isin(original_codes)].copy()

    return new_etfs

# =========================
# 主逻辑
# =========================
def main():
    print("📥 akshare 拉 ETF 现货列表...")
    spot = ak.fund_etf_spot_em()
    print(f"   拿到 {len(spot)} 条")

    df = pd.DataFrame()
    df["code"] = spot["代码"].astype(str).str.strip()
    df["name"] = spot["名称"].astype(str).str.strip()
    df["size"] = pd.to_numeric(spot["流通市值"], errors="coerce") / 1e8
    df["amount"] = pd.to_numeric(spot["成交额"], errors="coerce")

    # 只保留 51 / 15 开头
    df = df[df["code"].str.startswith(("5", "1"))].copy()

    # ---------- 基础过滤 ----------
    mask = df["size"] >= MIN_FUND_SIZE
    mask &= df["amount"] >= MIN_TODAY_AMOUNT
    mask &= ~df["name"].str.contains("货币|债|国债|转债|货基|日利|添益")

    df = df[mask].copy()
    print(f"   📊 基础过滤后：{len(df)} 只")

    if df.empty:
        print("⚠️ 没有符合条件的 ETF")
        return

    # ---------- 提取指数关键词 ----------
    df["index_keyword"] = df["name"].apply(extract_index_keyword)

    # ---------- 同一指数只留规模最大 ----------
    df = df.sort_values("size", ascending=False)
    df = df.drop_duplicates(subset=["index_keyword"], keep="first")

    print(f"   🔍 按指数去重后：{len(df)} 只")

    # ---------- 转换为聚宽代码格式 ----------
    def to_jq_code(code):
        if code.startswith("5"):
            return f"sh.{code}"
        else:
            return f"sz.{code}"

    df["jq_code"] = df["code"].apply(to_jq_code)

    # ---------- 筛选原池中不存在的 ETF ----------
    print("\n🔍 筛选原池中不存在的 ETF...")
    new_etfs = filter_new_etfs(df, ORIGINAL_POOL)

    if new_etfs.empty:
        print("   ✅ 所有筛选出的 ETF 都已存在于原池中")
        return

    print(f"   📊 原池中不存在的 ETF：{len(new_etfs)} 只")

    # ---------- 排序 & 输出 ----------
    new_etfs = new_etfs.sort_values("size", ascending=False).head(MAX_ETF_COUNT)

    print("\n" + "=" * 60)
    print("✅ 原池中不存在的新 ETF（可直接添加到原池）")
    print("=" * 60)

    for _, r in new_etfs.iterrows():
        print(f'    "{r["jq_code"]}": "{r["name"]}",  # {r["index_keyword"]}')

    print("=" * 60)
    print(f"📌 共筛选出 {len(new_etfs)} 只新 ETF")

    # 保存 CSV
    new_etfs.to_csv("new_etfs_to_add.csv", index=False, encoding="utf-8-sig")
    print("📁 已保存为 new_etfs_to_add.csv")

    # ---------- 可选：显示原池中已存在的 ETF ----------
    existing_etfs = df[df["jq_code"].isin(ORIGINAL_POOL.keys())]
    if not existing_etfs.empty:
        print("\n📊 原池中已存在的 ETF（被过滤掉）：")
        print("=" * 60)
        for _, r in existing_etfs.iterrows():
            print(f'    "{r["jq_code"]}": "{r["name"]}",  # {r["index_keyword"]}')
        print("=" * 60)
        print(f"📌 共 {len(existing_etfs)} 只已在原池中")

if __name__ == "__main__":
    main()