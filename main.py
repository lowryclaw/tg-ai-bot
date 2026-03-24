import os
import requests
import json
import threading
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ===== 命令缓存 =====
COMMAND_CACHE = {"cmd": ""}

# ===== 工具函数 =====
def get_price(symbol):
    symbol_map = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "sol": "solana"
    }
    coin_id = symbol_map.get(symbol.lower(), symbol.lower())

    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd"}
        )
        data = res.json()
        return f"{symbol.upper()} 价格 {data[coin_id]['usd']} USD"
    except:
        return "价格获取失败"


def get_weather(city):
    try:
        return requests.get(f"https://wttr.in/{city}?format=3").text
    except:
        return "天气获取失败"


def web_search(query):
    try:
        res = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json"}
        )
        return res.json().get("AbstractText", "")
    except:
        return "搜索失败"


def send_command(cmd):
    COMMAND_CACHE["cmd"] = cmd
    return f"已发送命令: {cmd}"


# ===== 工具注册 =====
TOOLS = {
    "get_price": get_price,
    "get_weather": get_weather,
    "web_search": web_search,
    "send_command": send_command
}

# ===== Agent逻辑 =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    # ===== AI决策 =====
    decision_res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4.1-mini",
            "messages": [
                {
                    "role": "system",
                    "content": """
你是AI Agent，可调用工具：

get_price(symbol)
get_weather(city)
web_search(query)
send_command(cmd)

如果用户想“操作电脑”，必须用 send_command

示例：
{"tool": "send_command", "arguments": {"cmd": "open_browser"}}

只返回JSON
"""
                },
                {"role": "user", "content": user_msg}
            ]
        }
    )

    decision_text = decision_res.json()["choices"][0]["message"]["content"]

    try:
        decision = json.loads(decision_text)
    except:
        decision = {"tool": "none"}

    tool = decision.get("tool")
    args = decision.get("arguments", {})

    tool_result = ""

    if tool in TOOLS:
        await update.message.reply_text("⚙️ 执行中...")
        try:
            tool_result = TOOLS[tool](**args)
        except Exception as e:
            tool_result = str(e)

    # ===== 最终回答 =====
    final_res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4.1-mini",
            "messages": [
                {"role": "system", "content": "自然回答，不要解释工具"},
                {"role": "user", "content": f"{user_msg}\n结果:{tool_result}"}
            ]
        }
    )

    reply = final_res.json()["choices"][0]["message"]["content"]

    await update.message.reply_text(reply)


# ===== Telegram =====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))


# ===== API（给本地用）=====
api = Flask(__name__)

@api.route("/cmd")
def get_cmd():
    cmd = COMMAND_CACHE["cmd"]
    COMMAND_CACHE["cmd"] = ""
    return jsonify({"command": cmd})


def run_api():
    api.run(host="0.0.0.0", port=5000)


# ===== 启动 =====
threading.Thread(target=run_api).start()

print("🚀 Agent已启动")
app.run_polling()
