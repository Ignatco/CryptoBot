# Crypto EMA20 Breakout Bot

## Overview

This is a comprehensive multilingual cryptocurrency trading signal bot that monitors 50 USDT trading pairs on Binance for EMA20 breakouts with volume confirmation. The bot provides detailed trading signals with entry points, take profit levels, stop loss calculations, and risk management guidance. It features interactive Telegram commands with 5-language support (English, Spanish, French, German, Russian), real-time market analysis, and comprehensive coin status information for informed trading decisions.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (January 2025)

### CoinPaprika Primary API & Rate Limit Optimization (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **COINPAPRIKA PRIMARY**: Switched to CoinPaprika as primary API due to better rate limits, CoinGecko as fallback only
  - **OPTIMIZED RATE LIMITING**: Reduced delays - 1.5s for CoinPaprika, 2.0s for CoinGecko fallback
  - **SMART FALLBACK SYSTEM**: Primary CoinPaprika attempt first, then CoinGecko if needed, then synthetic as last resort
  - **AUTOMATIC FREE REGISTRATION**: All users automatically added to free tier when using any command until 100 users reached
  - **TRUE FREEMIUM MODEL**: First 100 users get PERMANENT premium access (grandfathered forever), then payment required
  - **REDUCED TO 20 PAIRS**: Updated to monitor user-specified 20 cryptocurrency pairs (LDO, EIGEN, THETA, DOGE, SOL, LTC, BTC, ETH, XRP, WLD, BNB, SUI, SEI, SAND, ARB, OP, XLM, ADA, UNI, DOT, ATOM)
  - **ELIMINATED HASH DISTRIBUTION**: Removed random API selection in favor of priority-based approach
  - **API OPTIMIZED MONITORING**: Adjusted to 15-minute cycles to prevent CoinGecko rate limit errors while maintaining effective signal detection
  - **SIGNAL HISTORY FEATURE**: Added "Signals" button showing last 5 trading signals with timestamps and entry points
  - **2-DAY COOLDOWN SYSTEM**: Implemented cooldown tracking to prevent duplicate signals - each coin gets 2-day cooldown after signal sent
  - **PRECISE SIGNAL CRITERIA**: Updated to advanced criteria - EMA20 above + rising slope + resistance breakout + volume surge (1.5-2x) + strong momentum candle (70% body)
  - **CLEAN SIGNAL FORMAT**: Redesigned signal messages to be concise and readable without screenshots
  - **ESSENTIAL INFO ONLY**: Signals now show only entry price, stop loss, take profit levels, and confirmation
  - **LONG POSITION FOCUS**: Optimized signal format specifically for long position entries
  - **ADMIN PREMIUM ACCESS**: Admin gets automatic premium access for testing and monitoring
  - **FIXED PREMIUM CHECKS**: Updated all command handlers to automatically register users before checking premium status
  - **DYNAMIC USER COUNT**: Error messages now show current user count (X/100) to inform users about free tier availability
- **Impact**: Significantly reduced CoinGecko rate limiting issues by prioritizing CoinPaprika API with better limits, providing faster and more reliable data fetching

## Recent Changes (January 2025)

### Payment Address Formatting Fixed & Persistent Menu Added (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **PAYMENT ADDRESS FORMATTING RESOLVED**: Fixed cryptocurrency address display issues by switching to clean plain text format
  - **CLEAN ADDRESS DISPLAY**: Addresses now display as simple text without formatting characters for easy copying
  - **PERSISTENT TELEGRAM MENU**: Added permanent command menu that appears at bottom of Telegram chat
  - **MENU COMMANDS SETUP**: Implemented /start, /menu, /status, /help commands in persistent Telegram interface
  - **IMPROVED USER EXPERIENCE**: Users can now access main functions without typing commands manually
  - **SEAMLESS PAYMENT FLOW**: Payment addresses display cleanly and are easily copyable in all languages
  - **BOT COMMANDS API**: Integrated Telegram's setMyCommands API for persistent menu functionality
  - **AUTOMATIC SETUP**: Menu commands are set up automatically when bot starts
