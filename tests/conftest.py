"""Configuração global dos testes."""

import os

# Força uso de banco em memória e provider mock nos testes
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEFAULT_PROVIDER", "mock")
os.environ.setdefault("JUDGE_PROVIDER", "mock")
os.environ.setdefault("JUDGE_MODEL", "mock")
