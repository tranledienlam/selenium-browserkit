import time
import ctypes
import subprocess
import sys

import urllib.request
from pathlib import Path
from io import BytesIO

import requests
from google import genai
from PIL import Image

from .core import Utility

class TeleHelper:
    def __init__(self) -> None:
        self.valid: bool = False
        self.bot_name = None
        self._chat_id = None
        self._token = None
        self._endpoint = None
        
        self._get_token()
        if not self.valid:
            print('❌ Telegram bot không hoạt động')

    def _check_token_valid(self) -> bool:
        if not self._token:
            return False

        url = f"{self._endpoint}/bot{self._token}/getMe"
        try:
            response = requests.get(url, timeout=5)
            data = response.json()
            if data.get("ok"):
                self.bot_name = f"@{data['result']['username']}"
                print(f"✅ Telegram bot hoạt động: {self.bot_name}")
                return True
            else:
                return False
        except Exception as e:
            return False

    def _get_token(self):
        """
        Đọc token Telegram từ file cấu hình và khởi tạo thông tin bot.

        Nếu đọc được token hợp lệ (đúng định dạng và được Telegram xác nhận),
        thì gán giá trị vào các thuộc tính:
            - self._chat_id
            - self._token
            - self._endpoint
            - self.valid = True

        Returns:
            bool: True nếu tìm thấy và xác thực được token, ngược lại False.
        """
        tokens = Utility._read_config('TELE_BOT')
        if tokens is not None:
            print(f'🛠️  Đang kiểm tra token Telegram bot...')
            for token in tokens:
                parts = [part.strip() for part in token.split('|')]
                if len(parts) >= 2:
                    self._chat_id = parts[0]
                    self._token = parts[1]
                    if len(parts) >= 3 and 'http' in parts[2]:
                        self._endpoint = parts[-1].rstrip('/')
                    else:
                        self._endpoint = 'https://api.telegram.org'
                    self.valid = self._check_token_valid()
                    if self.valid:
                        return True

            return False

    def send_photo(self, screenshot_png, message: str = 'khởi động...'):
        """
        Gửi tin nhắn đến Telegram bot. Kiểm tra token trước khi gửi.
        """
        if not self.valid or not all([self._chat_id, self._token]):
            Utility._logger(message="❌ Không thể gửi tin nhắn: Token không hợp lệ hoặc chưa được thiết lập.")
            self.valid = False
            return False

        url = f"{self._endpoint}/bot{self._token}/sendPhoto"

        
        data = {'chat_id': self._chat_id,
                'caption': message}
        # Gửi ảnh lên Telegram
        try:
            with BytesIO(screenshot_png) as screenshot_buffer:
                files = {
                    'photo': ('screenshot.png', screenshot_buffer, 'image/png')
                }
                response = requests.post(url, files=files, data=data, timeout=5)
                res_json = response.json()

                if not res_json.get("ok"):
                    Utility._logger(message=f"❌ Gửi ảnh thất bại: {res_json}")
                    self.valid = False
                    return False

                return True

        except requests.exceptions.RequestException as e:
            Utility._logger(message=f"❌ Lỗi kết nối khi gửi tin nhắn: {e}")
            self.valid = False
            return False

