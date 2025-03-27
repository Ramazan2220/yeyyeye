import os
import json
import logging
import time
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, BadPassword, ChallengeRequired

# Добавляем корневую директорию проекта в sys.path для импорта
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Правильный импорт из utils
from utils.email_utils import get_verification_code_from_email

from config import ACCOUNTS_DIR
from database.db_manager import get_instagram_account, update_account_session_data

logger = logging.getLogger(__name__)

class InstagramClient:
    def __init__(self, account_id):
        """
        Инициализирует клиент Instagram для указанного аккаунта.

        Args:
            account_id (int): ID аккаунта Instagram в базе данных
        """
        self.account_id = account_id
        self.account = get_instagram_account(account_id)
        self.client = Client()
        self.is_logged_in = False

    def login(self):
        """
        Выполняет вход в аккаунт Instagram.

        Returns:
            bool: True, если вход успешен, False в противном случае
        """
        if not self.account:
            logger.error(f"Аккаунт с ID {self.account_id} не найден")
            return False

        try:
            # Пытаемся использовать сохраненную сессию
            session_file = os.path.join(ACCOUNTS_DIR, str(self.account_id), "session.json")

            if os.path.exists(session_file):
                logger.info(f"Найден файл сессии для аккаунта {self.account.username}")

                try:
                    # Загружаем данные сессии
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)

                    # Устанавливаем настройки клиента из сессии
                    if 'settings' in session_data:
                        self.client.set_settings(session_data['settings'])

                    # Пытаемся использовать сохраненную сессию
                    self.client.login(self.account.username, self.account.password)
                    self.is_logged_in = True
                    logger.info(f"Успешный вход по сохраненной сессии для {self.account.username}")
                    return True
                except Exception as e:
                    logger.warning(f"Не удалось использовать сохраненную сессию для {self.account.username}: {e}")
                    # Продолжаем с обычным входом

            # Обычный вход
            logger.info(f"Выполняется вход для пользователя {self.account.username}")
            self.client.login(self.account.username, self.account.password)
            self.is_logged_in = True

            # Сохраняем сессию
            self._save_session()

            logger.info(f"Успешный вход для пользователя {self.account.username}")
            return True

        except BadPassword:
            logger.error(f"Неверный пароль для пользователя {self.account.username}")
            return False

        except ChallengeRequired as e:
            logger.error(f"Требуется подтверждение для пользователя {self.account.username}: {e}")
            return False

        except LoginRequired:
            logger.error(f"Не удалось войти для пользователя {self.account.username}")
            return False

        except Exception as e:
            logger.error(f"Ошибка при входе для пользователя {self.account.username}: {str(e)}")
            return False

    def _save_session(self):
        """Сохраняет данные сессии"""
        try:
            # Создаем директорию для аккаунта, если она не существует
            account_dir = os.path.join(ACCOUNTS_DIR, str(self.account_id))
            os.makedirs(account_dir, exist_ok=True)

            # Получаем настройки клиента
            settings = self.client.get_settings()

            # Формируем данные сессии
            session_data = {
                'username': self.account.username,
                'account_id': self.account_id,
                'last_login': time.strftime('%Y-%m-%d %H:%M:%S'),
                'settings': settings
            }

            # Сохраняем в файл
            session_file = os.path.join(account_dir, "session.json")
            with open(session_file, 'w') as f:
                json.dump(session_data, f)

            # Обновляем данные сессии в базе данных
            update_account_session_data(self.account_id, json.dumps(session_data))

            logger.info(f"Сессия сохранена для пользователя {self.account.username}")

        except Exception as e:
            logger.error(f"Ошибка при сохранении сессии для {self.account.username}: {e}")

    def check_login(self):
        """
        Проверяет статус входа и выполняет вход при необходимости.

        Returns:
            bool: True, если вход выполнен, False в противном случае
        """
        if not self.is_logged_in:
            return self.login()

        try:
            # Проверяем, активна ли сессия
            self.client.get_timeline_feed()
            return True
        except Exception:
            # Если сессия не активна, пытаемся войти снова
            logger.info(f"Сессия не активна для {self.account.username}, выполняется повторный вход")
            return self.login()

    def logout(self):
        """Выполняет выход из аккаунта Instagram"""
        if self.is_logged_in:
            try:
                self.client.logout()
                self.is_logged_in = False
                logger.info(f"Выход выполнен для пользователя {self.account.username}")
                return True
            except Exception as e:
                logger.error(f"Ошибка при выходе для пользователя {self.account.username}: {str(e)}")
                return False
        return True

