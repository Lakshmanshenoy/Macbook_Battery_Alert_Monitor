import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "release_smoke_test.py"


def _next_patch_version(version: str) -> str:
    cleaned = version.lower().strip().lstrip("v").split("-")[0]
    parts = []
    for token in cleaned.split("."):
        try:
            parts.append(int(token))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    parts[2] += 1
    return f"{parts[0]}.{parts[1]}.{parts[2]}"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("release_smoke_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_smoke_module_install_rumps_stub():
    module = _load_smoke_module()
    module.install_rumps_stub()

    assert "rumps" in sys.modules
    assert hasattr(sys.modules["rumps"], "App")


def test_smoke_script_main_passes(monkeypatch, tmp_path):
    module = _load_smoke_module()
    app_module, app = module.new_app()

    # Make the smoke test operate in a deterministic temp directory.
    app.config_dir = tmp_path
    app.config_file = tmp_path / "config.json"
    app.log_file = tmp_path / "alert_history.json"
    app.runtime_log_file = tmp_path / "logs" / "battery_alert.log"
    app.update_state_file = tmp_path / "update_state.json"

    app.config_file.write_text(json.dumps(app.settings, indent=2))
    app.log_file.write_text("[]")
    app.runtime_log_file.parent.mkdir(parents=True, exist_ok=True)
    app.runtime_log_file.write_text("runtime log line")

    next_version = _next_patch_version(app_module.APP_VERSION)
    monkeypatch.setattr(module, "new_app", lambda: (app_module, app))
    monkeypatch.setattr(
        app,
        "get_latest_release",
        lambda: {"version": next_version, "url": f"https://example.com/release/{next_version}"},
    )

    assert module.main() == 0
