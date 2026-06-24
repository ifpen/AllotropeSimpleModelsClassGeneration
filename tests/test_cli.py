"""Tests for :mod:`allotrope_gen.cli`."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from allotrope_gen.cli import _build_parser, _validate_args, main
from allotrope_gen.config import LANGUAGES, SPECS


class TestCli:
    def test_build_parser_defaults(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.specs == list(SPECS)
        assert args.langs == list(LANGUAGES)
        assert args.dry_run is False
        assert args.no_clean is False
        assert args.commons_only is False

    def test_validate_args_valid(self):
        parser = _build_parser()
        args = parser.parse_args(["--specs", "gc", "--langs", "java"])
        assert _validate_args(args) == 0

    def test_validate_args_invalid_spec(self, capsys: pytest.CaptureFixture[str]):
        parser = _build_parser()
        args = parser.parse_args(["--specs", "invalid_spec"])
        assert _validate_args(args) == 1
        captured = capsys.readouterr()
        assert "[ERROR] Unknown spec(s): ['invalid_spec']" in captured.err

    def test_validate_args_invalid_lang(self, capsys: pytest.CaptureFixture[str]):
        parser = _build_parser()
        args = parser.parse_args(["--langs", "invalid_lang"])
        assert _validate_args(args) == 1
        captured = capsys.readouterr()
        assert "[ERROR] Unknown language(s): ['invalid_lang']" in captured.err

    def test_list_specs(self, capsys: pytest.CaptureFixture[str]):
        rc = main(["--list-specs"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "gc" in captured.out

    def test_list_langs(self, capsys: pytest.CaptureFixture[str]):
        rc = main(["--list-langs"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "java" in captured.out
        assert "python" in captured.out

    def test_invalid_args_exits_early(self):
        with patch("allotrope_gen.cli.generate_commons") as mock_commons:
            rc = main(["--specs", "invalid_spec"])
            assert rc == 1
            mock_commons.assert_not_called()

    @patch("allotrope_gen.cli.generate_commons", return_value=True)
    @patch("allotrope_gen.cli.generate_specs", return_value=True)
    def test_main_success(self, mock_specs: MagicMock, mock_commons: MagicMock):
        rc = main(["--specs", "gc", "--langs", "java", "--dry-run"])
        assert rc == 0
        mock_commons.assert_called_once_with(["java"], dry_run=True, no_clean=False)
        mock_specs.assert_called_once_with(["gc"], ["java"], dry_run=True, no_clean=False)

    @patch("allotrope_gen.cli.generate_commons", return_value=False)
    @patch("allotrope_gen.cli.generate_specs", return_value=True)
    def test_main_commons_failure(self, mock_specs: MagicMock, mock_commons: MagicMock):
        rc = main([])
        assert rc == 1

    @patch("allotrope_gen.cli.generate_commons", return_value=True)
    @patch("allotrope_gen.cli.generate_specs", return_value=False)
    def test_main_specs_failure(self, mock_specs: MagicMock, mock_commons: MagicMock):
        rc = main([])
        assert rc == 1

    @patch("allotrope_gen.cli.generate_commons", return_value=True)
    @patch("allotrope_gen.cli.generate_specs", return_value=True)
    def test_main_commons_only(self, mock_specs: MagicMock, mock_commons: MagicMock):
        rc = main(["--commons-only"])
        assert rc == 0
        mock_commons.assert_called_once()
        mock_specs.assert_not_called()
