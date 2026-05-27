"""
明日 ETF 操作信号脚本（Baostock 版）
-----------------------------------
逻辑：
1. 使用今日收盘数据
2. 判断大盘是否安全（沪深300ETF > MA17）
3. 筛选符合条件的 ETF
4. 若当前持仓不为空，检查是否跌破5日线
5. 输出明日操作建议
"""
import time

import baostock as bs
import pandas as pd
from qq_bot import qq_bot
from datetime import datetime, timedelta
from qq_bot.notifier import generate_html, extract_summary, send_signal_via_template
msg = ""
# =========================
# 参数配置
# =========================
ETF_POOL = {
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
    "sh.516150": "稀土ETF嘉实",
    "sz.159869": "游戏ETF华夏",
    "sz.159326": "电网设备ETF华夏"
}

TOP_N = 2

# =========================
# 工具函数
# =========================

def bs_login():
    lg = bs.login()
    if lg.error_code != "0":
        contact_message("❌ 登录失败")
        raise RuntimeError("❌ Baostock 登录失败")


def bs_logout():
    bs.logout()


def get_close_data(code: str, days: int = 180) -> pd.DataFrame:
    """
    获取后复权收盘数据
    """
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        code,
        "date,close",
        start_date=start,
        end_date=end,
        frequency="d",
        adjustflag="3"  # 后复权
    )

    data = rs.get_data()
    if data.empty:
        return pd.DataFrame()

    data["close"] = pd.to_numeric(data["close"])
    data["date"] = pd.to_datetime(data["date"])
    data.set_index("date", inplace=True)
    return data[["close"]]


def calculate_indicators(df: pd.DataFrame) -> pd.Series:
    df["MA5"] = df["close"].rolling(5).mean()
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA60"] = df["close"].rolling(60).mean()

    df["close_20"] = df["close"].shift(20)
    df["pct_change_20d"] = (df["close"] - df["close_20"]) / df["close_20"] * 100
    df["bias_60"] = (df["close"] - df["MA60"]) / df["MA60"] * 100

    return df.dropna().iloc[-1]


def select_etf(row: pd.Series) -> bool:
    return (
            row["close"]>row["MA5"] > row["MA20"]
            and row["pct_change_20d"] > 5
            and row["bias_60"] < 25
    )


def market_safe() -> bool:
    df = get_close_data("sz.159919")
    if len(df) < 20:
        return False

    df["MA17"] = df["close"].rolling(17).mean()
    last = df.dropna().iloc[-1]
    # return False
    return last["close"] > last["MA17"]


def check_holdings_below_ma5(holdings: list) -> dict:
    """
    检查持仓是否跌破5日线
    返回：{'below_ma5': [], 'above_ma5': []}
    """
    result = {'below_ma5': [], 'above_ma5': []}
    if not holdings:
        return result

    contact_message("📊 检查当前持仓5日线状态:")
    contact_message("-" * 40)

    for code in holdings:
        try:
            # 获取最近60天的数据计算MA5
            df = get_close_data(code, days=60)
            if len(df) < 5:
                contact_message(f"⚠️ {code}: 数据不足，跳过检查")
                continue

            df["MA5"] = df["close"].rolling(5).mean()
            df = df.dropna()

            if df.empty:
                continue

            last = df.iloc[-1]
            name = ETF_POOL.get(code, "未知ETF")

            if last["close"] < last["MA5"]:
                result['below_ma5'].append({
                    'code': code,
                    'name': name,
                    'close': round(last["close"], 3),
                    'ma5': round(last["MA5"], 3)
                })
                contact_message(f"📉 {name} ({code}): 收盘价 {last['close']:.3f} < MA5 {last['MA5']:.3f} (跌破)")
            else:
                result['above_ma5'].append({
                    'code': code,
                    'name': name,
                    'close': round(last["close"], 3),
                    'ma5': round(last["MA5"], 3)
                })
                contact_message(f"📈 {name} ({code}): 收盘价 {last['close']:.3f} > MA5 {last['MA5']:.3f} (安全)")

        except Exception as e:
            contact_message(f"❌ 检查 {code} 失败: {e}")
            continue

    return result


# =========================
# 主逻辑
# =========================

