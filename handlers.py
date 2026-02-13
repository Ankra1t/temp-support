import time
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from settings import (
    TELEGRAM_SUPPORT_CHAT_ID,
    FORWARD_MODE,
    PERSONAL_ACCOUNT_CHAT_ID,
    WELCOME_MESSAGE,
)
from database import (
    get_user_by_chat_id,
    get_user_by_topic_id,
    create_user,
    update_user_topic,
)
import logging


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(
        f"{WELCOME_MESSAGE} {update.effective_user.first_name}"
    )


def generate_topic_name(update: Update) -> str:
    """Генерирует имя для forum topic на основе данных пользователя."""
    user = update.effective_user
    parts = []

    if user.first_name:
        parts.append(user.first_name)
    if user.last_name:
        parts.append(user.last_name)

    name = ' '.join(parts) if parts else f"User{user.id}"

    if user.username:
        name += f" (@{user.username})"

    name += f" #{user.id}"

    return name[:128]  # Telegram ограничивает 128 символов


async def ensure_user_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """
    Создаёт forum topic для пользователя если не существует.
    Возвращает topic_id.
    """
    user_id = update.effective_user.id
    user = get_user_by_chat_id(user_id)

    if user and user.get('topic_id'):
        return user['topic_id']

    # Создаём пользователя если не существует
    if not user:
        user = create_user(chat_id=user_id, platform='telegram')

    # Генерируем имя темы
    topic_name = generate_topic_name(update)

    try:
        # Создаём forum topic
        result = await context.bot.create_forum_topic(
            chat_id=TELEGRAM_SUPPORT_CHAT_ID,
            name=topic_name
        )

        if result.message_thread_id:
            update_user_topic(user_id, result.message_thread_id)
            logging.info(
                f"Created topic {result.message_thread_id} for user {user_id}"
            )
            return result.message_thread_id

    except BadRequest as e:
        logging.error(f"Error creating forum topic: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")

    return None