class AIHelper:
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Khởi tạo AI Helper với API key và model name
        
        Args:
            api_key (str): API key của Gemini
            model_name (str, optional): Tên model sử dụng. Mặc định là "gemini-2.0-flash"
            
        Returns:
            bool: True nếu AI hoạt động, False nếu không hoạt động
        """
        self.is_working = False
        self.model_name = model_name
        self.valid = False
        self._token = None
        self._client = None
        
        self._get_token()
        if not self.valid:
            print('❌ AI bot không hoạt động')

    def _check_token_valid(self) -> bool:
        try:
            client = genai.Client(api_key=self._token)
            _ = client.models.list()
            self._client = client
            print("✅ AI bot hoạt động")
            return True
        except Exception as e:
            print(f"❌ Token lỗi: {e}")
            return False
        
    def _get_token(self):
        """
        Đọc token AI Gemini từ file cấu hình và khởi tạo thông tin bot.

        Nếu đọc được token hợp lệ (đúng định dạng và được Telegram xác nhận),
        thì gán giá trị vào các thuộc tính:
            - self._chat_id
            - self._token
            - self._endpoint
            - self.valid = True

        Returns:
            bool: True nếu tìm thấy và xác thực được token, ngược lại False.
        """
        tokens = Utility._read_config('AI_BOT')
        if tokens is not None:
            print(f'🛠️  Đang kiểm tra token AI bot...')
            for token in tokens:
                self._token = token
                self.valid = self._check_token_valid()
                if self.valid:
                    return True

            return False

    @staticmethod
    def _process_image(image: Image.Image) -> Image.Image:
        """
        Xử lý ảnh để tối ưu kích thước trước khi gửi lên AI
        
        Args:
            image (Image): Ảnh cần xử lý
            
        Returns:
            Image: Ảnh đã được resize
        """
        if type(image) == bytes:
            image = Image.open(BytesIO(image))
            
        width, height = image.size
        max_size = 384
        
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))

        new_size = (new_width, new_height)
        return image.resize(new_size, Image.Resampling.LANCZOS)
    
    def ask(self, prompt: str, img_bytes: bytes | None = None) -> tuple[str | None, str | None]:
        """
        Gửi prompt và ảnh lên AI để phân tích
        
        Args:
            prompt (str): Câu hỏi hoặc yêu cầu gửi đến AI
            image (Image, optional): Ảnh cần phân tích. Nếu None, sẽ trả về None
            
        Returns:
            tuple[str | None, str | None]: 
                - Phần tử đầu tiên: Kết quả phân tích từ AI hoặc None nếu có lỗi
                - Phần tử thứ hai: Thông báo lỗi hoặc None nếu không có lỗi
        """
        result = None
        try:
            if not self._client:
                return None, "AI bot không hoạt động"
            
            if img_bytes:
                image = Image.open(BytesIO(img_bytes))
                resized_image = self._process_image(image)
                response = self._client.models.generate_content(
                                    model=self.model_name,
                                    contents=[resized_image, prompt]
                                )
            else:
                response = self._client.models.generate_content(
                                    model=self.model_name,
                                    contents=prompt
                                )
            
            result = response.text
            return result, None
            
        except Exception as e:
            error_message = str(e)
            if "INVALID_ARGUMENT" in error_message or "API key not valid" in error_message:
                return None, f"API key không hợp lệ. Vui lòng kiểm tra lại token."
            elif "blocked" in error_message.lower():
                return None, f"Prompt vi phạm chính sách nội dung - {error_message}"
            elif "permission" in error_message.lower():
                return None, f"Không có quyền truy cập API - {error_message}"
            elif "quota" in error_message.lower() or "limit" in error_message.lower():
                return None, f"Vượt quá giới hạn tài nguyên - {error_message}"
            elif "timeout" in error_message.lower() or "deadline" in error_message.lower():
                return None, f"Vượt quá thời gian xử lý - {error_message}"
            else:
                return None, f"Lỗi không xác định khi gửi yêu cầu đến AI - {error_message}"

class Chromium:
    """
    Hỗ trợ tự động tải về và giải nén trình duyệt Chromium từ GitHub, bằng công cụ 7zr.exe.

    Nguồn github: https://github.com/macchrome/winchrome/releases
    """
    def __init__(self):
        f"""
        Khởi tạo class với các tham số mặc định:
        - URL tải Chromium và công cụ 7zr.exe
        - Tên tệp nén và công cụ giải nén
        - Đường dẫn thư mục tải và thư mục đích
        """
        self._CHROMIUM_URL = "https://github.com/macchrome/winchrome/releases/download/v136.7103.97-M136.0.7103.97-r1440670-Win64/ungoogled-chromium-136.0.7103.97-1_Win64.7z"
        self._EXE_URL = "https://www.7-zip.org/a/7zr.exe"
        self._FILE_CHROMIUM = "chromium136.7z"
        self._FILE_EXE = "7zr.exe"
        self._TARGET_FOLDER_NAME = "chromium136"
        self._DOWLOAD_PATH = Path(self._get_system_drive()) / 'chromium'

        self.path = self._setup()
    
    @staticmethod
    def _get_system_drive() -> Path:
        """
        Lấy ổ hệ điều hành hiện tại (ví dụ: 'C:\', 'D:\').
        Trả về một đối tượng Path đại diện cho ổ đĩa hệ thống.
        """
        buffer = ctypes.create_unicode_buffer(260)
        ctypes.windll.kernel32.GetWindowsDirectoryW(buffer, 260)
        return Path(Path(buffer.value).drive + "\\")

    def _show_download_progress(self, block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = downloaded / total_size * 100 if total_size > 0 else 0
        percent = percent if percent < 100 else 100
        bar_len = 40
        filled_len = int(bar_len * downloaded // total_size) if total_size else 0
        bar = '=' * filled_len + '-' * (bar_len - filled_len)
        sys.stdout.write(f"\r📥 [{bar}] {percent:5.1f}%")
        sys.stdout.flush()

    def _download_file(self, file_name: str, url: str) -> Path | None:
        """
        Tải một tập tin từ URL nếu chưa tồn tại trong thư mục chỉ định.

        Args:
            file_name (str): Tên tệp cần tải.
            url (str): URL nguồn.

        Returns:
            Path | None: Trả về đường dẫn tệp nếu mới tải, None nếu tệp đã tồn tại.
        """
        file_path = self._DOWLOAD_PATH / file_name

        if file_path.exists():
            size = file_path.stat().st_size
            if size > 0:
                print(f"✅ Đã tồn tại {file_name}")
                return file_path
            else:
                print(f"❌ File lỗi ({size} bytes). Xóa file...")
                file_path.unlink(missing_ok=True)
        try:
            print(f"⬇️ Đang tải {file_name}...")
            urllib.request.urlretrieve(url, file_path, reporthook=self._show_download_progress)
            Utility.wait_time(2)
            
            if file_path.exists():
                if file_path.stat().st_size > 0:
                    print(f"✅ Tải {file_name} thành công")
                    return file_path
                else:
                    print(f"❌ File tải bị lỗi ({size} bytes). Xóa file...")
                    file_path.unlink(missing_ok=True)
            else:
                print(f"❌ Không tìm thấy {file_path} đã tải...")

        except Exception as e:
            print(f"❌ Lỗi quá trình tải: {e}")
        
        return None
    
    def _delete_file(self, file_path: Path):
        """
        Xóa một tệp nếu tồn tại.

        Args:
            file_path (Path): Đường dẫn đến tệp cần xóa.

        Returns:
            bool: True nếu xóa thành công, False nếu thất bại.
        """
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
                return True
            except Exception as e:
                print(f"❌ Không thể xóa file {file_path}: {e}")
        else:
            print(f"⚠️ File không tồn tại: {file_path}")
        return False

    def _extract_7z_with_7zr(self, file_path: Path | None, tool_extract: Path | None)-> Path | None:
        """
        Giải nén tệp `.7z` bằng công cụ `7zr.exe`, và tìm thư mục mới được tạo sau khi giải nén.

        Args:
            file_path (Path): Đường dẫn đến file `.7z`.
            tool_extract (Path): Đường dẫn đến `7zr.exe`.

        Returns:
            Path | None: Trả về thư mục mới được giải nén, hoặc None nếu thất bại.
        """
        before_folders = set(f.name for f in self._DOWLOAD_PATH.iterdir() if f.is_dir())

        timeout = time.time()+10
        if not (tool_extract and file_path):
            if not tool_extract:
               print(f"❌ tool_extract không thể là None")
            if not file_path:
               print(f"❌ file_path không thể là None") 
            return None
        
        while True:
            if tool_extract and tool_extract.exists():
                if file_path and file_path.exists() and (file_path.stat().st_size / (1024 *1024) > 100):
                    break
            if timeout - time.time() < 0:
                print(f'Lỗi không tìm thấy đủ 2 file: {self._FILE_CHROMIUM} (>100M) - {self._FILE_EXE} (500k)')
                return None
            Utility.wait_time(1)

        try:
            result = subprocess.run(
                [str(tool_extract), 'x', str(file_path), f'-o{self._DOWLOAD_PATH}', '-y'],
                capture_output=True, text=True
            )
        except Exception as e:
            Utility._logger(f'Lỗi giải nén file: {e}')
            return None
        
        if result.returncode == 0:
            print("✅ Giải nén hoàn tất.")
            self._delete_file(file_path)
            self._delete_file(tool_extract)
            after_folders = set(f.name for f in self._DOWLOAD_PATH.iterdir() if f.is_dir())
            new_folders = list(after_folders - before_folders)
            if new_folders:
                for name in new_folders:
                    if "ungoogled" in name.lower():
                        return self._DOWLOAD_PATH / name
                return self._DOWLOAD_PATH / new_folders[0]
            else:
                print("⚠️ Không tìm thấy thư mục mới.")
                return None
        else:
            print(f"❌ Giải nén lỗi: {result.stderr}")
            return None
    
    def _setup(self) -> Path | None:
        """
        Hàm chính để thiết lập trình duyệt Chromium:
        - Tạo thư mục tải nếu chưa có
        - Kiểm tra nếu thư mục đích đã tồn tại thì bỏ qua
        - Nếu chưa có, tải xuống và giải nén
        - Đổi tên thư mục giải nén thành thư mục đích

        Returns:
            Path | None: Trả về path chrome.exe, hoặc None nếu thất bại.
        """
        self._DOWLOAD_PATH.mkdir(parents=True, exist_ok=True)

        target_dir = self._DOWLOAD_PATH / self._TARGET_FOLDER_NAME
        target_chromium = target_dir / 'chrome.exe'

        if target_chromium.exists():
            return target_chromium
        else:
            chromium_path = self._download_file(self._FILE_CHROMIUM, self._CHROMIUM_URL)
            exe_path = self._download_file(self._FILE_EXE, self._EXE_URL)
            if chromium_path and exe_path:
                extracted_folder = self._extract_7z_with_7zr(chromium_path, exe_path)
                if extracted_folder:
                    extracted_chromium = extracted_folder / 'chrome.exe'
                    if (extracted_chromium).exists():
                        extracted_folder.rename(target_dir)
                        if target_chromium.exists():
                            print(f"✅ Phiên bản chromium lưu tại: {target_dir}")
                            return target_chromium
                        else:
                            print(f"❌ Không tìm thấy {target_chromium}")
                    else:
                        print(f"❌ Không tìm thấy {extracted_chromium}")
                else:
                    print(f"❌ Không tìm thấy {extracted_folder}")
            else:
                print(f"❌ Không thể thực hiện giải nén vì thiếu file.")
            
        return None
  