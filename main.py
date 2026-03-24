import os
import requests
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ===== 搜索工具 =====
def web_search(query):
    try:
        res = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json"}
        )
        data = res.json()
        return data.get("AbstractText", "")[:500]
    except:
        return "搜索失败"


# ===== 通用价格工具 =====
def get_price(symbol):
    try:
        symbol_map = {
            "btc": "bitcoin",
            "bitcoin": "bitcoin",
            "eth": "ethereum",
            "ethereum": "ethereum",
            "bnb": "binancecoin",
            "sol": "solana",
            "doge": "dogecoin",
            "xrp": "ripple"
        }

        coin_id = symbol_map.get(symbol.lower(), symbol.lower())

        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": "usd"
            }
        )

        data = res.json()

        if coin_id not in data:
            return f"暂不支持 {symbol} 的价格查询"

        price = data[coin_id]["usd"]

        return f"{symbol.upper()} 当前价格约为 {price} USD"

    except Exception as e:
        return f"获取价格失败：{str(e)}"


# ===== 主逻辑 =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    # ===== 1️⃣ AI决策（强化版）=====
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
你是一个工具决策AI。

你的任务：判断用户是否在询问“价格”。

【必须用 get_price 的情况】
- 出现：价格 / price / 多少钱
- 或出现币种：btc / bitcoin / eth / ethereum / sol 等

例如：
- btc价格
- bitcoin
- eth多少钱

返回：
{"tool": "get_price", "symbol": "BTC"}

---

【使用 web_search】
- 新闻 / 介绍 / 是什么

返回：
{"tool": "web_search", "query": "xxx"}

---

【否则】
{"tool": "none"}

⚠️ 只返回JSON
"""
                },
                {"role": "user", "content": user_msg}
            ]
        }
    )

    decision_text = decision_res.json()["choices"][0]["message"]["content"]

    try:
        decision = json.loads(decision_text)
        tool = decision.get("tool", "none")
    except:
        tool = "none"
        decision = {}

    tool_result = ""

    # ===== 2️⃣ 执行工具 =====
    if tool == "get_price":
        await update.message.reply_text("📊 查询价格中...")
        symbol = decision.get("symbol", "BTC")
        tool_result = get_price(symbol)

    elif tool == "web_search":
        await update.message.reply_text("🔎 搜索中...")
        tool_result = web_search(decision.get("query", user_msg))

    # ===== 3️⃣ 多角色AI =====
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
你是一个AI团队（龙虾大脑），包含：

1. 产品经理
2. 设计师
3. 测试工程师
4. 开发工程师

规则：
- 用户说“产品：xxx” → 产品经理
- 用户说“设计：xxx” → 设计师
- 用户说“测试：xxx” → 测试工程师
- 用户说“开发：xxx” → 开发工程师
- 未指定 → 自动选择

工具规则：
- 如果有工具结果，必须基于工具结果回答
- 不要说“我调用了工具”

必须：
- 开头标注角色，例如：[开发工程师]
- 语言自然
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

print("🤖 龙虾大脑（最终稳定版）已启动...")
app.run_polling()
