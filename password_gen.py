import secrets
import string

PASSWORD_LENGTH = 12

LOWER = string.ascii_lowercase
UPPER = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS = "!@#$%^*-_+=?"


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    """Криптостойкий пароль: минимум по одному символу каждого типа."""
    pools = (LOWER, UPPER, DIGITS, SYMBOLS)
    if length < len(pools):
        raise ValueError("Слишком короткая длина пароля")

    chars = [secrets.choice(pool) for pool in pools]
    alphabet = "".join(pools)
    chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]

    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)
