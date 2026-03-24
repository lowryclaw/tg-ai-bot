import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ===== 环境变量 =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ===== 搜索函数（联网能力）=====
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
                {"role": "system", "content": "判断用户问题是否需要联网获取最新信息，只回答 YES 或 NO"},
                {"role": "user", "content": user_msg}
            ]
        }
    )

    decision = judge.json()["choices"][0]["message"]["content"].strip()

    # ===== 2. 是否联网 =====
    if "YES" in decision:
        await update.message.reply_text("🔎 我查一下...")

        search_result = search(user_msg)

        final_prompt = f"""
你是一个智能助手，请基于以下搜索结果回答用户问题，用自然语言总结：

搜索结果：
{search_result}

用户问题：
{user_msg}
"""
    else:
        final_prompt = user_msg

    # ===== 3. 多角色AI回答 =====
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
你是一个AI团队（龙虾大脑），拥有多个角色：

1. 产品经理：负责需求分析、功能设计
2. 设计师：负责UI/UX建议
3. 测试工程师：负责找bug、提测试点
4. 开发工程师：负责写代码、技术实现

规则：
- 用户说“产品：xxx” → 用产品经理回答
- 用户说“设计：xxx” → 用设计师回答
- 用户说“测试：xxx” → 用测试回答
- 用户说“开发：xxx” → 用开发回答
- 如果没指定 → 自动选择角色

必须：
- 回答自然，不像机器人
- 每次开头必须标注角色，例如：[产品经理]
"""
                },
                {"role": "user", "content": final_prompt}
            ]
        }
    )

    reply = res.json()["choices"][0]["message"]["content"]

    await update.message.reply_text(reply)


# ===== 启动Bot =====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🤖 龙虾大脑已启动...")
app.run_polling()
