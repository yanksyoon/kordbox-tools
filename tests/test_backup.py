"""Tests for src.backup."""

import os
import tempfile
from pathlib import Path

from src.backup import (
    BackupReport,
    PlaylistTrack,
    backup_tracks,
    find_track,
    parse_m3u8,
    parse_playlist,
    parse_txt_playlist,
    resolve_tracks,
    _safe_dirname,
    _unique_path,
)


def _tmp_dir() -> str:
    return tempfile.mkdtemp()


def _tmp_file(name: str, content: bytes = b"", base: str | None = None) -> str:
    d = base or _tmp_dir()
    p = Path(d) / name
    p.write_bytes(content)
    return str(p)


def _write_text(name: str, content: str, base: str | None = None) -> str:
    d = base or _tmp_dir()
    p = Path(d) / name
    p.write_text(content)
    return str(p)


class TestParseM3u8:
    def test_empty_file(self):
        pl = _write_text("empty.m3u8", "")
        assert parse_m3u8(pl) == []

    def test_skips_comments(self):
        pl = _write_text("test.m3u8", "#EXTM3U\n#EXTINF:180,Artist - Title\n/track01.wav\n")
        tracks = parse_m3u8(pl)
        assert tracks == ["/track01.wav"]

    def test_multiple_tracks(self):
        pl = _write_text(
            "test.m3u8",
            "#EXTM3U\n"
            "#EXTINF:180,Track One\n/track01.wav\n"
            "#EXTINF:200,Track Two\n/track02.flac\n",
        )
        tracks = parse_m3u8(pl)
        assert len(tracks) == 2
        assert "/track01.wav" in tracks
        assert "/track02.flac" in tracks


class TestParseTxtPlaylist:
    def test_skips_header(self):
        pl = _write_text("test.txt", "#\tArtwork\tBPM\tTitle\tKey\tTime\tGenre\tArtist\tAlbum\tRating\tDate\n")
        assert parse_txt_playlist(pl) == []

    def test_parses_track_title(self):
        pl = _write_text(
            "test.txt",
            "1\timg\t120\tMy Track\tAm\t03:45\tHouse\tDJ\tAlbum\t5\t2024-01-01\n"
        )
        tracks = parse_txt_playlist(pl)
        assert tracks == ["My Track"]


class TestParsePlaylist:
    def test_auto_detect_m3u8(self):
        pl = _write_text("test.m3u8", "#EXTM3U\n/track.wav\n")
        assert parse_playlist(pl) == ["/track.wav"]

    def test_auto_detect_txt(self):
        pl = _write_text("test.txt", "1\t\t120\tTrack Title\t\t\t\t\t\t\t\n")
        tracks = parse_playlist(pl)
        assert tracks == ["Track Title"]


class TestFindTrack:
    def test_absolute_path_exists(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            result = find_track(f.name, ["/nonexistent"])
            assert result == f.name

    def test_exact_match_in_search_dir(self):
        d = _tmp_dir()
        music_dir = Path(d) / "music"
        music_dir.mkdir()
        (music_dir / "track01.wav").write_bytes(b"audio")

        result = find_track("some/path/track01.wav", [str(music_dir)])
        assert result is not None
        assert Path(result).name == "track01.wav"

    def test_not_found(self):
        result = find_track("nonexistent_track_xyz.wav", ["/nonexistent"])
        assert result is None


class TestResolveTracks:
    def test_resolves_found_and_missing(self):
        d = _tmp_dir()
        music_dir = Path(d) / "music"
        music_dir.mkdir()
        (music_dir / "found.wav").write_bytes(b"audio")

        raw = ["found.wav", "missing.flac"]
        tracks = resolve_tracks(raw, [str(music_dir)])

        assert len(tracks) == 2
        assert tracks[0].exists is True
        assert tracks[1].exists is False


class TestBackupTracks:
    def test_copies_found_tracks(self):
        src = _tmp_dir()
        Path(src, "track01.wav").write_bytes(b"audio data here")

        out = _tmp_dir()

        tracks = [
            PlaylistTrack(
                original_path="track01.wav",
                found_path=str(Path(src, "track01.wav")),
                exists=True,
            ),
            PlaylistTrack(
                original_path="missing.flac",
                found_path=None,
                exists=False,
            ),
        ]

        report = backup_tracks(tracks, out)

        assert report.copied == 1
        assert report.missing == 1
        assert Path(out, "track01.wav").exists()

    def test_skip_existing(self):
        src = _tmp_dir()
        Path(src, "track.wav").write_bytes(b"same")

        out = _tmp_dir()
        Path(out, "track.wav").write_bytes(b"same")  # already identical

        tracks = [
            PlaylistTrack(
                original_path="track.wav",
                found_path=str(Path(src, "track.wav")),
                exists=True,
            ),
        ]

        report = backup_tracks(tracks, out, skip_existing=True)
        assert report.skipped == 1
        assert report.copied == 0


class TestHelpers:
    def test_safe_dirname(self):
        assert _safe_dirname("My Playlist") == "My Playlist"
        assert "/" not in _safe_dirname("with/slash")

    def test_unique_path(self):
        d = _tmp_dir()
        base = Path(d)
        (base / "file.wav").write_bytes(b"x")
        result = _unique_path(base, "file", ".wav")
        assert result == base / "file_1.wav"

    def test_backup_report_defaults(self):
        report = BackupReport()
        assert report.total == 0
        assert report.copied == 0
        assert report.missing_log == []
