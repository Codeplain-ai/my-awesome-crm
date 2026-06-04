import os

import pytest

from src.config import load_dotenv


@pytest.fixture
def clean_env(monkeypatch):
    for key in ("FOO", "BAR", "BAZ", "QUOTED", "CRM_ENV_FILE"):
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def test_loads_keys_from_file(tmp_path, clean_env):
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=one\nBAR=two\n")

    loaded = load_dotenv(str(env_file))

    assert loaded == 2
    assert os.environ["FOO"] == "one"
    assert os.environ["BAR"] == "two"


def test_missing_file_is_a_noop(tmp_path, clean_env):
    assert load_dotenv(str(tmp_path / "does-not-exist.env")) == 0


def test_shell_value_wins_over_file(tmp_path, clean_env):
    clean_env.setenv("FOO", "from-shell")
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=from-file\nBAR=two\n")

    loaded = load_dotenv(str(env_file))

    # FOO is already set, so only BAR is loaded; FOO keeps the shell value.
    assert loaded == 1
    assert os.environ["FOO"] == "from-shell"
    assert os.environ["BAR"] == "two"


def test_handles_comments_blanks_export_and_quotes(tmp_path, clean_env):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n"
        "# a comment\n"
        "export FOO=one\n"
        '   BAR = "two"  \n'
        "BAZ='three'\n"
        "QUOTED=\n"
    )

    loaded = load_dotenv(str(env_file))

    assert loaded == 4
    assert os.environ["FOO"] == "one"
    assert os.environ["BAR"] == "two"
    assert os.environ["BAZ"] == "three"
    assert os.environ["QUOTED"] == ""


def test_respects_crm_env_file_override(tmp_path, clean_env):
    env_file = tmp_path / "custom.env"
    env_file.write_text("FOO=custom\n")
    clean_env.setenv("CRM_ENV_FILE", str(env_file))

    assert load_dotenv() == 1
    assert os.environ["FOO"] == "custom"
