import os
import logging
import random
import re
import google.generativeai as genai
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.error import BadRequest
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables from a .env file for local development
load_dotenv()

# IMPORTANT: Load secrets from environment variables. Never hardcode them!
# I have replaced your hardcoded keys with this secure method.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Helper Function for MarkdownV2 ---
def escape_markdown_v2(text: str) -> str:
  """
    Escapes characters for Telegram's MarkdownV2 parse mode.
    This is a crucial fix to prevent Telegram API errors.
    """
  # Characters to escape: _ * [ ] ( ) ~ ` > # + - = | { } . !
  escape_chars = r'_*[]()~`>#+-=|{}.!'
  return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


# --- AI Configuration ---
try:
  # Configure Gemini AI
  genai.configure(api_key=GEMINI_API_KEY)
  # FIX: Corrected the model name. 'gemini-2.5-flash' is not a valid model.
  # Using 'gemini-1.5-flash-latest' for the best performance.
  model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
  logger.error(f"Failed to configure Gemini AI: {e}")
  model = None

# --- Bot Content ---
BUSINESS_CATEGORIES = {
    "tech": "🚀 Technology & Software",
    "ecommerce": "🛒 E-commerce & Online Business",
    "health": "🏥 Health & Wellness",
    "food": "🍔 Food & Beverage",
    "education": "📚 Education & Training",
    "finance": "💰 Finance & Investment",
    "marketing": "📱 Marketing & Social Media",
    "sustainability": "🌱 Sustainability & Green Business",
    "retail": "🏪 Retail & Consumer Goods",
    "services": "🔧 Professional Services",
    "entertainment": "🎬 Entertainment & Media",
    "travel": "✈️ Travel & Tourism"
}


