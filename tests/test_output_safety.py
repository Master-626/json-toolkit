import errno
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from json_toolkit import core


@pytest.fixture(params=[core.format_json, core.minify_json], ids=["format", "minify"])
def transform(request):
    return request.param


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "source.json"
    path.write_text('{"z":1,"a":{"z":2,"a":3},"text":"你好"}', encoding="utf-8")
    return path


def assert_no_temporary_files(tmp_path):
    assert list(tmp_path.rglob(".json-toolkit-*.tmp")) == []


def test_new_output_and_parents(transform, source, tmp_path):
    output = tmp_path / "new" / "中文.json"
    original = source.read_bytes()
    result = transform(str(source), str(output))
    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(original)
    assert "你好" in output.read_text(encoding="utf-8")
    assert source.read_bytes() == original
    if transform is core.minify_json:
        assert result == len(output.read_bytes())
        assert b"\n" not in output.read_bytes()
    assert_no_temporary_files(tmp_path)


@pytest.mark.parametrize("original", [b"KEEP ORIGINAL", b""])
def test_existing_output_is_never_overwritten(transform, source, tmp_path, original):
    output = tmp_path / "output.json"
    output.write_bytes(original)
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        transform(str(source), str(output))
    assert output.read_bytes() == original
    assert_no_temporary_files(tmp_path)


def test_input_output_same_path(transform, source, tmp_path):
    original = source.read_bytes()
    with pytest.raises(FileExistsError):
        transform(str(source), str(source))
    assert source.read_bytes() == original
    assert_no_temporary_files(tmp_path)


def test_relative_alias(transform, source, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = source.read_bytes()
    with pytest.raises(FileExistsError):
        transform(str(source), "./source.json")
    assert source.read_bytes() == original
    assert_no_temporary_files(tmp_path)


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "broken_symlink"])
def test_output_links_are_preserved(transform, source, tmp_path, kind):
    output = tmp_path / "output.json"
    target = tmp_path / "missing.json" if kind == "broken_symlink" else source
    original = source.read_bytes()
    try:
        if kind == "hardlink":
            os.link(str(target), str(output))
        else:
            output.symlink_to(target)
    except (NotImplementedError, OSError) as error:
        pytest.skip("Links unavailable: {}".format(error))
    original_link_target = os.readlink(str(output)) if kind != "hardlink" else None
    with pytest.raises(FileExistsError):
        transform(str(source), str(output))
    assert source.read_bytes() == original
    if kind == "hardlink":
        assert os.path.samefile(str(output), str(source))
    else:
        assert output.is_symlink()
        assert os.readlink(str(output)) == original_link_target
    if kind == "broken_symlink":
        assert not target.exists()
    assert_no_temporary_files(tmp_path)


def test_directory_alias_to_input(transform, source, tmp_path):
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(tmp_path, target_is_directory=True)
    except (NotImplementedError, OSError) as error:
        pytest.skip("Symlinks unavailable: {}".format(error))
    original = source.read_bytes()
    with pytest.raises(FileExistsError):
        transform(str(source), str(alias / source.name))
    assert source.read_bytes() == original
    assert_no_temporary_files(tmp_path)


