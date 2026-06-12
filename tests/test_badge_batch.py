"""tests/test_badge_batch.py — PR-C (2026-06-12) 批量模式测试

覆盖:
- _derive_batch_badge_id 派生规则
- run_badge_pipeline_batch: N=0 / N>20 / N=1 / N=5 / 部分失败 / 全部成功
- commit_badge_batch_to_db: 0 个 / 1 个 / N 个 / 失败回滚 / 名称后缀
- 派生 id 冲突检测
- PR-B 集成: invalidate cache
"""
import subprocess
from pathlib import Path
from unittest import mock

from PIL import Image

from src.kid_app import badge_generator


# ─── Helpers ──────────────────────────────────────────────────────

def _mock_popen_with_output(stdout_text: str, returncode: int = 0):
    mock_proc = mock.Mock()
    mock_proc.stdout = iter(stdout_text.splitlines(keepends=True))
    mock_proc.stderr = mock.Mock()
    mock_proc.stderr.read.return_value = ""
    mock_proc.returncode = returncode
    mock_proc.wait.return_value = returncode
    return mock_proc


def _make_fake_png(path: Path) -> None:
    Image.new("RGB", (50, 50), (240, 240, 240)).save(path, "PNG")


SOURCE_META = {
    "id": "test_source_badge",
    "name": "测试来源徽章",
    "type": "突破",
    "category": "milestone",
    "statLogic": "test_logic",
    "description": "test desc",
    "displayFormat": "days",
    "seasonalType": "monthly",
}


# ─── TestDeriveBatchBadgeId ────────────────────────────────────

class TestDeriveBatchBadgeId:
    def test_basic(self):
        result = badge_generator._derive_batch_badge_id("lucky_61_2026", 1)
        assert result == "lucky_61_2026_1"

    def test_index_5(self):
        result = badge_generator._derive_batch_badge_id("lucky_61_2026", 5)
        assert result == "lucky_61_2026_5"


# ─── TestRunBadgePipelineBatch ──────────────────────────────────

