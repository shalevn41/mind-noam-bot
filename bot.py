import asyncio
import logging
import os
from collections import defaultdict, deque

from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

_tavily_key = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=_tavily_key) if _tavily_key else None

SYSTEM_PROMPT = "אתה עוזר אישי חכם ומועיל. עונה תמיד בעברית בצורה ברורה וידידותית."
MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
TEMPERATURE = 0.7
MAX_HISTORY = 10  # message objects (5 conversation turns)

# user_id -> deque of {"role": ..., "content": ...}
conversation_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))

# Keywords that signal the question needs current/real-time information
CURRENT_INFO_KEYWORDS = [
    "היום", "עכשיו", "כרגע", "חדשות", "עדכון", "מחיר", "שער", "תוצאה",
    "אתמול", "השבוע", "החודש", "2024", "2025", "2026",
    "today", "now", "current", "latest", "news", "price", "score", "recent",
    "live", "breaking", "update", "weather", "forecast", "who won", "result",
]


def needs_current_info(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in CURRENT_INFO_KEYWORDS)


def search_tavily(query: str) -> str:
    if not tavily_client:
        return ""
    try:
        result = tavily_client.search(query=query, max_results=3)
        snippets = [
            f"- {r['title']}: {r['content'][:300]}"
            for r in result.get("results", [])
        ]
        return "\n".join(snippets)
    except Exception as e:
        logger.error("Tavily search error: %s", e)
        return ""


def get_groq_response(user_id: int, user_message: str) -> str:
    history = conversation_history[user_id]

    search_context = ""
    if needs_current_info(user_message):
        logger.info("Searching Tavily for: %s", user_message)
        search_context = search_tavily(user_message)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(list(history))

    if search_context:
        augmented = f"{user_message}\n\n[מידע עדכני מהאינטרנט]:\n{search_context}"
        messages.append({"role": "user", "content": augmented})
    else:
        messages.append({"role": "user", "content": user_message})

    completion = groq_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    assistant_reply = completion.choices[0].message.content

    # Store original message (not augmented) so history stays clean
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_reply})

    return assistant_reply


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    first_name = user.first_name if user.first_name else "שם"
    await update.message.reply_text(
        f"שלום {first_name}! 👋\n\n"
        "אני העוזר האישי שלך המופעל על ידי בינה מלאכותית.\n"
        "אני כאן כדי לעזור לך בכל שאלה או בקשה.\n\n"
        "פשוט כתוב לי ואני אשמח לעזור! 😊"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        response = get_groq_response(user_id, user_message)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error("Error getting Groq response: %s", e)
        await update.message.reply_text(
            "מצטער, אירעה שגיאה בעיבוד הבקשה שלך. 😔\n"
            "אנא נסה שוב בעוד מספר שניות."
        )


async def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is not set in environment variables")
    if not tavily_client:
        logger.warning("TAVILY_API_KEY not set — web search disabled")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is starting...")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
