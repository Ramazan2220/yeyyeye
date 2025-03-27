# email_utils.py
import logging
import re
import time
import imaplib
import email as email_lib
from email.header import decode_header
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_code_from_firstmail(email, password, max_attempts=3, delay_between_attempts=5):
    """
    Получает код подтверждения из FirstMail через IMAP

    Args:
        email (str): Адрес электронной почты
        password (str): Пароль от почты
        max_attempts (int): Максимальное количество попыток
        delay_between_attempts (int): Задержка между попытками в секундах

    Returns:
        str: Код подтверждения или None, если не удалось получить
    """
    print(f"[DEBUG] Получение кода из FirstMail для {email}")
    logger.info(f"Получение кода из FirstMail для {email}")

    for attempt in range(max_attempts):
        try:
            print(f"[DEBUG] Попытка {attempt+1} получения кода из FirstMail")

            # Подключаемся к FirstMail через IMAP
            # Используем правильный сервер и порт для FirstMail
            mail = imaplib.IMAP4_SSL("imap.firstmail.ltd", 993)
            mail.login(email, password)
            mail.select("inbox")

            # Ищем письма от Instagram
            status, messages = mail.search(None, '(FROM "security@mail.instagram.com")')

            if status != "OK" or not messages[0]:
                print(f"[DEBUG] Письма от Instagram не найдены")
                # Попробуем более широкий поиск
                status, messages = mail.search(None, 'ALL')
                if status != "OK" or not messages[0]:
                    print(f"[DEBUG] Письма не найдены")
                    mail.close()
                    mail.logout()
                    time.sleep(delay_between_attempts)
                    continue

            # Получаем ID писем
            email_ids = messages[0].split()
            print(f"[DEBUG] Найдено {len(email_ids)} писем")

            # Перебираем письма от новых к старым
            for email_id in reversed(email_ids):
                status, msg_data = mail.fetch(email_id, "(RFC822)")

                if status != "OK":
                    continue

                # Парсим письмо
                msg = email_lib.message_from_bytes(msg_data[0][1])

                # Получаем отправителя и тему
                from_header = msg.get("From", "")
                subject_header = msg.get("Subject", "")

                # Декодируем заголовки, если нужно
                subject = ""
                if subject_header:
                    decoded_subject = decode_header(subject_header)
                    subject = decoded_subject[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(decoded_subject[0][1] or 'utf-8')

                print(f"[DEBUG] Проверяем письмо от: {from_header}, тема: {subject}")

                # Проверяем, от Instagram ли письмо
                if "instagram" in from_header.lower() or "security code" in subject.lower():
                    # Получаем текст письма
                    message_text = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition", ""))

                            # Пропускаем вложения
                            if "attachment" in content_disposition:
                                continue

                            if content_type == "text/plain" or content_type == "text/html":
                                try:
                                    payload = part.get_payload(decode=True)
                                    charset = part.get_content_charset() or 'utf-8'
                                    message_text += payload.decode(charset, errors='replace')
                                except Exception as e:
                                    print(f"[DEBUG] Ошибка при декодировании части письма: {str(e)}")
                    else:
                        try:
                            payload = msg.get_payload(decode=True)
                            charset = msg.get_content_charset() or 'utf-8'
                            message_text = payload.decode(charset, errors='replace')
                        except Exception as e:
                            print(f"[DEBUG] Ошибка при декодировании письма: {str(e)}")

                    print(f"[DEBUG] Текст письма: {message_text[:100]}...")

                    # Ищем код подтверждения в тексте письма
                    # Instagram обычно отправляет 6-значный код
                    code_match = re.search(r'(\d{6})', message_text)
                    if code_match:
                        verification_code = code_match.group(1)
                        print(f"[DEBUG] Найден код подтверждения: {verification_code}")
                        mail.close()
                        mail.logout()
                        return verification_code

                    # Если не нашли 6-значный код, ищем любой код
                    code_match = re.search(r'[Cc]ode[:\s]+(\d+)', message_text)
                    if code_match:
                        verification_code = code_match.group(1)
                        print(f"[DEBUG] Найден код подтверждения: {verification_code}")
                        mail.close()
                        mail.logout()
                        return verification_code

            print(f"[DEBUG] Код подтверждения не найден в письмах. Ждем {delay_between_attempts} секунд...")
            mail.close()
            mail.logout()
            time.sleep(delay_between_attempts)

        except Exception as e:
            print(f"[DEBUG] Ошибка при получении кода из FirstMail: {str(e)}")
            logger.error(f"Ошибка при получении кода из FirstMail: {str(e)}")
            time.sleep(delay_between_attempts)

    print(f"[DEBUG] Не удалось получить код подтверждения после {max_attempts} попыток")
    return None

def get_code_from_firstmail_with_imap_tools(email, password, max_attempts=3, delay_between_attempts=5):
    """
    Получает код подтверждения из FirstMail с использованием imap_tools

    Args:
        email (str): Адрес электронной почты
        password (str): Пароль от почты
        max_attempts (int): Максимальное количество попыток
        delay_between_attempts (int): Задержка между попытками в секундах

    Returns:
        str: Код подтверждения или None, если не удалось получить
    """
    print(f"[DEBUG] Получение кода из FirstMail для {email} с использованием imap_tools")
    logger.info(f"Получение кода из FirstMail для {email} с использованием imap_tools")

    for attempt in range(max_attempts):
        try:
            from imap_tools import MailBox, AND, A

            print(f"[DEBUG] Попытка {attempt+1} получения кода из FirstMail")

            # Подключаемся к FirstMail с правильным сервером и портом
            with MailBox('imap.firstmail.ltd', 993).login(email, password) as mailbox:
                # Получаем все письма, сортируем по дате (новые первыми)
                messages = list(mailbox.fetch(limit=10, reverse=True))

                # Сортируем письма по дате получения (от новых к старым)
                messages.sort(key=lambda msg: msg.date, reverse=True)

                print(f"[DEBUG] Найдено {len(messages)} писем")

                # Сначала ищем письма с темой "Подтвердите свой аккаунт"
                for msg in messages:
                    if "Подтвердите свой аккаунт" in msg.subject or "Verify your account" in msg.subject:
                        print(f"[DEBUG] Проверяем письмо с темой: {msg.subject}")

                        # Получаем текст письма
                        body_html = msg.html or ""
                        body_text = msg.text or ""

                        # Используем HTML, если доступен, иначе текст
                        message_content = body_html if body_html else body_text

                        # Ищем все 6-значные числа в тексте письма
                        codes = re.findall(r'\b\d{6}\b', message_content)

                        if codes:
                            # Фильтруем коды, исключая известные "не-коды"
                            filtered_codes = [code for code in codes if code not in ['262626', '999999']]

                            if filtered_codes:
                                verification_code = filtered_codes[0]
                                print(f"[DEBUG] Найден код подтверждения: {verification_code}")
                                return verification_code

                # Если не нашли в письмах с подходящей темой, ищем в любых письмах от Instagram
                for msg in messages:
                    if "instagram" in msg.from_.lower():
                        print(f"[DEBUG] Проверяем письмо от: {msg.from_}, тема: {msg.subject}")

                        # Получаем текст письма
                        body_html = msg.html or ""
                        body_text = msg.text or ""

                        # Используем HTML, если доступен, иначе текст
                        message_content = body_html if body_html else body_text

                        # Ищем все 6-значные числа в тексте письма
                        codes = re.findall(r'\b\d{6}\b', message_content)

                        if codes:
                            # Фильтруем коды, исключая известные "не-коды"
                            filtered_codes = [code for code in codes if code not in ['262626', '999999']]

                            if filtered_codes:
                                verification_code = filtered_codes[0]
                                print(f"[DEBUG] Найден код подтверждения: {verification_code}")
                                return verification_code

            print(f"[DEBUG] Код подтверждения не найден. Ждем {delay_between_attempts} секунд...")
            time.sleep(delay_between_attempts)

        except Exception as e:
            print(f"[DEBUG] Ошибка при получении кода из FirstMail: {str(e)}")
            logger.error(f"Ошибка при получении кода из FirstMail: {str(e)}")
            time.sleep(delay_between_attempts)

    print(f"[DEBUG] Не удалось получить код подтверждения после {max_attempts} попыток")
    return None

def get_verification_code_from_email(email, password, max_attempts=5, delay_between_attempts=10):
    """
    Получает код подтверждения из почты

    Args:
        email (str): Адрес электронной почты
        password (str): Пароль от почты
        max_attempts (int): Максимальное количество попыток
        delay_between_attempts (int): Задержка между попытками в секундах

    Returns:
        str: Код подтверждения или None, если не удалось получить
    """
    print(f"[DEBUG] Получение кода подтверждения из почты {email}")
    logger.info(f"Получение кода подтверждения из почты {email}")

    try:
        # Проверяем, какой почтовый сервис используется
        if any(email.endswith(domain) for domain in [
            '@fmailler.com', '@fmailler.net', '@fmaillerbox.net', '@firstmail.ltd',
            '@fmailler.ltd', '@firstmail.net', '@firstmail.com'
        ]):
            # Сначала пробуем с imap_tools, если установлен
            try:
                import imap_tools
                return get_code_from_firstmail_with_imap_tools(email, password, max_attempts, delay_between_attempts)
            except ImportError:
                # Если imap_tools не установлен, используем стандартный imaplib
                return get_code_from_firstmail(email, password, max_attempts, delay_between_attempts)
        elif "@gmail.com" in email:
            # Здесь можно добавить функцию для Gmail
            print(f"[DEBUG] Поддержка Gmail пока не реализована")
            return None
        else:
            # Для других почтовых сервисов используем общий метод
            return get_code_from_generic_email(email, password, max_attempts, delay_between_attempts)
    except Exception as e:
        print(f"[DEBUG] Ошибка при получении кода подтверждения: {str(e)}")
        logger.error(f"Ошибка при получении кода подтверждения: {str(e)}")
        return None

def get_code_from_generic_email(email, password, max_attempts=3, delay_between_attempts=5):
    """
    Получает код подтверждения из любой почты через IMAP

    Args:
        email (str): Адрес электронной почты
        password (str): Пароль от почты
        max_attempts (int): Максимальное количество попыток
        delay_between_attempts (int): Задержка между попытками в секундах

    Returns:
        str: Код подтверждения или None, если не удалось получить
    """
    print(f"[DEBUG] Получение кода из почты {email}")
    logger.info(f"Получение кода из почты {email}")

    # Определяем сервер IMAP в зависимости от домена почты
    if email.endswith('@gmail.com'):
        imap_server = 'imap.gmail.com'
    elif email.endswith('@yahoo.com'):
        imap_server = 'imap.mail.yahoo.com'
    elif email.endswith('@outlook.com') or email.endswith('@hotmail.com'):
        imap_server = 'outlook.office365.com'
    elif email.endswith('@mail.ru'):
        imap_server = 'imap.mail.ru'
    elif email.endswith('@yandex.ru'):
        imap_server = 'imap.yandex.ru'
    elif any(email.endswith(domain) for domain in [
        '@fmailler.com', '@fmailler.net', '@fmaillerbox.net', '@firstmail.ltd',
        '@fmailler.ltd', '@firstmail.net', '@firstmail.com'
    ]):
        imap_server = 'imap.firstmail.ltd'
    else:
        # Для других доменов можно попробовать стандартный формат
        domain = email.split('@')[1]
        imap_server = f'imap.{domain}'

    print(f"[DEBUG] Подключение к IMAP-серверу: {imap_server}")

    for attempt in range(max_attempts):
        try:
            print(f"[DEBUG] Попытка {attempt+1} получения кода из почты")

            # Подключаемся к серверу IMAP
            mail = imaplib.IMAP4_SSL(imap_server, 993)
            mail.login(email, password)
            mail.select("inbox")

            # Ищем письма от Instagram
            status, messages = mail.search(None, '(FROM "instagram" UNSEEN)')

            if status != "OK" or not messages[0]:
                print(f"[DEBUG] Письма от Instagram не найдены")
                # Попробуем более широкий поиск
                status, messages = mail.search(None, 'ALL')
                if status != "OK" or not messages[0]:
                    print(f"[DEBUG] Письма не найдены")
                    mail.close()
                    mail.logout()
                    time.sleep(delay_between_attempts)
                    continue

            # Получаем ID писем
            email_ids = messages[0].split()
            print(f"[DEBUG] Найдено {len(email_ids)} писем")

            # Перебираем письма от новых к старым
            for email_id in reversed(email_ids):
                status, msg_data = mail.fetch(email_id, "(RFC822)")

                if status != "OK":
                    continue

                # Парсим письмо
                msg = email_lib.message_from_bytes(msg_data[0][1])

                # Получаем отправителя и тему
                from_header = msg.get("From", "")
                subject_header = msg.get("Subject", "")

                print(f"[DEBUG] Проверяем письмо от: {from_header}, тема: {subject_header}")

                # Проверяем, от Instagram ли письмо
                if "instagram" in from_header.lower() or "security code" in subject_header.lower():
                    # Получаем текст письма
                    message_text = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain" or content_type == "text/html":
                                try:
                                    payload = part.get_payload(decode=True)
                                    charset = part.get_content_charset() or 'utf-8'
                                    message_text += payload.decode(charset, errors='replace')
                                except Exception as e:
                                    print(f"[DEBUG] Ошибка при декодировании части письма: {str(e)}")
                    else:
                        try:
                            payload = msg.get_payload(decode=True)
                            charset = msg.get_content_charset() or 'utf-8'
                            message_text = payload.decode(charset, errors='replace')
                        except Exception as e:
                            print(f"[DEBUG] Ошибка при декодировании письма: {str(e)}")

                    print(f"[DEBUG] Текст письма: {message_text[:100]}...")

                    # Ищем код подтверждения в тексте письма
                    # Сначала ищем по шаблону "код: XXXXXX" или "code: XXXXXX"
                    code_match = re.search(r'[Cc]ode:?\s*(\d{6})', message_text)
                    if not code_match:
                        # Если не нашли, ищем просто 6 цифр подряд
                        code_match = re.search(r'(\d{6})', message_text)

                    if code_match:
                        verification_code = code_match.group(1)
                        print(f"[DEBUG] Найден код подтверждения: {verification_code}")
                        mail.close()
                        mail.logout()
                        return verification_code

            print(f"[DEBUG] Код подтверждения не найден в письмах. Ждем {delay_between_attempts} секунд...")
            mail.close()
            mail.logout()
            time.sleep(delay_between_attempts)

        except Exception as e:
            print(f"[DEBUG] Ошибка при получении кода из почты: {str(e)}")
            logger.error(f"Ошибка при получении кода из почты: {str(e)}")
            time.sleep(delay_between_attempts)

    print(f"[DEBUG] Не удалось получить код подтверждения после {max_attempts} попыток")
    return None

def test_email_connection(email_address, password):
    """
    Проверяет подключение к почтовому ящику

    Возвращает:
    - success: True, если подключение успешно
    - message: Сообщение об успехе или ошибке
    """
    # Определяем сервер IMAP в зависимости от домена почты
    if email_address.endswith('@gmail.com'):
        imap_server = 'imap.gmail.com'
    elif email_address.endswith('@yahoo.com'):
        imap_server = 'imap.mail.yahoo.com'
    elif email_address.endswith('@outlook.com') or email_address.endswith('@hotmail.com'):
        imap_server = 'outlook.office365.com'
    elif email_address.endswith('@mail.ru'):
        imap_server = 'imap.mail.ru'
    elif email_address.endswith('@yandex.ru'):
        imap_server = 'imap.yandex.ru'
    # Обрабатываем все возможные домены FirstMail
    elif any(email_address.endswith(domain) for domain in [
        '@fmailler.com', '@fmailler.net', '@fmaillerbox.net', '@firstmail.ltd',
        '@fmailler.ltd', '@firstmail.net', '@firstmail.com'
    ]):
        imap_server = 'imap.firstmail.ltd'  # Используем правильный IMAP-сервер для FirstMail
    else:
        # Для других доменов можно попробовать стандартный формат
        domain = email_address.split('@')[1]
        imap_server = f'imap.{domain}'

    print(f"[DEBUG] Подключение к IMAP-серверу: {imap_server}")

    try:
        # Подключаемся к серверу IMAP с использованием SSL и порта 993
        mail = imaplib.IMAP4_SSL(imap_server, 993)

        # Пытаемся войти
        mail.login(email_address, password)

        # Если дошли до этой точки, значит вход успешен
        mail.logout()
        return True, "Подключение к почте успешно установлено"

    except imaplib.IMAP4.error as e:
        return False, f"Ошибка аутентификации: {str(e)}"
    except Exception as e:
        return False, f"Ошибка подключения: {str(e)}"