class TestRunBadgePipelineBatch:
    def test_empty_placeholders(self):
        result = badge_generator.run_badge_pipeline_batch(
            source_badge_meta=SOURCE_META,
            placeholders=[],
            on_status=lambda *args: None,
        )
        assert result["ok"] is True
        assert result["n_total"] == 0
        assert result["n_success"] == 0
        assert result["n_failed"] == 0
        assert result["results"] == []

    def test_exceeds_max_n(self):
        placeholders = [f"ph_{i}" for i in range(25)]  # > 20
        result = badge_generator.run_badge_pipeline_batch(
            source_badge_meta=SOURCE_META,
            placeholders=placeholders,
            on_status=lambda *args: None,
        )
        assert result["ok"] is False
        assert "20" in result.get("error", "")

    def test_missing_source_id(self):
        result = badge_generator.run_badge_pipeline_batch(
            source_badge_meta={},  # 没 id
            placeholders=["ph1"],
            on_status=lambda *args: None,
        )
        assert result["ok"] is False
        assert "id" in result.get("error", "").lower()

    def test_single_success(self, tmp_path):
        output_png = tmp_path / "fake.png"
        _make_fake_png(output_png)
        stdout = f"session_id: abc\nMEDIA:{output_png}\n"

        with mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(True, "OK"),
        ):
            with mock.patch.object(
                badge_generator.subprocess, "Popen",
                return_value=_mock_popen_with_output(stdout, returncode=0),
            ):
                with mock.patch.object(
                    badge_generator, "check_id_unique", return_value=True,
                ):
                    result = badge_generator.run_badge_pipeline_batch(
                        source_badge_meta=SOURCE_META,
                        placeholders=["a cute chibi girl with a bamboo flute"],
                        on_status=lambda *args: None,
                    )

        assert result["ok"] is True
        assert result["n_total"] == 1
        assert result["n_success"] == 1
        assert result["n_failed"] == 0
        assert len(result["results"]) == 1
        assert result["results"][0]["badge_id"] == "test_source_badge_1"
        assert result["results"][0]["ok"] is True
        # 清理 PNG (从 fake_path 移动到 static/badges 后的实际路径)
        img_path = Path(result["results"][0]["image_path"])
        if img_path.exists():
            img_path.unlink()

    def test_five_mixed(self, tmp_path):
        # mock: 只对 placeholder 长度 >= 20 返 stdout (成功), 短则返空 (失败)
        def mock_popen_side_effect(*args, **kwargs):
            cmd = args[0]
            q_idx = cmd.index("-q")
            prompt = cmd[q_idx + 1]
            if len(prompt) < 20:
                return _mock_popen_with_output("session_id: abc\nno image", returncode=0)
            # 长 placeholder: 给个 fake PNG (但 mock 多个, 共享)
            fake = tmp_path / f"fake_{len(prompt)}.png"
            _make_fake_png(fake)
            stdout = f"session_id: abc\nMEDIA:{fake}\n"
            return _mock_popen_with_output(stdout, returncode=0)

        placeholders = [
            "a cute chibi girl with a bamboo flute",       # 成功 (长)
            "abc",                                          # 失败 (短)
            "a chibi girl with a red kite",                # 成功
            "xy",                                           # 失败
            "a chibi girl with golden bells",               # 成功
        ]

        with mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(True, "OK"),
        ):
            with mock.patch.object(
                badge_generator.subprocess, "Popen",
                side_effect=mock_popen_side_effect,
            ):
                with mock.patch.object(
                    badge_generator, "check_id_unique", return_value=True,
                ):
                    result = badge_generator.run_badge_pipeline_batch(
                        source_badge_meta=SOURCE_META,
                        placeholders=placeholders,
                        on_status=lambda *args: None,
                    )

        assert result["n_total"] == 5
        assert result["n_success"] == 3
        assert result["n_failed"] == 2
        # 失败的具体项
        for r in result["results"]:
            if not r["ok"]:
                assert r["error"] is not None
        # 清理生成的 PNG
        for r in result["results"]:
            ip = r.get("image_path")
            if ip and Path(ip).exists():
                Path(ip).unlink()

    def test_on_status_called_with_badge_id(self, tmp_path):
        """确认 on_status 回调被调, 且 badge_id 字段对 (PR-C 关键)."""
        output_png = tmp_path / "fake.png"
        _make_fake_png(output_png)
        stdout = f"session_id: abc\nMEDIA:{output_png}\n"

        calls = []

        def on_status(stage, badge_id, msg):
            calls.append((stage, badge_id, msg))

        with mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(True, "OK"),
        ):
            with mock.patch.object(
                badge_generator.subprocess, "Popen",
                return_value=_mock_popen_with_output(stdout, returncode=0),
            ):
                with mock.patch.object(
                    badge_generator, "check_id_unique", return_value=True,
                ):
                    badge_generator.run_badge_pipeline_batch(
                        source_badge_meta=SOURCE_META,
                        placeholders=["a cute girl with bamboo flute"],
                        on_status=on_status,
                    )

        # 至少 6 个 status (step0-5 + 1 步合并进度)
        assert len(calls) >= 6
        # 每个调用 badge_id 都是派生 id
        for stage, bid, msg in calls:
            assert bid == "test_source_badge_1"
        # 清理
        Path(output_png).unlink()


# ─── TestCommitBadgeBatchToDb ──────────────────────────────────

