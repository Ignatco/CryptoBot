import asyncio
import aiohttp
import os

# Use your specific chat ID
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = '304403982'  # Your specific chat ID

async def test_telegram_connection():
    """Test if we can send a message to Telegram"""
    base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    
    # Test bot connection
    async with aiohttp.ClientSession() as session:
        # Check bot info
        try:
            async with session.get(f"{base_url}/getMe") as response:
                if response.status == 200:
                    bot_info = await response.json()
                    print(f"✅ Bot authenticated: {bot_info['result']['username']}")
                else:
                    print(f"❌ Bot authentication failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
        
        # Send test message
        try:
            url = f"{base_url}/sendMessage"
            data = {
                'chat_id': CHAT_ID,
                'text': '🤖 Test Message\n\nYour crypto bot is working!\nThis confirms the connection is established.'
            }
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    print("✅ Test message sent successfully!")
                    result = await response.json()
                    print(f"Message ID: {result['result']['message_id']}")
                    return True
                else:
                    response_text = await response.text()
                    print(f"❌ Failed to send message: {response.status}")
                    print(f"Error details: {response_text}")
                    return False
        except Exception as e:
            print(f"❌ Error sending test message: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(test_telegram_connection())