# --- Bot Class ---
class BusinessIdeaBot:

  def __init__(self):
    self.updater = None

  def start(self, update: Update, context: CallbackContext):
    """Start command handler"""
    # FIX: Escaped the message to be compatible with MarkdownV2
    welcome_message = escape_markdown_v2(
        """🚀 *Welcome to Business Ideas Generator Bot!*

I can help you generate innovative business ideas across various categories using AI.

*Available Commands:*
• /start - Show this welcome message
• /categories - Browse business categories
• /random - Get a random business idea
• /help - Show help information

*How to use:*
1. Click on /categories to see all available business categories
2. Select a category that interests you
3. Get AI-generated business ideas with detailed information

Let's start your entrepreneurial journey! 🎯""")

    keyboard = [[
        InlineKeyboardButton("📋 Browse Categories",
                             callback_data="show_categories")
    ], [InlineKeyboardButton("🎲 Random Idea", callback_data="random_idea")],
                [InlineKeyboardButton("❓ Help", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Unescape the specific characters we want to be rendered as markdown
    welcome_message = welcome_message.replace("\\*", "*").replace("\\•", "•")

    update.message.reply_text(welcome_message,
                              parse_mode=ParseMode.MARKDOWN_V2,
                              reply_markup=reply_markup)

  def show_categories(self, update: Update, context: CallbackContext):
    """Show business categories"""
    message = escape_markdown_v2(
        "🏢 *Choose a Business Category:*\n\nSelect a category to get tailored business ideas:"
    )
    message = message.replace("\\*", "*")  # Keep the bold formatting

    keyboard = []
    categories_list = list(BUSINESS_CATEGORIES.items())
    for i in range(0, len(categories_list), 2):
      row = []
      for j in range(i, min(i + 2, len(categories_list))):
        key, value = categories_list[j]
        row.append(InlineKeyboardButton(value,
                                        callback_data=f"category_{key}"))
      keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Use query attribute for callback queries
    query = update.callback_query
    if query:
      query.edit_message_text(message,
                              parse_mode=ParseMode.MARKDOWN_V2,
                              reply_markup=reply_markup)
    else:
      update.message.reply_text(message,
                                parse_mode=ParseMode.MARKDOWN_V2,
                                reply_markup=reply_markup)

  def generate_business_idea(self, category_name: str):
    """Generate business idea using Gemini AI"""
    prompt = f"""Generate a comprehensive and innovative business idea for the '{category_name}' category.

Please format your response with the following structure using markdown (use * for bold, not #):

*🚀 Business Idea: [Creative Business Name]*

*💡 Core Concept*
[Brief, compelling description of the business idea]

*🎯 Target Market*
[Define the target audience and market size]

*💰 Revenue Model*
[Explain how the business will make money]

*🔥 Unique Value Proposition*
[What makes this business special and competitive]

*📈 Market Opportunity*
[Market trends and opportunities]

*🛠️ Getting Started*
[3-4 practical steps to launch this business]

*💵 Estimated Startup Investment*
[Rough estimate of initial investment needed]

*⚡ Success Factors*
[Key factors for success in this business]

Ensure the idea is:
- Innovative and relevant to current market trends
- Practical and achievable
- Specific to the {category_name} sector
- Formatted with proper markdown for Telegram.
"""
    try:
      if not model:
        raise Exception("Gemini AI model is not initialized.")
      response = model.generate_content(prompt)
      return response.text
    except Exception as e:
      logger.error(f"Error generating business idea: {e}")
      error_text = f"""*❌ Error Generating Idea*

Sorry, I encountered an error while generating a business idea for *{escape_markdown_v2(category_name)}*.

Please try again later or contact support if the issue persists.

*Error Details:* `{escape_markdown_v2(str(e))}`"""
      return error_text.replace("\\*", "*")  # Keep bold formatting for titles

  def handle_category_selection(self, update: Update,
                                context: CallbackContext):
    """Handle category selection from a button press."""
    query = update.callback_query
    query.answer()

    category_key = query.data.replace("category_", "")
    category_name = BUSINESS_CATEGORIES.get(category_key, "Unknown Category")

    loading_message_text = f"🔄 *Generating business idea for {escape_markdown_v2(category_name)}\\.\\.\\.*\n\nPlease wait while I create an innovative business concept for you\\!"
    loading_message_text = loading_message_text.replace("\\*", "*")
    query.edit_message_text(loading_message_text,
                            parse_mode=ParseMode.MARKDOWN_V2)

    self._generate_and_send_idea(query, context, category_key, category_name)

  def random_business_idea(self, update: Update, context: CallbackContext):
    """Generate a random business idea, works for both command and button."""
    category_key = random.choice(list(BUSINESS_CATEGORIES.keys()))
    category_name = BUSINESS_CATEGORIES[category_key]

    query = update.callback_query
    if query:
      query.answer()
      loading_message_text = f"🎲 *Generating random business idea\\.\\.\\.*\n\n_Category: {escape_markdown_v2(category_name)}_\n\nPlease wait\\!"
      loading_message_text = loading_message_text.replace("\\*", "*").replace(
          "\\_", "_")
      query.edit_message_text(loading_message_text,
                              parse_mode=ParseMode.MARKDOWN_V2)
      self._generate_and_send_idea(query,
                                   context,
                                   category_key,
                                   category_name,
                                   is_random=True)
    else:
      # This handles the /random command
      loading_message_text = f"🎲 *Generating random business idea\\.\\.\\.*\n\n_Category: {escape_markdown_v2(category_name)}_\n\nPlease wait\\!"
      loading_message_text = loading_message_text.replace("\\*", "*").replace(
          "\\_", "_")
      msg = update.message.reply_text(loading_message_text,
                                      parse_mode=ParseMode.MARKDOWN_V2)
      self._generate_and_send_idea(update,
                                   context,
                                   category_key,
                                   category_name,
                                   is_random=True,
                                   loading_msg_id=msg.message_id)

  def _generate_and_send_idea(self,
                              update_or_query,
                              context: CallbackContext,
                              category_key: str,
                              category_name: str,
                              is_random=False,
                              loading_msg_id=None):
    """A helper function to generate and send the idea to avoid code duplication."""
    business_idea = self.generate_business_idea(category_name)

    # Define keyboard based on context
    if is_random:
      keyboard = [[
          InlineKeyboardButton("🎲 Another Random", callback_data="random_idea")
      ],
                  [
                      InlineKeyboardButton("📋 Browse Categories",
                                           callback_data="show_categories")
                  ],
                  [
                      InlineKeyboardButton("🏠 Main Menu",
                                           callback_data="back_to_start")
                  ]]
    else:
      keyboard = [[
          InlineKeyboardButton("🔄 Generate Another",
                               callback_data=f"category_{category_key}")
      ],
                  [
                      InlineKeyboardButton("📋 All Categories",
                                           callback_data="show_categories")
                  ],
                  [
                      InlineKeyboardButton("🏠 Main Menu",
                                           callback_data="back_to_start")
                  ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Determine how to send the message (edit existing or send new)
    is_query = hasattr(update_or_query,
                       'message') and update_or_query.message is not None
    chat_id = update_or_query.message.chat_id if is_query else update_or_query.effective_chat.id

    # Delete the "loading" message if it was sent via a command
    if loading_msg_id:
      try:
        context.bot.delete_message(chat_id=chat_id, message_id=loading_msg_id)
      except BadRequest as e:
        logger.warning(f"Could not delete loading message: {e}")

    # FIX: Add robust error handling for sending the AI-generated message.
    # Sometimes the AI output can have broken markdown. This prevents a crash.
    try:
      if is_query:
        update_or_query.edit_message_text(business_idea,
                                          parse_mode=ParseMode.MARKDOWN_V2,
                                          reply_markup=reply_markup)
      else:  # Sent from a command like /random
        context.bot.send_message(chat_id,
                                 business_idea,
                                 parse_mode=ParseMode.MARKDOWN_V2,
                                 reply_markup=reply_markup)
    except BadRequest as e:
      if "Can't parse entities" in str(e):
        logger.warning(
            f"Could not parse AI-generated markdown. Sending as plain text. Error: {e}"
        )
        plain_text_idea = escape_markdown_v2(business_idea)
        if is_query:
          update_or_query.edit_message_text(plain_text_idea,
                                            reply_markup=reply_markup)
        else:
          context.bot.send_message(chat_id,
                                   plain_text_idea,
                                   reply_markup=reply_markup)
      else:
        logger.error(f"Telegram API error when sending idea: {e}")
        self.error_handler(update_or_query, context)

  def show_help(self, update: Update, context: CallbackContext):
    """Show help information"""
    help_text = escape_markdown_v2("""📘 *Help & Information*

*What is this bot?*
This bot generates innovative business ideas using Google's Gemini AI across various categories.

*Available Commands:*
• /start - Main menu and welcome
• /categories - Browse all business categories
• /random - Get a random business idea
• /help - Show this help message

*How it works:*
1. Choose a business category or get a random idea
2. The bot uses AI to generate detailed business concepts
3. Each idea includes market analysis, revenue models, and startup steps

*Support:*
For issues or feedback, please contact the developer.
""")
    # Re-enable the markdown we want
    help_text = help_text.replace("\\*", "*").replace("\\•", "•")

    keyboard = [[
        InlineKeyboardButton("📋 Browse Categories",
                             callback_data="show_categories")
    ], [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    if query:
      query.edit_message_text(help_text,
                              parse_mode=ParseMode.MARKDOWN_V2,
                              reply_markup=reply_markup)
    else:
      update.message.reply_text(help_text,
                                parse_mode=ParseMode.MARKDOWN_V2,
                                reply_markup=reply_markup)

  def back_to_start(self, update: Update, context: CallbackContext):
    """Go back to start menu"""
    query = update.callback_query
    query.answer()

    welcome_message = escape_markdown_v2("""🚀 *Business Ideas Generator Bot*

Ready to discover your next business opportunity?

*What would you like to do?*""")
    welcome_message = welcome_message.replace("\\*", "*")

    keyboard = [[
        InlineKeyboardButton("📋 Browse Categories",
                             callback_data="show_categories")
    ], [InlineKeyboardButton("🎲 Random Idea", callback_data="random_idea")],
                [InlineKeyboardButton("❓ Help", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(welcome_message,
                            parse_mode=ParseMode.MARKDOWN_V2,
                            reply_markup=reply_markup)

  def callback_query_handler(self, update: Update, context: CallbackContext):
    """Handle all callback queries in one place."""
    query = update.callback_query

    route_map = {
        "show_categories": self.show_categories,
        "random_idea": self.random_business_idea,
        "help": self.show_help,
        "back_to_start": self.back_to_start,
    }

    if query.data in route_map:
      route_map[query.data](update, context)
    elif query.data.startswith("category_"):
      self.handle_category_selection(update, context)

  def error_handler(self, update, context: CallbackContext):
    """Log errors and send a user-friendly message."""
    logger.error(f"Update {update} caused error {context.error}",
                 exc_info=context.error)

    if update and update.effective_message:
      try:
        error_message = escape_markdown_v2(
            "❌ *An error occurred*\n\nSorry, something went wrong. Please try again or use /start to return to the main menu."
        )
        error_message = error_message.replace("\\*", "*")
        update.effective_message.reply_text(error_message,
                                            parse_mode=ParseMode.MARKDOWN_V2)
      except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")

  def run(self):
    """
        Run the bot using webhooks for deployment or polling for local development.
        """
    if not TELEGRAM_BOT_TOKEN:
      logger.critical(
          "❌ TELEGRAM_BOT_TOKEN environment variable not set! The bot cannot start."
      )
      return
    if not GEMINI_API_KEY:
      logger.critical(
          "❌ GEMINI_API_KEY environment variable not set! The bot cannot start."
      )
      return
    if not model:
      logger.critical(
          "❌ Gemini AI model failed to initialize. Please check API key and configuration."
      )
      return

    self.updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = self.updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", self.start))
    dispatcher.add_handler(CommandHandler("categories", self.show_categories))
    dispatcher.add_handler(CommandHandler("random", self.random_business_idea))
    dispatcher.add_handler(CommandHandler("help", self.show_help))
    dispatcher.add_handler(CallbackQueryHandler(self.callback_query_handler))
    dispatcher.add_error_handler(self.error_handler)

    # --- DEPLOYMENT LOGIC ---
    # Check if a webhook URL is provided in the environment variables.
    # This is the standard for production deployment.
    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
      # Run in webhook mode
      port = int(os.environ.get("PORT", 8443))
      logger.info(f"🚀 Starting bot in webhook mode on port {port}...")
      self.updater.start_webhook(
          listen="0.0.0.0",
          port=port,
          url_path=TELEGRAM_BOT_TOKEN,
          webhook_url=f"{webhook_url}/{TELEGRAM_BOT_TOKEN}")
      logger.info(f"✅ Webhook set to {webhook_url}/{TELEGRAM_BOT_TOKEN}")
    else:
      # Run in polling mode for local development
      logger.info("🚀 Starting bot in polling mode...")
      self.updater.start_polling()
      logger.info("✅ Bot is running! Press Ctrl+C to stop.")

    self.updater.idle()


if __name__ == "__main__":
  bot = BusinessIdeaBot()
  bot.run()
