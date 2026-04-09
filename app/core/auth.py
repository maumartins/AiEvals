"""Preparacao minima para futura autenticacao."""

from dataclasses import dataclass


@dataclass
class AuthContext:
    user_id: str = "local-user"
    is_authenticated: bool = False
    auth_mode: str = "disabled"


def get_auth_context() -> AuthContext:
    """Stub atual do MVP.

    O laboratorio roda sem autenticacao, mas a dependencia pode ser
    substituida futuramente por sessao, SSO ou API key interna.
    """
    return AuthContext()
