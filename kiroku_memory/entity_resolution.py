"""Entity resolution: normalize and canonicalize entity names"""

from __future__ import annotations

import re


def normalize_entity(text: str) -> str:
    """Basic normalization: lowercase, strip, collapse whitespace."""
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


BUILTIN_ALIASES: dict[str, str] = {
    # User self-references
    "我": "user",
    "i": "user",
    "me": "user",
    "myself": "user",
    "使用者": "user",
    "用戶": "user",
    "本人": "user",
    # Programming languages
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "rb": "ruby",
    "rs": "rust",
    # Common tools
    "vim": "neovim",
    "pg": "postgresql",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "tf": "terraform",
    "gh": "github",
    # OS
    "mac": "macos",
    "osx": "macos",
    "win": "windows",
}


def resolve_entity(text: str) -> str:
    """Normalize + alias lookup → canonical form."""
    normalized = normalize_entity(text)
    return BUILTIN_ALIASES.get(normalized, normalized)
