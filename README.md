# Selenium BrowserKit

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.3-orange.svg)](pyproject.toml)

**Selenium BrowserKit** là một bộ công cụ tự động hóa mạnh mẽ với Selenium, được thiết kế để quản lý nhiều profile trình duyệt, chạy song song, và tích hợp các tính năng AI và Telegram. Phù hợp cho việc xây dựng bot, tool automation, hoặc quản lý nhiều tài khoản cùng lúc.

## ✨ Tính năng chính

- 🚀 **Quản lý đa profile**: Hỗ trợ chạy nhiều profile trình duyệt độc lập
- ⚡ **Chạy song song**: BrowserManager cho phép chạy nhiều profile đồng thời
- 🔒 **Hệ thống lock**: Tránh xung đột khi chạy nhiều tiến trình
- 🌐 **Quản lý proxy**: Hỗ trợ proxy với nhiều định dạng khác nhau
- 📱 **Tích hợp Telegram**: Gửi log, screenshot qua Telegram bot
- 🤖 **AI Helper**: Tích hợp Gemini AI để phân tích văn bản và hình ảnh
- 🔧 **Tùy biến linh hoạt**: Hỗ trợ cả class và function cho Auto/Setup Handler
- 📦 **Extension support**: Tự động load các extension Chrome (.crx)

## 📦 Cài đặt

### Yêu cầu hệ thống
- Python 3.8+
- Chrome/Chromium & ChromeDriver
- Windows/Linux/macOS

### Cài đặt từ PyPI
```bash
pip install selenium-browserkit==1.1.3
```

### Cài đặt từ source
```bash
git clone https://github.com/tranledienlam/selenium-browserkit.git
cd selenium-browserkit
pip install -e .
```

## 🚀 Quick Start

### Cách 1: Sử dụng Class

```python
from selenium_browserkit import BrowserManager, Node, By

class Auto:
    def __init__(self, node: Node, profile: dict):
        self.node = node
        self.profile = profile

        self.run()

    def run(self):
        # Logic tự động chính
        self.node.go_to("https://www.selenium.dev")
        self.node.find_and_click(By.XPATH, '//span[contains(text(),"Download")]')
        self.node.log("Đã click vào Download")

class Setup:
    def __init__(self, node: Node, profile: dict):
        self.node = node
        self.profile = profile

        self.run()

    def run(self):
        # Logic thiết lập ban đầu
        self.node.go_to("https://www.selenium.dev")
        self.node.log("Đã mở https://www.selenium.dev")

# Khởi tạo và chạy
manager = BrowserManager(auto_handler=Auto, setup_handler=Setup)
manager.run_menu(profiles=[{'profile_name': 'test'}])
```

### Cách 2: Sử dụng Function

```python
from selenium_browserkit import BrowserManager, Node, By

def auto(node: Node, profile: dict):
    node.go_to("https://www.selenium.dev")
    node.find_and_click(By.XPATH, '//span[contains(text(),"Download")]')
    node.log("Đã click vào Download")

def setup(node: Node, profile: dict):
    node.go_to("https://www.selenium.dev")
    node.log("Đã mở https://www.selenium.dev")

# Khởi tạo và chạy
manager = BrowserManager(auto_handler=auto, setup_handler=setup)
manager.run_menu(profiles=[{'profile_name': 'test'}])
```

## ⚙️ Cấu hình BrowserManager

### Cấu hình cơ bản

```python
manager = BrowserManager(auto_handler=Auto, setup_handler=Setup)

# Cấu hình các tùy chọn
manager.update_config(
    headless=False,      # Ẩn trình duyệt
    disable_gpu=False,   # Tắt GPU
    sys_chrome=False,    # Sử dụng Chrome hệ thống
    use_tele=False,      # Bật Telegram helper
    use_ai=False         # Bật AI helper
)
```

### Thêm Extension

```python
# Thêm extension từ thư mục extensions/
manager.add_extensions('Meta-Wallet-*.crx', 'OKX-Wallet-*.crx')
```

### Profile với Proxy

```python
profiles = [
    {
        'profile_name': 'profile1',
        'proxy_info': 'ip:port@username:password'  # Proxy với auth
    },
    {
        'profile_name': 'profile2', 
        'proxy_info': 'ip:port'  # Proxy không auth
    },
    {
        'profile_name': 'profile3',
        'proxy_info': 'username:password@ip:port'  # Proxy auth khác
    }
]

# Thêm proxy dự phòng (fallback)
# Nếu profile không có proxy hoặc proxy trong profile bị lỗi
manager.add_proxies(
    "38.153.152.244:9594",
    "38.153.152.244:9594@user:pass",
    "user:pass@38.153.152.244:9594"
)

manager.run_menu(profiles=profiles)
```

## 🔧 API Reference

