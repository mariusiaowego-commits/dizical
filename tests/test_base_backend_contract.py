"""PR-A-2: BaseBackend 抽象基类契约.

要求所有 backend (SQLite / MySQL) 实现 4 个 session 方法,
防止今后再遗漏 MySQL 实现 (7-28 缺 update/delete 教训).

不覆盖通用 CRUD (create_practice_item 等), 只强制 session 相关.
"""
import inspect
import pytest

from src.database import BaseBackend, Database
from src.database_mysql import MySQLBackend


def test_base_backend_abstract_methods():
    """BaseBackend 必须声明 4 个 session 抽象方法."""
    expected = {
        "create_practice_session",
        "update_practice_session",
        "delete_practice_session",
        "save_practice_session_and_daily_summary",
    }
    actual = set(BaseBackend.__abstractmethods__)
    assert expected.issubset(actual), f"缺: {expected - actual}"


def test_sqlite_database_subclass():
    """SQLite Database 继承 BaseBackend, 必须实现所有抽象方法."""
    abstract = BaseBackend.__abstractmethods__
    for method_name in abstract:
        assert hasattr(Database, method_name), f"Database 缺 {method_name}"
        method = getattr(Database, method_name)
        # 必须是 method (绑定到类), 不能是 abstract property
        assert callable(method), f"Database.{method_name} 不可调用"


def test_mysql_backend_subclass():
    """MySQLBackend 继承 BaseBackend, 必须实现所有抽象方法."""
    abstract = BaseBackend.__abstractmethods__
    for method_name in abstract:
        assert hasattr(MySQLBackend, method_name), f"MySQLBackend 缺 {method_name}"
        method = getattr(MySQLBackend, method_name)
        assert callable(method), f"MySQLBackend.{method_name} 不可调用"


def test_base_backend_instantiation_fails():
    """BaseBackend 自身不能被实例化 (有抽象方法)."""
    with pytest.raises(TypeError) as exc_info:
        BaseBackend()  # noqa
    assert "abstract" in str(exc_info.value).lower() or "instantiate" in str(exc_info.value).lower()


def test_methods_signature_compatible():
    """SQLite / MySQL 的同名 session 方法签名应一致 (类型提示对照)."""
    methods = ["create_practice_session", "update_practice_session", "delete_practice_session"]
    for m in methods:
        sqlite_sig = inspect.signature(getattr(Database, m))
        mysql_sig = inspect.signature(getattr(MySQLBackend, m))
        sqlite_params = list(sqlite_sig.parameters.keys())
        mysql_params = list(mysql_sig.parameters.keys())
        # 关键参数必须同名 (允许 SQLite 多 **kwargs)
        for required in ["self", "session_id"]:
            if required in sqlite_params:
                assert required in mysql_params, f"{m}: MySQL 缺 {required} 参数"