- **Impact**: Resolved address copying issues and added convenient persistent menu for better user accessibility

### Redesigned Payment Flow with Individual Cryptocurrency Address Messages (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **STREAMLINED PAYMENT UX**: Completely redesigned payment flow for optimal user experience with individual payment method selection
  - **INDIVIDUAL CRYPTO BUTTONS**: Payment method selection now shows separate buttons for Bitcoin (BTC), Ethereum (ETH), USDT (TRC20), and Bank Transfer
  - **SIMPLIFIED USER JOURNEY**: Users select plan → choose payment method → get specific address + instructions (no information overload)
  - **ENHANCED CALLBACK HANDLING**: Updated callback system to handle new button format (pay_plan_method) for precise payment routing
  - **SEPARATE INSTRUCTION MESSAGES**: Payment instructions and support contact information sent as separate messages with back-to-menu navigation
  - **MULTILINGUAL COVERAGE**: All payment methods and instructions fully localized across 5 supported languages
  - **BANK TRANSFER INTEGRATION**: Dedicated bank transfer option with clear contact instructions for traditional payment preferences
  - **CONSISTENT NAVIGATION**: Back to menu buttons on all payment screens for seamless user experience
- **Impact**: Dramatically improved payment user experience by eliminating confusion and providing clean, focused payment information for each cryptocurrency option

### Added Payment Notice to Main Menu for All Languages (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **PAYMENT TRANSPARENCY**: Added clear payment notice to main menu across all 5 supported languages
  - **USER COUNT DISPLAY**: Shows current user count vs. 100-user limit (e.g., "Current users: 15/100")
  - **MULTILINGUAL COVERAGE**: Localized payment notice text for English, Spanish, French, German, and Russian
  - **CLEAR MESSAGING**: Users now see upfront that bot requires payment after 100 users join
  - **REAL-TIME COUNTER**: Dynamic user count updates automatically in the main menu
  - **IMPROVED TRANSPARENCY**: Eliminates surprises about payment requirements for new users
  - Notice text examples: "Bot will require payment after 100 users" (EN), "El bot requerirá pago después de 100 usuarios" (ES)
- **Impact**: Enhanced user transparency and clear communication about freemium model, helping users understand payment requirements upfront

### TradingView API Integration for Real-Time Market Data (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **MAJOR DATA SOURCE UPGRADE**: Integrated TradingView API for professional-grade market data access
  - **REAL-TIME DATA FEEDS**: Enhanced bot with live cryptocurrency price feeds and technical indicators
  - **PROFESSIONAL ANALYTICS**: Added multi-timeframe analysis (1H, 4H, 1D) with institutional-grade data
  - **ENHANCED SIGNAL ACCURACY**: Improved EMA20 breakout detection with real market data
  - **TRADINGVIEW MODULE**: Created dedicated `tradingview_integration.py` for API management
  - **FALLBACK SYSTEM**: Maintains functionality with synthetic data when API is unavailable
  - **CREDENTIAL MANAGEMENT**: Secure handling of TradingView username/password via environment variables
  - **DATA CACHING**: Implemented 5-minute cache system to optimize API usage and performance
  - **MARKET COVERAGE**: Enhanced monitoring of 50+ cryptocurrency pairs with real-time data
  - **PROFESSIONAL CHARTS**: Integration supports advanced chart generation with current market prices
- **Impact**: Bot now provides institutional-quality market analysis with real-time data from TradingView, significantly improving signal accuracy and reliability

### Added Back to Menu Buttons for Enhanced Navigation (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **NAVIGATION ENHANCEMENT**: Added "Back to Menu" buttons to all message responses throughout the bot
  - **MULTILINGUAL SUPPORT**: Back button text localized for all 5 supported languages
  - **COMPLETE COVERAGE**: Applied to status, coin list, help, subscription, payment, support, and admin messages
  - **CONSISTENT UX**: Users can now return to main menu from any screen with a single button tap
  - **ACCESSIBILITY IMPROVEMENT**: Eliminates need to type /menu command or restart conversation
  - **HELPER FUNCTION**: Created `create_back_to_menu_keyboard()` for consistent button implementation
  - Button texts: "🔙 Back to Menu" (EN), "🔙 Al Menú" (ES), "🔙 Au Menu" (FR), "🔙 Zum Menü" (DE), "🔙 В Меню" (RU)
