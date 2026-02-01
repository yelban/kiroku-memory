"""SurrealDB backend for Kiroku Memory"""

from .connection import (
    get_surreal_connection,
    init_surreal_db,
    close_surreal_db,
    SurrealConnection,
)

__all__ = [
    "get_surreal_connection",
    "init_surreal_db",
    "close_surreal_db",
    "SurrealConnection",
]
