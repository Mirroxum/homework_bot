class KeyMissError(Exception):
    """В ответе отсвутствуют нужные ключи"""
    pass

class JSONError(Exception):
    """Ошибка обработки JSON"""
    pass

class RequestError(Exception):
    """Ошибка Request"""
    pass

class HTTPStatusNotOK(Exception):
    """API вернул код отличный от 200"""
    pass

class TGError(Exception):
    """Ошибка пакета python-telegram-bot"""
    pass