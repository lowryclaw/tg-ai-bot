import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ===== 搜索函数 =====
def search(query):
    try:
        res = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_html": 1
            }
        )
        data = res.json()

        abstract = data.get("AbstractText", "")
        related = data.get("RelatedTopics", [])

        texts = []

        if abstract:
            texts.append(abstract)

        for item in related[:3]:
            if isinstance(item, dict) and "Text" in item:
                texts.append(item["Text"])

        return "\n".join(texts)[:1000]

    except Exception:
        return "搜索失败"


# ===== 主逻辑 =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    # ===== 1. 判断是否需要联网 =====
    judge = requests.post(
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
                    "content": "判断用户问题是否需要联网获取最新信息（如价格、天气、新闻等），只回答 YES 或 NO"
                },
                {"role": "user", "content": user_msg}
            ]
        }
    )

    decision = judge.json()["choices"][0]["message"]["content"].strip()
    need_search = "YES" in decision.upper()

    # ===== 2. 是否联网 =====
    if need_search:
        await update.message.reply_text("🔎 我查一下...")

        search_result = search(user_msg)

        final_prompt = f"""
请直接回答用户问题，不要讨论方案，不要反问，不要角色扮演。

基于以下信息给出简洁、明确的答案：

{search_result}

用户问题：
{user_msg}
"""
    else:
        final_prompt = user_msg

    # ===== 3. AI回答 =====
    res = requests.post(
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
优先规则：
- 如果是查询事实（价格、天气、新闻等），直接回答，不进入角色扮演

你是一个AI团队（龙虾大脑），拥有多个角色：

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

要求：
- 回答自然，不像机器人
- 非查询类问题才使用角色
"""
                },
                {"role": "user", "content": final_prompt}
            ]
        }
    )

    reply = res.json()["choices"][0]["message"]["content"]

    await update.message.reply_text(reply)


# ===== 启动 =====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🤖 龙虾大脑 v2 已启动...")
app.run_polling()