def test_instagram_login(username, password):
    """
    Тестирует вход в Instagram с указанными учетными данными.

    Args:
        username (str): Имя пользователя Instagram
        password (str): Пароль пользователя Instagram

    Returns:
        bool: True, если вход успешен, False в противном случае
    """
    try:
        logger.info(f"Тестирование входа для пользователя {username}")

        # Создаем клиент Instagram
        client = Client()

        # Пытаемся войти
        client.login(username, password)

        # Если дошли до этой точки, значит вход успешен
        logger.info(f"Вход успешен для пользователя {username}")

        # Выходим из аккаунта
        client.logout()

        return True

    except BadPassword:
        logger.error(f"Неверный пароль для пользователя {username}")
        return False

    except ChallengeRequired:
        logger.error(f"Требуется подтверждение для пользователя {username}")
        return False

    except LoginRequired:
        logger.error(f"Не удалось войти для пользователя {username}")
        return False

    except Exception as e:
        logger.error(f"Ошибка при входе для пользователя {username}: {str(e)}")
        return False

def login_with_session(username, password, account_id):
    """
    Выполняет вход в Instagram с использованием сохраненной сессии.

    Args:
        username (str): Имя пользователя Instagram
        password (str): Пароль пользователя Instagram
        account_id (int): ID аккаунта в базе данных

    Returns:
        Client: Клиент Instagram или None в случае ошибки
    """
    try:
        logger.info(f"Вход с сессией для пользователя {username}")

        # Создаем клиент Instagram
        client = Client()

        # Проверяем наличие файла сессии
        session_file = os.path.join(ACCOUNTS_DIR, str(account_id), "session.json")

        if os.path.exists(session_file):
            logger.info(f"Найден файл сессии для аккаунта {username}")

            try:
                # Загружаем данные сессии
                with open(session_file, 'r') as f:
                    session_data = json.load(f)

                # Устанавливаем настройки клиента из сессии
                if 'settings' in session_data:
                    client.set_settings(session_data['settings'])

                # Пытаемся использовать сохраненную сессию
                client.login(username, password)
                logger.info(f"Успешный вход по сохраненной сессии для {username}")
                return client
            except Exception as e:
                logger.warning(f"Не удалось использовать сохраненную сессию для {username}: {e}")
                # Продолжаем с обычным входом

        # Обычный вход
        client.login(username, password)

        # Сохраняем сессию
        try:
            # Создаем директорию для аккаунта, если она не существует
            account_dir = os.path.join(ACCOUNTS_DIR, str(account_id))
            os.makedirs(account_dir, exist_ok=True)

            # Получаем настройки клиента
            settings = client.get_settings()

            # Формируем данные сессии
            session_data = {
                'username': username,
                'account_id': account_id,
                'last_login': time.strftime('%Y-%m-%d %H:%M:%S'),
                'settings': settings
            }

            # Сохраняем в файл
            with open(session_file, 'w') as f:
                json.dump(session_data, f)

            # Обновляем данные сессии в базе данных
            update_account_session_data(account_id, json.dumps(session_data))

            logger.info(f"Сессия сохранена для пользователя {username}")

        except Exception as e:
            logger.error(f"Ошибка при сохранении сессии для {username}: {e}")

        return client

    except Exception as e:
        logger.error(f"Ошибка при входе для пользователя {username}: {str(e)}")
        return None

