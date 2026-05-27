import requests
open_id = "o4qtq6wS9zthnKP8z5f74e1m_vrI"
APPID = "wxbe3dd6f4aaddc86f"
APPSECRET = "cc79700d7668dcf42590795d94051f00"
template_id = "B6g-Fe3d1iN1jbRImBipVVkTfmVtOGKX4_euWVMmMLU"
def get_access_token():
    url = "https://api.weixin.qq.com/cgi-bin/token"
    resp = requests.get(url, params={
        "grant_type": "client_credential",
        "appid": APPID,
        "secret": APPSECRET,
    }, timeout=10)
    return resp.json()["access_token"]
