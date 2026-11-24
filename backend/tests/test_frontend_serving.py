"""Single-service deployment: the backend serves the built React app."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import mount_frontend


def _client(tmp_path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app shell</html>")
    (dist / "assets" / "app.js").write_text("console.log('ok')")
    (tmp_path / "secret.txt").write_text("outside the build folder")
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    mount_frontend(app, dist)
    return TestClient(app)


def test_serves_index_assets_and_spa_routes(tmp_path):
    client = _client(tmp_path)
    assert client.get("/").text == "<html>app shell</html>"
    assert client.get("/workflow").text == "<html>app shell</html>"  # React Router path
    asset = client.get("/assets/app.js")
    assert asset.text == "console.log('ok')"
    assert "immutable" in asset.headers["cache-control"]


def test_api_routes_win_and_unknown_api_paths_404(tmp_path):
    client = _client(tmp_path)
    assert client.get("/api/ping").json() == {"ok": True}
    assert client.get("/api/does-not-exist").status_code == 404


def test_never_serves_files_outside_build_folder(tmp_path):
    client = _client(tmp_path)
    response = client.get("/..%2Fsecret.txt")
    assert "outside the build folder" not in response.text


def test_missing_build_is_ignored(tmp_path):
    app = FastAPI()
    mount_frontend(app, tmp_path / "missing")
    assert TestClient(app).get("/").status_code == 404
