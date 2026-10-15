import json

from examples.generate_hunter_demo import generate
from flip_core.auth_store import AuthStore
from universal_v2.hunter.__main__ import main
from universal_v2.hunter.bootstrap import main as bootstrap


def test_offline_cli_is_repeatable_and_does_not_send(tmp_path, capsys):
    config = generate(tmp_path)
    assert main(["--config", str(config), "validate"]) == 0
    assert not (tmp_path / "hunter.sqlite3").exists()
    capsys.readouterr()
    assert main(["--config", str(config), "scan"]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert sum(row["queued"] for row in rows) == 5
    assert main(["--config", str(config), "scan"]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert sum(row["queued"] for row in rows) == 0


def test_failed_source_has_nonzero_exit_code(tmp_path, capsys):
    config = generate(tmp_path)
    data = json.loads(config.read_text())
    data["sources"] = [{"platform": "OLX", "mode": "html"}]
    data["searches"] = [{**data["searches"][0], "platforms": ["OLX"]}]
    config.write_text(json.dumps(data))
    assert main(["--config", str(config), "scan"]) == 1
    assert "NETWORK_DISABLED" in capsys.readouterr().out


def test_bootstrap_keeps_password_out_of_output(tmp_path, capsys, monkeypatch):
    password = "safe-local-test-password-123"
    monkeypatch.setattr("getpass.getpass", lambda _: password)
    path = tmp_path / "auth.sqlite3"
    assert bootstrap(["--auth-db", str(path), "--username", "owner"]) == 0
    output = capsys.readouterr().out
    assert "owner_id:" in output and password not in output
    assert AuthStore(path).login("owner", password)["access_token"]
