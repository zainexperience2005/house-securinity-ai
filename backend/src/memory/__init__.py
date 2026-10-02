"""src/memory - Short-term and Long-term Scrutiny Memory Package.

Provides:
- Short-term Memory: Thread-scoped checkpointing backed by Neon PostgreSQL (PostgresSaver).
  Each PDF scrutiny runs in an isolated thread_id with full node state preservation.
- Long-term Memory: Cross-thread submission registry, drawing precedents, and audit history.
  (User preferences are intentionally excluded to keep submissions independent).
"""

from src.memory.database import (
    get_database_url,
    get_db_connection,
    init_database_tables,
    run_migrations,
)
from src.memory.long_term import (
    delete_thread,
    find_related_submissions,
    get_chat_messages,
    get_thread_record,
    list_all_threads,
    save_chat_message,
    save_thread_scrutiny,
)
from src.memory.models_store import (
    add_model,
    delete_model,
    get_default_model,
    get_model,
    init_models_table,
    list_models,
    list_providers,
    seed_default_models,
    set_default_model,
)
from src.memory.short_term import (
    generate_thread_id,
    get_checkpointer,
    get_thread_checkpoint_history,
    get_thread_state,
)

__all__ = [
    "add_model",
    "delete_model",
    "delete_thread",
    "find_related_submissions",
    "generate_thread_id",
    "get_chat_messages",
    "get_checkpointer",
    "get_database_url",
    "get_db_connection",
    "get_default_model",
    "get_model",
    "get_thread_checkpoint_history",
    "get_thread_record",
    "get_thread_state",
    "init_database_tables",
    "init_models_table",
    "list_all_threads",
    "list_models",
    "list_providers",
    "run_migrations",
    "save_chat_message",
    "save_thread_scrutiny",
    "seed_default_models",
    "set_default_model",
]
