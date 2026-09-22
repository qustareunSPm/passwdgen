import asyncio
import base64
import contextlib
import json
import os

_lock = asyncio.Lock()


class VaultError(Exception):
    pass


async def _bw(creds: dict, *args: str, session: str | None = None) -> str:
    env = {
        **os.environ,
        "BW_NOINTERACTION": "true",
        "BW_CLIENTID": creds["client_id"],
        "BW_CLIENTSECRET": creds["client_secret"],
        "BW_PASSWORD": creds["password"],
    }
    if session:
        env["BW_SESSION"] = session

    proc = await asyncio.create_subprocess_exec(
        "bw",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        proc.kill()
        raise VaultError(f"bw {args[0]}: таймаут")

    if proc.returncode != 0:
        raise VaultError(f"bw {args[0]}: {err.decode().strip()}")
    return out.decode().strip()


async def _login_and_unlock(creds: dict, relogin: bool = False) -> str:
    if relogin:
        # сбрасываем старый вход, чтобы применились новые сервер и ключи
        with contextlib.suppress(VaultError):
            await _bw(creds, "logout")

    status = json.loads(await _bw(creds, "status"))["status"]
    if status == "unauthenticated":
        await _bw(creds, "config", "server", creds["server"])
        await _bw(creds, "login", "--apikey")
    return await _bw(creds, "unlock", "--passwordenv", "BW_PASSWORD", "--raw")


async def verify(creds: dict) -> None:
    """Проверяет сервер, API-ключ и мастер-пароль."""
    async with _lock:
        await _login_and_unlock(creds, relogin=True)


async def add_login(creds: dict, name: str, password: str) -> None:
    """Создаёт запись типа Login в Vaultwarden через Bitwarden CLI."""
    item = {
        "organizationId": None,
        "collectionIds": None,
        "folderId": None,
        "type": 1,
        "name": name,
        "notes": "Создано Telegram-ботом",
        "favorite": False,
        "fields": [],
        "login": {"uris": [], "username": None, "password": password, "totp": None},
        "reprompt": 0,
    }
    encoded = base64.b64encode(json.dumps(item).encode()).decode()

    async with _lock:
        session = await _login_and_unlock(creds)
        await _bw(creds, "create", "item", encoded, session=session)
