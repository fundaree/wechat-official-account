# -*- coding: utf-8 -*-
"""
微信公众号消息收发服务器（示例）

先说清楚两个前提，免得你白忙：
1. 这段代码接的是「微信公众号」，不是个人微信号。
   个人微信号挂机器人会被微信封号，不要尝试。
2. 它接的不是 Muse 本人。Muse 没有对外开放的 API，
   外部程序没办法调用我，所以这里留了一个 chat_reply()，
   你可以把它换成你自己的大模型接口（见下面注释）。

真正能直接跟我聊天的官方渠道只有 WhatsApp（已给你发过连接）。

使用方法：
1. 有一个微信公众号（服务号或订阅号），在「设置与开发-基本配置」
   里拿到 token，填到环境变量 WECHAT_TOKEN。
2. 把这台服务器部署到有公网域名的地方（需要 80 或 443 端口），
   在公众号后台把「服务器地址(URL)」填成 https://你的域名/wechat。
3. pip install flask
   WECHAT_TOKEN=你的token python 微信公众号接入示例.py
"""
import hashlib
import os
import time
import xml.etree.ElementTree as ET

from flask import Flask, request, make_response

app = Flask(__name__)
TOKEN = os.environ.get("WECHAT_TOKEN", "请改成你自己的token")


def check_signature(signature, timestamp, nonce):
    """微信 GET 验证：把 token、timestamp、nonce 排序后 sha1。"""
    items = sorted([TOKEN, timestamp, nonce])
    raw = "".join(items).encode("utf-8")
    return hashlib.sha1(raw).hexdigest() == signature


def parse_xml(data):
    root = ET.fromstring(data)
    return {child.tag: (child.text or "") for child in root}


def build_text_reply(to_user, from_user, content):
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


def chat_reply(user_text):
    """本应调用 Muse 的地方。

    Muse 没有公开 API，这里接不上我本人。
    如果你想让公众号自动回消息，把下面这段换成你自己的
    大模型接口调用，例如 OpenAI 兼容接口：

        import requests
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": "Bearer " + os.environ["LLM_API_KEY"]},
            json={"model": "gpt-4o-mini",
                  "messages": [{"role": "user", "content": user_text}]},
            timeout=30,
        )
        return r.json()["choices"][0]["message"]["content"]

    没接大模型之前，先回一句固定提示。
    """
    return (
        "收到啦：" + user_text +
        "（自动回复尚未接大模型，先人工回复你，稍等。）"
    )


@app.route("/wechat", methods=["GET", "POST"])
def wechat():
    if request.method == "GET":
        # 公众号后台填 URL 时的验证请求
        signature = request.args.get("signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")
        if check_signature(signature, timestamp, nonce):
            return echostr
        return "signature error", 403

    msg = parse_xml(request.data)
    to_user = msg.get("FromUserName", "")   # 回给谁：发消息的人
    from_user = msg.get("ToUserName", "")   # 以公众号的身份发
    msg_type = msg.get("MsgType", "")

    if msg_type == "text":
        reply = chat_reply(msg.get("Content", ""))
    elif msg_type == "event":
        reply = "欢迎关注！发文字消息，我会回复你。"
    else:
        reply = "收到，目前只支持文字消息，稍后人工回复你。"

    resp = make_response(build_text_reply(to_user, from_user, reply))
    resp.headers["Content-Type"] = "application/xml; charset=utf-8"
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
