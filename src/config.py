import logging
import os
from pydantic_settings import BaseSettings

logger = logging.getLogger("crm.config")


def load_dotenv(path: str | None = None) -> int:
    """Load secrets from a .env file into os.environ on startup.

    - The file location defaults to ``CRM_ENV_FILE`` if set, otherwise ``.env``
      in the current working directory (the project root).
    - A missing file is not an error — the function is a no-op and returns 0.
    - Existing environment variables are never overwritten, so values exported
      in the shell or injected by CI always win over the file.
    - Lines may use ``KEY=VALUE``, an optional leading ``export``, ``#`` comments,
      blank lines, and single- or double-quoted values.

    Returns the number of variables loaded from the file.
    """
    env_path = path or os.environ.get("CRM_ENV_FILE", ".env")
    if not os.path.isfile(env_path):
        return 0

    loaded = 0
    with open(env_path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if not key:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            if key in os.environ:
                # Shell / CI value takes precedence over the file.
                continue
            os.environ[key] = value
            loaded += 1

    logger.info("Loaded %d secret(s) from %s", loaded, env_path)
    return loaded


class Settings:
    """Lazy-loaded settings to prevent import-time failures."""
    
    @property
    def CRM_PORT(self) -> int:
        return int(os.environ.get("CRM_PORT", "8000"))

    @property
    def CRM_DB_PATH(self) -> str:
        return os.environ.get("CRM_DB_PATH", "crm.db")

    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite:///{self.CRM_DB_PATH}"

settings = Settings()