class StatusCodeError(Exception):
    """Код запроса отличается."""
    pass


class TokenError(Exception):
    """Ошибка в токенах."""
    pass