async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward user messages to support group with forum topic."""
    user_id = update.effective_user.id

    # Проверка на бан пользователя (опционально)
    user = get_user_by_chat_id(user_id)
    if user and user.get('is_banned'):
        await update.message.reply_text("Вы забанены(")
        return

    # Получаем или создаём topic для пользователя
    topic_id = await ensure_user_topic(update, context)

    if not topic_id:
        await update.message.reply_text(
            "Проблема сервера. Повторите попытку позже."
        )
        return

    # Определяем чат для пересылки
    target_chat_id = TELEGRAM_SUPPORT_CHAT_ID
    if FORWARD_MODE == "personal_account":
        target_chat_id = PERSONAL_ACCOUNT_CHAT_ID

    try:
        sent_msg = None
        message = update.message

        # Копируем сообщение в нужную тему
        if message.text:
            sent_msg = await context.bot.send_message(
                chat_id=target_chat_id,
                message_thread_id=topic_id,
                text=message.text
            )
        elif message.photo:
            sent_msg = await context.bot.send_photo(
                chat_id=target_chat_id,
                message_thread_id=topic_id,
                photo=message.photo[-1].file_id,
                caption=message.caption
            )
        elif message.document:
            sent_msg = await context.bot.send_document(
                chat_id=target_chat_id,
                message_thread_id=topic_id,
                document=message.document.file_id,
                caption=message.caption
            )
        elif message.voice:
            sent_msg = await context.bot.send_voice(
                chat_id=target_chat_id,
                message_thread_id=topic_id,
                voice=message.voice.file_id
            )
        elif message.video:
            sent_msg = await context.bot.send_video(
                chat_id=target_chat_id,
                message_thread_id=topic_id,
                video=message.video.file_id,
                caption=message.caption
            )
        elif message.video_note:
            sent_msg = await context.bot.send_video_note(
                chat_id=target_chat_id,
                message_thread_id=topic_id,
                video_note=message.video_note.file_id
            )
        elif message.sticker:
            sent_msg = await context.bot.send_sticker(
                chat_id=target_chat_id,
                message_thread_id=topic_id,
                sticker=message.sticker.file_id
            )
        elif message.location:
            sent_msg = await context.bot.send_location(
                chat_id=target_chat_id,
                message_thread_id=topic_id,
                latitude=message.location.latitude,
                longitude=message.location.longitude
            )
        elif message.contact:
            sent_msg = await context.bot.send_contact(
                chat_id=target_chat_id,
                message_thread_id=topic_id,
                phone_number=message.contact.phone_number,
                first_name=message.contact.first_name,
                last_name=message.contact.last_name
            )
        else:
            # Для остальных типов пробуем forward
            sent_msg = await message.forward(
                chat_id=target_chat_id
            )

        # Сохраняем соответствие для обратной связи (legacy)
        if sent_msg:
            last_message_ts = context.bot_data.get('ts')
            current_ts = int(time.time())

            # Отправляем сообщение, если пользователь не писал более 2 часов
            if not last_message_ts or current_ts - last_message_ts > 60 * 60 * 2:
                await update.message.reply_text(
                    "Обращение принято. Мы уже работаем над вашим вопросом и скоро вернёмся с ответом."
                )
            logging.info(
                f"Forwarded message to topic {topic_id} from user {user_id}"
            )

            # Запоминаем, время последнего сообщения пользователя
            context.bot_data['ts'] = current_ts

    except BadRequest as e:
        logging.error(f"BadRequest forwarding message: {str(e)}")
        await update.message.reply_text(
            "Ошибка отправки. Повторите попытка позже."
        )
    except Exception as e:
        logging.error(f"Error forwarding message: {str(e)}")
        await update.message.reply_text(
            "Ошибка отправки. Повторите попытка позже."
        )


async def forward_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward messages from support group back to user."""
    logging.info("forward_to_user called")

    # Проверяем, что сообщение из forum topic
    if not update.effective_message.message_thread_id:
        return

    topic_id = update.effective_message.message_thread_id
    logging.info(f"Message from topic {topic_id}")

    # Получаем пользователя по topic_id
    user = get_user_by_topic_id(topic_id)

    if not user:
        logging.warning(f"Could not find user for topic {topic_id}")
        await update.message.reply_text(
            "Пользователь не найден."
        )
        return

    user_id = user['chat_id']

    try:
        message = update.message

        # Отправляем ответ пользователю
        if message.text:
            await context.bot.send_message(
                chat_id=user_id,
                text=message.text
            )
        elif message.photo:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=message.photo[-1].file_id,
                caption=message.caption
            )
        elif message.document:
            await context.bot.send_document(
                chat_id=user_id,
                document=message.document.file_id,
                caption=message.caption
            )
        elif message.voice:
            await context.bot.send_voice(
                chat_id=user_id,
                voice=message.voice.file_id
            )
        elif message.video:
            await context.bot.send_video(
                chat_id=user_id,
                video=message.video.file_id,
                caption=message.caption
            )
        elif message.video_note:
            await context.bot.send_video_note(
                chat_id=user_id,
                video_note=message.video_note.file_id
            )
        elif message.sticker:
            await context.bot.send_sticker(
                chat_id=user_id,
                sticker=message.sticker.file_id
            )
        elif message.location:
            await context.bot.send_location(
                chat_id=user_id,
                latitude=message.location.latitude,
                longitude=message.location.longitude
            )
        elif message.contact:
            await context.bot.send_contact(
                chat_id=user_id,
                phone_number=message.contact.phone_number,
                first_name=message.contact.first_name,
                last_name=message.contact.last_name
            )
        else:
            if message.reply_to_message:
                await message.reply_to_message.forward(user_id)

        logging.info(
            f"Sent reply from topic {topic_id} to user {user_id}"
        )

    except BadRequest as e:
        if "bot was blocked" in str(e).lower():
            logging.warning(f"User {user_id} blocked the bot")
            await update.message.reply_text(
                f"Пользователь забанен."
            )
        elif "user not found" in str(e).lower():
            logging.warning(f"User {user_id} not found")
            await update.message.reply_text(
                f"Пользователь не найден."
            )
        else:
            logging.error(f"BadRequest: {str(e)}")
            await update.message.reply_text(
                f"Ошибка: {str(e)}"
            )
    except Exception as e:
        logging.error(f"Error sending message to user: {str(e)}")
        await update.message.reply_text(
            f"Ошибка: {str(e)}"
        )
