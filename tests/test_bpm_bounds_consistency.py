"""tempo_bpm 上下限必须三层一致 (2026-11-03).

事故: schemas.py 的 BPM_MAX 放宽到 200, 但 database.py / database_mysql.py 的
_BPM_MAX 仍是 150 -> 151-200 通过 pydantic 后在后端校验被拒成 400,
前端 200 的档位写了会失败。DB 层的测试当时还断言「151 拒」, 反而把 bug 锁住了。

这里只做常量对齐守门 + 直接喂 DB 层校验函数, 不碰数据库。
"""

import pytest

from src.database import Database
from src.database_mysql import MySQLBackend
from src.kid_app.schemas import BPM_MAX, BPM_MIN


def test_bpm_bounds_aligned_across_layers():
    assert Database._BPM_MIN == BPM_MIN == 40
    assert Database._BPM_MAX == BPM_MAX == 200
    assert MySQLBackend._BPM_MIN == BPM_MIN
    assert MySQLBackend._BPM_MAX == BPM_MAX


@pytest.mark.parametrize("backend_cls", [Database, MySQLBackend])
@pytest.mark.parametrize("bpm,ok", [(40, True), (160, True), (200, True), (39, False), (201, False)])
def test_validate_session_fields_bpm(backend_cls, bpm, ok):
    instance = backend_cls.__new__(backend_cls)
    note = backend_cls._ALLOWED_TEMPO_NOTES[0]
    if ok:
        instance._validate_session_fields(note, bpm, 5, "test", 1)
    else:
        with pytest.raises(ValueError, match="tempo_bpm"):
            instance._validate_session_fields(note, bpm, 5, "test", 1)
