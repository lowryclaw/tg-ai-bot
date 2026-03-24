import os
import requests
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ===== 通用搜索 =====
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


# ===== 通用价格查询（支持BTC/ETH等）=====
def get_price(symbol):
    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": symbol.lower(),
                "vs_currencies": "usd"
            }
        )
        data = res.json()
        return f"{symbol.upper()} 当前价格约为 {data[symbol.lower()]['usd']} USD"
    except:
        return "获取价格失败"


# ===== 主逻辑 =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    # ===== 1️⃣ AI决策工具 =====
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

你可以选择：

1. web_search → 查询信息
2. get_price → 查询币价（BTC/ETH等）
3. none → 不需要工具

必须返回JSON，例如：

{"tool": "web_search", "query": "今天黄金价格"}

或

{"tool": "get_price", "symbol": "BTC"}

或

{"tool": "none"}
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
    if tool == "web_search":
        await update.message.reply_text("🔎 搜索中...")
        tool_result = web_search(decision.get("query", user_msg))

    elif tool == "get_price":
        await update.message.reply_text("📊 查询价格中...")
        symbol = decision.get("symbol", "BTC")
        tool_result = get_price(symbol)

    # ===== 3️⃣ AI最终回答（多角色）=====
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
你是一个AI团队（龙虾大脑），包含多个角色：

1. 产品经理
2. 设计师
3. 测试工程师
4. 开发工程师

规则：
- 用户说“产品：xxx” → 产品经理
- 用户说“设计：xxx” → 设计师
- 用户说“测试：xxx” → 测试工程师
- 用户说“开发：xxx” → 开发工程师
- 如果没有指定 → 自动选择最合适角色

工具规则：
- 如果有工具结果，优先基于工具结果回答
- 不要解释工具调用过程

必须：
- 回答自然
- 每次开头标注角色，例如：[开发工程师]
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

print("🤖 龙虾大脑（通用Agent版）已启动...")
app.run_polling()
