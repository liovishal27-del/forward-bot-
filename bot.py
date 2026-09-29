import os
import re
import asyncio
from telethon import TelegramClient, events

# Aapke diye hue credentials
API_ID = 26754022
API_HASH = '1a0b65e7a4d48e08687c732bdc0f2cc4'
BOT_TOKEN = '8394573713:AAFh-a4ImwAKmm7okKx52RQs1KqjEvHf-Z0'

client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# User states tracking dictionary
user_states = {}

def parse_message_link(link):
    match = re.search(r't\.me/(?:c/)?([^/]+)/(\d+)', link)
    if match:
        channel_identifier = match.group(1)
        if channel_identifier.isdigit():
            channel_identifier = int('-100' + channel_identifier)
        msg_id = int(match.group(2))
        return channel_identifier, msg_id
    return None, None

def parse_topic_link(link):
    match = re.search(r't\.me/(?:c/)?([^/]+)/(\d+)(?:/(\d+))?', link)
    if match:
        chat_identifier = match.group(1)
        if chat_identifier.isdigit():
            chat_identifier = int('-100' + chat_identifier)
        parts = link.strip('/').split('/')
        thread_id = int(parts[-1]) if parts[-1].isdigit() else None
        return chat_identifier, thread_id
    return None, None

@client.on(events.NewMessage(pattern=r'/start'))
async def start_handler(event):
    user_id = event.sender_id
    user_states[user_id] = {'step': 'WAITING_START'}
    await event.reply(
        "👋 Welcome! Chaliye bina kisi miss ke safely messages forward karte hain.\n\n"
        "Sabse pehle, channel ke us message ki **START link** bhejo jahan se shuru karni hai:"
    )

@client.on(events.NewMessage(incoming=True))
async def message_handler(event):
    user_id = event.sender_id
    if user_id not in user_states:
        return
    
    if event.raw_text.startswith('/'):
        if event.raw_text == '/cancel':
            user_states.pop(user_id, None)
            await event.reply("❌ Process cancel kar diya gaya. Dubara shuru karne ke liye /start bhejein.")
        return

    state = user_states[user_id].get('step')
    text = event.raw_text.strip()

    if state == 'WAITING_START':
        channel_entity, msg_id = parse_message_link(text)
        if not channel_entity or not msg_id:
            await event.reply("❌ Yeh link galat lag raha hai. Sahi Telegram message link bhejo:")
            return
        
        user_states[user_id]['channel'] = channel_entity
        user_states[user_id]['start_id'] = msg_id
        user_states[user_id]['step'] = 'WAITING_END'
        await event.reply("✅ Start link save ho gaya!\n\nAb channel ke us message ki **END link** bhejo jahan tak forward karna hai:")

    elif state == 'WAITING_END':
        _, msg_id = parse_message_link(text)
        if not msg_id:
            await event.reply("❌ Yeh link galat lag raha hai. Sahi END message link bhejo:")
            return
        
        user_states[user_id]['end_id'] = msg_id
        user_states[user_id]['step'] = 'WAITING_TOPIC'
        await event.reply("✅ End link bhi save ho gaya!\n\nAb apne group ke us **Topic ka link** bhejo jahan messages bhejne hain:")

    elif state == 'WAITING_TOPIC':
        group_entity, topic_id = parse_topic_link(text)
        if not group_entity or not topic_id:
            await event.reply("❌ Yeh topic link galat lag raha hai. Sahi Group Topic link bhejo:")
            return
        
        data = user_states.pop(user_id, {})
        channel_entity = data.get('channel')
        start_id = data.get('start_id')
        end_id = data.get('end_id')

        status_msg = await event.reply("🚀 Links mil gaye! Bot actual messages fetch karke 100-100 ke batch mein safely forward kar raha hai...")

        min_id = min(start_id, end_id) - 1
        max_id = max(start_id, end_id) + 1

        # Telethon automatic sabhi valid existing messages ko fetch karega (no gaps/skips)
        messages_to_forward = []
        async for message in client.iter_messages(channel_entity, min_id=min_id, max_id=max_id, reverse=True):
            messages_to_forward.append(message)

        total_messages = len(messages_to_forward)
        forwarded_count = 0

        # 100-100 ke batch mein divide karke bhejna
        for i in range(0, total_messages, 100):
            batch = messages_to_forward[i:i+100]
            for message in batch:
                try:
                    await client.forward_messages(
                        entity=group_entity,
                        messages=message,
                        drop_author=True,    # Sender name hide karne ke liye
                        reply_to=topic_id    # Specific forum topic mein bhejne ke liye
                    )
                    forwarded_count += 1
                except Exception as ex:
                    print(f"Error forwarding message: {ex}")
            
            # Har 100 messages ke baad 3 seconds ka break
            if i + 100 < total_messages:
                await asyncio.sleep(3)

        await status_msg.edit(f"🎉 Kaam ho gaya! Total **{forwarded_count}** messages bina kisi miss ke successfully topic mein forward ho gaye hain.")

print("Telethon Bot started successfully...")
client.run_until_disconnected()