def test_existing_directory_is_preserved(transform, source, tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    child = output / "keep.txt"
    child.write_bytes(b"KEEP")
    with pytest.raises(FileExistsError):
        transform(str(source), str(output))
    assert child.read_bytes() == b"KEEP"
    assert_no_temporary_files(tmp_path)


def test_existing_fifo_is_preserved(transform, source, tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO is not available")
    output = tmp_path / "fifo"
    os.mkfifo(str(output))
    original_mode = output.stat().st_mode
    with pytest.raises(FileExistsError):
        transform(str(source), str(output))
    assert output.stat().st_mode == original_mode
    assert_no_temporary_files(tmp_path)


@pytest.mark.parametrize("content", [b"{invalid", b"\xff", b'"\\ud800"'])
def test_invalid_input_leaves_no_output(transform, tmp_path, content):
    source = tmp_path / "source.json"
    source.write_bytes(content)
    output = tmp_path / "new" / "output.json"
    with pytest.raises((ValueError, UnicodeError)):
        transform(str(source), str(output))
    assert source.read_bytes() == content
    assert not output.parent.exists()
    assert_no_temporary_files(tmp_path)


def test_missing_input_leaves_no_output(transform, tmp_path):
    with pytest.raises(FileNotFoundError):
        transform(str(tmp_path / "missing.json"), str(tmp_path / "new" / "out.json"))
    assert not (tmp_path / "new").exists()


def test_fsync_failure_leaves_no_output(transform, source, tmp_path, monkeypatch):
    output = tmp_path / "output.json"

    def fail(fd):
        raise OSError(errno.EIO, "injected sync failure")

    monkeypatch.setattr(core.os, "fsync", fail)
    with pytest.raises(OSError, match="injected sync failure"):
        transform(str(source), str(output))
    assert not output.exists()
    assert_no_temporary_files(tmp_path)


def test_partial_write_failure_leaves_no_output(transform, source, tmp_path, monkeypatch):
    output = tmp_path / "output.json"
    real_temporary = core.tempfile.NamedTemporaryFile

    class FailingWrite:
        def __init__(self, **kwargs):
            self.file = real_temporary(**kwargs)
            self.name = self.file.name

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.file.__exit__(*args)

        def write(self, data):
            self.file.write(data[:3])
            raise OSError(errno.ENOSPC, "injected full disk")

    monkeypatch.setattr(core.tempfile, "NamedTemporaryFile", FailingWrite)
    with pytest.raises(OSError, match="injected full disk"):
        transform(str(source), str(output))
    assert not output.exists()
    assert_no_temporary_files(tmp_path)


def test_publish_failure_is_safe(transform, source, tmp_path, monkeypatch):
    output = tmp_path / "output.json"

    def fail(src, dst):
        assert Path(src).read_bytes()
        assert not Path(dst).exists()
        raise OSError(errno.EPERM, "hard links unavailable")

    monkeypatch.setattr(core.os, "link", fail)
    with pytest.raises(OSError, match="hard links unavailable"):
        transform(str(source), str(output))
    assert not output.exists()
    assert_no_temporary_files(tmp_path)


@pytest.mark.parametrize("competitor", ["file", "symlink"])
def test_destination_created_during_write_is_preserved(
    transform, source, tmp_path, monkeypatch, competitor
):
    output = tmp_path / "output.json"
    real_link = os.link
    original = source.read_bytes()

    def raced_link(src, dst):
        if competitor == "file":
            Path(dst).write_bytes(b"RACE WINNER")
        else:
            try:
                Path(dst).symlink_to(source)
            except (NotImplementedError, OSError) as error:
                pytest.skip("Symlinks unavailable: {}".format(error))
        real_link(src, dst)

    monkeypatch.setattr(core.os, "link", raced_link)
    with pytest.raises(FileExistsError):
        transform(str(source), str(output))
    assert source.read_bytes() == original
    if competitor == "file":
        assert output.read_bytes() == b"RACE WINNER"
    else:
        assert output.is_symlink()
    assert_no_temporary_files(tmp_path)


def test_two_concurrent_writers_publish_one_complete_file(tmp_path, monkeypatch):
    barrier = Barrier(2)
    output = tmp_path / "output.json"
    real_link = os.link

    def synchronized_link(src, dst):
        barrier.wait(timeout=10)
        real_link(src, dst)

    def write(value):
        try:
            core.write_json(output, {"value": value})
            return "success"
        except FileExistsError:
            return "exists"

    monkeypatch.setattr(core.os, "link", synchronized_link)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(write, ["a" * 10000, "b" * 10000]))
    assert sorted(results) == ["exists", "success"]
    assert json.loads(output.read_text()) in [{"value": "a" * 10000}, {"value": "b" * 10000}]
    assert_no_temporary_files(tmp_path)


@pytest.mark.parametrize("sort_keys", [False, True])
def test_sort_keys_applies_to_nested_objects_and_lists(tmp_path, sort_keys):
    source = tmp_path / "input.json"
    output = tmp_path / "output.json"
    source.write_text('{"z":{"z":1,"a":2},"a":[{"z":3,"a":4}]}')
    core.format_json(str(source), str(output), indent=4, sort_keys=sort_keys)
    data = json.loads(output.read_text())
    expected = ["a", "z"] if sort_keys else ["z", "a"]
    assert list(data) == expected
    assert list(data["z"]) == expected
    assert list(data["a"][0]) == expected
    assert '\n    "' in output.read_text()


def test_write_json_helper_refuses_overwrite(tmp_path):
    output = tmp_path / "output.json"
    output.write_bytes(b"KEEP")
    with pytest.raises(FileExistsError):
        core.write_json(output, {"new": True})
    assert output.read_bytes() == b"KEEP"
    assert_no_temporary_files(tmp_path)


def test_write_json_serialization_failure_is_safe(tmp_path):
    output = tmp_path / "new" / "output.json"
    with pytest.raises(TypeError):
        core.write_json(output, {"not_serializable": object()})
    assert not output.parent.exists()


def test_write_json_helper_sorts(tmp_path):
    output = tmp_path / "output.json"
    core.write_json(output, {"z": 1, "a": 2}, sort_keys=True)
    assert list(json.loads(output.read_text())) == ["a", "z"]


@pytest.mark.parametrize("publish_succeeds", [True, False])
def test_cleanup_failure_preserves_publication_result(
    transform, source, tmp_path, monkeypatch, caplog, publish_succeeds
):
    output = tmp_path / "output.json"
    real_unlink = Path.unlink

    def fail_cleanup(path, *args, **kwargs):
        if path.name.startswith(".json-toolkit-"):
            raise PermissionError("injected cleanup failure")
        return real_unlink(path, *args, **kwargs)

    def fail_publish(src, dst):
        raise OSError(errno.EPERM, "injected publication failure")

    monkeypatch.setattr(Path, "unlink", fail_cleanup)
    if not publish_succeeds:
        monkeypatch.setattr(core.os, "link", fail_publish)
        with pytest.raises(OSError, match="injected publication failure"):
            transform(str(source), str(output))
        assert not output.exists()
        assert "Output not saved" in caplog.text
    else:
        transform(str(source), str(output))
        assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
            source.read_text(encoding="utf-8")
        )
        assert "Output saved to" in caplog.text
    assert "could not remove temporary file" in caplog.text
    leftovers = list(tmp_path.glob(".json-toolkit-*.tmp"))
    assert len(leftovers) == 1
    for leftover in leftovers:
        real_unlink(leftover)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_output_has_private_permissions(source, tmp_path, transform):
    output = tmp_path / "output.json"
    transform(str(source), str(output))
    assert output.stat().st_mode & 0o777 == 0o600
