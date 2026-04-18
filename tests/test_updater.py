"""
Testes para o módulo updater — parsing de versão e configuração.
"""

from app.core.updater import (
    _parse_version,
    GITHUB_OWNER,
    GITHUB_REPO,
    GITHUB_API_URL,
)


class TestParseVersion:
    """Testes para a função _parse_version."""

    def test_basic_version(self):
        assert _parse_version("v1.2.3") == (1, 2, 3)

    def test_without_v_prefix(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_uppercase_v(self):
        assert _parse_version("V1.2.3") == (1, 2, 3)

    def test_zero_version(self):
        assert _parse_version("v0.0.0") == (0, 0, 0)

    def test_large_numbers(self):
        assert _parse_version("v10.20.300") == (10, 20, 300)

    def test_two_parts(self):
        assert _parse_version("v1.2") == (1, 2)

    def test_single_part(self):
        assert _parse_version("v5") == (5,)

    def test_invalid_parts_become_zero(self):
        assert _parse_version("v1.abc.3") == (1, 0, 3)

    def test_with_whitespace(self):
        assert _parse_version("  v1.2.3  ") == (1, 2, 3)

    def test_empty_string(self):
        result = _parse_version("")
        assert result == (0,)


class TestVersionComparison:
    """Testes para comparação de versões usando tuplas."""

    def test_newer_patch(self):
        assert _parse_version("v0.1.1") > _parse_version("v0.1.0")

    def test_newer_minor(self):
        assert _parse_version("v0.2.0") > _parse_version("v0.1.9")

    def test_newer_major(self):
        assert _parse_version("v1.0.0") > _parse_version("v0.99.99")

    def test_same_version(self):
        assert not (_parse_version("v1.0.0") > _parse_version("v1.0.0"))

    def test_older_version(self):
        assert not (_parse_version("v0.1.0") > _parse_version("v0.2.0"))

    def test_equality(self):
        assert _parse_version("v1.2.3") == _parse_version("1.2.3")


class TestGitHubConfig:
    """Testes para a configuração do GitHub."""

    def test_owner(self):
        assert GITHUB_OWNER == "clebersfonseca"

    def test_repo(self):
        assert GITHUB_REPO == "StreamDeckDIY"

    def test_api_url_format(self):
        assert GITHUB_API_URL.startswith("https://api.github.com/repos/")
        assert GITHUB_OWNER in GITHUB_API_URL
        assert GITHUB_REPO in GITHUB_API_URL
        assert GITHUB_API_URL.endswith("/releases/latest")
