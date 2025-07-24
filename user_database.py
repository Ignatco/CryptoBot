import os
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json

class UserDatabase:
    def __init__(self):
        self.db_path = 'crypto_bot.db'
        self.db = None
        
    async def init_database(self):
        """Initialize SQLite database and create tables"""
        try:
            self.db = await aiosqlite.connect(self.db_path)
            await self.create_tables()
            print("✅ SQLite database initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False
    
    async def create_tables(self):
        """Create necessary database tables"""
        if not self.db:
            return
            
        # Users table with comprehensive tracking
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                selected_language TEXT DEFAULT 'en',
                user_type TEXT DEFAULT 'free',
                first_interaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
                last_activity_date TEXT DEFAULT CURRENT_TIMESTAMP,
                total_commands INTEGER DEFAULT 0,
                total_signals_received INTEGER DEFAULT 0,
                subscription_start_date TEXT,
                subscription_end_date TEXT,
                is_active INTEGER DEFAULT 1,
                weekly_activity_count INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User activity log table
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                activity_type TEXT,
                activity_data TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Weekly activity tracking
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS weekly_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                week_start_date TEXT,
                week_end_date TEXT,
                activity_count INTEGER DEFAULT 0,
                commands_used TEXT DEFAULT '[]',
                last_activity TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, week_start_date)
            )
        ''')
        
        # Signals sent tracking
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                signal_data TEXT,
                sent_to_users INTEGER DEFAULT 0,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await self.db.commit()
        print("✅ SQLite database tables created successfully")
    
    async def add_or_update_user(self, user_data: Dict[str, Any]) -> bool:
        """Add new user or update existing user with comprehensive tracking"""
        if not self.db:
            print(f"⚠️ Database not initialized, skipping user tracking for {user_data.get('id', 'unknown')}")
            return False
            
        try:
            user_id = str(user_data.get('id', ''))
            username = user_data.get('username', '')
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
            language_code = user_data.get('language_code', 'en')
            
            # Check if user exists
            cursor = await self.db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            existing_user = await cursor.fetchone()
            
            if existing_user:
                # Update existing user
                await self.db.execute('''
                    UPDATE users SET 
                        username = ?,
                        first_name = ?,
                        last_name = ?,
                        language_code = ?,
                        last_activity_date = datetime('now'),
                        total_commands = total_commands + 1,
                        updated_at = datetime('now')
                    WHERE user_id = ?
                ''', (username, first_name, last_name, language_code, user_id))
                
                # Update weekly activity
                await self.update_weekly_activity(user_id, 'command_used')
                
                await self.db.commit()
                return True
            else:
                # Insert new user
                await self.db.execute('''
                    INSERT INTO users (
                        user_id, username, first_name, last_name, 
                        language_code, user_type, weekly_activity_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, language_code, 'free', 1))
                
                # Create initial weekly activity record
                await self.update_weekly_activity(user_id, 'first_interaction')
                
                await self.db.commit()
                print(f"✅ Added new user to database: {user_id} ({first_name})")
                return True
                
        except Exception as e:
            print(f"❌ Error adding/updating user {user_data.get('id', 'unknown')}: {e}")
            return False
    
    async def update_weekly_activity(self, user_id: str, activity_type: str):
        """Update weekly activity tracking for user"""
        if not self.db:
            return
            
        try:
            # Get current week start (Monday)
            now = datetime.now()
            days_since_monday = now.weekday()
            week_start = (now - timedelta(days=days_since_monday)).date().isoformat()
            week_end = (now - timedelta(days=days_since_monday) + timedelta(days=6)).date().isoformat()
            
            # Check if weekly record exists
            cursor = await self.db.execute('''
                SELECT activity_count FROM weekly_usage 
                WHERE user_id = ? AND week_start_date = ?
            ''', (user_id, week_start))
            existing = await cursor.fetchone()
            
            if existing:
                # Update existing weekly record
                await self.db.execute('''
                    UPDATE weekly_usage SET 
                        activity_count = activity_count + 1,
                        last_activity = datetime('now')
                    WHERE user_id = ? AND week_start_date = ?
                ''', (user_id, week_start))
            else:
                # Insert new weekly record
                await self.db.execute('''
                    INSERT INTO weekly_usage (user_id, week_start_date, week_end_date, activity_count, last_activity)
                    VALUES (?, ?, ?, 1, datetime('now'))
                ''', (user_id, week_start, week_end))
            
            # Log specific activity
            await self.db.execute('''
                INSERT INTO user_activity (user_id, activity_type, activity_data)
                VALUES (?, ?, ?)
            ''', (user_id, activity_type, json.dumps({'timestamp': now.isoformat()})))
            
            await self.db.commit()
                
        except Exception as e:
            print(f"❌ Error updating weekly activity for {user_id}: {e}")
    
    async def get_all_users_with_profiles(self) -> List[Dict[str, Any]]:
        """Get all user profiles with detailed information"""
        if not self.db:
            return []
            
        try:
            # Get current week start
            now = datetime.now()
            days_since_monday = now.weekday()
            week_start = (now - timedelta(days=days_since_monday)).date().isoformat()
            
            cursor = await self.db.execute('''
                SELECT 
                    u.*,
                    COALESCE(w.activity_count, 0) as current_week_activity,
                    COALESCE(w.last_activity, u.last_activity_date) as last_week_activity,
                    (SELECT COUNT(*) FROM user_activity WHERE user_id = u.user_id) as total_activities
                FROM users u
                LEFT JOIN weekly_usage w ON u.user_id = w.user_id 
                    AND w.week_start_date = ?
                ORDER BY u.last_activity_date DESC
            ''', (week_start,))
            
            users = await cursor.fetchall()
            
            # Convert to list of dictionaries
            result = []
            for user in users:
                user_dict = {
                    'user_id': user[0],
                    'username': user[1],
                    'first_name': user[2],
                    'last_name': user[3],
                    'language_code': user[4],
                    'selected_language': user[5],
                    'user_type': user[6],
                    'first_interaction_date': user[7],
                    'last_activity_date': user[8],
                    'total_commands': user[9],
                    'total_signals_received': user[10],
                    'current_week_activity': user[17],
                    'total_activities': user[19]
                }
                result.append(user_dict)
            
            return result
                
        except Exception as e:
            print(f"❌ Error fetching user profiles: {e}")
            return []
    
    async def get_weekly_active_users(self) -> int:
        """Get count of users active in current week"""
        if not self.db:
            return 0
            
        try:
            # Get current week start
            now = datetime.now()
            days_since_monday = now.weekday()
            week_start = (now - timedelta(days=days_since_monday)).date().isoformat()
            
            cursor = await self.db.execute('''
                SELECT COUNT(DISTINCT user_id) 
                FROM weekly_usage 
                WHERE week_start_date = ?
            ''', (week_start,))
            
            result = await cursor.fetchone()
            return result[0] if result else 0
                
        except Exception as e:
            print(f"❌ Error getting weekly active users: {e}")
            return 0
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        if not self.db:
            return {}
            
        try:
            # Total users ever registered
            cursor = await self.db.execute('SELECT COUNT(*) FROM users')
            total_users_result = await cursor.fetchone()
            total_users = total_users_result[0] if total_users_result else 0
            
            # Users active this week
            weekly_active = await self.get_weekly_active_users()
            
            # Users active in last 24 hours  
            cursor = await self.db.execute('''
                SELECT COUNT(*) FROM users 
                WHERE datetime(last_activity_date) > datetime('now', '-24 hours')
            ''')
            daily_result = await cursor.fetchone()
            daily_active = daily_result[0] if daily_result else 0
            
            # Free vs premium users
            cursor = await self.db.execute("SELECT COUNT(*) FROM users WHERE user_type = 'free'")
            free_result = await cursor.fetchone()
            free_users = free_result[0] if free_result else 0
            
            cursor = await self.db.execute("SELECT COUNT(*) FROM users WHERE user_type = 'premium'")
            premium_result = await cursor.fetchone()
            premium_users = premium_result[0] if premium_result else 0
            
            # Most active users this week
            now = datetime.now()
            days_since_monday = now.weekday()
            week_start = (now - timedelta(days=days_since_monday)).date().isoformat()
            
            cursor = await self.db.execute('''
                SELECT u.first_name, u.username, w.activity_count
                FROM users u
                JOIN weekly_usage w ON u.user_id = w.user_id
                WHERE w.week_start_date = ?
                ORDER BY w.activity_count DESC
                LIMIT 5
            ''', (week_start,))
            
            top_users_raw = await cursor.fetchall()
            top_users = []
            for user in top_users_raw:
                top_users.append({
                    'first_name': user[0],
                    'username': user[1],
                    'activity_count': user[2]
                })
            
            return {
                'total_users_ever': total_users,
                'weekly_active_users': weekly_active,
                'daily_active_users': daily_active,
                'free_users': free_users,
                'premium_users': premium_users,
                'top_weekly_users': top_users
            }
                
        except Exception as e:
            print(f"❌ Error getting user stats: {e}")
            return {}
    
    async def log_signal_sent(self, symbol: str, signal_data: str, user_count: int):
        """Log when a signal is sent"""
        if not self.db:
            return
            
        try:
            await self.db.execute('''
                INSERT INTO signal_history (symbol, signal_data, sent_to_users)
                VALUES (?, ?, ?)
            ''', (symbol, json.dumps({'message': signal_data[:500]}), user_count))
            
            await self.db.commit()
                
        except Exception as e:
            print(f"❌ Error logging signal: {e}")
    
    async def update_user_signals_received(self, user_ids: List[str]):
        """Update signal count for users who received a signal"""
        if not self.db:
            return
            
        try:
            for user_id in user_ids:
                await self.db.execute('''
                    UPDATE users SET 
                        total_signals_received = total_signals_received + 1,
                        last_activity_date = datetime('now')
                    WHERE user_id = ?
                ''', (user_id,))
                
                # Update weekly activity for signal reception
                await self.update_weekly_activity(user_id, 'signal_received')
            
            await self.db.commit()
                    
        except Exception as e:
            print(f"❌ Error updating user signal counts: {e}")
    
    async def close(self):
        """Close database connection"""
        if self.db:
            await self.db.close()
            print("✅ Database connection closed")