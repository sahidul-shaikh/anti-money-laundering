"""The factory's GitHub identity: aml-factory-bot.

The bot can push branches and open pull requests. Branch protection means it
can never approve or merge one. Every use first proves the token belongs to
the bot, so a missing or wrong token fails loudly instead of quietly acting as
whoever is logged in to gh.
"""

from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path

LOGIN = "aml-factory-bot"
EMAIL = "27765017+aml-factory-bot@users.noreply.github.com"
TOKEN_FILE = Path.home() / ".aml-factory-bot" / "token.txt"


class NotTheBot(RuntimeError):
    """The token is missing or resolves to another account."""


def token(path: Path = TOKEN_FILE) -> str:
    """The bot token, stripped of whatever an editor wrapped around it."""
    if not path.exists():
        raise NotTheBot(f"no bot token at {path}")
    value = path.read_text(encoding="utf-8-sig").strip()
    if not value:
        raise NotTheBot(f"bot token at {path} is empty")
    return value


def gh_env(secret: str) -> dict[str, str]:
    """Environment that makes gh act as the token's owner."""
    return dict(os.environ, GH_TOKEN=secret)


def whoami(secret: str) -> str:
    """The GitHub login a token belongs to."""
    return subprocess.run(
        ["gh", "api", "user", "--jq", ".login"], env=gh_env(secret),
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def require_bot(secret: str) -> str:
    """The token unchanged, only if it belongs to the bot."""
    login = whoami(secret)
    if login != LOGIN:
        raise NotTheBot(f"token belongs to {login!r}, not {LOGIN!r}")
    return secret


def verified_token(path: Path = TOKEN_FILE) -> str:
    """The bot token from disk, proven to be the bot's."""
    return require_bot(token(path))


def git_env(secret: str) -> dict[str, str]:
    """Environment that makes git commit and push as the bot.

    The token travels in environment variables, never on the command line:
    a failed command's arguments end up in error messages and process lists,
    and the auth header is only base64, not encryption.
    """
    basic = base64.b64encode(f"x-access-token:{secret}".encode()).decode()
    config = {
        "credential.helper": "",
        "http.https://github.com/.extraheader": f"AUTHORIZATION: basic {basic}",
        "user.name": LOGIN,
        "user.email": EMAIL,
    }
    env = dict(os.environ, GIT_CONFIG_COUNT=str(len(config)))
    for n, (key, value) in enumerate(config.items()):
        env[f"GIT_CONFIG_KEY_{n}"] = key
        env[f"GIT_CONFIG_VALUE_{n}"] = value
    return env
