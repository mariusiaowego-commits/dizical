"""配置管理模块"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "dizi.db"

# 加载环境变量
load_dotenv(ROOT_DIR / ".env")

# 默认配置
DEFAULT_LESSON_TIME = "17:15"
DEFAULT_LESSON_FEE = 600
DEFAULT_PAYMENT_METHOD = "现金"
REMINDERS_LIST_NAME = "dizi"
TELEGRAM_BOT_USERNAME = "hermes_for_mtt_bot"

# Obsidian 配置 (2026-08-12 安全加固: 默认值用公开占位符, 不写死 dad 真实 iCloud 路径)
# 没设 OBSIDIAN_PATH 时 fallback 到 ~/Documents/ObsidianVault (公开通用占位, 不是 dad 真实路径)
OBSIDIAN_PATH = Path(os.getenv("OBSIDIAN_PATH", os.path.expanduser("~/Documents/ObsidianVault")))

# Telegram 配置 (2026-08-12 安全加固: 默认值 0 占位, 不写死 dad 真实 chat id)
# 没设 TELEGRAM_CHAT_ID 时发通知会失败 (chat_id=0 无效), fail-loud 提示去 .env 配
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "0")


def ensure_data_dir() -> None:
    """确保数据目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
