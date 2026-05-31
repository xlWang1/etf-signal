import os
import requests
from datetime import datetime

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "signal.html")
HTML_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "html_output")

os.makedirs(HTML_OUTPUT_DIR, exist_ok=True)


def load_html_template() -> str:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def generate_html(msg: str) -> str:
    """
    生成 HTML 文件并返回文件路径
    """
    html = load_html_template().replace("{{CONTENT}}", msg)

    filename = datetime.now().strftime("%Y%m%d.html")
    path = os.path.join("../page/", filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    html_path = f"https://xlwang1.github.io/etf-signal/page/{filename}"
    print(f"HTML 文件已生成：{html_path}")
    return html_path


def extract_summary(msg: str) -> str:
    """
    从脚本输出中提取 <=20 字摘要（适配微信模板）
    """
    lines = [l.strip() for l in msg.splitlines() if l.strip()]
    for l in lines:
        if any(k in l for k in ["操作建议", "可开仓", "持现金", "卖出", "持有"]):
            return l[:20]
    return lines[0][:20] if lines else "信号已生成"


def send_signal_via_template(openid, template_id, access_token, html_url: str):
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"

    payload = {
        "touser": openid,
        "template_id": template_id,
        "url": html_url,
        "data": {
            "date": {"value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            "notice": {"value": html_url}
        }
    }

    r = requests.post(url, json=payload, timeout=10)
    return r.json()