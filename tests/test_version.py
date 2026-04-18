"""
Testes para o módulo app — versão e imports básicos.
"""

import re


def test_version_exists():
    """Verifica que __version__ está definido."""
    from app import __version__
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_format():
    """Verifica que __version__ segue o formato semver (X.Y.Z)."""
    from app import __version__
    pattern = r"^\d+\.\d+\.\d+$"
    assert re.match(pattern, __version__), (
        f"Versão '{__version__}' não segue o formato X.Y.Z"
    )
