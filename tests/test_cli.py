from pathlib import Path
import json

import pytest

pytest.importorskip("typer")
pytest.importorskip("PIL")
pytest.importorskip("imageio.v3")
pytest.importorskip("numpy")

from typer.testing import CliRunner
from goldman_video.cli import app


runner = CliRunner()


def test_multishot_invalid_transition_returns_friendly_error(tmp_path: Path):
    spec = tmp_path / "shots.json"
    spec.write_text(json.dumps({
        "shots": [
            {"prompt": "one", "transition": "fade"}
        ]
    }))

    result = runner.invoke(app, ["multishot", str(spec)])

    assert result.exit_code != 0
    assert "Invalid shot spec" in result.stdout
    assert "transition" in result.stdout
