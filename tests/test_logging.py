"""Testes de redaction de dados sensíveis nos logs."""

import pytest

from app.core.logging import redact


class TestRedaction:
    def test_redacts_openai_key(self):
        text = "Usando api_key sk-abc123def456ghi789jkl012 para autenticar"
        result = redact(text)
        assert "sk-abc123" not in result
        assert "[REDACTED_API_KEY]" in result

    def test_redacts_email(self):
        text = "Contato: usuario@exemplo.com.br"
        result = redact(text)
        assert "usuario@exemplo.com.br" not in result
        assert "[REDACTED_EMAIL]" in result

    def test_redacts_api_key_in_json(self):
        text = '{"api_key": "minha-chave-secreta-123"}'
        result = redact(text)
        assert "minha-chave-secreta-123" not in result
        assert "[REDACTED]" in result

    def test_redacts_password_in_json(self):
        text = '{"password": "senha_super_secreta"}'
        result = redact(text)
        assert "senha_super_secreta" not in result
        assert "[REDACTED]" in result

    def test_preserves_normal_text(self):
        text = "Esta é uma mensagem normal sem dados sensíveis"
        result = redact(text)
        assert result == text

    def test_redacts_anthropic_key(self):
        text = "Key: sk-ant-api03-xyzabc123def456ghi789jkl012mno345pqr"
        result = redact(text)
        assert "sk-ant-api03" not in result
        assert "[REDACTED_API_KEY]" in result

    def test_redacts_secret_in_json(self):
        text = '{"secret": "valor_secreto_importante"}'
        result = redact(text)
        assert "valor_secreto_importante" not in result
