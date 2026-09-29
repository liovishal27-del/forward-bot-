import os
import re
from telethon import TelegramClient, events

# Railway environment variables se credentials uthayega
api_id = int(os.environ.get('26754022', 0))
api_hash = os.environ.get('1a0b65e7a4d48e08687c732bdc0f2cc4', '1a0b65e7a4d48e08687c732bdc0f2cc4')
bot_token = os.environ.get('8394573713:AAFh-a4ImwAKmm7okKx52RQs1KqjEvHf-Z0', '8394573713:AAFh-a4ImwAKmm7okKx52RQs1KqjEvHf-Z0')

if not api_id or not api_hash or not bot_token:
    print("❌ Error: API_ID, API_HASH, aur BOT_TOKEN environment variables set karna zaroori hai!")
    exit(1)

client = TelegramClient('bot_session', api_id, api_hash).start(bot_token=bot_token)

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

@client.on(events.NewMessage(pattern=r'/forward'))
async def forward_handler(event):
    args = event.raw_text.split()
    
    if len(args) < 4:
        await event.reply(
            "❌ **Galat format!**\n\n"
            "Sahi tarika:\n"
            "`/forward <start_link> <end_link> <topic_link>`"
        )
        return

    start_link = args[1]
    end_link = args[2]
    topic_link = args[3]

    channel_entity, start_id = parse_message_link(start_link)
    _, end_id = parse_message_link(end_link)
    group_entity, topic_id = parse_topic_link(topic_link)

    if not channel_entity or not start_id or not end_id:
        await event.reply("❌ Error: Channel ke message links galat hain!")
        return

    if not group_entity or not topic_id:
        await event.reply("❌ Error: Group topic ka link galat hai!")
        return

    status_msg = await event.reply("🔄 Messages forward hona shuru ho gaye hain...")

    min_id = min(start_id, end_id) - 1
    max_id = max(start_id, end_id) + 1
    forwarded_count = 0

    async for message in client.iter_messages(channel_entity, min_id=min_id, max_id=max_id, reverse=True):
        try:
            await client.forward_messages(
                entity=group_entity,
                messages=message,
                drop_author=True,
                reply_to=topic_id
            )
            forwarded_count += 1
        except Exception as e:
            print(f"Error forwarding {message.id}: {e}")

    await status_msg.edit(f"🎉 Kaam ho gaya! Total **{forwarded_count}** messages successfully topic mein forward ho gaye hain.")

print("Bot is up and running on Railway...")
client.run_until_disconnected()