- **Impact**: Significantly improved user experience by providing easy navigation back to main menu from any bot screen

### Enhanced Payment Address Formatting for Easy Copying (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **PAYMENT UX IMPROVEMENT**: Updated all payment messages with monospace formatting for easy address copying
  - **PROFESSIONAL FORMATTING**: Cryptocurrency addresses now use `backticks` for monospace display in Telegram
  - **VISUAL ENHANCEMENT**: Added bold headers for each cryptocurrency type with colored emojis
  - **CONSISTENT EXPERIENCE**: Applied formatting across all 5 languages and both payment sections
  - **CLEAN LAYOUT**: Separated addresses on individual lines with proper spacing for better readability
  - **MULTILINGUAL COVERAGE**: Updated both subscription selection and payment method handler functions
  - Format: 🟡 **Bitcoin (BTC)** followed by `address in monospace` for easy copying
- **Impact**: Users can now easily copy cryptocurrency addresses with a single tap, significantly improving payment experience across all languages

### Advanced Signal System with Professional Charts & Accuracy Scoring (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **MAJOR SIGNAL ENHANCEMENT**: Implemented advanced signal generation with professional chart screenshots and accuracy percentages
  - **PROFESSIONAL CHART GENERATION**: Added matplotlib-based dark-theme trading charts with technical indicators
  - **SIGNAL ACCURACY SYSTEM**: Dynamic accuracy calculation (60-100%) based on multiple technical factors
  - **ENHANCED VISUAL SIGNALS**: Multi-factor signal strength display with 5-level scoring system
  - **VOLUME ANALYSIS UPGRADE**: Advanced volume surge detection and institutional activity monitoring
  - **CHART FEATURES**: Price action with EMA20/SMA200, volume bars, RSI indicator, support/resistance levels
  - **POSITION SETUP DETAILS**: Comprehensive trading plans with entry zones, stop loss, take profit levels
  - **MARKET SENTIMENT**: Added Fear & Greed Index, social sentiment, whale activity tracking
  - **RISK MANAGEMENT**: Professional position sizing, risk/reward ratios, scaling strategies
  - **TECHNICAL INDICATORS**: RSI momentum, volume confirmation, trend consistency evaluation
  - **VISUAL STRENGTH LEVELS**: 🟢🟢🟢🟢🟢 EXTREMELY STRONG (90%+) to 🟢🟢⚪⚪⚪ MODERATE (60%+)
  - **CHART INTEGRATION**: Real-time screenshot generation with signal overlays and technical analysis
- **Impact**: Premium-quality trading signals with professional visual analysis, accurate scoring, and comprehensive position guidance for enhanced trading decisions

### Complete Language Localization Audit & Full Message Coverage (January 24, 2025)
- **Date**: January 24, 2025  
- **Changes Made**:
  - **COMPREHENSIVE LOCALIZATION COMPLETION**: Completed full audit and enhancement of all 5 supported languages
  - **MISSING MESSAGE KEYS ADDED**: Added help_message_free, help_message_premium, and command_menu to all languages
  - **WELCOME MESSAGE ENHANCEMENT**: Added clear bot explanation at start of all welcome messages across all languages
  - Enhanced free_tier_welcome and free_tier_full messages in English, Spanish, French, German, and Russian
  - Added missing comprehensive welcome messages for French, German, and Russian language support
  - Updated language selection interfaces to remove references to removed languages (Chinese, Arabic, Japanese)
  - Clear bot description in all languages: "This bot automatically monitors 50 major cryptocurrencies and sends you instant trading signals when it detects profitable EMA20 breakout opportunities. You get entry points, take profit levels, stop loss calculations, and risk management guidance - all delivered straight to your Telegram."
  - Updated all pair counts from 22 to 50 pairs throughout all language files
  - Updated all language counts from 8 to 5 languages in help messages
  - Added comprehensive help guides with technical analysis explanations in all 5 languages
  - Verified complete message coverage: 16 message keys per language across all supported languages
