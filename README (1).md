# 🛡️ GroupGuard Bot — Telegram Group Management

A powerful Telegram bot for group moderation with welcome messages, customizable rules, anti-spam protection, and full admin tools.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Telegram](https://img.shields.io/badge/Telegram-Bot_API_20+-26A5E4?logo=telegram&logoColor=white)

## Features

- **Welcome System** — Auto-greet new members with custom messages + inline "Read Rules" button
- **Rules Management** — Set and display group rules with `/rules`
- **Anti-Spam** — Detects message flooding and link spam, auto-mutes offenders
- **Moderation Tools** — Warn, mute, unmute, kick, ban, unban users
- **Warning System** — 3 warnings = automatic mute (configurable)
- **Stats Dashboard** — View group member count, warnings, and config status
- **Persistent Config** — Settings saved to JSON, survive restarts

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Manuel20452/groupguard-bot.git
cd groupguard-bot

# Install dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
```

On first run, the bot asks for your Telegram Bot Token. Get one from [@BotFather](https://t.me/BotFather).

You can also set it as an environment variable:
```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
python bot.py
```

## Setup in Your Group

1. Add the bot to your Telegram group
2. Make it **admin** with these permissions:
   - Delete messages
   - Ban users
   - Restrict members
3. Done! The bot starts working immediately

## Commands

| Command | Description | Who |
|---------|-------------|-----|
| `/start` | Bot info | Everyone |
| `/help` | Show all commands | Everyone |
| `/rules` | Display group rules | Everyone |
| `/stats` | Group statistics | Everyone |
| `/setwelcome <text>` | Set welcome message | Admin |
| `/setrules <rules>` | Set rules (separate with `\|`) | Admin |
| `/antispam on/off` | Toggle anti-spam | Admin |
| `/config` | Show current settings | Admin |
| `/warn` | Warn a user (reply) | Admin |
| `/mute [minutes]` | Mute user (reply, default 5min) | Admin |
| `/unmute` | Unmute user (reply) | Admin |
| `/kick` | Kick user (reply) | Admin |
| `/ban` | Permanent ban (reply) | Admin |
| `/unban` | Unban user (reply) | Admin |

## Anti-Spam Settings

Default configuration:
- **Max messages:** 5 messages per 10 seconds triggers mute
- **Mute duration:** 5 minutes
- **Max links:** 2 per message
- **Warning limit:** 3 warns before auto-mute

All settings are customizable via `config.json`.

## Example Usage

### Set Custom Welcome
```
/setwelcome 🎉 Welcome {name}! Please read the rules and enjoy your stay!
```

### Set Custom Rules
```
/setrules No spam | Be respectful | English only | No NSFW
```

### Moderate Users
Reply to a message and use:
```
/warn    → Gives a warning (3 = auto-mute)
/mute 10 → Mutes for 10 minutes
/kick    → Removes from group
/ban     → Permanent ban
```

## Project Structure

```
groupguard-bot/
├── bot.py              # Main bot code
├── config.json         # Auto-generated settings (after first run)
├── requirements.txt    # Python dependencies
└── README.md
```

## Tech Stack

`Python` `python-telegram-bot` `Telegram Bot API` `JSON`

## License

MIT — free to use and modify.

## Author

**Manuel** — Python Developer & Automation Specialist
- GitHub: [@Manuel20452](https://github.com/Manuel20452)
