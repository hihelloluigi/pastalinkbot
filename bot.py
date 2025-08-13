import os
import json
import logging
import random
import re
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)

from llm import classify  # Local LLM classifier via Ollama
from utils.i18n import get_translator  # gettext translator

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DATA_PATH = os.getenv("DATA_PATH", "./data/pa_bot_links_seed.json")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Load catalog data ---
with open(DATA_PATH, "r", encoding="utf-8") as f:
    CATALOG: List[Dict[str, Any]] = json.load(f)

REGIONS = sorted({row["region"] for row in CATALOG if row.get("region") and row["region"] != "Nazionale"})
ASK_REGION, = range(1)

# --- Patterns that should trigger help/about before LLM ---
HELP_PATTERNS = [
    r"\bhelp\b",
    r"\baiuto\b",
    r"\bcosa\s+sai\s+fare\b",
    r"\bwhat\s+can\s+you\s+do\b",
]
ABOUT_PATTERNS = [
    r"\bchi\s+sei\b",
    r"\bwho\s+are\s+you\b",
]

def matches_any(text: str, patterns) -> bool:
    """Return True if text matches any regex in patterns."""
    t = text.lower()
    return any(re.search(p, t) for p in patterns)


def links_for(intent: str, region: Optional[str]) -> List[Dict[str, Any]]:
    """Return catalog entries matching the intent and (optionally) a region."""
    res = []
    for row in CATALOG:
        if row.get("intent") != intent:
            continue
        if region and row.get("region") == region:
            res.append(row)
        elif not region and row.get("region") == "Nazionale":
            res.append(row)
    return res


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with i18n help text."""
    _ = get_translator("it")
    await update.message.reply_text(_(
        "Here’s what I can do:\n"
        "• Health record / prescriptions / reports (per region)\n"
        "• Car tax (calculation/payment)\n"
        "• Driving license renewal\n"
        "• ANPR / registry certificates\n"
        "• IO App / PagoPA\n"
        "• CUP (medical booking) and school (enrolments)\n"
        "• Waste tax (TARI) info\n"
        "\n"
        "Examples:\n"
        "• *Where do I see the doctor’s prescriptions in Lombardia?*\n"
        "• *Where do I pay the car tax?*\n"
        "• *How do I renew my driving license?*"
    ),
     parse_mode=ParseMode.MARKDOWN
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command (i18n)."""
    _ = get_translator("it")
    await update.message.reply_text(_(
        "Here’s what I can do:\n"
        "• Health record / prescriptions / reports (per region)\n"
        "• Car tax (calculation/payment)\n"
        "• Driving license renewal\n"
        "• ANPR / registry certificates\n"
        "• IO App / PagoPA\n"
        "• CUP (medical booking) and school (enrolments)\n"
        "• Waste tax (TARI) info\n"
        "\n"
        "Examples:\n"
        "• *Where do I see the doctor’s prescriptions in Lombardia?*\n"
        "• *Where do I pay the car tax?*\n"
        "• *How do I renew my driving license?*"
    ),
     parse_mode=ParseMode.MARKDOWN
    )


async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command (i18n)."""
    _ = get_translator(update.effective_user.language_code)
    await update.message.reply_text(_(
        "I'm **PAstaLinkBot** by PastaBits 🍝\n"
        "I give you the official links to Italian public services without wasting time.\n"
        "No personal data: just quick links and clear instructions."
    ),
     parse_mode=ParseMode.MARKDOWN
    )


async def reply_with_links(update: Update, intent: str, region: Optional[str]):
    """Send the final list of links for the given intent/region using i18n strings."""
    _ = get_translator(update.effective_user.language_code)

    rows = links_for(intent, region)
    if not rows and region:
        rows = links_for(intent, None)  # fallback to national

    if not rows:
        await update.message.reply_text(_("I couldn’t find a link."))
        return

    header = _("Useful links ({intent})\n").format(intent=intent.replace("_", " "))
    body = "\n".join(f"• {r.get('label')}: {r.get('url')}" for r in rows[:6])
    await update.message.reply_text(header + body)


async def ask_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the region answer without calling the LLM (conversation state)."""
    _ = get_translator(update.effective_user.language_code)
    region_text = (update.message.text or "").strip()
    intent = context.user_data.get("pending_intent")

    if not intent:
        # No pending intent, fall back to normal flow
        await update.message.reply_text(_("🧠..."))
        return ConversationHandler.END

    if not region_text:
        await update.message.reply_text(_("For which region?"))
        return ASK_REGION

    await reply_with_links(update, intent, region_text)
    context.user_data.pop("pending_intent", None)
    return ConversationHandler.END


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler: classify text with LLM and reply with i18n strings."""
    _ = get_translator(update.effective_user.language_code)
    text = (update.message.text or "").strip()

    # Heuristic overrides for help/about
    if matches_any(text, HELP_PATTERNS):
        await help_cmd(update, context)
        return
    if matches_any(text, ABOUT_PATTERNS):
        await about_cmd(update, context)
        return

    # Typing indicator + placeholder
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    placeholder = await update.message.reply_text(_("🧠..."))

    # LLM classification
    result = classify(text)
    intent = (result.get("intent") or "unknown").lower()
    region = result.get("region")
    needs_region = bool(result.get("needs_region"))

    # Conversational intents
    if intent == "greeting":
        await placeholder.edit_text(random.choice([
            _("Hi there! 👋 Ready to serve your links al dente 🍝"),
            _("Hey! I'm here to untangle your public service spaghetti 😉"),
            _("Hello! Tell me what you need and I’ll link it in one click.")
        ]))
        return

    if intent == "smalltalk":
        await placeholder.edit_text(random.choice([
            _("All good here! Stirring some links in the pot 😄"),
            _("Thanks! Ask me about car tax, health records, driving license, CUP…"),
            _("Always online: pixels, pasta, and public administration!")
        ]))
        return

    if intent == "help":
        await placeholder.delete()
        await help_cmd(update, context)
        return

    if intent == "about":
        await placeholder.delete()
        await about_cmd(update, context)
        return

    if intent == "off_topic":
        await placeholder.edit_text(_(
            "I deal with **Italian public services**: health record/recipes, car tax, driving license, "
            "ANPR/certificates, IO/PagoPA, CUP, school, waste tax.\n"
            "Try: *“Where do I pay the car tax in Lombardia?”* or *“Where do I see the doctor’s prescriptions?”*"
        ))
        return

    # Operational intents that require a region
    if intent in {"fascicolo_sanitario", "bollo_auto", "cup"} and not region and needs_region:
        await placeholder.edit_text(_("For which region?"))
        context.user_data["pending_intent"] = intent
        return ASK_REGION  # <-- enter region state

    # We have enough info: send links
    await placeholder.delete()
    await reply_with_links(update, intent, region)


def main():
    """Main entry point for the bot."""
    if not TELEGRAM_TOKEN:
        raise RuntimeError("Set TELEGRAM_TOKEN in .env")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            ASK_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_region)]
        },
        fallbacks=[CommandHandler("start", start), CommandHandler("help", help_cmd)],
        name="region_conversation",
        persistent=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(conv)

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()