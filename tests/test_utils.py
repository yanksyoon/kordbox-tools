"""Tests for src.utils."""

import platform
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils import (
    FFmpegNotFoundError,
    find_binary,
    format_duration,
    format_size,
    normalise_model_name,
    get_display_model_name,
)


class TestFormatDuration:
    def test_zero(self):
        assert format_duration(0) == "0:00"

    def test_seconds_only(self):
        assert format_duration(45) == "0:45"

    def test_minutes_seconds(self):
        assert format_duration(185) == "3:05"

    def test_hours_minutes_seconds(self):
        assert format_duration(3661) == "1:01:01"

    def test_negative(self):
        assert format_duration(-10) == "0:00"


class TestFormatSize:
    def test_bytes(self):
        assert format_size(500) == "500 B"

    def test_kilobytes(self):
        assert format_size(1536) == "1.5 KB"

    def test_megabytes(self):
        assert format_size(5_242_880) == "5.0 MB"

    def test_gigabytes(self):
        assert format_size(5_368_709_120) == "5.0 GB"


class TestNormaliseModelName:
    def test_lowercase(self):
        assert normalise_model_name("CDJ-3000") == "cdj-3000"

    def test_spaces_to_dashes(self):
        assert normalise_model_name("cdj 3000") == "cdj-3000"

    def test_underscores_to_dashes(self):
        assert normalise_model_name("cdj_3000") == "cdj-3000"


class TestGetDisplayModelName:
    def test_known_model(self):
        assert get_display_model_name("cdj-3000") == "CDJ-3000"
        assert get_display_model_name("cdj-2000nxs2") == "CDJ-2000NXS2"

    def test_unknown_key(self):
        assert get_display_model_name("unknown") == "UNKNOWN"


class TestFindBinary:
    def test_not_found_raises(self):
        with patch("src.utils.shutil.which", return_value=None):
            # Force no bundled binary
            with patch("src.utils.Path.exists", return_value=False):
                with pytest.raises(FFmpegNotFoundError):
                    find_binary("nonexistent_tool_xyz")