- **Impact**: Complete multilingual user experience with 100% message coverage, consistent bot explanations, comprehensive feature descriptions, and professional help guides across all 5 supported languages

### Reduced Language Support from 8 to 5 Languages (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **LANGUAGE SUPPORT OPTIMIZATION**: Reduced multilingual support from 8 to 5 languages
  - Removed Chinese (中文), Arabic (العربية), and Japanese (日本語) language support completely
  - Deleted entire language dictionaries for zh, ar, ja from bot codebase
  - Updated language selection interface to show only: English, Spanish, French, German, Russian
  - Cleaned up all language references and updated count from "8 languages" to "5 languages"
  - Updated help messages across all remaining languages to reflect new language count
  - Language selection buttons now display: 🇺🇸 English | 🇪🇸 Español | 🇫🇷 Français | 🇩🇪 Deutsch | 🇷🇺 Русский
  - Maintained full functionality for all supported features in remaining 5 languages
- **Impact**: Streamlined language support focuses on core user base while maintaining full multilingual functionality

### Expanded to Top 50 Cryptocurrency Pairs by Market Cap (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **MAJOR EXPANSION**: Increased monitoring from 22 to 50 USDT trading pairs
  - Updated pairs list to include top 50 cryptocurrencies by market capitalization
  - Added major coins: SHIB, PEPE, TON, BCH, NEAR, APT, HBAR, ETC, RNDR, INJ, STX, FLOW, ARB, OP, and others
  - Updated all multilingual messages across 8 languages to reflect 50 pairs
  - Enhanced coin list displays with complete top 50 cryptocurrency information
  - Maintained all existing technical analysis and signal generation functionality
  - Updated help messages, status reports, and coin list displays
- **Impact**: Bot now monitors significantly more trading opportunities, covering broader market with top cryptocurrencies by market cap

### Enhanced Button Interface with Emoji + Labels (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **UI ENHANCEMENT**: Updated buttons to combine emojis with descriptive labels for optimal user experience
  - Main menu buttons: 📊 Status | 💰 Coins | 📚 Help | 🌍 Language | 🗑️ Delete | 🔄 Refresh
  - Premium buttons: 💎 Premium | 💳 I Paid | ❓ Support
  - Admin buttons: ⚙️ Admin | 🔁 Restart
  - Language selection: 🇺🇸 English | 🇪🇸 Español | 🇫🇷 Français | etc.
  - Subscription plans: 📅 Weekly | 🗓️ Monthly | 📆 Yearly
  - Delete confirmation: ✅ Yes | ❌ No
  - Payment options: 💳 Crypto | 🏦 Bank | 🔙 Back
  - Removed separate button guide text from menu for cleaner presentation
  - Enhanced accessibility and clarity while maintaining visual appeal
- **Impact**: Perfect balance of visual icons and text labels for intuitive navigation across all languages

### Converted to Fully Button-Based Interface (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **MAJOR ARCHITECTURAL CHANGE**: Converted from command-based to button-based interface
  - Replaced send_command_buttons() with comprehensive send_main_menu() function
  - Updated /start and /menu commands to show interactive main menu with user status
  - Added dynamic button layout based on user tier (free/premium/restricted)
  - Implemented menu refresh button for real-time status updates
  - Added admin panel and restart buttons for administrators
  - Updated language selection to show main menu after selection
  - Simplified bot command menu to only /start and /menu (buttons handle everything else)
  - Enhanced user experience with personalized menu text and status indicators
  - All major functions now accessible through intuitive button interface
- **Impact**: Users no longer need to type commands - everything is accessible through buttons, significantly improving user experience and reducing learning curve

