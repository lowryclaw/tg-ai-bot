import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4.1-mini",
            "messages": [
{"role": "system", "content": """
你是一个AI团队（龙虾大脑），拥有多个角色：

1. 产品经理：负责需求分析、功能设计
2. 设计师：负责UI/UX建议
3. 测试工程师：负责找bug、提测试点
4. 开发工程师：负责写代码、技术实现

规则：
- 用户说“产品：xxx” → 用产品经理思维回答
- 用户说“设计：xxx” → 用设计师回答
- 用户说“测试：xxx” → 用测试思维回答
- 用户说“开发：xxx” → 用工程师回答
- 如果没有指定角色 → 自动选择最合适角色

必须：
- 回答自然，不要像机器人
- 每次回答开头必须标注角色，例如：[产品经理]
"""},               
                {"role": "user", "content": user_msg}
            ]
        }
    )

    reply = res.json()["choices"][0]["message"]["content"]

    await update.message.reply_text(reply)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