### BrowserManager Class

```python
BrowserManager(auto_handler=None, setup_handler=None)
```

| Method | Mô tả |
|--------|-------|
| `update_config(**kwargs)` | Cập nhật cấu hình |
| `add_extensions(*args)` | Thêm extension Chrome |
| `add_proxies(*args)` | Thêm proxy |
| `run_menu(profiles)` | Chạy với giao diện menu |

### Node Class

| Method | Mô tả |
|--------|-------|
| `get_driver()` | Trả về đối tượng Selenium WebDriver gốc |
| `go_to(url, method, wait, timeout)` | Điều hướng đến URL |
| `find(by, value, parent_element, wait, timeout)` | Tìm element |
| `finds(by, value, parent_element, wait, timeout)` | Tìm tất cả elements |
| `find_and_click(by, value, parent_element, wait, timeout)` | Tìm và click element |
| `find_and_input(by, value, text, parent_element, delay, wait, timeout)` | Tìm và nhập text |
| `click(element, wait)` | Click element |
| `press_key(key, parent_element, wait, timeout)` | Nhấn phím |
| `get_text(by, value, parent_element, wait, timeout)` | Lấy text từ element |
| `find_in_shadow(selectors, wait, timeout)` | Tìm element trong shadow DOM |
| `finds_by_text(text, parent_element, wait, timeout)` | Tìm tất cả element chứa text |
| `has_texts(texts, wait)` | Kiểm tra nhanh xem trang có chứa một hoặc nhiều đoạn text. Trả về danh sách các text thực sự tồn tại. |
| `take_screenshot()` | Chụp màn hình (trả về bytes) |
| `snapshot(message, stop)` | Chụp và lưu ảnh hoặc gửi đến Tele (nếu có). Nếu `stop=True` thì sẽ dừng luồng code sau khi chụp|
| `log(message, show_log)` | Ghi log |
| `new_tab(url, method, wait, timeout)` | Mở tab mới |
| `switch_tab(value, type, wait, timeout)` | Chuyển tab |
| `close_tab(value, type, wait, timeout)` | Đóng tab |
| `reload_tab(wait)` | Reload tab hiện tại |
| `get_url(wait)` | Lấy URL hiện tại |
| `scroll_to_element(element, wait)` | Cuộn đến element |
| `scroll_to_position(position, wait)` | Cuộn đến vị trí  "top", "middle", "end" của trang|
| `wait_for_disappear(by, value, parent_element, wait, timeout)` | Chờ element biến mất |
| `wait_for_page_load(wait, timeout)` | Chờ trang load xong |
| `ask_ai(prompt, is_image, wait)` | Hỏi AI (Gemini) |
| `execute_chain(actions, message_error)` | Thực hiện chuỗi hành động |

#### Ví dụ sử dụng Node

```python
def auto(node: Node, profile: dict):
    # Điều hướng
    node.go_to("https://www.saucedemo.com")
    
    # Nhập text
    node.find_and_input(By.ID, "user-name", "standard_user")
    node.find_and_input(By.ID, "password", "secret_sauce")
    node.find_and_click(By.ID, "login-button")
    
    # Chụp màn hình và lưu lại
    node.snapshot()
    
    # Ghi log
    node.log("Đã đăng nhập thành công")
```

### Utility Class

| Method | Mô tả |
|--------|-------|
| `wait_time(second, fix)` | Chờ thời gian (có random) |
| `fake_data(numbers)` | Tạo dữ liệu fake cho test |
| `read_data(*field_names)` | Đọc dữ liệu từ file data.txt |
| `read_config(keyname)` | Đọc dữ liệu từ file config.txt |
| `timeout(second)` | Tạo hàm kiểm tra timeout |

#### Ví dụ sử dụng Utility

```python
from selenium_browserkit import Utility

# Tạo dữ liệu fake
profiles = Utility.fake_data(5)

# Đọc dữ liệu từ file data.txt
profiles = Utility.read_data('profile_name', 'email', 'password')

# Đọc dữ liệu từ file config.txt
proxies = Utility.read_data('PROXY')

# Chờ thời gian (có random ±40%)
Utility.wait_time(5, fix=False)  # Random 3-7 giây
Utility.wait_time(5, fix=True)   # Chính xác 5 giây

# Set timeout cho vòng lặp
check_timeout = Utility.timeout(30)
while check_timeout():
    # Thực hiện logic
    pass
```

## 📁 Cấu trúc dự án

### Khi cài đặt từ PyPI
```
site-packages/selenium_browserkit/
├── __init__.py
├── browser.py          # BrowserManager
├── node.py            # Node class
└── utils/
    ├── __init__.py
    ├── core.py        # Utility functions
    └── browser_helper.py  # TeleHelper, AIHelper
```

