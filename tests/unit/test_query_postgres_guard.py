"""The query_postgres tool must refuse anything that isn't a bare SELECT."""

from __future__ import annotations

import pytest

from multirag.agent.tools.query_postgres import _validate


def test_select_ok():
    out = _validate("SELECT 1")
    assert "LIMIT 100" in out


def test_with_ok():
    out = _validate("WITH x AS (SELECT 1) SELECT * FROM x")
    assert "LIMIT 100" in out


def test_existing_limit_is_preserved():
    out = _validate("SELECT * FROM orders LIMIT 5")
    assert "LIMIT 5" in out
    assert out.count("LIMIT") == 1


@pytest.mark.parametrize("sql", [
    "INSERT INTO orders VALUES (1)",
    "UPDATE orders SET total = 0",
    "DELETE FROM orders",
    "DROP TABLE orders",
    "ALTER TABLE orders ADD COLUMN x int",
    "TRUNCATE orders",
    "CREATE TABLE x (id int)",
    "GRANT ALL ON orders TO postgres",
    "COPY orders TO STDOUT",
])
def test_forbidden_verbs_rejected(sql: str):
    with pytest.raises(ValueError):
        _validate(sql)


def test_multi_statement_rejected():
    with pytest.raises(ValueError):
        _validate("SELECT 1; DROP TABLE orders")


def test_bare_string_rejected():
    with pytest.raises(ValueError):
        _validate("show tables")
