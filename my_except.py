class ServerError(Exception):
    def __init__(self, text='Ошибка сервера'):
        self.txt = text