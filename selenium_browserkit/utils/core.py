import time
import psutil
import random
import inspect
import re
import os
import sys
import pathlib

from pathlib import Path
from typing import List, Optional

import requests

DIR_PATH = Path(sys.argv[0]).resolve().parent

class Utility:

    @staticmethod
    def wait_time(second: float = 5, fix: bool = False) -> None:
        '''
        Đợi trong một khoảng thời gian nhất định.  Với giá trị dao động từ -50% đên 50%

        Args:
            seconds (int) = 2: Số giây cần đợi.
            fix (bool) = False: False sẽ random, True không random
        '''
        try:
            sec = float(second)
            if sec < 0:
                raise ValueError
        except (ValueError, TypeError):
            Utility._logger('SYS', f'⏰ Giá trị second không hợp lệ ({second}), dùng mặc định 5s')
            sec = 5.0

        if not fix:
            gap = 0.4
            sec = random.uniform(sec * (1 - gap), sec * (1 + gap))

        time.sleep(second)

    @staticmethod
    def timeout(second: int = 5):
        """
        Trả về một hàm kiểm tra, cho biết liệu thời gian đã vượt quá giới hạn timeout hay chưa.

        Hàm này được dùng để thay thế biểu thức lặp kiểu:
            start_time = time.time()
            while time.time() - start_time < seconds:

        Args:
            secons (int): Thời gian giới hạn tính bằng giây.

        Returns:
            Callable[[], bool]: Một hàm không tham số, trả về True nếu vẫn còn trong thời gian cho phép, False nếu đã hết thời gian.
        
        Cách dùng:
            check_timeout = timeout(5) while check_timeout(): ...
        """
        start_time = time.time()
        
        def checker():
            return time.time() - start_time < second
        
        return checker
        
    @staticmethod
    def _sanitize_text(text: str) -> str:
        """
        Biến đổi chuỗi bất kỳ thành chuỗi 'an toàn':
        - Chỉ giữ a-z, A-Z, 0-9, '_', '-'
        - Các ký tự khác thay bằng '_'
        """
        return re.sub(r'[^a-zA-Z0-9_\-]', '_', text)
    
    @staticmethod
    def _logger(profile_name: str = 'System', message: str = 'Chưa có mô tả nhật ký', show_log: bool = True):
        '''
        Ghi và hiển thị thông báo nhật ký (log)
        
        Cấu trúc log hiển thị:
            [profile_name][func_thuc_thi]: {message}
        
        Args:
            profile_name (str): tên hồ sơ hiện tại
            message (str): Nội dung thông báo log.
            show_log (bool, option): cho phép hiển thị nhật ký hay không. Mặc định: True (cho phép)
        '''
        if show_log:
            func_name = inspect.stack()[2].function
            print(f'[{profile_name}][{func_name}]: {message}')
    
    @staticmethod
    def _print_section(title: str, icon: str = "🔔"):
        print("\n"+"=" * 60)
        print(f"{icon} {title.upper()}")
        print("=" * 60+"\n")

    @staticmethod
    def _need_no_sandbox() -> bool:
        # 1. Nếu là container Docker
        if pathlib.Path("/.dockerenv").exists():
            return True

        # 2. Nếu chạy trong CI/CD
        if os.environ.get("CI") == "true":
            return True

        # 3. Nếu user không có quyền root (Linux) và không support user namespace
        if os.name == "posix" and os.geteuid() != 0:
            try:
                # check xem kernel có hỗ trợ user namespace không
                with open("/proc/sys/kernel/unprivileged_userns_clone") as f:
                    if f.read().strip() == "0":
                        return True
            except FileNotFoundError:
                # file không tồn tại => khả năng cao kernel cũ, chưa hỗ trợ
                return True

        return 
        
    @staticmethod
    def _parse_proxy(proxy_str: str):
        """
        Hỗ trợ các định dạng:
        - 38.153.152.244:9594
        - 38.153.152.244:9594@user:pass
        - user:pass@38.153.152.244:9594
        """
        # Trường hợp 1: user:pass@ip:port
        match = re.match(r"(?P<user>[^:@]+):(?P<pass>[^:@]+)@(?P<ip>[\d\.]+):(?P<port>\d+)", proxy_str)
        if match:
            return match.groupdict()
        
        # Trường hợp 2: ip:port@user:pass
        match = re.match(r"(?P<ip>[\d\.]+):(?P<port>\d+)@(?P<user>[^:@]+):(?P<pass>[^:@]+)", proxy_str)
        if match:
            return match.groupdict()
        
        # Trường hợp 3: ip:port (no auth)
        match = re.match(r"(?P<ip>[\d\.]+):(?P<port>\d+)$", proxy_str)
        if match:
            result = match.groupdict()
            result['user'] = None
            result['pass'] = None
            return result
        
        return None

    @staticmethod
    def _is_proxy_working(proxy_parts: dict|None = None):
        ''' Kiểm tra proxy có hoạt động không bằng cách gửi request đến một trang kiểm tra IP
        
        Args:
            proxy_info (str, option): thông tin proxy được truyền vào có dạng sau
                - "ip:port"
                - "username:password@ip:port"
        
        Returns:
            bool: True nếu proxy hoạt động, False nếu không.
        '''
        if not proxy_parts:
            return False
        
        if proxy_parts['user'] and proxy_parts['pass']:
            proxy_str = f"http://{proxy_parts['user']}:{proxy_parts['pass']}@{proxy_parts['ip']}:{proxy_parts['port']}"
        else:
            proxy_str = f"http://{proxy_parts['ip']}:{proxy_parts['port']}"

        proxies = {
            "http": f"{proxy_str}",
            "https": f"{proxy_str}",
        }
        
        test_url = "http://ip-api.com/json"  # API kiểm tra địa chỉ IP

        try:
            response = requests.get(test_url, proxies=proxies, timeout=5)
            if response.status_code == 200:
                print(f"✅ Proxy hoạt động! IP: {response.json().get('query')}")
                return True
            else:
                print(f"❌ Proxy {proxy_str} không hoạt động! Mã lỗi: {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"❌ Proxy {proxy_str} lỗi: {e}")
            return False

    @staticmethod
    def read_data(*field_names):
        '''
        Lấy dữ liệu từ tệp data.txt

        Args:
            *field_names: tên các trường cần lấy

        Returns:
            list: danh sách các dictionary, mỗi dictionary là một profile

        Xử lý dữ liệu:
            - Nếu parts trong dòng ít hơn field_names, field_name được gán bằng None
            - Nếu parts trong dòng nhiều hơn field_names, phần tử còn lại sẽ được gán vào `extra_fields`
            - Dữ liệu phải bắt đầu bằng `profile_name`, kết thúc bằng `extra_fields` (optional) và `proxy_info` (optional)
        '''
        data_path = DIR_PATH /'data.txt'

        if not data_path.exists():
            print(f"File {data_path} không tồn tại.")
            return []

        proxy_re = re.compile(r"^(\w+:\w+@)?\d{1,3}(?:\.\d{1,3}){3}:\d{1,5}(@\w+:\w+)?$")
        profiles = []

        with open(data_path, 'r') as file:
            data = file.readlines()

        for line in data:
            parts = [part.strip() for part in line.strip().split('|')]
            
            # Kiểm tra và tách proxy nếu có
            proxy_info = parts[-1] if proxy_re.match(parts[-1]) else None
            if proxy_info:
                parts = parts[:-1]
                
            # Kiểm tra số lượng dữ liệu
            if len(parts) < 1:
                print(f"Warning: Dữ liệu không hợp lệ - {line}")
                continue
                
            # Tạo dictionary với các trường được chỉ định
            profile = {}
            # Gán giá trị cho các field có trong parts
            for i, field_name in enumerate(field_names):
                if i < len(parts):
                    profile[field_name] = parts[i]
                else:
                    profile[field_name] = None

            profile['extra_fields'] = parts[len(field_names):]
            profile['proxy_info'] = proxy_info
            profiles.append(profile)
        
        return profiles
    
    @staticmethod
    def fake_data(numbers: int = 0):
        '''
        Sinh danh sách profile giả lập để test.

        Args:
            numbers (int): Số lượng profile cần tạo (mặc định = 0).

        Returns:
            list[dict]: Danh sách các profile dạng dict, 
                        mỗi profile chứa ít nhất khóa "profile_name".

        Ví dụ:
            >>> fake_data(3)
            [{'profile_name': '1'}, {'profile_name': '2'}, {'profile_name': '3'}]
        '''
        profiles = []
        for i in range(numbers):
            profile = {}
            profile['profile_name'] = str(i + 1)
            profiles.append(profile)
        return profiles
    
    @staticmethod
    def read_config(keyname: str) -> Optional[List]:
        """
        Lấy thông tin cấu hình từ tệp `config.txt`.

        File `config.txt` phải nằm trong cùng thư mục với tệp mã nguồn. 

        Args:
            keyname (str): Tên định danh trong file `config.txt`, ví dụ: 'USER_DATA_DIR', 'TELE_BOT', 'AI_BOT', 'MAX_PROFLIES', 'PROXY',...

        Returns:
            Optional[List]: 
                - Danh sách giá trị được lấy, không bao gồm keyname.
                - Danh sách rỗng nếu không tìm thấy dòng nào phù hợp.
                - None nếu tệp không tồn tại hoặc gặp lỗi khi đọc.
        
        Ghi chú:
            - Nếu tệp không tồn tại, sẽ ghi log và trả về None.
            - Nếu dòng không hợp lệ (ít hơn 2 phần tử), sẽ ghi cảnh báo nhưng bỏ qua dòng đó.
        """
        config_path = DIR_PATH / 'config.txt'
        results = []

        if not config_path.exists():
            return None
    
        try:
            with open(config_path, 'r',encoding='utf-8') as file:
                data = file.readlines()
            for line in data:
                if line.strip().startswith(keyname):
                    parts = line.strip().split('=', 1)
                    if len(parts) >= 2 and parts[-1]:
                        results.append(parts[-1].strip())
            
            return results
        
        except Exception as e:
            Utility._logger(message=f'Lỗi khi đọc tệp {config_path}: {e}')
            return None

    @staticmethod
    def _wait_until_profile_free(profile_name: str, lock_path: Path, timeout: int = 60):
        """
        Chờ cho đến khi profile được giải phóng (file lock không còn tồn tại).

        Args:
            lock_path (str): Đường dẫn đến file lock.
            timeout (int, optional): Thời gian chờ tối đa (giây). Mặc định là 60.

        Raises:
            TimeoutError: Nếu vượt quá thời gian chờ mà profile vẫn bị khóa.
        """
        # Cần kiểm tra có tồn tại chrome quá trình không?
        # Kiểm tra nếu file lock tồn tại quá 12h thì xóa file
        if os.path.exists(lock_path):
            try:
                print(f'🔍 Kiểm tra trạng thái 🗝️ [{profile_name}.lock]')
                ctime = os.path.getctime(lock_path)
                now = time.time()
                # Xóa lock, nếu đã tồn tại hơn 12 tiếng
                if now - ctime > 43200:  # 12h = 43200 giây
                    os.remove(lock_path)
            except Exception:
                raise 

        start_time = time.time()
        while os.path.exists(lock_path):
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Chờ quá {timeout}s nhưng [profile {profile_name}] vẫn bị khóa.")
            Utility.wait_time(10, True)
            print(f"🔒 Profile [{profile_name}] đang bận, chờ...")
    
    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        try:
            pid = int(pid)
            process = psutil.Process(pid)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False
        except Exception as e:
            print(f"Lỗi khi kiểm tra process {pid}: {e}")
            return False
    
    @staticmethod
    def _read_lock(path_lock: Path):
        """
        Đọc file lock và trả về dict chứa các cặp key=value.

        Args:
            path_lock (Path): Đường dẫn tới file lock.

        Returns:
            dict[str, str] | None: Dict dữ liệu từ file lock, 
                                   hoặc None nếu không tồn tại / lỗi.
        """
        try:
            if not path_lock.exists():
                return None

            result = {}
            with open(path_lock, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    result[k.strip().upper()] = v.strip()

            return result if result else None
        except Exception as e:
            print(f"Lỗi khi đọc lock file {path_lock}: {e}")
            return None
    
    @staticmethod
    def _kill_chrome(chrome_pid):
        """
        Kill Chrome process theo PID.

        Args:
            chrome_pid (int): PID của process Chrome.

        Returns:
            bool: True nếu kill thành công, False nếu thất bại hoặc không tìm thấy.
        """
        if not chrome_pid:
            return False

        try:
            chrome_pid = int(chrome_pid)
            proc = psutil.Process(chrome_pid)
            # Kill tất cả process con trước (tránh orphan)
            for child in proc.children(recursive=True):
                try:
                    child.kill()
                except Exception as e:
                    print(f"Lỗi khi kill child {child.pid}: {e}")
            proc.kill()
            return True
        except psutil.NoSuchProcess:
            # Chrome PID không tồn tại.
            return True
        except Exception as e:
            print(f"Lỗi khi kill Chrome PID {chrome_pid}: {e}")
            return False
    
    @staticmethod
    def _remove_lock(lock_path: str):
        """
        Xóa file lock để giải phóng profile.

        Args:
            lock_path (str): Đường dẫn đến file lock cần xóa.
        """
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except Exception as e:
                print(f"Lỗi khi xóa lock file {lock_path}: {e}")

    @staticmethod
    def _pid_python(tmp_path: Path):
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "w") as f:
            f.write(f"TOOL={Utility._sanitize_text(DIR_PATH.name)}\n")

    @staticmethod
    def _lock_profile(lock_path: Path, chrome_pid: str ):
        """
        Tạo file lock để khóa profile.

        Args:
            lock_path (str): Đường dẫn đến file lock cần tạo.
        """
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(f"CHROMEPID={chrome_pid}\n")
            f.write(f"TOOL={Utility._sanitize_text(DIR_PATH.name)}\n")
            f.write(f"PYTHONPID={os.getpid()}\n")