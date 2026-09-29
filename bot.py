import re
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram.error import BadRequest, RetryAfter

# Aapke diye hue credentials
API_ID = 26754022
API_HASH = '1a0b65e7a4d48e08687c732bdc0f2cc4'
BOT_TOKEN = '8394573713:AAFh-a4ImwAKmm7okKx52RQs1KqjEvHf-Z0'

# States for conversation
WAITING_START_LINK, WAITING_END_LINK, WAITING_TOPIC_LINK = range(3)

user_data_store = {}

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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_store[user_id] = {}
    await update.message.reply_text(
        "👋 Welcome Boss! Bot ab bilkul ready hai.\n\n"
        "Sabse pehle, channel ke us message ki **START link** bhejo jahan se shuru karni hai:"
    )
    return WAITING_START_LINK

async def receive_start_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    channel_entity, msg_id = parse_message_link(text)
    if not channel_entity or not msg_id:
        await update.message.reply_text("❌ Yeh link galat lag raha hai. Sahi Telegram message link bhejo:")
        return WAITING_START_LINK
    
    user_data_store[user_id]['channel'] = channel_entity
    user_data_store[user_id]['start_id'] = msg_id
    
    await update.message.reply_text("✅ Start link save ho gaya!\n\nAb channel ke us message ki **END link** bhejo jahan tak forward karna hai:")
    return WAITING_END_LINK

async def receive_end_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    _, msg_id = parse_message_link(text)
    if not msg_id:
        await update.message.reply_text("❌ Yeh link galat lag raha hai. Sahi END message link bhejo:")
        return WAITING_END_LINK
    
    user_data_store[user_id]['end_id'] = msg_id
    
    await update.message.reply_text("✅ End link bhi save ho gaya!\n\nAb apne group ke us **Topic ka link** bhejo jahan messages bhejne hain:")
    return WAITING_TOPIC_LINK

async def receive_topic_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    group_entity, topic_id = parse_topic_link(text)
    if not group_entity or not topic_id:
        await update.message.reply_text("❌ Yeh topic link galat lag raha hai. Sahi Group Topic link bhejo:")
        return WAITING_TOPIC_LINK
    
    data = user_data_store.get(user_id, {})
    channel_entity = data.get('channel')
    start_id = data.get('start_id')
    end_id = data.get('end_id')
    
    status_msg = await update.message.reply_text("🚀 Links mil gaye! Bot 50-50 ke batches mein bina ruke copy karna shuru kar raha hai...")
    
    client_app = context.bot
    min_id = min(start_id, end_id)
    max_id = max(start_id, end_id)
    
    copied_count = 0
    batch_count = 0
    
    try:
        msg_id = min_id
        while msg_id <= max_id:
            try:
                await client_app.copy_message(
                    chat_id=group_entity,
                    from_chat_id=channel_entity,
                    message_id=msg_id,
                    message_thread_id=topic_id
                )
                copied_count += 1
                batch_count += 1
                
                # Har 50 messages ke baad 4 seconds ka proper rest
                if batch_count >= 50:
                    batch_count = 0
                    try:
                        await status_msg.edit_text(f"⏳ Progress: {copied_count} messages successfully copy ho chuke hain... (Resting for 4s)")
                    except:
                        pass
                    await asyncio.sleep(4)
                
                msg_id += 1
                
            except RetryAfter as ra:
                # Agar Telegram speed limit lagaye, toh bot utni der ruk jayega
                print(f"⚠️ RetryAfter hit: Paused for {ra.retry_after} seconds.")
                try:
                    await status_msg.edit_text(f"⚠️ Telegram speed limit hit! Paused for {ra.retry_after}s...")
                except:
                    pass
                await asyncio.sleep(ra.retry_after + 2)
                
            except BadRequest as br:
                # Agar message delete/missing hai toh aage badh jayega
                print(f"Skipped missing ID {msg_id}: {br}")
                msg_id += 1
                
            except Exception as ex:
                print(f"Error on ID {msg_id}: {ex}")
                await asyncio.sleep(2)
                
        await status_msg.edit_text(f"🎉 Kaam ho gaya! Total **{copied_count}** messages bina sender name ke safely topic mein bhej diye gaye hain.")
    except Exception as e:
        await status_msg.edit_text(f"⚠️ Kuch bada error aa gaya: {e}")
        
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancel kar diya gaya. Dubara shuru karne ke liye /start bhejein.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            WAITING_START_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_start_link)],
            WAITING_END_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_end_link)],
            WAITING_TOPIC_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topic_link)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)
    print("Bot started successfully with RetryAfter safety engine...")
    app.run_polling()

if __name__ == '__main__':
    main()