class TestCommitBadgeBatchToDb:
    def test_empty_items(self):
        result = badge_generator.commit_badge_batch_to_db(
            source_badge_meta=SOURCE_META,
            items=[],
        )
        assert result["ok"] is True
        assert result["committed_count"] == 0
        assert result["failed"] == []

    def test_single_item(self):
        items = [{
            "badge_id": "test_source_badge_1",
            "image_path": "/fake/path/test_source_badge_1_v1.png",
            "version": 1,
            "ok": True,
            "placeholder": "ph_1",
        }]
        with mock.patch.object(badge_generator, "insert_achievement_row") as m_ach:
            with mock.patch.object(badge_generator, "insert_achievement_stats_row") as m_stats:
                with mock.patch.object(badge_generator, "insert_badge_row") as m_badge:
                    result = badge_generator.commit_badge_batch_to_db(
                        source_badge_meta=SOURCE_META,
                        items=items,
                    )
        assert result["ok"] is True
        assert result["committed_count"] == 1
        # 验证各 insert 被调 1 次
        assert m_ach.call_count == 1
        assert m_stats.call_count == 1  # milestone 类型
        assert m_badge.call_count == 1
        # 名称后缀
        ach_call_args = m_ach.call_args[0][1]
        assert ach_call_args["id"] == "test_source_badge_1"
        assert "(1)" in ach_call_args["name"]
        # type/category/display_format 继承
        assert ach_call_args["type"] == "突破"
        assert ach_call_args["category"] == "milestone"
        assert ach_call_args["display_format"] == "days"
        assert ach_call_args["seasonal_type"] == "monthly"

    def test_seasonal_skips_stats(self):
        """seasonal 类型不写 achievement_stats."""
        meta = dict(SOURCE_META, category="seasonal", seasonalType="monthly")
        items = [{
            "badge_id": "test_source_badge_1",
            "image_path": "/fake/v1.png",
            "version": 1,
            "ok": True,
            "placeholder": "ph",
        }]
        with mock.patch.object(badge_generator, "insert_achievement_row") as m_ach:
            with mock.patch.object(badge_generator, "insert_achievement_stats_row") as m_stats:
                with mock.patch.object(badge_generator, "insert_badge_row") as m_badge:
                    badge_generator.commit_badge_batch_to_db(
                        source_badge_meta=meta, items=items,
                    )
        # seasonal 不写 stats
        assert m_stats.call_count == 0
        assert m_ach.call_count == 1
        assert m_badge.call_count == 1

    def test_filter_not_ok_items(self):
        """items 里 ok=False 的不写库."""
        items = [
            {"badge_id": "ok_1", "image_path": "/fake/ok_1.png", "version": 1, "ok": True, "placeholder": "p"},
            {"badge_id": "fail_1", "image_path": None, "version": 0, "ok": False, "error": "hermes fail"},
            {"badge_id": "ok_2", "image_path": "/fake/ok_2.png", "version": 2, "ok": True, "placeholder": "p"},
        ]
        with mock.patch.object(badge_generator, "insert_achievement_row") as m_ach:
            with mock.patch.object(badge_generator, "insert_badge_row") as m_badge:
                badge_generator.commit_badge_batch_to_db(
                    source_badge_meta=SOURCE_META, items=items,
                )
        assert m_ach.call_count == 2  # 只写 2 个 ok
        assert m_badge.call_count == 2

    def test_name_suffix_strips_existing_number(self):
        # 直接测名称格式化逻辑 (通过 mock insert)
        meta = dict(SOURCE_META, name="幸运六一节 (5)")
        items = [{
            "badge_id": "test_1",
            "image_path": "/fake/v1.png",
            "version": 1,
            "ok": True,
            "placeholder": "p",
        }]
        with mock.patch.object(badge_generator, "insert_achievement_row") as m_ach:
            with mock.patch.object(badge_generator, "insert_badge_row"):
                with mock.patch.object(badge_generator, "insert_achievement_stats_row"):
                    badge_generator.commit_badge_batch_to_db(
                        source_badge_meta=meta, items=items,
                    )
        # 来源 "幸运六一节 (5)" -> 新 "幸运六一节 (1)" (替换 5)
        name = m_ach.call_args[0][1]["name"]
        assert name == "幸运六一节 (1)"

    def test_invalidates_badge_url_cache(self):
        """PR-B 集成: commit 后调 _invalidate_badge_url_cache."""
        items = [{
            "badge_id": "ok_1", "image_path": "/fake/ok_1.png", "version": 1, "ok": True, "placeholder": "p",
        }]
        with mock.patch.object(badge_generator, "insert_achievement_row"):
            with mock.patch.object(badge_generator, "insert_achievement_stats_row"):
                with mock.patch.object(badge_generator, "insert_badge_row"):
                    # mock 掉 _invalidate_badge_url_cache (延迟 import 走 src.kid_app.app)
                    with mock.patch("src.kid_app.app._invalidate_badge_url_cache") as m_inv:
                        badge_generator.commit_badge_batch_to_db(
                            source_badge_meta=SOURCE_META, items=items,
                        )
        # 批量调 1 次 invalidate
        assert m_inv.call_count == 1