def check_login_challenge(username, password, email=None, email_password=None):
    """
    Проверяет, требуется ли код подтверждения при входе

    Возвращает:
    - challenge_required: True, если требуется код подтверждения
    - challenge_info: Информация о запросе на подтверждение
    """
    print(f"[DEBUG] check_login_challenge вызван для {username}")
    logger.info(f"Проверка входа для пользователя {username}")

    try:
        client = Client()

        try:
            # Пытаемся войти
            client.login(username, password)

            # Если вход успешен, возвращаем False (код не требуется)
            return False, None

        except ChallengeRequired as e:
            print(f"[DEBUG] Требуется код подтверждения для {username}")

            # Получаем информацию о запросе на подтверждение
            challenge_url = client.last_json.get("challenge", {}).get("api_path")

            if not challenge_url:
                print(f"[DEBUG] Ошибка: не удалось получить URL запроса на подтверждение")
                return False, f"Ошибка: не удалось получить URL запроса на подтверждение"

            # Выбираем метод подтверждения (email)
            try:
                print(f"[DEBUG] Разрешаем запрос на подтверждение для {username}")
                client.challenge_resolve(challenge_url)
            except Exception as e:
                print(f"[DEBUG] Ошибка при разрешении запроса на подтверждение: {str(e)}")

            # Пытаемся автоматически получить код из почты
            if email and email_password:
                try:
                    print(f"[DEBUG] Пытаемся автоматически получить код из почты {email}")
                    # Импорт уже выполнен в начале файла
                    # from utils.email_utils import get_verification_code_from_email

                    # Ждем немного, чтобы письмо успело прийти
                    import time
                    time.sleep(10)

                    # Получаем код из почты
                    verification_code = get_verification_code_from_email(email, email_password)

                    if verification_code:
                        print(f"[DEBUG] Получен код подтверждения из почты: {verification_code}")

                        # Отправляем код
                        result = client.challenge_resolve(challenge_url, verification_code)

                        if result:
                            print(f"[DEBUG] Автоматическое подтверждение успешно для {username}")
                            return False, None
                except Exception as e:
                    print(f"[DEBUG] Ошибка при автоматическом подтверждении: {str(e)}")

            # Если автоматическое подтверждение не удалось, возвращаем информацию для ручного ввода
            challenge_info = {
                'api_path': challenge_url,
                'client_settings': client.get_settings()
            }

            print(f"[DEBUG] Требуется код подтверждения для {username}")
            return True, challenge_info

        except Exception as e:
            print(f"[DEBUG] Ошибка при проверке входа для {username}: {str(e)}")
            logger.error(f"Ошибка при проверке входа для пользователя {username}: {str(e)}")
            return False, str(e)

    except Exception as e:
        print(f"[DEBUG] Ошибка при проверке входа для {username}: {str(e)}")
        logger.error(f"Ошибка при проверке входа для пользователя {username}: {str(e)}")
        return False, str(e)

def submit_challenge_code(username, password, code, challenge_info):
    """
    Отправляет код подтверждения для завершения процесса входа

    Возвращает:
    - success: True, если код принят
    - result: Сообщение об успехе или ошибке
    """
    print(f"[DEBUG] submit_challenge_code вызван для {username} с кодом {code}")
    logger.info(f"Отправка кода подтверждения для пользователя {username}")

    try:
        print(f"[DEBUG] Восстанавливаем настройки клиента для {username}")
        client = Client()

        # Восстанавливаем состояние клиента из challenge_info
        if isinstance(challenge_info, dict) and 'client_settings' in challenge_info:
            client.set_settings(challenge_info['client_settings'])

        # Получаем данные о запросе на подтверждение
        api_path = challenge_info.get('api_path')
        if not api_path:
            print(f"[DEBUG] Ошибка: api_path не найден в challenge_info")
            return False, "Данные о запросе на подтверждение отсутствуют"

        print(f"[DEBUG] Отправляем код подтверждения {code} для {username}")

        # Используем метод challenge_resolve из instagrapi
        try:
            result = client.challenge_resolve(api_path, code)
            if result:
                print(f"[DEBUG] Код подтверждения принят для {username}")
                return True, "Код подтверждения принят"
            else:
                print(f"[DEBUG] Код подтверждения отклонен для {username}")
                return False, "Код подтверждения отклонен"
        except Exception as e:
            print(f"[DEBUG] Ошибка при отправке кода подтверждения для {username}: {str(e)}")
            logger.error(f"Ошибка при отправке кода подтверждения: {str(e)}")
            return False, str(e)

    except Exception as e:
        print(f"[DEBUG] Ошибка при отправке кода подтверждения для {username}: {str(e)}")
        logger.error(f"Ошибка при отправке кода подтверждения: {str(e)}")
        return False, str(e)