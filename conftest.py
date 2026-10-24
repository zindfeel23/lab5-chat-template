"""Готовые фикстуры. Автопроверка использует исходную копию этого файла."""
import importlib
import json
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption("--impl", default="solution", help="модуль проверяемой реализации")


@pytest.fixture
def impl(request):
    return importlib.import_module(request.config.getoption("--impl"))


@pytest.fixture
def state():
    """Каждый тест получает новые словари и списки."""
    return json.loads(Path(__file__).with_name("world.json").read_text(encoding="utf-8"))


@pytest.fixture
def log():
    return []
