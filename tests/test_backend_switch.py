"""
Sprint 09 PR-A (web-only): /config/api/backend 切换测试

覆盖:
- GET 默认 (无 settings 记录) → mode=local
- PUT mode=cloud + dizical_url → 持久化, GET 读回
- PUT 非法 mode → 400
- PUT 带错误 PIN → 403 (dad_pin 已设置时)
- PUT 无 PIN → 403 (dad_pin 已设置时)
"""
import os
import tempfile
import sqlite3

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """临时 SQLite + 注入 app 模块 db, 返回 TestClient.

    P0-2026-08-05 修复: 用 monkeypatch 自动恢复 (db_module.db / app_module.db / settings.db_path).
    旧实现: 替换 db_module.db 后不恢复 → 全量跑时污染后续测试.
    """
    from src.database import Database
    from src.kid_app.app import app as fastapi_app
    from src import models
    import src.database as db_module
    import src.kid_app.app as app_module

    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.environ['DATABASE_URL'] = ''
    new_db = Database(db_path=path)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(models.settings, "db_path", path)
    monkeypatch.setattr(db_module, "db", new_db)
    monkeypatch.setattr(app_module, "db", new_db)

    with TestClient(fastapi_app) as c:
        yield c, new_db, path

    monkeypatch.undo()
    try:
        os.unlink(path)
    except Exception:
        pass


def test_get_backend_default_local(client):
    c, db, path = client
    r = c.get('/config/api/backend')
    assert r.status_code == 200
    d = r.json()
    assert d['mode'] == 'local'
    assert d['dizical_url'] == ''


def test_put_cloud_persists(client):
    c, db, path = client
    r = c.put('/config/api/backend', json={'mode': 'cloud', 'dizical_url': 'https://dizical-prod.example.com'})
    assert r.status_code == 200
    assert r.json()['ok'] is True

    # GET 读回
    r2 = c.get('/config/api/backend')
    d2 = r2.json()
    assert d2['mode'] == 'cloud'
    assert d2['dizical_url'] == 'https://dizical-prod.example.com'

    # settings 表落盘
    with db._get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='backend_mode'").fetchone()
    assert row is not None
    assert row[0] == 'cloud'


def test_put_invalid_mode_400(client):
    c, db, path = client
    r = c.put('/config/api/backend', json={'mode': 'mars'})
    assert r.status_code == 400
    assert 'cloud' in r.json()['error']


def test_put_pin_required_when_set(client):
    c, db, path = client
    # 设置 dad_pin
    db.set_setting('dad_pin', '1234')
    # 不带 PIN → 403
    r = c.put('/config/api/backend', json={'mode': 'cloud', 'dizical_url': 'https://x'})
    assert r.status_code == 403
    # 错误 PIN → 403
    r2 = c.put('/config/api/backend', json={'mode': 'cloud', 'dizical_url': 'https://x', 'pin': '9999'})
    assert r2.status_code == 403
    # 正确 PIN → 200
    r3 = c.put('/config/api/backend', json={'mode': 'cloud', 'dizical_url': 'https://x', 'pin': '1234'})
    assert r3.status_code == 200
    assert r3.json()['ok'] is True


def test_put_back_to_local(client):
    c, db, path = client
    c.put('/config/api/backend', json={'mode': 'cloud', 'dizical_url': 'https://x'})
    r = c.put('/config/api/backend', json={'mode': 'local'})
    assert r.status_code == 200
    r2 = c.get('/config/api/backend')
    assert r2.json()['mode'] == 'local'
    # dizical_url 保留 (不删除)
    assert r2.json()['dizical_url'] == 'https://x'
