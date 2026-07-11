import json
import stat
from pathlib import Path
from unittest.mock import patch

from main import write_json_atomic


def test_write_json_atomic_replaces_existing_file_without_leaving_temporary_files(
    tmp_path,
):
    output = tmp_path / "report.json"
    output.write_text('{"stale": true}\n', encoding="utf-8")
    real_replace = Path.replace

    with patch.object(Path, "replace", autospec=True, side_effect=real_replace) as replace:
        write_json_atomic({"complete": True}, output)

    assert json.loads(output.read_text(encoding="utf-8")) == {"complete": True}
    assert replace.call_count == 1
    assert replace.call_args.args[1] == output
    assert list(tmp_path.glob(".report.json.*.tmp")) == []


def test_write_json_atomic_preserves_existing_file_mode(tmp_path):
    output = tmp_path / "private-report.json"
    output.write_text('{"stale": true}\n', encoding="utf-8")
    output.chmod(0o640)

    write_json_atomic({"complete": True}, output)

    assert stat.S_IMODE(output.stat().st_mode) == 0o640
