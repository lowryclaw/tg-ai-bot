import os
import requests
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ===== 工具函数 =====

def get_price(symbol):
    symbol_map = {
        "btc": "bitcoin",
        "bitcoin": "bitcoin",
        "eth": "ethereum",
        "ethereum": "ethereum",
        "bnb": "binancecoin",
        "sol": "solana"
    }

    coin_id = symbol_map.get(symbol.lower(), symbol.lower())

    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd"}
        )
        data = res.json()

        if coin_id not in data:
            return f"不支持 {symbol}"

        return f"{symbol.upper()} 当前价格约为 {data[coin_id]['usd']} USD"

    except:
        return "价格获取失败"


def get_weather(city):
    try:
        res = requests.get(f"https://wttr.in/{city}?format=3")
        return res.text
    except:
        return "天气获取失败"


def web_search(query):
    try:
        res = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json"}
        )
        data = res.json()
        return data.get("AbstractText", "")[:300]
    except:
        return "搜索失败"


# ===== 工具注册表（核心）=====
TOOLS = {
    "get_price": get_price,
    "get_weather": get_weather,
    "web_search": web_search
}


# ===== Agent核心 =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    # ===== 1️⃣ AI决定要不要调用工具 =====
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
你是一个AI Agent。

你可以调用以下工具：

1. get_price(symbol)
2. get_weather(city)
3. web_search(query)

当需要工具时，返回JSON：

{
  "tool": "get_price",
  "arguments": {"symbol": "BTC"}
}

否则返回：

{"tool": "none"}

⚠️ 只返回JSON，不要解释
"""
                },
                {"role": "user", "content": user_msg}
            ]
        }
    )

    decision_text = decision_res.json()["choices"][0]["message"]["content"]

    # ===== 解析 =====
    try:
        decision = json.loads(decision_text)
    except:
        decision = {"tool": "none"}

    tool = decision.get("tool")
    args = decision.get("arguments", {})

    tool_result = ""

    # ===== 2️⃣ 通用执行（关键！）=====
    if tool in TOOLS:
        await update.message.reply_text("⚙️ 正在处理...")
        try:
            tool_result = TOOLS[tool](**args)
        except Exception as e:
            tool_result = f"工具执行失败: {str(e)}"

    # ===== 3️⃣ 多角色回答 =====
    final_res = requests.post(
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
你是AI团队（龙虾大脑）：

角色：
- 产品经理
- 设计师
- 测试工程师
- 开发工程师

规则：
- 自动选择角色
- 回答自然
- 开头标注：[角色]

工具规则：
- 如果有工具结果，必须用它
- 不要解释工具
"""
                },
                {
                    "role": "user",
                    "content": f"""
用户问题：
{user_msg}

工具结果：
{tool_result}
"""
                }
            ]
        }
    )

    reply = final_res.json()["choices"][0]["message"]["content"]

    await update.message.reply_text(reply)


# ===== 启动 =====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🚀 Agent（函数调用版）已启动")
app.run_polling()
