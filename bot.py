"""
GroupGuard Bot — Telegram Group Management Bot
Handles welcome messages, rules, anti-spam, and moderation.
Author: Manuel | GitHub: Manuel20452
"""

import logging
import time
import json
import os
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)

# --- Configuration ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "welcome_message": "👋 Welcome to the group, {name}!\nPlease read the /rules before posting.",
    "rules": [
        "1. Be respectful to all members",
        "2. No spam or self-promotion",
        "3. No NSFW content",
        "4. Stay on topic",
        "5. English and Spanish only",
    ],
    "antispam": {
        "enabled": True,
        "max_messages": 5,
        "time_window": 10,
        "mute_duration": 300,
        "max_links": 2,
        "block_forwards": False,
    },
    "goodbye_enabled": True,
    "goodbye_message": "👋 {name} has left the group.",
    "auto_delete_join": True,
    "warn_limit": 3,
}


class GroupGuardBot:
    """Telegram bot for group management, moderation and anti-spam."""

    def __init__(self, token):
        self.token = token
        self.config = self._load_config()
        self.message_tracker = {}  # {user_id: [timestamp, ...]}
        self.warnings = {}         # {user_id: count}
        self.app = Application.builder().token(token).build()
        self._register_handlers()

    def _load_config(self):
        """Load bot configuration from file."""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(saved)
                return config
        return DEFAULT_CONFIG.copy()

    def _save_config(self):
        """Save current configuration to file."""
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def _register_handlers(self):
        """Register all command and message handlers."""
        # Commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("rules", self.cmd_rules))
        self.app.add_handler(CommandHandler("setwelcome", self.cmd_set_welcome))
        self.app.add_handler(CommandHandler("setrules", self.cmd_set_rules))
        self.app.add_handler(CommandHandler("warn", self.cmd_warn))
        self.app.add_handler(CommandHandler("mute", self.cmd_mute))
        self.app.add_handler(CommandHandler("unmute", self.cmd_unmute))
        self.app.add_handler(CommandHandler("kick", self.cmd_kick))
        self.app.add_handler(CommandHandler("ban", self.cmd_ban))
        self.app.add_handler(CommandHandler("unban", self.cmd_unban))
        self.app.add_handler(CommandHandler("antispam", self.cmd_antispam))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("config", self.cmd_config))

        # New members
        self.app.add_handler(
            ChatMemberHandler(self.on_member_join, ChatMemberHandler.CHAT_MEMBER)
        )

        # Anti-spam: monitor all text messages
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message)
        )

        # Callback queries (inline buttons)
        self.app.add_handler(CallbackQueryHandler(self.on_callback))

    # --- Helper Methods ---

    async def _is_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check if the user is a group admin or creator."""
        user = update.effective_user
        chat = update.effective_chat
        member = await chat.get_member(user.id)
        return member.status in ("administrator", "creator")

    def _check_spam(self, user_id):
        """
        Check if a user is spamming.
        Returns True if spam detected.
        """
        if not self.config["antispam"]["enabled"]:
            return False

        now = time.time()
        window = self.config["antispam"]["time_window"]
        max_msgs = self.config["antispam"]["max_messages"]

        if user_id not in self.message_tracker:
            self.message_tracker[user_id] = []

        # Clean old timestamps
        self.message_tracker[user_id] = [
            t for t in self.message_tracker[user_id] if now - t < window
        ]

        self.message_tracker[user_id].append(now)

        return len(self.message_tracker[user_id]) > max_msgs

    def _count_links(self, text):
        """Count number of URLs in a message."""
        import re
        url_pattern = r'https?://\S+|www\.\S+'
        return len(re.findall(url_pattern, text))

    # --- Command Handlers ---

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "🛡️ **GroupGuard Bot**\n\n"
            "I help manage Telegram groups with:\n"
            "• Welcome messages for new members\n"
            "• Group rules display\n"
            "• Anti-spam protection\n"
            "• Moderation tools (warn, mute, kick, ban)\n\n"
            "Add me to a group and make me admin to get started!\n"
            "Use /help to see all commands.",
            parse_mode="Markdown",
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "🛡️ **GroupGuard Commands**\n\n"
            "📋 **General:**\n"
            "/rules — Show group rules\n"
            "/stats — Show group stats\n"
            "/config — Show current config\n\n"
            "⚙️ **Admin Only:**\n"
            "/setwelcome `<text>` — Set welcome message\n"
            "/setrules `<rules>` — Set group rules\n"
            "/antispam `on/off` — Toggle anti-spam\n\n"
            "🔨 **Moderation (reply to a message):**\n"
            "/warn — Warn a user (3 warns = mute)\n"
            "/mute `[minutes]` — Mute a user (default: 5 min)\n"
            "/unmute — Unmute a user\n"
            "/kick — Kick a user\n"
            "/ban — Ban a user permanently\n"
            "/unban — Unban a user\n\n"
            "💡 Use `{name}` in welcome/goodbye messages\n"
            "for the user's name."
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display group rules."""
        rules = self.config["rules"]
        rules_text = "📜 **Group Rules**\n\n" + "\n".join(rules)
        await update.message.reply_text(rules_text, parse_mode="Markdown")

    async def cmd_set_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set custom welcome message. Admin only."""
        if not await self._is_admin(update, context):
            await update.message.reply_text("⛔ Admin only command.")
            return

        text = " ".join(context.args) if context.args else ""
        if not text:
            await update.message.reply_text(
                "Usage: `/setwelcome Your welcome message here`\n"
                "Use `{name}` for the member's name.",
                parse_mode="Markdown",
            )
            return

        self.config["welcome_message"] = text
        self._save_config()
        await update.message.reply_text(f"✅ Welcome message updated:\n\n{text}")

    async def cmd_set_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set group rules. Admin only."""
        if not await self._is_admin(update, context):
            await update.message.reply_text("⛔ Admin only command.")
            return

        text = " ".join(context.args) if context.args else ""
        if not text:
            await update.message.reply_text(
                "Usage: `/setrules Rule 1 | Rule 2 | Rule 3`\n"
                "Separate rules with `|`",
                parse_mode="Markdown",
            )
            return

        self.config["rules"] = [r.strip() for r in text.split("|")]
        self._save_config()
        await update.message.reply_text("✅ Rules updated! Use /rules to see them.")

    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Warn a user. Reply to their message. Admin only."""
        if not await self._is_admin(update, context):
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ Reply to a message to warn the user.")
            return

        target = update.message.reply_to_message.from_user
        user_id = target.id

        if user_id not in self.warnings:
            self.warnings[user_id] = 0
        self.warnings[user_id] += 1

        count = self.warnings[user_id]
        limit = self.config["warn_limit"]

        if count >= limit:
            # Auto-mute after reaching warn limit
            await update.effective_chat.restrict_member(
                user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(hours=1),
            )
            self.warnings[user_id] = 0
            await update.message.reply_text(
                f"🔇 **{target.first_name}** has been muted for 1 hour "
                f"after reaching {limit} warnings.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"⚠️ **{target.first_name}** has been warned. "
                f"({count}/{limit})\n"
                f"{'⚠️' * count}{'◽' * (limit - count)}",
                parse_mode="Markdown",
            )

    async def cmd_mute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mute a user. Reply to their message. Admin only."""
        if not await self._is_admin(update, context):
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ Reply to a message to mute the user.")
            return

        target = update.message.reply_to_message.from_user
        minutes = int(context.args[0]) if context.args else 5

        await update.effective_chat.restrict_member(
            target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(minutes=minutes),
        )

        await update.message.reply_text(
            f"🔇 **{target.first_name}** has been muted for {minutes} minutes.",
            parse_mode="Markdown",
        )

    async def cmd_unmute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Unmute a user. Reply to their message. Admin only."""
        if not await self._is_admin(update, context):
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ Reply to a message to unmute the user.")
            return

        target = update.message.reply_to_message.from_user

        await update.effective_chat.restrict_member(
            target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )

        await update.message.reply_text(
            f"🔊 **{target.first_name}** has been unmuted.",
            parse_mode="Markdown",
        )

    async def cmd_kick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Kick a user from the group. Admin only."""
        if not await self._is_admin(update, context):
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ Reply to a message to kick the user.")
            return

        target = update.message.reply_to_message.from_user

        await update.effective_chat.ban_member(target.id)
        await update.effective_chat.unban_member(target.id)  # Unban so they can rejoin

        await update.message.reply_text(
            f"👢 **{target.first_name}** has been kicked from the group.",
            parse_mode="Markdown",
        )

    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Permanently ban a user. Admin only."""
        if not await self._is_admin(update, context):
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ Reply to a message to ban the user.")
            return

        target = update.message.reply_to_message.from_user

        await update.effective_chat.ban_member(target.id)

        await update.message.reply_text(
            f"🚫 **{target.first_name}** has been permanently banned.",
            parse_mode="Markdown",
        )

    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Unban a user. Admin only."""
        if not await self._is_admin(update, context):
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ Reply to a message to unban the user.")
            return

        target = update.message.reply_to_message.from_user
        await update.effective_chat.unban_member(target.id)

        await update.message.reply_text(
            f"✅ **{target.first_name}** has been unbanned.",
            parse_mode="Markdown",
        )

    async def cmd_antispam(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle anti-spam. Admin only."""
        if not await self._is_admin(update, context):
            return

        if not context.args:
            status = "ON ✅" if self.config["antispam"]["enabled"] else "OFF ❌"
            await update.message.reply_text(
                f"🛡️ Anti-spam is currently: **{status}**\n"
                f"Usage: `/antispam on` or `/antispam off`",
                parse_mode="Markdown",
            )
            return

        setting = context.args[0].lower()
        if setting in ("on", "true", "1"):
            self.config["antispam"]["enabled"] = True
            self._save_config()
            await update.message.reply_text("✅ Anti-spam enabled.")
        elif setting in ("off", "false", "0"):
            self.config["antispam"]["enabled"] = False
            self._save_config()
            await update.message.reply_text("❌ Anti-spam disabled.")

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show group statistics."""
        chat = update.effective_chat
        member_count = await chat.get_member_count()
        warnings_total = sum(self.warnings.values())
        antispam = "ON ✅" if self.config["antispam"]["enabled"] else "OFF ❌"

        await update.message.reply_text(
            f"📊 **Group Stats**\n\n"
            f"👥 Members: {member_count}\n"
            f"⚠️ Active warnings: {warnings_total}\n"
            f"🛡️ Anti-spam: {antispam}\n"
            f"📜 Rules: {len(self.config['rules'])} rules set",
            parse_mode="Markdown",
        )

    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current bot configuration. Admin only."""
        if not await self._is_admin(update, context):
            return

        spam = self.config["antispam"]
        await update.message.reply_text(
            f"⚙️ **Current Configuration**\n\n"
            f"Welcome: `{self.config['welcome_message'][:50]}...`\n"
            f"Goodbye: {'ON' if self.config['goodbye_enabled'] else 'OFF'}\n"
            f"Anti-spam: {'ON' if spam['enabled'] else 'OFF'}\n"
            f"  Max msgs: {spam['max_messages']} per {spam['time_window']}s\n"
            f"  Mute duration: {spam['mute_duration']}s\n"
            f"  Max links: {spam['max_links']}\n"
            f"Warn limit: {self.config['warn_limit']}",
            parse_mode="Markdown",
        )

    # --- Event Handlers ---

    async def on_member_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle new member joining the group."""
        result = update.chat_member
        if result.new_chat_member.status == "member" and result.old_chat_member.status in (
            "left", "kicked"
        ):
            user = result.new_chat_member.user
            name = user.first_name

            welcome = self.config["welcome_message"].replace("{name}", name)

            keyboard = [[InlineKeyboardButton("📜 Read Rules", callback_data="show_rules")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Monitor messages for spam detection."""
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        message = update.message

        # Skip admins
        member = await update.effective_chat.get_member(user.id)
        if member.status in ("administrator", "creator"):
            return

        # Check link spam
        if message.text:
            max_links = self.config["antispam"]["max_links"]
            if self._count_links(message.text) > max_links:
                await message.delete()
                await update.effective_chat.send_message(
                    f"🚫 **{user.first_name}**, too many links! Max {max_links} per message.",
                    parse_mode="Markdown",
                )
                return

        # Check message flood
        if self._check_spam(user.id):
            mute_seconds = self.config["antispam"]["mute_duration"]

            await update.effective_chat.restrict_member(
                user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(seconds=mute_seconds),
            )

            await message.delete()
            await update.effective_chat.send_message(
                f"🔇 **{user.first_name}** has been muted for "
                f"{mute_seconds // 60} minutes (spam detected).",
                parse_mode="Markdown",
            )

    async def on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button presses."""
        query = update.callback_query
        await query.answer()

        if query.data == "show_rules":
            rules = self.config["rules"]
            rules_text = "📜 **Group Rules**\n\n" + "\n".join(rules)
            await query.message.reply_text(rules_text, parse_mode="Markdown")

    # --- Run ---

    def run(self):
        """Start the bot."""
        print("🛡️ GroupGuard Bot is running...")
        print("Press Ctrl+C to stop.\n")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

    if not token:
        print("=" * 50)
        print(" GroupGuard Bot — Setup")
        print("=" * 50)
        print("\n1. Open Telegram and search for @BotFather")
        print("2. Send /newbot and follow the instructions")
        print("3. Copy the token BotFather gives you")
        token = input("\n🔑 Paste your bot token here: ").strip()

        if not token:
            print("[!] No token provided. Exiting.")
            return

    bot = GroupGuardBot(token)
    bot.run()


if __name__ == "__main__":
    main()
