from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.main import app, get_db

# testler gerçek benchlog.db yerine bellekteki geçici veritabanını kullanır
engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
Base.metadata.create_all(engine)
TestSession = sessionmaker(bind=engine, autoflush=False)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_create_and_get_run():
    r = client.post("/api/runs", json={"bits": 14, "seed": 3})
    assert r.status_code == 201
    run = r.json()
    assert run["status"] in ("pass", "fail")
    assert run["enob"] > 10

    r2 = client.get(f"/api/runs/{run['id']}")
    assert r2.status_code == 200
    assert r2.json()["id"] == run["id"]


def test_list_runs_newest_first():
    a = client.post("/api/runs", json={"seed": 1}).json()
    b = client.post("/api/runs", json={"seed": 2}).json()
    ids = [x["id"] for x in client.get("/api/runs").json()]
    assert ids.index(b["id"]) < ids.index(a["id"])


def test_fin_above_nyquist_is_rejected():
    r = client.post("/api/runs", json={"fs_mhz": 100, "fin_mhz": 60})
    assert r.status_code == 422


def test_delete_run():
    run = client.post("/api/runs", json={}).json()
    assert client.delete(f"/api/runs/{run['id']}").status_code == 204
    assert client.get(f"/api/runs/{run['id']}").status_code == 404


def test_spectrum_endpoint():
    run = client.post("/api/runs", json={"seed": 5}).json()
    r = client.get(f"/api/runs/{run['id']}/spectrum")
    assert r.status_code == 200
    body = r.json()
    assert len(body["dbfs"]) == 2048
    assert max(body["dbfs"][1:]) <= 0.5   # tam ölçeğin üstüne çıkmamalı