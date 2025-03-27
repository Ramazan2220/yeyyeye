import time
import logging
import threading
import queue
from enum import Enum
from telegram import ParseMode

logger = logging.getLogger(__name__)

class ChallengeChoice(Enum):
    SMS = 0
    EMAIL = 1

class TelegramChallengeHandler:
    """Обработчик запросов на подтверждение через Telegram"""

    # Глобальный словарь для хранения кодов подтверждения
    verification_codes = {}

    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id
        self.code_queue = queue.Queue()
        self.is_waiting = False
        logger.info(f"Создан обработчик запросов для пользователя {chat_id}")

        # Регистрируем пользователя в глобальном словаре
        TelegramChallengeHandler.verification_codes[chat_id] = self.code_queue

    def reset(self):
        """Сбрасывает состояние обработчика"""
        self.is_waiting = False

        # Очищаем очередь
        while not self.code_queue.empty():
            try:
                self.code_queue.get_nowait()
            except queue.Empty:
                break

    @classmethod
    def set_code(cls, user_id, code):
        """Устанавливает код для пользователя"""
        print(f"[AUTH_MANAGER] Устанавливаем код {code} для пользователя {user_id}")
        if user_id in cls.verification_codes:
            cls.verification_codes[user_id].put(code)
            print(f"[AUTH_MANAGER] Код {code} добавлен в очередь для пользователя {user_id}")
            return True
        return False

    def handle_challenge(self, username, choice_type):
        """Обработчик запроса кода подтверждения"""
        print(f"[AUTH_MANAGER] Вызван handle_challenge для {username}, choice_type={choice_type}")

        if choice_type == ChallengeChoice.EMAIL:
            choice_name = "электронной почты"
        elif choice_type == ChallengeChoice.SMS:
            choice_name = "SMS"
        else:
            choice_name = "неизвестного источника"

        # Отправляем сообщение в Telegram
        message = (
            f"📱 Требуется подтверждение для аккаунта *{username}*\n\n"
            f"Instagram запрашивает код подтверждения, отправленный на {choice_name}.\n\n"
            f"Пожалуйста, введите код подтверждения (6 цифр):"
        )

        self.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode='Markdown'
        )

        # Устанавливаем флаг ожидания
        self.is_waiting = True
        print(f"[AUTH_MANAGER] Ожидание кода подтверждения для {username}, is_waiting={self.is_waiting}")

        # Ждем, пока код не будет введен (максимум 300 секунд = 5 минут)
        start_time = time.time()
        while self.is_waiting and time.time() - start_time < 300:
            try:
                # Пытаемся получить код из очереди с таймаутом
                code = self.code_queue.get(timeout=1)
                print(f"[AUTH_MANAGER] Получен код {code} для {username}")
                self.reset()
                return code
            except queue.Empty:
                # Если очередь пуста, продолжаем ожидание
                pass

        # Если код не был введен за отведенное время
        self.bot.send_message(
            chat_id=self.chat_id,
            text="⏱ Время ожидания кода истекло. Пожалуйста, попробуйте снова."
        )

        self.reset()
        return None