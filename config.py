import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Не задана переменная {name} (см. .env.example)")
    return value


BOT_TOKEN = _require("BOT_TOKEN")
ALLOWED_USER_ID = int(_require("ALLOWED_USER_ID"))
