"""Point the app at a throwaway database before anything imports it.

`app.db` opens its file at import time, so this has to run first — conftest is
loaded before the test modules, which is exactly the hook needed.
"""

import os
import tempfile
from pathlib import Path

os.environ["HOUSETASKS_DB"] = str(Path(tempfile.gettempdir()) / "housetasks-test.db")

import pytest  # noqa: E402

from app import db  # noqa: E402


@pytest.fixture
def clean_db():
    db.execute("DELETE FROM tasks")
    db.execute("DELETE FROM task_log")
    yield db
