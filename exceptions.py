class StatusCodeError(Exception):
    """Код запроса отличается."""
    pass


class TokenError(Exception):
    """Oшибка переменных окружения."""
    pass
