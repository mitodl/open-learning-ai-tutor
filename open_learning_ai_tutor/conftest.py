import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """Start each test without LangSmith, and undo its os.environ changes."""
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    with patch.dict(os.environ):
        yield
