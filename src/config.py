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

# Obsidian 配置
OBSIDIAN_PATH = Path(os.getenv(
    "OBSIDIAN_PATH",
    "/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/"
))

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "351549096")


def ensure_data_dir() -> None:
    """确保数据目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