### Admin User Profile System with PostgreSQL Database (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **POSTGRESQL INTEGRATION**: Added comprehensive user database with PostgreSQL for persistent user tracking
  - **USER PROFILE SYSTEM**: Implemented detailed user profiles with comprehensive activity tracking
  - **WEEKLY ACTIVITY TRACKING**: Users counted as active if they used bot within current week (Monday-Sunday)
  - **DATABASE TABLES**: Created users, user_activity, weekly_usage, and signal_history tables
  - **NEW ADMIN COMMANDS**: Added /userprofiles and /userstats for detailed user insights
  - **ENGAGEMENT METRICS**: Weekly engagement rate, activity leaders, and retention tracking
  - **COMPREHENSIVE TRACKING**: Total commands, signals received, first interaction date, last activity
  - **ACTIVITY LOGGING**: All user interactions logged with timestamps and activity types
  - **USER STATISTICS**: Total users ever, weekly active users, daily active users, free vs premium counts
  - **DATABASE PERSISTENCE**: User data persists across bot restarts with full profile history
- **Impact**: Admin now has complete visibility into user engagement patterns and detailed profile information for data-driven decisions

### Added Delete Messages Feature with Multilingual Support (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - Added "Delete Messages" button to main command menu for all users
  - Implemented confirmation dialog with Yes/No buttons before deletion
  - Added multilingual support for delete feature across all 8 languages
  - Created delete_all_user_messages() function with safety confirmation
  - Implemented perform_message_deletion() to delete last 200 bot messages
  - Added callback handlers for deletion confirmation (confirm_delete_yes/no)
  - Enhanced delete_message() function to accept chat_id parameter for user-specific deletion
  - Added appropriate success, error, and "no messages found" feedback messages
- **Impact**: Users can now clean up bot messages from their chats with multilingual confirmation dialogs

### Enhanced Signal Criteria with Precise EMA20 Breakout Logic (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - **REFINED SIGNAL CRITERIA**: Updated breakout detection to require candles break AND close above EMA20 on both timeframes
  - **PRECISE BREAKOUT LOGIC**: Enhanced check_breakout() function with three conditions: close above EMA20, previous candle below EMA20, and high above EMA20
  - **DUAL TIMEFRAME REQUIREMENT**: Both 4H and 1D candles must break and close above EMA20 with high volume (1.5x average)
  - **IMPROVED VOLUME CALCULATION**: Enhanced volume analysis using rolling 20-period average excluding current candle
  - **DEBUG MONITORING**: Added detailed logging for major pairs (BTC, ETH, XRP) to track signal detection
  - **SIGNAL MESSAGE UPDATES**: Updated test signal messages to reflect new criteria with clear breakout confirmation
  - **VOLUME THRESHOLD**: Maintained 1.5x average volume requirement for high volume confirmation
- **Impact**: More precise and reliable signal detection ensuring both timeframes show genuine EMA20 breakouts with strong volume support

### Fixed Critical Bot Configuration & Restart System (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - Fixed hardcoded admin chat ID that prevented bot from working with other users
  - Updated all message sending functions to use individual user chat IDs
  - Modified command handlers to respond to users in their own chats
  - Updated helper functions (send_language_keyboard, send_command_buttons, etc.) to accept chat_id
  - Maintained admin notifications to go to admin chat while user interactions stay in user chats
  - **CRITICAL**: Fixed /restart command that was using sys.exit(0) and crashing entire process
  - Added graceful restart system with restart_requested flag and automatic recovery loop
  - Completely refactored bot to support public multi-user operation with safe admin controls
- **Impact**: Bot now works for all users and /restart command works safely without process crashes

### Implemented Subscription Expiry Management & Admin Dashboard (January 24, 2025)
- **Date**: January 24, 2025
- **Changes Made**:
  - Added subscription expiry tracking for premium users
  - Automatic subscription expiration and removal from premium access
  - Comprehensive /admin dashboard command with all admin tools
  - Enhanced /adduser command to support custom subscription duration
  - Added automatic expiry checking in monitoring loop
  - Real-time subscription status monitoring with alerts for expiring users
  - Complete admin command reference and user statistics in dashboard
