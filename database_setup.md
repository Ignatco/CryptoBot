# Database Setup Guide

## ✅ **Current Setup: SQLite (No Installation Required)**

The bot now uses SQLite database which requires **zero setup**:

- **Database file**: `crypto_bot.db` (created automatically)
- **No installation needed**: SQLite is built into Python
- **Portable**: Database file can be copied/moved easily
- **Perfect for local development**

## Running the Bot

### For Replit (Current)
```bash
python simple_bot.py
```

### For Local Machine
1. **Install Python dependencies:**
   ```bash
   pip install aiohttp pandas python-telegram-bot requests matplotlib numpy pillow aiosqlite
   ```

2. **Create .env file:**
   ```env
   TELEGRAM_TOKEN=your_bot_token_here
   CHAT_ID=your_chat_id_here
   TRADINGVIEW_USERNAME=optional
   TRADINGVIEW_PASSWORD=optional
   ```

3. **Run the bot:**
   ```bash
   python simple_bot.py
   ```

## Database Features

- **Automatic creation**: All tables created on first run
- **User profiles**: Complete user tracking and engagement metrics
- **Weekly activity**: Monday-Sunday activity cycles
- **Signal history**: All trading signals logged
- **Admin commands**: `/userprofiles` and `/userstats` for insights

## Database File Location

- **Replit**: `/home/runner/workspace/crypto_bot.db`
- **Local**: `./crypto_bot.db` (same folder as bot)

## No More Setup Required!

The SQLite conversion means:
- ✅ No PostgreSQL installation
- ✅ No Docker containers
- ✅ No connection strings
- ✅ No user management
- ✅ Works everywhere Python works