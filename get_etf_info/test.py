import baostock as bs
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# 解决中文显示问题（Windows为SimHei，Mac系统可改为 Arial Unicode MS）
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def test_etf_pool_correlation(etf_pool_dict, start_date='2023-05-24', end_date='2026-05-24'):
    """
    对指定的ETF池进行相关性测试与分析
    """
    # 1. 登录 Baostock
    lg = bs.login()
    if lg.error_code != '0':
        print(f"❌ 登录失败: {lg.error_msg}")
        return

    print("🚀 正在获取池中所有ETF的历史数据...")

    # 2. 封装获取单只ETF收盘价的函数
    def get_close_price(code):
        rs = bs.query_history_k_data_plus(
            code,
            "date,close",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3"  # 后复权
        )
        data = rs.get_data()
        if data.empty:
            return None
        data['close'] = pd.to_numeric(data['close'], errors='coerce')
        data.set_index('date', inplace=True)
        return data['close']

    # 3. 遍历你的 etf_pool 字典，提取数据
    price_data = {}
    for code, name in etf_pool_dict.items():
        close_series = get_close_price(code)
        if close_series is not None:
            price_data[name] = close_series  # 用名称作为列名，方便看图表
        else:
            print(f"⚠️ 警告: 未获取到 {code} ({name}) 的数据，已跳过。")

    if len(price_data) < 2:
        print("❌ 有效数据不足，无法计算相关性。")
        bs.logout()
        return

    # 4. 合并数据并计算日收益率
    df_prices = pd.concat(price_data.values(), axis=1, join='inner')
    df_prices.columns = price_data.keys()

    # 计算每日涨跌幅 (pct_change)，这是计算金融相关性的标准做法
    df_returns = df_prices.pct_change().dropna()

    # 5. 计算相关系数矩阵
    corr_matrix = df_returns.corr()

    # 6. 自动化分析：找出高度相关的“内卷”组合
    print("\n🔍 正在扫描高度相关（相关系数 > 0.8）的ETF配对...")
    high_corr_pairs = []
    etf_names = corr_matrix.columns

    for i in range(len(etf_names)):
        for j in range(i + 1, len(etf_names)):
            name1, name2 = etf_names[i], etf_names[j]
            corr_value = corr_matrix.loc[name1, name2]
            if corr_value > 0.8:  # 阈值设为0.85，可根据需求调整
                high_corr_pairs.append((name1, name2, corr_value))

    if high_corr_pairs:
        print("⚠️ 发现以下高度相关（可能存在持仓重叠风险）的组合：")
        for n1, n2, val in sorted(high_corr_pairs, key=lambda x: x[2], reverse=True):
            print(f"   - {n1} 与 {n2}: 相关系数 {val:.4f}")
    else:
        print("✅ 恭喜！未发现相关系数超过 0.8 的高度重叠组合，池子分散度良好。")

    # 7. 可视化：绘制热力图
    plt.figure(figsize=(16, 12))
    # 使用掩码只显示下三角，避免重复展示
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1,
                fmt='.2f', mask=mask, square=True, linewidths=0.5, cbar_kws={"shrink": .8})
    plt.title('你的 ETF 池相关性热力图', fontsize=16)
    plt.tight_layout()
    plt.show()

    # 8. 退出 Baostock
    bs.logout()
    return corr_matrix


if __name__ == '__main__':
    # 将你目前的 ETF 池直接复制进来
    current_etf_pool =  {
        "sh.510300": "沪深300ETF",
        "sh.515030": "新能源车ETF",
        "sh.515790": "光伏产业ETF",
        "sh.512170": "医疗ETF",
        "sz.159865": "养殖ETF",
        "sh.562500": "机器人ETF",
        # "sz.159996": "家电ETF",
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
        # "sh.515070": "人工智能ETF",
        # "sz.159949": "创业板50ETF华安",
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
        "sh.515880": "通信ETF国泰",
        "sh.512980": "传媒ETF广发",
        "sz.159326": "电网设备ETF华夏"

    }

    # 执行测试
    test_etf_pool_correlation(current_etf_pool)