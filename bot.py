import os
import re
import asyncio
from telethon import TelegramClient, events

# Aapke diye hue credentials
API_ID = 26754022
API_HASH = '1a0b65e7a4d48e08687c732bdc0f2cc4'
BOT_TOKEN = '8394573713:AAFh-a4ImwAKmm7okKx52RQs1KqjEvHf-Z0'

client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

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
        "👋 Welcome! Chaliye safely messages forward karte hain.\n\n"
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
        channel_identifier, msg_id = parse_message_link(text)
        if not channel_identifier or not msg_id:
            await event.reply("❌ Yeh link galat lag raha hai. Sahi Telegram message link bhejo:")
            return
        
        user_states[user_id]['channel'] = channel_identifier
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
        group_identifier, topic_id = parse_topic_link(text)
        if not group_identifier or not topic_id:
            await event.reply("❌ Yeh topic link galat lag raha hai. Sahi Group Topic link bhejo:")
            return
        
        data = user_states.pop(user_id, {})
        raw_channel = data.get('channel')
        start_id = data.get('start_id')
        end_id = data.get('end_id')

        status_msg = await event.reply("🔄 Connecting to channel and group...")

        try:
            channel_entity = await client.get_entity(raw_channel)
            group_entity = await client.get_entity(group_identifier)
        except Exception as e:
            await status_msg.edit(f"❌ Connection Error: Channel ya Group access nahi ho pa raha hai. Error: {e}")
            return

        await status_msg.edit("🚀 Connected! Messages fetch kiye ja rahe hain...")

        min_id = min(start_id, end_id) - 1
        max_id = max(start_id, end_id) + 1

        messages_to_forward = []
        try:
            async for message in client.iter_messages(channel_entity, min_id=min_id, max_id=max_id, reverse=True):
                if message:
                    messages_to_forward.append(message)
        except Exception as fetch_err:
            await status_msg.edit(f"❌ Fetching Error: Messages load karte waqt error aayi: {fetch_err}")
            return

        total_messages = len(messages_to_forward)
        if total_messages == 0:
            await status_msg.edit("⚠️ Diye gaye range mein koi messages nahi mile! Check karein ki start aur end message sahi hain ya nahi.")
            return

        await status_msg.edit(f"📦 Total **{total_messages}** messages mil gaye hain. Forwarding shuru ho rahi hai...")

        forwarded_count = 0

        for i in range(0, total_messages, 100):
            batch = messages_to_forward[i:i+100]
            for message in batch:
                try:
                    await client.forward_messages(
                        entity=group_entity,
                        messages=message,
                        drop_author=True,
                        reply_to=topic_id
                    )
                    forwarded_count += 1
                except Exception as ex:
                    print(f"Error forwarding message: {ex}")
            
            try:
                await status_msg.edit(f"⏳ Progress: {forwarded_count}/{total_messages} messages forward ho chuke hain...")
            except:
                pass
                
            if i + 100 < total_messages:
                await asyncio.sleep(3)

        await status_msg.edit(f"🎉 Kaam ho gaya! Total **{forwarded_count}** messages successfully topic mein forward ho gaye hain.")

print("Telethon Bot started successfully...")
client.run_until_disconnected()
