import os
import random
import sys
import json
import shutil
import psutil
import zipfile
from pathlib import Path
from math import ceil
from typing import overload
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from screeninfo import get_monitors
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions

from .node import Node
from .utils import Utility, DIR_PATH
from .utils.browser_helper import Chromium, TeleHelper, AIHelper

@dataclass
class BrowserConfig:
    headless: bool = False
    disable_gpu: bool = False
    sys_chrome: bool = False
    use_tele: bool = False
    use_ai: bool = False

class BrowserManager:                                                                                                                                                                              # Anh em cứ yên tâm chạy nhé, không có mã độc đâu! :D Chỉ giả vờ đánh lừa người ngoài chút thôi! 🚀
    def __init__(self, auto_handler=None, setup_handler =None) -> None:
        '''
        Khởi tạo đối tượng BrowserManager để quản lý và tự động hóa trình duyệt.

        Args:
        - auto_handler (callable, optional): Logic chính để chạy profile.
            - Có thể truyền vào class (sẽ được khởi tạo với `node, profile`).
            - Hoặc truyền vào function (sẽ được gọi trực tiếp với `node, profile`).
        - setup_handler (callable, optional): Logic dùng khi chạy ở chế độ thiết lập (setup).
            - Tương tự, có thể là class hoặc function.

        Chức năng:
        - Cho phép lập trình viên định nghĩa cách thức điều khiển trình duyệt cho từng profile.
        - Hỗ trợ cả hai kiểu: class (tự xử lý trong `__init__`) hoặc function đơn giản.
        - Tách riêng 2 ngữ cảnh: 
            - setup_handler: chạy khi khởi tạo môi trường / chuẩn bị.
            - auto_handler: chạy logic tự động chính.

        Ví dụ sử dụng:

        # Dùng class
        class Auto:
            def __init__(self, node, profile):
                node.new_tab("https://mail.google.com")

        browser_manager = BrowserManager(auto_handler=Auto)

        # Dùng function
        def auto_handler(node, profile):
            node.new_tab("https://mail.google.com")

        browser_manager = BrowserManager(auto_handler=auto_handler)
        '''
        self.config: BrowserConfig  = BrowserConfig()
        self._auto_handler = auto_handler
        self._setup_handler  = setup_handler 

        self._user_data_dir = None
        self._extensions_dir = DIR_PATH / 'extensions'
        self._path_chromium = None
        self._pid_path = None
        self._tele_bot = None
        self._ai_bot = None
        self._matrix: list[list[str | None]] = [[None]]
        self._extensions = []
        self._proxies_info = []
        self._live_proxies_parts = []
        # lấy kích thước màn hình
        monitors = get_monitors()
        if len(monitors) > 1:
            select_monitor = monitors[1]
        else:
            select_monitor = monitors[0]
        self._screen_width = select_monitor.width
        self._screen_height = select_monitor.height

    @overload
    def update_config(
        self, *, headless: bool, disable_gpu: bool, sys_chrome: bool, use_tele: bool, use_ai: bool) -> None: ...
    def update_config(self, **kwargs: BrowserConfig):
        """
        Cập nhật lại cấu hình cho BrowserManager trước khi thực thi.

        Các tham số hợp lệ:
            headless (bool, optional): 
                Nếu True, trình duyệt sẽ chạy ẩn (không hiển thị UI).
                Mặc định là False.
            disable_gpu (bool, optional): 
                Nếu True, tắt tăng tốc GPU. 
                Hữu ích khi chạy trên máy không có GPU vật lý. 
                Mặc định là False.
            sys_chrome (bool, optional): 
                Nếu True, sử dụng Chrome hệ thống thay vì Chromium đi kèm.
                Mặc định là False.
            use_tele (bool, optional):
                Nếu True, khởi tạo class `TeleHelper` và có thể dùng chức năng gửi hình ảnh lên Tele khi token được cấu hình `config.txt` hợp lệ. 
                Mặc định là False.
            use_ai (bool, optional):
                Nếu True, khởi tạo class `AIHelper` và có thể dùng `Node.ask_ai` khi token được cấu hình `config.txt` hợp lệ.
                Mặc định là False.
        Args:
            **kwargs (BrowserConfig): 
                Tập các key-value để ghi đè lên config hiện tại.

        Raises:
            KeyError: Nếu `kwargs` chứa key không hợp lệ.
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                self._log(message=f"Không có config '{key}'")

    def _log(self, profile_name: str = 'SYS', message: str = 'message chưa có mô tả'):
        '''
        Ghi và hiển thị thông báo nhật ký (log)

        Cấu trúc log hiển thị:
            [profile_name][func_thuc_thi]: {message}

        Args:
            profile_name (str): tên hồ sơ hiện tại
            message (str, optional): Nội dung thông báo log. Mặc định là 'message chưa có mô tả'.

        Mô tả:
            - Phương thức sử dụng tiện ích `Utility.logger` để ghi lại thông tin nhật ký kèm theo tên hồ sơ (`profile_name`) của phiên làm việc hiện tại.
        '''
        Utility._logger(profile_name, message)

    def _get_user_data_dir(self):
        dir_path = Utility.read_config('USER_DATA_DIR')
        if dir_path and Path(dir_path[0]).exists():
            return Path(dir_path[0])
        else:
            return DIR_PATH/'user_data'
            
    def _get_matrix(self, number_profiles: int, max_concurrent_profiles: int):
        """
        Phương thức tạo ma trận vị trí cho các trình duyệt dựa trên số lượng hồ sơ và luồng song song tối đa.

        Args:
            number_profiles (int): Tổng số lượng hồ sơ cần chạy.
            max_concurrent_profiles (int): Số lượng hồ sơ chạy đồng thời tối đa.

        Hoạt động:
            - Nếu chỉ có 1 hồ sơ chạy, tạo ma trận 1x1.
            - Tự động điều chỉnh số hàng và cột dựa trên số lượng hồ sơ thực tế và giới hạn luồng song song.
            - Đảm bảo ma trận không dư thừa hàng/cột khi số lượng hồ sơ nhỏ hơn giới hạn song song.
        """
        # Số lượng hàng dựa trên giới hạn song song
        rows = 1 if (max_concurrent_profiles == 1 or number_profiles == 1) else 2

        # Tính toán số cột cần thiết
        if number_profiles <= max_concurrent_profiles:
            # Dựa trên số lượng hồ sơ thực tế
            cols = ceil(number_profiles / rows)
        else:
            # Dựa trên giới hạn song song
            cols = ceil(max_concurrent_profiles / rows)
        
        # Tạo ma trận với số hàng và cột đã xác định
        self._matrix = [[None for _ in range(cols)] for _ in range(rows)]

    def _arrange_window(self, driver, row, col):
        cols = len(self._matrix[0])
        y = row * self._screen_height

        if cols > 1 and (cols * self._screen_width) > self._screen_width*2:
            x = col * (self._screen_width // (cols-1))
        else:
            x = col * self._screen_width
        driver.set_window_rect(x, y, self._screen_width, self._screen_height)

    def _get_position(self, profile_name: str):
        """
        Gán profile vào một ô trống và trả về tọa độ (x, y).
        """
        for row in range(len(self._matrix)):
            for col in range(len(self._matrix[0])):
                if self._matrix[row][col] is None:
                    self._matrix[row][col] = profile_name
                    return row, col
        return None, None

    def _release_position(self, profile_name: int, row, col):
        """
        Giải phóng ô khi profile kết thúc.
        """
        for row in range(len(self._matrix)):
            for col in range(len(self._matrix[0])):
                if self._matrix[row][col] == profile_name:
                    self._matrix[row][col] = None
                    return True
        return False

    def _create_extension_proxy(self, profile_name, proxy_parts):

        manifest_json = """
        {
            "version": "1.1.1",
            "manifest_version": 2,
            "name": "Proxies",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            },
            "minimum_chrome_version":"22.0.0"
        }
        """
        background_js = """
        var config = {
            mode: "fixed_servers",
            rules: {
                singleProxy: {
                    scheme: "http",
                    host: "%s",
                    port: parseInt(%s)
                },
                bypassList: ["localhost"]
            }
        };

        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "%s",
                    password: "%s"
                }
            };
        }

        chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {urls: ["<all_urls>"]},
            ['blocking']
        );
        """ % (proxy_parts['ip'], proxy_parts['port'], proxy_parts['user'], proxy_parts['pass'])

        if not self._extensions_dir.exists():
            self._extensions_dir.mkdir(parents=True, exist_ok=True)

        extension_path = self._extensions_dir/f'proxie_{profile_name}.zip'
        # Nếu file đã tồn tại thì xóa
        if extension_path.exists():
            extension_path.unlink()

        try:
            with zipfile.ZipFile(extension_path, 'w') as zp:
                zp.writestr("manifest.json", manifest_json)
                zp.writestr("background.js", background_js)
            return extension_path
        except Exception as e:
            self._log(profile_name, f'Lỗi tạo extension {extension_path}: {e}')
            return None

    def _browser(self, profile_name: str, proxy_info: str|None = None) -> webdriver.Chrome:
        '''
        Phương thức khởi tạo trình duyệt Chrome (browser) với các cấu hình cụ thể, tự động khởi chạy khi gọi `BrowserManager._run_browser()`.

        Args:
            profile_name (str): tên hồ sơ. Được tự động thêm vào khi chạy phương thức `BrowserManager._run_browser()`

        Returns:
            driver (webdriver.Chrome): Đối tượng trình duyệt được khởi tạo.

        Mô tả:
            - Dựa trên thông tin hồ sơ (`profile_data`), hàm sẽ thiết lập và khởi tạo trình duyệt Chrome với các tùy chọn cấu hình sau:
                - Chạy browser với dữ liệu người dùng (`--user-data-dir`).
                - Tùy chọn tỉ lệ hiển thị trình duyệt (`--force-device-scale-factor`)
                - Tắt các thông báo tự động và hạn chế các tính năng tự động hóa của trình duyệt.
                - Vô hiệu hóa dịch tự động của Chrome.
                - Vô hiệu hóa tính năng lưu mật khẩu (chỉ áp dụng khi sử dụng hồ sơ mặc định).
            - Các tiện ích mở rộng (extensions) được thêm vào trình duyệt (Nếu có).       
        '''
        rows = len(self._matrix)
        scale = 1 if (rows == 1) else 0.5

        chrome_options = ChromeOptions()
        if self._path_chromium:
            chrome_options.binary_location = str(self._path_chromium)
        chrome_options.add_argument(
            f'--user-data-dir={self._user_data_dir}/{profile_name}')
        chrome_options.add_argument(f'--profile-directory={profile_name}') # tắt để sử dụng profile default trong profile_name

        chrome_options.add_argument('--lang=en')
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument(f"--force-device-scale-factor={scale}")
        chrome_options.add_argument('--disable-blink-features=AutomationControlled') # để có thể đăng nhập google
        # Tắt dòng thông báo auto
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--log-level=3')

        # hiệu suất
        if Utility._need_no_sandbox():
            chrome_options.add_argument("--no-sandbox") # chỉ chạy khi Docker / Container / VM không có quyền root
        chrome_options.add_argument("--disable-dev-shm-usage")  # Tránh lỗi memory
        if self.config.disable_gpu:
            chrome_options.add_argument("--disable-gpu")  # Tắt GPU, dành cho máy không có GPU vật lý
        if self.config.headless:
            chrome_options.add_argument("--headless=new") # ẩn UI khi đang chạy
        
        # add proxy for profile
        live_proxy_parts =  random.choice(self._live_proxies_parts) if self._live_proxies_parts else None
            
        if proxy_info:
            proxy_parts = Utility._parse_proxy(proxy_info)
            if proxy_parts:
                check_proxy = Utility._is_proxy_working(proxy_parts)
                if check_proxy:
                    live_proxy_parts = proxy_parts
                else:
                    if live_proxy_parts:
                        self._log(profile_name, f'{proxy_info} không hoạt động! Dùng proxy dự phòng')
                    else:
                        self._log(profile_name, f'{proxy_info} không hoạt động! Không dùng proxy')
            else:
                if live_proxy_parts:
                    self._log(profile_name, f'{proxy_info} sai định dạng! Dùng proxy dự phòng')
                else:
                    self._log(profile_name, f'{proxy_info} sai định dạng! Không dùng proxy')

        if live_proxy_parts:
            if live_proxy_parts.get('user') and live_proxy_parts.get('pass'):
                proxy_extension_path = self._create_extension_proxy(profile_name, live_proxy_parts)
                if proxy_extension_path:
                    chrome_options.add_extension(proxy_extension_path)
            else:
                chrome_options.add_argument(f'--proxy-server=http://{live_proxy_parts["ip"]}:{live_proxy_parts["port"]}')

        # add extensions
        for ext in self._extensions:
            chrome_options.add_extension(ext)

        service = Service(log_path='NUL')
        self._log(profile_name, 'Đang mở Chrome...')
        driver = webdriver.Chrome(service=service, options=chrome_options)

        return driver

    def add_extensions(self, *args: str | list[str]):
        '''
        Thêm danh sách tiện ích mở rộng (extensions) cần load.

        Args:
            *args (str | list[str]): 
                - Một hoặc nhiều tên file / pattern, ví dụ:
                    add_extensions("ext1.crx", "ext2*.crx")
                - Hoặc một list chứa tên file / pattern, ví dụ:
                    add_extensions(["ext1.crx", "ext2*.crx"])

        Ghi chú:
            - Chỉ lưu tên/file pattern, chưa kiểm tra sự tồn tại thực tế.
            - Thư mục extensions mặc định: self._extensions_dir.

        Returns:
            list[str]: Danh sách extensions đã chuẩn hoá và loại bỏ trùng lặp.
        '''
        extensions: list[str] = []

        # Gom tất cả argument lại thành một list phẳng
        for arg in args:
            if isinstance(arg, (list, tuple, set)):
                extensions.extend(arg)
            else:
                extensions.append(arg)

        # Loại bỏ None, rỗng, strip() khoảng trắng
        extensions = [e.strip() for e in extensions if e and isinstance(e, str)]

        # Loại bỏ trùng lặp, giữ nguyên thứ tự xuất hiện đầu tiên
        seen = set()
        unique_exts = []
        for e in extensions:
            if e not in seen:
                unique_exts.append(e)
                seen.add(e)

        self._extensions = unique_exts
        return unique_exts

    def add_proxies(self, *args: str | list[str]):
        '''
        Thiết lập danh sách proxy cho toàn bộ phiên duyệt trình.

        Args:
            *args (str | list[str]): 
                - Một hoặc nhiều chuỗi proxy, ví dụ:
                    add_proxies("ip1:port1", "ip2:port2")
                - Hoặc một list chứa chuỗi proxy, ví dụ:
                    add_proxies(["ip1:port1", "ip2:port2"])
            
            Hỗ trợ các định dạng:
                - "ip:port"
                - "ip:port@username:password"
                - "username:password@ip:port"

        Ghi chú:
            - Proxy chỉ được lưu vào `self._proxies_info`.
            - Proxy sẽ được kiểm tra tính hợp lệ trước khi áp dụng khi khởi tạo trình duyệt.
            - Nếu profile đã có cấu hình proxy riêng thì danh sách này sẽ bị bỏ qua.

        Returns:
            list[str]: Danh sách proxy đã chuẩn hoá và loại bỏ trùng lặp.
        '''
        proxies: list[str] = []

        # Gom tất cả argument lại thành một list phẳng
        for arg in args:
            if isinstance(arg, (list, tuple, set)):
                proxies.extend(arg)
            else:
                proxies.append(arg)

        # Loại bỏ None, rỗng, strip() khoảng trắng
        proxies = [p.strip() for p in proxies if p and isinstance(p, str)]

        # Loại bỏ trùng lặp, giữ nguyên thứ tự xuất hiện đầu tiên
        seen = set()
        unique_proxies = []
        for p in proxies:
            if p not in seen:
                unique_proxies.append(p)
                seen.add(p)

        self._proxies_info = unique_proxies
        return unique_proxies

    def _listen_for_enter(self, profile_name: str):
        """Lắng nghe sự kiện Enter để dừng trình duyệt"""
        if sys.stdin.isatty():  # Kiểm tra nếu có stdin hợp lệ
            input(f"[{profile_name}] Nhấn ENTER để đóng trình duyệt...")
        else:
            self._log(
                f"⚠ Không thể sử dụng input() trong môi trường này. Đóng tự động sau 10 giây.")
            Utility.wait_time(10)
    
    def _check_extensions(self):
        '''
        Kiểm tra và xác thực các tiện ích mở rộng (extensions) đã được cấu hình.

        Quá trình:
            - Duyệt qua danh sách `self._extensions` (được truyền từ `add_extensions`).
            - Với mỗi extension:
                + Nếu có ký tự `*` → tìm file khớp trong thư mục `self._extensions_dir` 
                và chọn file mới nhất (dựa vào thời gian tạo).
                + Nếu là tên file cụ thể → kiểm tra sự tồn tại trong `self._extensions_dir`.
            - Nếu không tìm thấy file phù hợp → ghi log lỗi và bỏ qua extension đó.
            - Nếu tìm thấy → thêm vào danh sách kết quả.

        Kết quả:
            - Cập nhật `self._extensions` thành `list[Path]` chứa các đường dẫn extension hợp lệ.
            - Những extension không tồn tại sẽ bị loại bỏ.

        Lưu ý:
            - Phương thức không ném lỗi, chỉ log cảnh báo khi extension không tồn tại.
            - Nếu cần dừng chương trình khi thiếu extension, có thể thay `continue` bằng `raise SystemExit`.

        Ví dụ:
            Giả sử thư mục extensions/ có file `Bitget-Wallet-123.crx`:
            >>> self._extensions = ["Bitget-Wallet-*.crx", "NonExist.crx"]
            >>> self._check_extensions()
            # Kết quả: self._extensions chỉ còn [Path("extensions/Bitget-Wallet-123.crx")]
        '''
        print(f'🛠️  Đang kiểm tra Extensions...')
        if not self._extensions_dir.exists():
            print(f'❌ {self._extensions_dir} không tồn tại')
            return
        result = []
        for extension in self._extensions:
            if "." not in extension:  
                pattern = extension + ".crx"
            elif extension.lower().endswith(".crx"):
                # Người dùng gõ đúng .crx → giữ nguyên
                pattern = extension
            else:
                # Có đuôi khác .crx → loại bỏ
                print(f"❌ Bỏ qua '{extension}' vì không phải .crx")
                continue

            ext_path = None
            # Nếu có ký tự '*' trong tên, thực hiện tìm kiếm
            if '*' in extension:
                matched_files = list(self._extensions_dir.glob(pattern))
                if matched_files:
                    # Chọn file mới nhất
                    ext_path = max(matched_files, key=lambda f: f.stat().st_ctime)
            else:
                ext_path = self._extensions_dir / pattern
                if not ext_path.exists():
                    ext_path = None

            if ext_path:
                result.append(ext_path)
            else:
                print(f'❌ {extension} không tìm thấy trong {self._extensions_dir}')

        self._extensions = result

    def _check_before_run_tool(self):
        print("=================================")
        print('Checking trước khi chạy...')
        print("=================================")
        print("...")
        if not self.config.sys_chrome:
            self._path_chromium = Chromium().path
        # Đọc file config
        config_path = DIR_PATH / 'config.txt'
        if config_path.exists():
            if self.config.use_tele:
                self._tele_bot = TeleHelper()
            if self.config.use_ai:
                self._ai_bot = AIHelper()
        else:
            print(f"⚠️  Không tìm thấy file config: {config_path}\n→ Đang sử dụng cấu hình mặc định.\n📘 Tham khảo config_example.txt tại: https://github.com/tranledienlam/selenium-browserkit/tree/main/examples")      
        self._user_data_dir = self._get_user_data_dir()

        # check extension
        if self._extensions:
            self._check_extensions()

        # check proxies
        if not self._proxies_info:
            self._proxies_info = Utility.read_config('PROXY')
            if self._proxies_info is None:
                self._proxies_info = []
        if self._proxies_info:
            print(f'🛠️  Đang kiểm tra proxy...')
        for proxy_info in self._proxies_info:
            proxy_parts = Utility._parse_proxy(proxy_info)
            check_proxy = Utility._is_proxy_working(proxy_parts)
            if check_proxy:
                self._live_proxies_parts.append(proxy_parts)

        # xử lý file pid nếu tồn tại
        pid_files = list(self._user_data_dir.glob("*.pid"))
        for file in pid_files:
            python_pid = int(file.stem)
            if not Utility._is_process_alive(python_pid):
                Utility._remove_lock(file)
        self._pid_path = self._user_data_dir/f"{os.getpid()}.pid"
        Utility._pid_python(self._pid_path)
        # Xử lý file lock nếu tồn tại
        lock_files = list(self._user_data_dir.glob("*.lock"))
        for lock in lock_files:
            data = Utility._read_lock(lock)
            if data:
                if Utility._is_process_alive(data.get('PYTHONPID')):
                    pass
                else:
                    Utility._kill_chrome(data.get('CHROMEPID'))
                    Utility._remove_lock(lock)

    def _check_before_run_browser(self, path_lock, profile_name):
        path_lock_chrome = self._user_data_dir/profile_name/"lockfile"

        # check lockfile chrome có tồn tại hay không
        if path_lock_chrome.exists():
            # Chờ profile được giải phóng nếu đang bị khóa
            data_lock = Utility._read_lock(path_lock)
            if data_lock == None:
                pass
            elif data_lock == {}:
                Utility._remove_lock(path_lock)
            else:
                name_tool = data_lock.get("TOOL")
                if not (name_tool == Utility._sanitize_text(DIR_PATH.name)) and Utility._is_process_alive(data_lock.get('PYTHONPID')):
                    self._log(profile_name, f"❌ Đang lock bởi tool [{name_tool}]")
                    return False

            self._log(profile_name, f"❌ Đang lock. Nhưng không xác định được tool cụ thể đang chạy")
            return False

        Utility._remove_lock(path_lock)

        # fix thuộc tính "exit_type": "Crashed" → "Normal".
        try:
            path_references = self._user_data_dir/profile_name/profile_name/"Preferences"
            if path_references.exists():
                with open(path_references, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Thay giá trị exit_type
                if "exit_type" in data:
                    data["exit_type"] = "Normal"
                elif "profile" in data and "exit_type" in data["profile"]:
                    data["profile"]["exit_type"] = "Normal"
                else:
                    print("Không tìm thấy khóa exit_type trong Preferences")

                with open(path_references, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

        except Exception as e:
            self._log(message={e})

        return True

    def _check_after_run_browser(self, driver, path_lock):
        # Tìm Chrome con của chromedriver
        chrome_pid = None
        try:
            chromedriver_pid = driver.service.process.pid
            parent = psutil.Process(chromedriver_pid)
            children = parent.children(recursive=True)
            for child in children:
                if "chrome" in child.name().lower():
                    chrome_pid = child.pid
                    break
        except Exception as e:
            print("Không tìm thấy Chrome con:", e)

        # Lock profile với PID
        Utility._lock_profile(path_lock, chrome_pid)
        
        return chrome_pid

    def _check_after_close_browser(self, path_lock, chrome_pid):
        Utility._kill_chrome(chrome_pid)
        Utility._remove_lock(path_lock)

    def _check_before_close_tool(self):
        Utility._remove_lock(self._pid_path)

    def _run_browser(self, profile: dict, row: int = 0, col: int = 0, stop_flag: bool = False):
        '''
        Phương thức khởi chạy trình duyệt (browser).

        Args:
            profile (dict): Thông tin cấu hình hồ sơ trình duyệt
                - profile_name (str): Tên hồ sơ trình duyệt.
            row (int, optional): Vị trí hàng để sắp xếp cửa sổ trình duyệt. Mặc định là 0.
            col (int, optional): Vị trí cột để sắp xếp cửa sổ trình duyệt. Mặc định là 0.
            stop_flag (multiprocessing.Value, optional): Cờ tín hiệu để dừng trình duyệt. 
                - Nếu `stop_flag` là `True`, trình duyệt sẽ duy trì trạng thái trước khi enter.
                - Nếu là `None|False`, trình duyệt sẽ tự động đóng sau khi chạy xong.

        Mô tả:
            - Hàm khởi chạy trình duyệt dựa trên thông tin hồ sơ (`profile`) được cung cấp.
            - Sử dụng phương thức `_browser` để khởi tạo đối tượng trình duyệt (`driver`).
            - Gọi phương thức `_arrange_window` để sắp xếp vị trí cửa sổ trình duyệt theo `row` và `col`.
            - Nếu `auto_handler` và `setup_handler ` được chỉ định, phương thức `_run` của lớp này sẽ được gọi để xử lý thêm logic.
            - Nêu `stop_flag` được cung cấp, trình duyệt sẽ duy trì hoạt động cho đến khi nhấn enter.
            - Sau cùng, - Đóng trình duyệt và giải phóng vị trí đã chiếm dụng bằng `_release_position`.

        Lưu ý:
            - Phương thức này có thể chạy độc lập hoặc được gọi bên trong `BrowserManager._run_multi()` và `BrowserManager._run_stop()`.
            - Đảm bảo rằng `auto_handler` (nếu có) được định nghĩa với phương thức `_run_browser()`.
        '''
        profile_name = profile['profile_name']
        proxy_info = profile.get('proxy_info')
        path_lock = self._user_data_dir / f'''{Utility._sanitize_text(profile_name)}.lock'''
        
        if not self._check_before_run_browser(path_lock=path_lock, profile_name=profile_name):
            return

        driver = None
        try:
            driver = self._browser(profile_name, proxy_info)
            chrome_pid = self._check_after_run_browser(driver=driver, path_lock=path_lock)

            self._arrange_window(driver, row, col)
            node = Node(driver, profile_name, self._tele_bot, self._ai_bot)

            handler = self._setup_handler if stop_flag else self._auto_handler
            if handler:
                handler(node, profile)

            if stop_flag:
                self._listen_for_enter(profile_name)
        except ValueError as e:
            # Node.snapshot() quăng lỗi ra đây
            pass
        except Exception as e:
            # Lỗi bất kỳ khác
            self._log(profile_name, f"Lỗi trong run_browser: {e}")

        finally:
            if driver:
                try:
                    Utility.wait_time(1, True)
                    self._log(profile_name, 'Đóng... wait')

                    driver.quit()
                except Exception as e:
                    print(f"Lỗi khi quit: {e}")
                    pass

            # Giải phóng profile
            self._check_after_close_browser(path_lock=path_lock,
                                            chrome_pid=chrome_pid)
            self._release_position(profile_name, row, col)

    def _run_multi(self, profiles: list[dict], max_concurrent_profiles: int = 1, delay_between_profiles: int = 10):
        '''
        Phương thức khởi chạy nhiều hồ sơ đồng thời

        Args:
            profiles (list[dict]): Danh sách các hồ sơ trình duyệt cần khởi chạy.
                Mỗi hồ sơ là một dictionary chứa thông tin, với key 'profile' là bắt buộc, ví dụ: {'profile': 'profile_name',...}.
            max_concurrent_profiles (int, optional): Số lượng tối đa các hồ sơ có thể chạy đồng thời. Mặc định là 1.
            delay_between_profiles (int, optional): Thời gian chờ giữa việc khởi chạy hai hồ sơ liên tiếp (tính bằng giây). Mặc định là 10 giây.
        Hoạt động:
            - Sử dụng `ThreadPoolExecutor` để khởi chạy các hồ sơ trình duyệt theo mô hình đa luồng.
            - Hàng đợi (`queue`) chứa danh sách các hồ sơ cần chạy.
            - Xác định vị trí hiển thị trình duyệt (`row`, `col`) thông qua `_get_position`.
            - Khi có vị trí trống, hồ sơ sẽ được khởi chạy thông qua phương thức `run`.
            - Nếu không có vị trí nào trống, chương trình chờ 10 giây trước khi kiểm tra lại.
        '''
        queue = [profile for profile in profiles]
        self._get_matrix(
            max_concurrent_profiles=max_concurrent_profiles,
            number_profiles=len(queue)
        )

        with ThreadPoolExecutor(max_workers=max_concurrent_profiles) as executor:
            while len(queue) > 0:
                profile = queue[0]
                profile_name = profile['profile_name']
                row, col = self._get_position(profile_name)

                if row is not None and col is not None:
                    queue.pop(0)
                    executor.submit(self._run_browser, profile, row, col)
                    # Thời gian chờ mở profile kế
                    Utility.wait_time(delay_between_profiles, True)
                else:
                    # Thời gian chờ check lại
                    Utility.wait_time(10, True)

    def _run_stop(self, profiles: list[dict]):
        '''
        Chạy từng hồ sơ trình duyệt tuần tự, đảm bảo chỉ mở một profile tại một thời điểm.

        Args:
            profiles (list[dict]): Danh sách các hồ sơ trình duyệt cần khởi chạy.
                Mỗi profile là một dictionary chứa thông tin, trong đó key 'profile' là bắt buộc. 
                Ví dụ: {'profile': 'profile_name', ...}
        Hoạt động:
            - Duyệt qua từng profile trong danh sách.
            - Hiển thị thông báo chờ 5 giây trước khi khởi chạy từng hồ sơ.
            - Gọi `_run_browser()` để chạy hồ sơ.
            - Chờ cho đến khi hồ sơ hiện tại đóng lại trước khi tiếp tục hồ sơ tiếp theo.
        '''
        self._matrix = [[None]]
        for index, profile in enumerate(profiles):
            self._log(
                profile_name=profile['profile_name'], message=f'[{index+1}/{len(profiles)}]Chờ 5s...')
            Utility.wait_time(5)

            self._run_browser(profile=profile, stop_flag=True)

    def run_menu(self, profiles: list[dict], max_concurrent_profiles: int = 4, auto: bool = False):
        '''
        Chạy giao diện dòng lệnh để người dùng chọn chế độ chạy.

        Args:
            profiles (list[dict]): Danh sách các profile trình duyệt có thể khởi chạy.
                Mỗi profile là một dictionary chứa thông tin, trong đó key 'profile_name' là bắt buộc. 
                Ví dụ: {'profile': 'profile_name', ...}
            max_concurrent_profiles (int, optional): Số lượng tối đa các hồ sơ có thể chạy đồng thời. Mặc định là 4.
            auto (bool, optional): True, bỏ qua tùy chọn menu và chạy trực tiếp `auto_handler`. Mặc định False.

        Chức năng:
            - Hiển thị menu cho phép người dùng chọn một trong các chế độ:
                1. Set up: Chọn và mở lần lượt từng profile để cấu hình.
                2. Chạy auto: Tự động chạy các profile đã cấu hình.
                3. Xóa profile: Xóa profile đã tồn tại.
                0. Thoát chương trình.
            - Khi chọn Set up, người dùng có thể chọn chạy tất cả hoặc chỉ một số profile cụ thể.
            - Khi chọn Chạy auto, chương trình sẽ khởi động tự động với số lượng profile tối đa có thể chạy đồng thời.
            - Hỗ trợ quay lại menu chính hoặc thoát chương trình khi cần.

        Hoạt đông:
            - Gọi `_run_stop()` nếu người dùng chọn Set up.
            - Gọi `_run_multi()` nếu người dùng chọn Chạy auto.

        '''
        profiles = [p for p in profiles if p.get('profile_name')]
        if not profiles:
            self._log(message=f"profiles phải là 1 list, chứa key 'profile_name'")
            return
        self._check_before_run_tool()

        # Đầu vào trước khi chạy tool

        max_concurrent_profiles = Utility.read_config('MAX_PROFLIES')
        try:
            if max_concurrent_profiles:
                max_concurrent_profiles = int(max_concurrent_profiles[0])
            else:
                max_concurrent_profiles = 4
        except (ValueError, TypeError):
            print(f'❌ Không thể đọc dữ liệu: (Sử dụng mặc định: 4)')
            for text in max_concurrent_profiles:
                print(f'    MAX_PROFLIES={text}')
            max_concurrent_profiles = 4

        # Thông báo nội dung Tool hoạt động
        print("\n"+"=" * 60)
        print(f"⚙️  Tool Automation Airdrop đang sử dụng:")
        if self._tele_bot and self._tele_bot.valid:
            print(f"{'':<4}{'📍 Tele bot:':<22}{self._tele_bot.bot_name}")
        if self._ai_bot and self._ai_bot.valid:
            print(f"{'':<4}{'📍 AI bot Gemini:':<22}{self._ai_bot.model_name}")
        if self._path_chromium:
            print(f"{'':<4}{'📍 Đường dẫn Chrome:':<22}{self._path_chromium}")
        else:
            print(f"{'':<4}{'📍 Chrome hệ thống':<22}")
        print(f"{'':<4}{'📍 Đường dẫn Profiles:':<22}{self._user_data_dir}")
        if self._extensions:
            print(f"{'':<4}{'📍 Extensions:':<22}")
            for ext in self._extensions:
                print(f"{'':<8}- {ext.name}")
        print("=" * 60+"\n")

        # Run Menu
        run_tool = True
        while run_tool:
            choice_a = None
            choice_b = None
            data_profiles = profiles
            user_data_profiles = []
            show_profiles = []
            execute_profiles = []

            if self._user_data_dir.exists() and self._user_data_dir.is_dir():
                raw_user_data_profiles = [folder.name for folder in self._user_data_dir.iterdir() if folder.is_dir()]
                
                # Thêm các profile theo thứ tự trong data_profiles trước
                for profile in data_profiles:
                    profile_name = profile['profile_name']
                    if profile_name in raw_user_data_profiles:
                        user_data_profiles.append({'profile_name': profile_name})
                # Thêm các profile còn lại không có trong profiles vào cuối
                for profile_name in raw_user_data_profiles:
                    profile = {'profile_name': profile_name}
                    if profile not in user_data_profiles:
                        user_data_profiles.append(profile)

            # Menu A
            if auto:
                choice_a = '2'
                run_tool = False
            else:
                print("[A] 📋 Chọn một tùy chọn:")
                print("   1. Set up       - Mở lần lượt từng profile để cấu hình.")
                print("   2. Chạy auto    - Tất cả profiles sau khi đã cấu hình.")
                if user_data_profiles:
                    print("   3. Xóa profile  - Xoá các profile đã tồn tại.") # đoạn này xuất hiện, nếu có tồn tại danh sách user_data_profiles ở trên
                print("   0. Thoát        - Thoát chương trình.")
                choice_a = input("Nhập lựa chọn: ")
            
            ## Xử lý A
            if choice_a in ('1', '2'):
                show_profiles = data_profiles
            elif choice_a == '3':
                if user_data_profiles:
                    show_profiles = user_data_profiles
                else:
                    Utility._print_section('LỖI: Lựa chọn không hợp lệ. Vui lòng thử lại...', "🛑")
                    continue
            elif choice_a == "0":
                run_tool = False
                Utility._print_section("THOÁT CHƯƠNG TRÌNH","❎")
                continue
            else:
                Utility._print_section('LỖI: Lựa chọn không hợp lệ. Vui lòng thử lại...', "🛑")
                continue
            
            ## Add profile đang hoạt động
            active_profiles = {}
            lock_files = list(self._user_data_dir.glob("*.lock"))
            for lock in lock_files:
                data = Utility._read_lock(lock)
                if data:
                    if Utility._is_process_alive(data.get('PYTHONPID')):
                        active_profiles[lock.name] = data.get('TOOL')
            for profile in show_profiles:
                name = profile["profile_name"]
                profile["tool"] = active_profiles.get(name, None)

            # Menu B
            if auto:
                choice_b = '0'
            else:
                print("=" * 10)
                show_profiles_len = len(show_profiles)
                if choice_a in ('1', '2'):
                    print(f"[B] 📋 Chọn các profile muốn chạy {'Set up' if choice_a == '1' else 'Auto'}:")
                    
                    if show_profiles_len == 0:
                        print(f"❌ Không tồn tại profile trong file data.txt")
                    elif show_profiles_len > 1:
                        print(f"   0. ALL ({show_profiles_len})")
                    for idx, profile in enumerate(show_profiles, start=1):
                        name =  profile['profile_name']
                        tick = '[✓]' if any(p["profile_name"] == profile["profile_name"] for p in user_data_profiles) else '[ ]'
                        tool = f"(opening... {profile['tool']})" if profile['tool'] else ''
                        print(f"   {idx}. {name:<8} {tick:<5} {tool}")
                elif choice_a in ('3'):
                    print("[B] 📋 Chọn các profile muốn xóa:")
                    if show_profiles_len == 0:
                        print(f"❌ Không tồn tại profile trong {self._user_data_dir}")
                    elif show_profiles_len > 1:
                        print(f"   0. ALL ({show_profiles_len})")
                    for idx, profile in enumerate(show_profiles, start=1):
                        name =  profile['profile_name']
                        tool = f"(opening... {profile['tool']})" if profile['tool'] else ''
                        print(f"   {idx}. {name:<8} {tool}")

                choice_b = input("Nhập số và cách nhau bằng dấu cách (nếu chọn nhiều) hoặc bất kì để quay lại: ")
            
            ## Xử lý B
            choice_b_parts = choice_b.split()
            selected_index = []
            for ch in choice_b_parts:
                if ch.isdigit():
                    index = int(ch) -1
                    if index not in selected_index and index < len(show_profiles):
                        selected_index.append(index)
                        continue
                print(f"⚠ Profile {ch} không hợp lệ, bỏ qua.")

            if not selected_index:
                Utility._print_section('LỖI: Lựa chọn không hợp lệ. Vui lòng thử lại...', "🛑")
                continue
            else: 
                # Chạy tất cả profiles
                if -1 in selected_index:
                    execute_profiles = show_profiles
                # Chạy 1 vài profiles (Lọc lại execute_profiles)
                else:
                    execute_profiles = [show_profiles[i] for i in selected_index]

            # Loại bỏ profile đang mở
            if any(p.get("tool") is not None for p in execute_profiles):
                Utility._print_section('Chương trình bỏ qua các profile đang mở ở tool khác', "🛑")
                execute_profiles = [p for p in execute_profiles if p['tool'] is not None]

            # Chạy tool
            if choice_a in ('1','2'):
                Utility._print_section("BẮT ĐẦU CHƯƠNG TRÌNH","🔄")
                if choice_a == '1':      
                    self._run_stop(execute_profiles)
                elif choice_a == '2':
                    self._run_multi(profiles=execute_profiles,
                                    max_concurrent_profiles=max_concurrent_profiles)
                Utility._print_section("KẾT THÚC CHƯƠNG TRÌNH","✅")             
            elif choice_a == '3':
                profiles_to_deleted = []
                for profile in execute_profiles:
                    # kiểm tra profile_name là string
                    if not isinstance(profile_name, str):
                        continue
                    profile_path = self._user_data_dir / profile['profile_name']
                    lock_path = self._user_data_dir / f"{profile['profile_name']}.lock"
                    for _ in range(1,3):
                        try:
                            shutil.rmtree(profile_path)
                            profiles_to_deleted.append(profile['profile_name'])
                            Utility._remove_lock(lock_path)
                            break
                        except Exception as e:
                            self._log(message=f"❌ Lỗi khi xóa profile {profile_name}: {e}")
                            lock_files = list(self._user_data_dir.glob("*.lock"))
                            for lock in lock_files:
                                data = Utility._read_lock(lock)
                                if data:
                                    if Utility._sanitize_text(DIR_PATH.name) != data.get('TOOL') and not Utility._is_process_alive(data.get('PYTHONPID')):
                                        pass
                                    else:
                                        Utility._kill_chrome(data.get('CHROMEPID'))
                                        Utility._remove_lock(lock)

                            self._log(message=f"Thử lại 2s...")
                            Utility.wait_time(2)
                Utility._print_section(f"Đã xóa profile: {profiles_to_deleted}")
        
        # Kêt thúc Tool
        self._check_before_close_tool()