- **Impact**: Bot now properly manages subscription lifecycles and provides comprehensive admin tools

### Implemented Free Tier System (First 100 Users)
- **Date**: January 24, 2025
- **Changes Made**:
  - Implemented free tier for first 100 users
  - Added automatic user onboarding to free tier
  - After 100 users, new users must pay for premium access
  - Updated signal broadcasting to include both free and paid users
  - Added admin commands: /freestats, enhanced /listusers
  - Created multilingual messages for free tier system
- **Impact**: Bot offers free access to early adopters, transitions to paid after reaching 100 users

## System Architecture

The application follows a modular architecture with clear separation of concerns:

- **Main Application Layer**: Entry point with bot lifecycle management and signal handling
- **Telegram Integration Layer**: Handles all Telegram bot operations and user commands
- **Market Analysis Layer**: Performs technical analysis on cryptocurrency data
- **Configuration Layer**: Centralized configuration management
- **External API Layer**: Interfaces with Binance API for market data

The system is built using asyncio for concurrent operations, allowing efficient monitoring of multiple cryptocurrency pairs simultaneously.

## Key Components

### 1. BotManager (main.py)
- **Purpose**: Manages bot lifecycle and graceful shutdown
- **Key Features**: Signal handling, bot initialization, configuration validation
- **Architecture Decision**: Centralized lifecycle management for clean startup/shutdown

### 2. CryptoTelegramBot (telegram_bot.py)
- **Purpose**: Telegram bot interface and command handling
- **Key Features**: Command processing, message sending, monitoring status
- **Architecture Decision**: Separated bot logic from analysis logic for better maintainability

### 3. CryptoAnalyzer (crypto_analyzer.py)
- **Purpose**: Market data analysis and signal detection
- **Key Features**: EMA20 calculation, breakout detection, volume analysis
- **Architecture Decision**: Standalone analyzer for reusability and testing

### 4. Configuration Management (config.py)
- **Purpose**: Centralized configuration with environment variable support
- **Key Features**: API endpoints, trading parameters, timeframe settings
- **Architecture Decision**: Environment-based configuration for deployment flexibility

## Data Flow

1. **Initialization**: Bot starts and validates configuration
2. **Market Data Fetching**: Continuously fetches USDT pairs from Binance
3. **Technical Analysis**: Calculates EMA20 and detects breakouts with volume confirmation
4. **Signal Generation**: Creates trading signals when conditions are met
5. **Notification**: Sends signals to configured Telegram chat
6. **Monitoring Loop**: Repeats analysis every 4 hours

## External Dependencies

### Binance API
- **Purpose**: Real-time cryptocurrency market data
- **Endpoints Used**: 
  - `/api/v3/klines` for candlestick data
  - `/api/v3/exchangeInfo` for trading pairs
- **Rate Limiting**: Built-in request handling with error management

### Telegram Bot API
- **Purpose**: User interface and notification delivery
- **Features**: Command handling, message broadcasting
- **Authentication**: Token-based authentication

### Python Libraries
- **aiohttp**: Async HTTP client for API calls
- **pandas**: Data manipulation and analysis
- **python-telegram-bot**: Telegram bot framework

## Deployment Strategy

The application is designed for continuous deployment with the following characteristics:

### Environment Configuration
- Uses environment variables for sensitive data (tokens, chat IDs)
- Fallback defaults for development/testing
- Configurable monitoring intervals and analysis parameters

### Error Handling
- Graceful degradation on API failures
- Duplicate signal prevention
- Comprehensive logging for debugging

### Scalability Considerations
- Async operations for concurrent market monitoring
- Efficient data structures for signal caching
- Modular design allows for easy feature additions

### Monitoring and Maintenance
- Built-in status commands for health checking
- Signal handlers for graceful shutdown
- Clear separation of concerns for easier debugging

The system is optimized for reliability and continuous operation, with robust error handling and recovery mechanisms to ensure consistent signal delivery.