def tomorrow_signal(current_positions: list = None):
    """
    生成明日操作信号
    :param current_positions: 当前持仓列表，如 ['sz.159919', 'sh.515030']
    """
    if current_positions is None:
        current_positions = []

    contact_message("📅 明日操作信号（Baostock）")
    contact_message(f"📆 当前日期：{datetime.now().strftime('%Y-%m-%d')}")
    if current_positions:
        contact_message(f"💼 当前持仓：{current_positions}")
    contact_message("=" * 40)

    bs_login()

    try:
        # 1️⃣ 大盘判断
        if not market_safe():
            print("⚠️ 大盘环境不安全")

            # 如果有持仓，检查是否跌破5日线
            if current_positions:
                ma5_check = check_holdings_below_ma5(current_positions)

                if ma5_check['below_ma5']:
                    contact_message("\n⛔ 操作建议：")
                    contact_message("   🔴 以下持仓已跌破5日线，建议卖出：")
                    for item in ma5_check['below_ma5']:
                        contact_message(f"      {item['name']} ({item['code']}) 收盘价:{item['close']} < MA5:{item['ma5']}")

                if ma5_check['above_ma5']:
                    contact_message("\n✅ 操作建议：")
                    contact_message("   🟢 以下持仓未跌破5日线，可继续持有：")
                    for item in ma5_check['above_ma5']:
                        contact_message(f"      {item['name']} ({item['code']}) 收盘价:{item['close']} > MA5:{item['ma5']}")

                # 如果既没有跌破也没有未跌破（比如数据不足），给出默认建议
                if not ma5_check['below_ma5'] and not ma5_check['above_ma5']:
                    contact_message("\n💰 操作建议：")
                    contact_message("   💰 无有效持仓数据，持有现金")
            else:
                contact_message("\n💰 操作建议：")
                contact_message("   💰 无持仓，持有现金")

            return  # 大盘不安全时，不进行选股和调仓

        # 2️⃣ 扫描 ETF
        ok_list = []
        for code, name in ETF_POOL.items():
            try:
                df = get_close_data(code)
                if len(df) < 60:
                    continue

                row = calculate_indicators(df)
                if select_etf(row):
                    ok_list.append({
                        "code": code,
                        "name": name,
                        "pct": round(row["pct_change_20d"], 2),
                        "bias_60": round(row["bias_60"], 2),
                        "close": round(row["close"], 3),
                        "ma5": round(row["MA5"], 3),
                        "ma20": round(row["MA20"], 3),
                        "ma60": round(row["MA60"], 3)
                    })
            except Exception:
                continue

        # 3️⃣ 有符合标的
        if ok_list:
            # 排序取前N名
            ok_list = sorted(ok_list, key=lambda x: x["pct"], reverse=True)
            ok_list_top_n = ok_list[:TOP_N]

            contact_message("✅ 明日操作建议：")
            contact_message("   🟢 可开仓 / 持有")
            contact_message("   🎯 目标 ETF：")
            for etf in ok_list_top_n:
                contact_message(f"      {etf['name']} ({etf['code']})  20日涨幅: {etf['pct']}%  60日乖离度: {etf['bias_60']}% close {etf['close']} ma5 {etf['ma5']} ma20 {etf['ma20']} ma60 {etf['ma60']}")

            # 如果有持仓，检查是否需要调整
            if current_positions:
                target_codes = [etf['code'] for etf in ok_list_top_n]
                holding_in_target = [pos for pos in current_positions if pos in target_codes]
                holding_not_in_target = [pos for pos in current_positions if pos not in target_codes]

                if holding_not_in_target:
                    contact_message("\n⚠️ 需要调整持仓：")
                    for code in holding_not_in_target:
                        name = ETF_POOL.get(code, "未知ETF")
                        contact_message(f"   🔴 卖出(不在目标池): {name} ({code})")

                if holding_in_target:
                    contact_message("\n✅ 可继续持有：")
                    for code in holding_in_target:
                        name = ETF_POOL.get(code, "未知ETF")
                        contact_message(f"   🟢 {name} ({code})")

            # 显示其他符合条件的ETF
            if len(ok_list) > TOP_N:
                contact_message("\n⚠️ 其他满足条件的ETF:")
                for etf in ok_list[TOP_N:]:
                    contact_message(f"   📈 {etf['name']} ({etf['code']})  20日涨幅: {etf['pct']}% 60日乖离度: {etf['bias_60']}% close {etf['close']} ma5 {etf['ma5']} ma20 {etf['ma20']} ma60 {etf['ma60']}")

        # 4️⃣ 无符合标的
        else:
            contact_message("⚠️ 无符合条件的新标的")

            # 检查当前持仓
            if current_positions:
                ma5_check = check_holdings_below_ma5(current_positions)

                if ma5_check['below_ma5']:
                    contact_message("\n⛔ 操作建议：")
                    contact_message("   🔴 以下持仓已跌破5日线，建议卖出：")
                    for item in ma5_check['below_ma5']:
                        contact_message(f"      {item['name']} ({item['code']}) 收盘价:{item['close']} < MA5:{item['ma5']}")

                if ma5_check['above_ma5']:
                    contact_message("\n✅ 操作建议：")
                    contact_message("   🟢 以下持仓未跌破5日线，可继续持有：")
                    for item in ma5_check['above_ma5']:
                        contact_message(f"      {item['name']} ({item['code']}) 收盘价:{item['close']} > MA5:{item['ma5']}")

                if not ma5_check['below_ma5'] and not ma5_check['above_ma5']:
                    contact_message("\n💰 操作建议：")
                    contact_message("   💰 无有效持仓数据，持有现金")
            else:
                contact_message("\n💰 操作建议：")
                contact_message("   💰 无符合条件标的，持有现金")

    finally:
        bs_logout()


# =========================
# 执行入口
# =========================
def contact_message(message):
    global msg
    msg = msg + "\n" + message
def print_message():
    global msg

    # 1️⃣ 生成 HTML
    html_path = generate_html(msg)

    # 2️⃣ 提取摘要
    summary = extract_summary(msg)

    # 3️⃣ 发送模板消息
    token = qq_bot.get_access_token()
    html_url = "file://" + html_path  # 本地调试用

    result = send_signal_via_template(
        qq_bot.open_id,
        qq_bot.template_id,
        token,
        html_url
    )

    print(result)
if __name__ == "__main__":
    mock_positions = [
        'sz.159131',
        'sh.562500',
    ]
    tomorrow_signal(mock_positions)
    print_message()
