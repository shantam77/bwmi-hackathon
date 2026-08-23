from app.config import _normalize_database_url


def test_rewrites_postgresql_scheme_to_psycopg_dialect():
    raw = "postgresql://user:pass@host:5432/db"
    assert _normalize_database_url(raw) == "postgresql+psycopg://user:pass@host:5432/db"


def test_rewrites_legacy_postgres_scheme_to_psycopg_dialect():
    raw = "postgres://user:pass@host:5432/db"
    assert _normalize_database_url(raw) == "postgresql+psycopg://user:pass@host:5432/db"


def test_leaves_an_already_explicit_dialect_untouched():
    raw = "postgresql+psycopg://user:pass@host:5432/db"
    assert _normalize_database_url(raw) == raw


def test_empty_string_stays_empty():
    assert _normalize_database_url("") == ""