### Khi sử dụng (trong project của bạn)
```
your_project/
├── snapshot/           # Nơi hình ảnh được lưu (tool tạo)
├── user_data/          # Browser profiles data (tool tạo)
├── extensions/         # Chrome extensions (.crx) (tự tạo)
├── config.txt          # Configuration file (tự tạo)
├── data.txt            # Profiles data (tự tạo)
└── main.py             # File chính
```

## 📝 File cấu hình

### config.txt (tự tạo trong project)
```
MAX_PROFILES=5
PYTHON_PATH=E:\venv\Scripts\python.exe
USER_DATA_DIR=E:\profiles\discord
TELE_BOT=<USER_ID>|<BOT_TOKEN>|<ENDPOINT_URL (nếu có)>
AI_BOT=<AI_BOT_TOKEN>
```

### data.txt (tự tạo trong project)
```
profile_name|email|password|proxy_info (nếu có)
test1|user1@example.com|pass1|ip:port@username:password
test2|user2@example.com|pass2
```

## 🤖 Tích hợp AI và Telegram

### Telegram Helper
- Tự động gửi screenshot lên Telegram
- Gửi log và thông báo trạng thái

### AI Helper (Gemini)
- Phân tích hình ảnh và văn bản
- Sử dụng `node.ask_ai()` để tương tác

### Cấu hình
```python
# Trong config.txt
TELE_BOT=123456789|bot_token_here|https://api.telegram.org
AI_BOT=your_gemini_api_key

# Sử dụng
manager.update_config(use_ai=True, use_tele=True)
```

### Ví dụ sử dụng AI và Tele
```python
def auto(node: Node, profile: dict):
    # Chụp ảnh gửi Tele
    node.snapshot("Chụp ảnh trang web")
    # Gửi ảnh và hỏi AI
    response = node.ask_ai("Phân tích nội dung trang web này", is_image=True)
    node.log(f"AI response: {response}")
```

## 🐛 Troubleshooting

### Lỗi thường gặp

1. **ChromeDriver không tìm thấy**
   ```bash
   # Cài đặt ChromeDriver
   pip install webdriver-manager
   ```

2. **Profile bị lock**
   ```bash
   # Xóa file lock
   rm user_data/*.pid
   # Hoặc trên Windows
   del user_data\*.pid
   ```

3. **Extension không load**
   - Đảm bảo file .crx nằm trong thư mục `extensions/`
   - Kiểm tra tên file extension
   - Kiểm tra quyền đọc file

4. **AI/Telegram không hoạt động**
   - Kiểm tra API key trong config.txt
   - Kiểm tra format cấu hình TELE_BOT và AI_BOT

## 🆕 Update v1.1.3

### Tối ưu chiến lược load trang (Page Load Strategy)

- Thêm cấu hình cho Chrome:
    ```
    chrome_options.page_load_strategy = 'eager'
    ```

- Giúp Selenium bắt đầu thao tác ngay sau khi DOM được tải (`DOMContentLoaded`),
không cần chờ toàn bộ tài nguyên (ảnh, iframe, video…) → tăng tốc độ chạy tool.

- Phù hợp cho automation, bot, VPS, môi trường không cần render đầy đủ giao diện.

---

📦 **Phiên bản:** `1.1.3`

## 📄 License

MIT License - xem file [LICENSE](LICENSE) để biết thêm chi tiết.

## 🤝 Contributing

Mọi đóng góp đều được chào đón! Vui lòng:

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📞 Support

- 📧 Email: lam.tranledien@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/tranledienlam/selenium-browserkit/issues)
- 📖 Documentation: [Wiki](https://github.com/tranledienlam/selenium-browserkit/wiki) (Chưa cập nhật)

---

## 🔗 Thông tin liên hệ

📢 **Telegram Channel:** [Airdrop Automation](https://t.me/+8o9ebAT9ZSFlZGNl)

💰 **Ủng hộ tác giả:**

- **EVM:** `0x3b3784f7b0fed3a8ecdd46c80097a781a6afdb09`
- **SOL:** `4z3JQNeTnMSHYeg9FjRmXYrQrPHBnPg3zNKisAJjobSP`
- **TON:** `UQDKgC6TesJJU9TilGYoZfj5YYtIzePhdzSDJTctJ-Z27lkR`
- **SUI:** `0x5fb56584bf561a4a0889e35a96ef3e6595c7ebd13294be436ad61eaf04be4b09`
- **APT (APTOS):** `0x557ea46189398da1ddf817a634fa91cfb54a32cfc22cadd98bb0327c880bac19`

☕ Nếu bạn thấy dự án hữu ích, hãy mời mình một ly cà phê bằng token gốc của mạng nhé.
Cảm ơn bạn rất nhiều!

---
**Made with ❤️ by Tran Lam**