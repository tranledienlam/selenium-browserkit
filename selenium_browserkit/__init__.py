"""
selenium_toolkit
================

Bộ công cụ hỗ trợ automation với Selenium:
- Node: Quản lý phiên làm việc Selenium (mở tab, click, nhập liệu, chụp màn hình, …)
- Utility: Các hàm tiện ích (log, proxy, đọc config/data, xử lý lock file, …)
- TeleHelper: Gửi log/ảnh lên Telegram bot
- AIHelper: Tích hợp Gemini AI để phân tích hình ảnh/nội dung

Cách sử dụng:
-------------
from selenium_toolkit import Node, Utility, TeleHelper, AIHelper
"""
from selenium.webdriver.common.by import By
from .browser import BrowserManager
from .node import Node
from .utils import Utility, DIR_PATH

__all__ = [
    "By",
    "Node",
    "BrowserManager",
    "Utility",
    "DIR_PATH"
]

__version__ = "0.1.0"
