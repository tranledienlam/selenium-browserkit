import sys
from datetime import datetime
from typing import cast
from selenium import webdriver
from selenium.webdriver.common.window import WindowTypes
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException, ElementNotVisibleException, NoSuchWindowException, WebDriverException

from .utils import Utility, DIR_PATH
from .utils.browser_helper import TeleHelper, AIHelper

class Node:
    def __init__(self, driver: webdriver.Chrome, profile_name: str, tele_bot: TeleHelper|None = None, ai_bot: AIHelper|None = None) -> None:
        '''
        Khởi tạo một đối tượng Node để quản lý và thực hiện các tác vụ tự động hóa trình duyệt.

        Args:
            driver (webdriver.Chrome): WebDriver điều khiển trình duyệt Chrome.
            profile_name (str): Tên profile được sử dụng để khởi chạy trình duyệt
        '''
        self._driver = driver
        self._profile_name = profile_name
        self._tele_bot = tele_bot
        self._ai_bot = ai_bot
        # Khoảng thời gian đợi mặc định giữa các hành động (giây)
        self.wait = 3
        self.timeout = 30  # Thời gian chờ mặc định (giây) cho các thao tác
    
    def _get_wait(self, wait: float|None = None):
        if wait is None:
            wait = self.wait
        return wait
    
    def _get_timeout(self, timeout: float|None = None):
        if timeout is None:
            timeout = self.timeout
        return timeout
    
    def _save_screenshot(self) -> str|None:
        snapshot_dir = DIR_PATH / 'snapshot'
        screenshot_png = self.take_screenshot()
        
        if screenshot_png is None:
            return None
        
        if not snapshot_dir.exists():
            self.log(f'Không tin thấy thư mục {snapshot_dir}. Đang tạo...')
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            self.log(f'Tạo thư mục Snapshot thành công')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = str(snapshot_dir/f'{self._profile_name}_{timestamp}.png')
        try:
            with open(file_path, 'wb') as f:
                f.write(screenshot_png)

        except Exception as e:
            self.log(f'❌ Không thể ghi file ảnh: {e}')
            return None
        
        self.log(f'✅ Ảnh đã được lưu tại Snapshot')
        return file_path

    def _send_screenshot_to_telegram(self, message: str):
        screenshot_png = self.take_screenshot()
        
        if screenshot_png is None:
            return
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        message = f'[{timestamp}][{self._profile_name}] - {message}'
        if self._tele_bot and self._tele_bot.send_photo(screenshot_png, message):
            self.log(message=f"✅ Ảnh đã được gửi đến Telegram bot.")

    def _execute_node(self, node_action, *args):
        """
        Thực hiện một hành động node bất kỳ.
        Đây là function hỗ trợ thực thi node cho execute_chain

        Args:
            node_action: tên node
            *args: arg được truyền vào node
        """

        if not node_action(*args):
            return False
        return True

    def execute_chain(self, actions: list[tuple], message_error: str = 'Dừng thực thi chuỗi hành động'):
        """
        Thực hiện chuỗi các node hành động. 
        Dừng lại nếu một node thất bại.

        Args:
            actions (list[tuple]): Danh sách các tuple đại diện cho các hành động.
                Mỗi tuple có cấu trúc: 
                    (hàm_thực_thi, *tham_số_cho_hàm)
                Trong đó:
                    - `hàm_thực_thi` là một hàm được định nghĩa trong class, chịu trách nhiệm thực hiện hành động.
                    - `*tham_số_cho_hàm` là danh sách các tham số sẽ được truyền vào `hàm_thực_thi`.
                    - `stop_on_failure` (bool): Nếu False, không dừng chuỗi hành động dù hành động hiện tại thất bại. Mặc định là True

            message_error (str): Thông báo lỗi khi xảy ra thất bại trong chuỗi hành động. Nên là tên actions cụ thể của nó

        Returns:
            bool: 
                - `True` nếu tất cả các hành động đều được thực thi thành công.
                - `False` nếu có bất kỳ hành động nào thất bại.    

        Ví dụ: 
            actions = [
                (find, By.ID, 'onboarding__terms-checkbox', False), # Nếu lỗi vẫn tiếp tục
                (find_and_input, By.CSS_SELECTOR, 'button[data-testid="onboarding-import-wallet"]', False),
                (find_and_click, By.ID, 'metametrics-opt-in'),
                (find_and_click, By.CSS_SELECTOR, 'button[data-testid="metametrics-i-agree"]')
            ]

            self.execute_chain(actions, message_error="Lỗi trong quá trình thực hiện chuỗi hành động.")
        """
        for action in actions:
            stop_on_failure = True

            if isinstance(action, tuple):
                *action_args, stop_on_failure = action if isinstance(
                    action[-1], bool) else (*action, True)

                func = action_args[0]
                args = action_args[1:]

                if not callable(func):
                    self.log(f'Lỗi {func} phải là 1 function')
                    return False

            elif callable(action):
                func = action
                args = []

            else:
                self.log(
                    f"Lỗi - {action} phải là một function hoặc tuple chứa function.")
                return False

            if not self._execute_node(func, *args):
                self.log(
                    f'Lỗi {["skip "] if not stop_on_failure else ""}- {message_error}')
                if stop_on_failure:
                    return False

        return True

    def get_driver(self):
        """Trả về đối tượng Selenium WebDriver gốc để sử dụng trực tiếp"""
        return self._driver

    def log(self, message: str = 'message chưa có mô tả', show_log: bool = True):
        '''
        Ghi và hiển thị thông báo nhật ký (log)

        Cấu trúc log hiển thị:
            [profile_name][func_thuc_thi]: {message}

        Args:
            message (str, optional): Nội dung thông báo log. Mặc định là 'message chưa có mô tả'.
            show_log (bool, optional): cho phép hiển thị nhật ký hay không. Mặc định: True (cho phép).

        Mô tả:
            - Phương thức sử dụng tiện ích `Utility.logger` để ghi lại thông tin nhật ký kèm theo tên hồ sơ (`profile_name`) của phiên làm việc hiện tại.
        '''
        Utility._logger(profile_name=self._profile_name,
                       message=message, show_log=show_log)
    
    def take_screenshot(self) -> bytes|None:
        """
        Chụp ảnh màn hình hiện tại của trình duyệt.

        Returns:
            bytes | None: Ảnh chụp màn hình ở dạng bytes PNG nếu thành công,
                        None nếu xảy ra lỗi.
        """
        try:
            return self._driver.get_screenshot_as_png()
        except Exception as e:
            self.log(f'❌ Không thể chụp ảnh màn hình: {e}')
            return None

    def snapshot(self, message: str = 'Mô tả lý do snapshot', stop: bool = True):
        '''
        Ghi lại trạng thái trình duyệt bằng hình ảnh và dừng thực thi chương trình.

        Args:
            message (str, optional): Thông điệp mô tả lý do dừng thực thi. Mặc định là 'Dừng thực thi.'. Nên gồm tên function chứa nó.
            stop (bool, optional): Nếu `True`, phương thức sẽ ném ra một ngoại lệ `ValueError`, dừng chương trình ngay lập tức.

        Mô tả:
            Phương thức này sẽ ghi lại thông điệp vào log và chụp ảnh màn hình trình duyệt.
            Nếu `stop=True`, phương thức sẽ quăng lỗi `ValueError`, dừng quá trình thực thi.
            Nếu `data_tele` tồn tại, ảnh chụp sẽ được gửi lên Telegram. Nếu không, ảnh sẽ được lưu cục bộ.
        '''
        self.log(message)
        if self._tele_bot and self._tele_bot.valid:
            self._send_screenshot_to_telegram(message)
        else:
            self._save_screenshot()

        if stop:
            raise ValueError(f'{message}')

    def new_tab(self, url: str|None = None, method: str = 'script', wait: float|None = None, timeout: float|None = None):
        '''
        Mở một tab mới trong trình duyệt và (tuỳ chọn) điều hướng đến URL cụ thể.

        Args:
            url (str, optional): URL đích cần điều hướng đến sau khi mở tab mới. Mặc định là `None`.
            method (str, optional): - Phương thức điều hướng URL. Mặc định: `script`
                - `'script'` → sử dụng JavaScript để thay đổi location.
                - `'get'` → sử dụng `driver.get(url)`.
            wait (float, optional): Thời gian chờ trước khi thực hiện thao tác (tính bằng giây). Mặc định là giá trị của `self.wait`.
            timeout (float, optional): Thời gian chờ tối đa để trang tải hoàn tất (tính bằng giây). Mặc định là giá trị của `self.timeout = 20`.

        Returns:
            bool:
                - `True`: Nếu tab mới được mở và (nếu có URL) trang đã tải thành công.
                - `None`: Nếu chỉ mở tab mới mà không điều hướng đến URL.

        Raises:
            Exception: Nếu xảy ra lỗi trong quá trình mở tab mới hoặc điều hướng trang.

        Example:
            # Chỉ mở tab mới
            self.new_tab()

            # Mở tab mới và điều hướng đến Google
            self.new_tab(url="https://www.google.com")
        '''

        wait = self._get_wait(wait)
        timeout = self._get_timeout(timeout)

        Utility.wait_time(wait)

        try:
            self._driver.switch_to.new_window(WindowTypes.TAB)

            if url:
                return self.go_to(url=url, method=method, wait=1, timeout=timeout)

        except Exception as e:
            self.log(f'Lỗi khi tải trang {url}: {e}')

        return False

    def go_to(self, url: str, method: str = 'script', wait: float|None = None, timeout: float|None = None):
        '''
        Điều hướng trình duyệt đến một URL cụ thể và chờ trang tải hoàn tất.

        Args:
            url (str): URL đích cần điều hướng đến.
            method (str, optional): - Phương thức điều hướng URL. Mặc định: `script`
                - `'script'` → sử dụng JavaScript để thay đổi location.
                - `'get'` → sử dụng `driver.get(url)`.
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.
            timeout (float, optional): Thời gian chờ tải trang, mặc định là giá trị của `self.timeout = 20`.

        Returns:
            bool:
                - `True`: nếu trang tải thành công.
                - `False`: nếu có lỗi xảy ra trong quá trình tải trang.
        '''
        wait = self._get_wait(wait)
        timeout = self._get_timeout(timeout)

        methods = ['script', 'get']
        Utility.wait_time(wait)
        if method not in methods:
            self.log(f'Gọi url sai phương thức. Chỉ gồm [{methods}]')
            return False
        try:
            if method == 'get':
                self._driver.get(url)
            elif method == 'script':
                self._driver.execute_script(f"window.location.href = '{url}';")

            WebDriverWait(self._driver, timeout).until(
                lambda driver: driver.execute_script(
                    "return document.readyState") == 'complete'
            )
            self.log(f'Trang {url} đã tải thành công.')
            return True

        except Exception as e:
            self.log(f'Lỗi - Khi tải trang "{url}": {e}')

            return False

    def wait_for_disappear(
        self,
        by: str,
        value: str,
        parent_element: WebElement|None = None,
        wait: float|None = None,
        timeout: float|None = None,
        show_log: bool = True
    ) -> bool:
        """
        Chờ cho đến khi phần tử (thường là loading spinner hoặc overlay) biến mất.

        Args:
            by (str): Kiểu định vị phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: tên ID, đường dẫn XPath, v.v.).
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa để chờ (đơn vị: giây). Mặc định sử dụng giá trị `self.timeout = 20`.
            show_log (bool, optional): Có log ra hay không.

        Returns:
            bool: 
                - True nếu phần tử biến mất (tức là hoàn tất loading).
                - False nếu hết timeout mà phần tử vẫn còn (coi như lỗi).
        """
        wait = self._get_wait(wait)
        timeout = timeout if timeout is not None else self.timeout

        Utility.wait_time(wait)
        search_context = parent_element if parent_element else self._driver

        check_timeout = Utility.timeout(timeout)
        wait_log = True
        try:
            while check_timeout():
                try:
                    element = search_context.find_element(by, value)
                    if not element.is_displayed():
                        if show_log:
                            self.log(f"✅ Phần tử ({by}, {value}) đã biến mất.")
                        return True
                    else:
                        if show_log and wait_log:
                            wait_log = False
                            self.log(f'⏳ Đang chờ ({by}, {value}) biến mất.')
                except (StaleElementReferenceException, NoSuchElementException):
                    # Element không còn tồn tại trong DOM → coi là đã biến mất
                    if show_log:
                        self.log(f"✅ Phần tử ({by}, {value}) không còn trong DOM.")
                    return True

                Utility.wait_time(0.5)

            if show_log:
                self.log(f"⏰ Timeout - Phần tử ({by}, {value}) vẫn còn sau {timeout}s.")
            return False

        except Exception as e:
            self.log(f"❌ Lỗi khi chờ phần tử biến mất ({by}, {value}): {e}")
            return False
        
    def get_url(self, wait: float|None = None):
        '''
        Phương thức lấy url hiện tại

        Args:
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.

        Returns:
            Chuỗi str URL hiện tại
        '''
        wait = self._get_wait(wait)

        Utility.wait_time(wait, True)
        return self._driver.current_url

    def find(self, by: str, value: str, parent_element: WebElement|None = None, wait: float|None = None, timeout: float|None = None, show_log: bool = True):
        '''
        Phương thức tìm một phần tử trên trang web trong khoảng thời gian chờ cụ thể.

        Args:
            by (By|str): Kiểu định vị phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: tên ID, đường dẫn XPath, v.v.).
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa chờ phần tử xuất hiện (đơn vị: giây). Mặc định sử dụng giá trị `self.timeout = 20`.

        Returns:
            WebElement | bool:
                - WebElement: nếu tìm thấy phần tử.
                - `None`: nếu không tìm thấy hoặc xảy ra lỗi.
        '''
        wait = self._get_wait(wait)
        timeout = self._get_timeout(timeout)

        Utility.wait_time(wait)
        try:
            search_context = parent_element if parent_element else self._driver
            element = WebDriverWait(search_context, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            self.log(message=f'Tìm thấy phần tử ({by}, {value})', show_log=show_log)
            return element

        except TimeoutException:
            self.log(
                f'Lỗi - Không tìm thấy phần tử ({by}, {value}) trong {timeout}s')
        except StaleElementReferenceException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) đã bị thay đổi hoặc bị loại bỏ khỏi DOM')
        except Exception as e:
            self.log(
                f'Lỗi - không xác định khi tìm phần tử ({by}, {value}) {e}')

        return None
    
    def finds(self, by: str, value: str, parent_element: WebElement|None = None, wait: float|None = None, timeout: float|None = None, show_log: bool = True):
        '''
        Phương thức tìm tất cả các phần tử trên trang web trong khoảng thời gian chờ cụ thể.

        Args:
            by (By | str): Kiểu định vị phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: tên ID, đường dẫn XPath, v.v.).
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi điều hướng, mặc định là giá trị của `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa chờ phần tử xuất hiện (đơn vị: giây). Mặc định sử dụng giá trị `self.timeout = 20`.

        Returns:
            list[WebElement]: Danh sách các phần tử tìm thấy.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)
        Utility.wait_time(wait)

        try:
            search_context = parent_element if parent_element else self._driver
            elements = WebDriverWait(search_context, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )   
            self.log(message=f'Tìm thấy {len(elements)} phần tử ({by}, {value})', show_log=show_log)
            return elements

        except TimeoutException:
            self.log(f'Lỗi - Không tìm thấy phần tử ({by}, {value}) trong {timeout}s')
        except StaleElementReferenceException:  
            self.log(f'Lỗi - Phần tử ({by}, {value}) đã bị thay đổi hoặc bị loại bỏ khỏi DOM')
        except Exception as e:
            self.log(f'Lỗi - không xác định khi tìm phần tử ({by}, {value}) {e}')

        return []   
    
    def find_in_shadow(self, selectors: list[tuple[str, str]], wait: float|None = None, timeout: float|None = None):
        '''
        Tìm phần tử trong nhiều lớp shadow-root.

        Args:
            selectors (list[tuple[str, str]]): Danh sách selectors để truy cập shadow-root.
            wait (float, optional): Thời gian chờ giữa các bước.
            timeout (float, optional): Thời gian chờ tối đa khi tìm phần tử.

        Returns:
            WebElement | None: Trả về phần tử cuối cùng nếu tìm thấy, ngược lại trả về None.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)
        Utility.wait_time(wait)

        if not isinstance(selectors, list) or len(selectors) < 2:
            self.log("Lỗi - Selectors không hợp lệ (phải có ít nhất 2 phần tử).")
            return None

        try:
            if not isinstance(selectors[0], tuple) and len(selectors[0]) != 2:
                self.log(
                    f"Lỗi - Selector {selectors[0]} phải có ít nhất 2 phần tử (pt1,pt2)).")
                return None

            element = WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located(selectors[0])
            )

            for i in range(1, len(selectors)):
                if not isinstance(selectors[i], tuple) and len(selectors[i]) != 2:
                    self.log(
                        f"Lỗi - Selector {selectors[i]} phải có ít nhất 2 phần tử (pt1,pt2)).")
                    return None
                try:
                    shadow_root = self._driver.execute_script(
                        "return arguments[0].shadowRoot", element)
                    if not shadow_root:
                        self.log(
                            f"⚠️ Không tìm thấy shadowRoot của {selectors[i-1]}")
                        return None

                    element = cast(
                        WebElement, shadow_root.find_element(*selectors[i]))

                except NoSuchElementException:
                    self.log(f"Lỗi - Không tìm thấy phần tử: {selectors[i]}")
                    return None
                except Exception as e:
                    self.log(
                        f'Lỗi - không xác định khi tìm phần tử {selectors[1]} {e}')
                    return None

            self.log(f'Tìm thấy phần tử {selectors[-1]}')
            return element

        except TimeoutException:
            self.log(
                f'Lỗi - Không tìm thấy phần tử {selectors[0]} trong {timeout}s')
        except StaleElementReferenceException:
            self.log(
                f'Lỗi - Phần tử {selectors[0]} đã bị thay đổi hoặc bị loại bỏ khỏi DOM')
        except Exception as e:
            self.log(
                f'Lỗi - không xác định khi tìm phần tử {selectors[0]} {e}')

        return None

    def finds_by_text(self, text: str, parent_element: WebElement | None = None, wait: float | None = None, timeout: float | None = None, show_log: bool = True) -> list[WebElement]:
        '''
        Tìm tất cả phần tử chứa đoạn text cho trước, bất kể thẻ nào (div, p, span,...).

        Args:
            text (str): Nội dung cần tìm (sẽ tìm theo contains, không phân biệt tag).
            by (str): Kiểu định vị phần tử, mặc định là By.XPATH.
            parent_element (WebElement, optional): Nếu có, tìm trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi tìm.
            timeout (float, optional): Thời gian chờ tối đa để tìm phần tử.
            show_log (bool, optional): Có hiển thị log hay không.

        Returns:
            list[WebElement]: Danh sách phần tử chứa đoạn text.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)
        Utility.wait_time(wait)

        # XPath để tìm phần tử chứa đoạn text
        value = f'.//*[contains(normalize-space(.), "{text}")]' if parent_element else f'//*[contains(normalize-space(.), "{text}")]'

        try:
            search_context = parent_element if parent_element else self._driver
            elements = WebDriverWait(search_context, timeout).until(
                EC.presence_of_all_elements_located((By.XPATH, value))
            )
            self.log(message=f'🔍 Tìm thấy {len(elements)} phần tử chứa "{text}"', show_log=show_log)
            return elements

        except TimeoutException:
            self.log(f'❌ Không tìm thấy phần tử chứa "{text}" trong {timeout}s', show_log=show_log)
        except StaleElementReferenceException:
            self.log(f'⚠️ Phần tử chứa "{text}" đã bị thay đổi trong DOM', show_log=show_log)
        except Exception as e:
            self.log(f'❗ Lỗi khi tìm phần tử chứa "{text}": {e}', show_log=show_log)

        return []

    def has_texts(self, texts: str | list[str] | set[str], wait: float | None = None, show_log: bool = True) -> list[str]:
        """
        Kiểm tra nhanh các đoạn text có tồn tại trên trang.
        Không chờ load, chỉ query DOM tức thì. 
        
        Args: 
            texts (str | list[str] | set[str]): nội dung cần tìm.
            wait (float, optional): Thời gian chờ trước khi kiểm tra (giây).
            show_log (bool, optional): Có hiển thị log hay không. 
        
        Returns: 
            list[str]: Danh sách nội dung thực sự tồn tại trên trang.
        """
        wait = self._get_wait(wait)
        Utility.wait_time(wait)
        if isinstance(texts, str):
            texts = [texts]
        else:
            texts = list(texts)

        found = []
        for text in texts:
            value = f'//*[contains(normalize-space(.), "{text}")]'
            elements = self._driver.find_elements(By.XPATH, value)
            if elements:
                found.append(text)

        if found:
            self.log(f'🔍 Tìm thấy nội dung: {found}', show_log=show_log)
        else:
            self.log(f'🔍 Không tìm thấy nội dung: {texts}', show_log=show_log)

        return found
    
    def click(self, element: WebElement|None = None, wait: float|None = None) -> bool:
        '''
        Nhấp vào một phần tử trên trang web.

        Args:
            value (WebElement): Phần tử cần nhấp.
            wait (float, optional): Thời gian chờ (giây) trước khi nhấp. Mặc định là `self.wait`.

        Returns:
            bool: 
                - `True`: nếu nhấp thành công.
                - `False`: nếu gặp lỗi.

        Ghi chú:
            - Gọi `.click()` trên phần tử sau khi chờ thời gian ngắn (nếu được chỉ định).
            - Ghi log kết quả thao tác hoặc lỗi gặp phải.
        '''
        wait = self._get_wait(wait)
        Utility.wait_time(wait)
        
        try:
            if element is None:
                self.log('❌ Không có phần tử để click (element is None)')
                return False
            element.click()
            self.log(f'Click phần tử thành công')
            return True

        except ElementClickInterceptedException:
                self.log('❌ Lỗi - Element bị chặn hoặc bị che, không thể nhấp được.')

        except ElementNotInteractableException:
            self.log('❌ Lỗi - Element không tương tác được (ẩn hoặc bị disable).')

        except StaleElementReferenceException:
            self.log('❌ Lỗi - Element không còn tồn tại hoặc DOM đã thay đổi.')

        except WebDriverException as e:
            self.log(f'❌ WebDriver lỗi khi click phần tử: {str(e)}')

        except Exception as e:
            self.log(f'❌ Lỗi không xác định khi click: {str(e)}')
    
        return False
    
    def find_and_click(self, by: str, value: str, parent_element: WebElement|None = None, wait: float|None = None, timeout: float|None = None) -> bool:
        '''
        Phương thức tìm và nhấp vào một phần tử trên trang web.

        Args:
            by (By | str): Kiểu định vị phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: tên ID, đường dẫn XPath, v.v.).
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi thực hiện thao tác nhấp. Mặc định sử dụng giá trị `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa để chờ phần tử có thể nhấp được. Mặc định sử dụng giá trị `self.timeout = 20`.

        Returns:
            bool: 
                `True`: nếu nhấp vào phần tử thành công.
                `False`: nếu gặp lỗi.

        Mô tả:
            - Phương thức sẽ tìm phần tử theo phương thức `by` và `value`.
            - Sau khi tìm thấy phần tử, phương thức sẽ đợi cho đến khi phần tử có thể nhấp được (nếu cần).
            - Sau khi phần tử có thể nhấp, sẽ tiến hành nhấp vào phần tử đó.
            - Nếu gặp lỗi, sẽ ghi lại thông báo lỗi cụ thể.
            - Nếu gặp lỗi liên quan đến Javascript (LavaMoat), phương thức sẽ thử lại bằng cách tìm phần tử theo cách khác.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)

        try:
            search_context = parent_element if parent_element else self._driver
            
            element = WebDriverWait(search_context, timeout). until(
                EC.element_to_be_clickable((by, value))
            )

            Utility.wait_time(wait)
            element.click()
            self.log(f'Click phần tử ({by}, {value}) thành công')
            return True

        except TimeoutException:
            self.log(
                f'Lỗi - Không tìm thấy phần tử ({by}, {value}) trong {timeout}s')
        except StaleElementReferenceException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) đã thay đổi hoặc không còn hợp lệ')
        except ElementClickInterceptedException:
            self.log(
                f'Lỗi - Không thể nhấp vào phần tử phần tử ({by}, {value}) vì bị che khuất hoặc ngăn chặn')
        except ElementNotInteractableException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) không thể tương tác, có thể bị vô hiệu hóa hoặc ẩn')
        except Exception as e:
            # Thử phương pháp click khác khi bị lỗi từ Javascript
            if 'LavaMoat' in str(e):
                try:
                    element = WebDriverWait(search_context, timeout).until(
                        EC.presence_of_element_located((by, value))
                    )
                    Utility.wait_time(wait)
                    element.click()
                    self.log(f'Click phần tử ({by}, {value}) thành công (PT2)')
                    return True
                except ElementClickInterceptedException as e:
                    error_msg = e.msg.split("\n")[0] if e.msg else str(e)
                    self.log(
                        f'Lỗi - Không thể nhấp vào phần tử phần tử ({by}, {value}) vì bị che khuất hoặc ngăn chặn: {error_msg}')
                except Exception as e:
                    self.log(f'Lỗi - Không xác định ({by}, {value}) (PT2) {e}')
            else:
                self.log(f'Lỗi - Không xác định ({by}, {value}) {e}')

        return False

    def find_and_input(self, by: str, value: str, text: str, parent_element: WebElement|None = None, delay: float = 0.2, wait: float|None = None, timeout: float|None = None):
        '''
        Phương thức tìm và điền văn bản vào một phần tử trên trang web.

        Args:
            by (By | str): Kiểu định vị phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: tên ID, đường dẫn XPath, v.v.).
            text (str): Nội dung văn bản cần nhập vào phần tử.
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            delay (float): Thời gian trễ giữa mỗi ký tự khi nhập văn bản. Mặc định là 0.2 giây.
            wait (float, optional): Thời gian chờ trước khi thực hiện thao tác nhấp. Mặc định sử dụng giá trị `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa để chờ phần tử có thể nhấp được. Mặc định sử dụng giá trị self.timeout = 20.

        Returns:
            bool: 
                `True`: nếu nhập văn bản vào phần tử thành công.
                `False`: nếu gặp lỗi trong quá trình tìm hoặc nhập văn bản.

        Mô tả:
            - Phương thức sẽ tìm phần tử theo phương thức `by` và `value`.
            - Sau khi tìm thấy phần tử và đảm bảo phần tử có thể tương tác, phương thức sẽ thực hiện nhập văn bản `text` vào phần tử đó.
            - Văn bản sẽ được nhập từng ký tự một, với thời gian trễ giữa mỗi ký tự được xác định bởi tham số `delay`.
            - Nếu gặp lỗi, sẽ ghi lại thông báo lỗi cụ thể.
            - Nếu gặp lỗi liên quan đến Javascript (LavaMoat), phương thức sẽ thử lại bằng cách tìm phần tử theo cách khác.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)

        if not text:
            self.log(f'Không có text để nhập vào input')
            return False
        try:
            search_context = parent_element if parent_element else self._driver
            
            element = WebDriverWait(search_context, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            Utility.wait_time(wait)

            for ch in text:
                Utility.wait_time(delay)
                ActionChains(self._driver).send_keys_to_element(element, ch).perform()
            self.log(f'Nhập văn bản phần tử ({by}, {value}) thành công')
            return True

        except TimeoutException:
            self.log(
                f'Lỗi - Không tìm thấy phần tử ({by}, {value}) trong {timeout}s')
        except StaleElementReferenceException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) đã bị thay đổi hoặc bị loại bỏ khỏi DOM')
        except ElementNotVisibleException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) có trong DOM nhưng không nhìn thấy. ví dụ display: none hoặc visibility: hidden')
        except Exception as e:
            # Thử phương pháp click khác khi bị lỗi từ Javascript
            if 'LavaMoat' in str(e):
                try:
                    element = WebDriverWait(search_context, timeout).until(
                        EC.presence_of_element_located((by, value))
                    )
                    Utility.wait_time(wait)
                    cmd_ctrl = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
                    
                    for ch in text:
                        Utility.wait_time(delay)
                        ActionChains(self._driver).send_keys_to_element(element, ch).perform()
                    self.log(f'Nhập văn bản phần tử ({by}, {value}) thành công (PT2)')
                
                except Exception as e:
                    self.log(f'Lỗi - không xác định ({by}, {value}) {e}')
            
            else:
                self.log(f'Lỗi - không xác định ({by}, {value}) {e}')

        return False
    def press_key(self, key: str, parent_element: WebElement|None = None, wait: float|None = None, timeout: float|None = None):
        '''
        Phương thức nhấn phím trên trang web.

        Args:
            key (str): Phím cần nhấn (ví dụ: 'Enter', 'Tab', 'a', '1', etc.)
            parent_element (WebElement, optional): Phần tử cụ thể để nhấn phím. Mặc định là None (nhấn trên toàn trang).
            wait (float, optional): Thời gian chờ trước khi nhấn phím. Mặc định là self.wait.
            timeout (float, optional): Thời gian chờ tối đa. Mặc định là self.timeout.

        Returns:
            bool: True nếu nhấn phím thành công, False nếu có lỗi.

        Ví dụ:
            # Nhấn Enter trên toàn trang
            node.press_key('Enter')
            
            # Nhấn Tab trong một element cụ thể
            element = node.find(By.ID, 'search')
            node.press_key('Tab', parent_element=element)
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)
        
        try:
            Utility.wait_time(wait)
            
            # Lấy key từ class Keys nếu có
            key_to_press = getattr(Keys, key.upper(), key)
        
            if parent_element:
                # Nhấn phím trong element cụ thể
                if parent_element.is_displayed():
                     ActionChains(self._driver).send_keys_to_element(parent_element, key_to_press).perform()
                else:
                    self.log(f"⚠️ Element không hiển thị, không thể nhấn phím {key}")
                    return False
            else:
                # Nhấn phím trên toàn trang bằng ActionChains
                ActionChains(self._driver).send_keys(key_to_press).perform()
            
            self.log(f'Nhấn phím {key} thành công')
            return True
            
        except AttributeError:
            self.log(f'Lỗi - Phím {key} không hợp lệ')
        except Exception as e:
            self.log(f'Lỗi - Không thể nhấn phím {key}: {e}')
        
        return False

    def get_text(self, by, value, parent_element: WebElement|None = None, wait: float|None = None, timeout: float|None = None):
        '''
        Phương thức tìm và lấy văn bản từ một phần tử trên trang web.

        Args:
            by (By | str): Phương thức xác định cách tìm phần tử (ví dụ: By.ID, By.CSS_SELECTOR, By.XPATH).
            value (str): Giá trị tương ứng với phương thức tìm phần tử (ví dụ: ID, đường dẫn XPath, v.v.).
            parent_element (WebElement, optional): Nếu có, tìm phần tử con bên trong phần tử này.
            wait (float, optional): Thời gian chờ trước khi thực hiện thao tác lấy văn bản, mặc định sử dụng giá trị `self.wait = 3`.
            timeout (float, optional): Thời gian tối đa để chờ phần tử hiển thị, mặc định sử dụng giá trị `self.timeout = 20`.

        Returns:
            str: Văn bản của phần tử nếu lấy thành công.
            `None`: Nếu không tìm thấy phần tử hoặc gặp lỗi.

        Mô tả:
            - Phương thức tìm phần tử trên trang web theo `by` và `value`.
            - Sau khi đảm bảo phần tử tồn tại, phương thức sẽ lấy văn bản từ phần tử và loại bỏ khoảng trắng thừa bằng phương thức `strip()`.
            - Nếu phần tử chứa văn bản, phương thức trả về văn bản đó và ghi log thông báo thành công.
            - Nếu gặp lỗi liên quan đến Javascript (LavaMoat), phương thức sẽ thử lại bằng cách tìm phần tử theo cách khác.
        '''
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)

        Utility.wait_time(wait)
        try:
            search_context = parent_element if parent_element else self._driver
            
            element = WebDriverWait(search_context, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            text = element.text.strip()

            if text:
                self.log(
                    f'Tìm thấy văn bản "{text}" trong phần tử ({by}, {value})')
                return text
            else:
                self.log(f'Lỗi - Phần tử ({by}, {value}) không chứa văn bản')

        except TimeoutException:
            self.log(
                f'Lỗi - Không tìm thấy phần tử ({by}, {value}) trong {timeout}s')
        except StaleElementReferenceException:
            self.log(
                f'Lỗi - Phần tử ({by}, {value}) đã bị thay đổi hoặc bị loại bỏ khỏi DOM')
        except Exception as e:
            self.log(
                f'Lỗi - Không xác định khi tìm văn bản trong phần tử ({by}, {value})')

        return None

    def switch_tab(self, value: str, type: str = 'url', wait: float|None = None, timeout: float|None = None, show_log: bool = True) -> bool:
        '''
        Chuyển đổi tab dựa trên tiêu đề hoặc URL.

        Args:
            value (str): Giá trị cần tìm kiếm (URL hoặc tiêu đề).
            type (str, optional): 'title' hoặc 'url' để xác định cách tìm kiếm tab. Mặc định là 'url'
            wait (float, optional): Thời gian chờ trước khi thực hiện hành động.
            timeout (float, optional): Tổng thời gian tối đa để tìm kiếm.
            show_log (bool, optional): Hiển thị nhật ký ra bênngoài. Mặc định là True

        Returns:
            bool: True nếu tìm thấy và chuyển đổi thành công, False nếu không.
        '''
        types = ['title', 'url']
        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)
        found = False

        if type not in types:
            self.log('Lỗi - Tìm không thành công. {type} phải thuộc {types}')
            return found
        Utility.wait_time(wait)
        try:
            current_handle = self._driver.current_window_handle
            current_title = self._driver.title
            current_url = self._driver.current_url
        except Exception as e:
            # Tab hiện tịa đã đóng, chuyển đến tab đầu tiên
            try:
                current_handle = self._driver.window_handles[0]
            except Exception as e:
                self.log(f'Lỗi không xác đinh: current_handle {e}')
        check_timeout = Utility.timeout(timeout)
        try:
            while check_timeout():
                for handle in self._driver.window_handles:
                    self._driver.switch_to.window(handle)

                    if type == 'title':
                        find_window = self._driver.title.lower()
                        match_found = (value.lower() in find_window)
                    elif type == 'url':
                        find_window = self._driver.current_url.lower()
                        match_found = find_window.startswith(value.lower())

                    if match_found:
                        found = True
                        self.log(
                            message=f'Đã chuyển sang tab: {self._driver.title} ({self._driver.current_url})',
                            show_log=show_log
                        )
                        return found

                Utility.wait_time(2)

            # Không tìm thấy → Quay lại tab cũ
            self._driver.switch_to.window(current_handle)
            self.log(
                message=f'Lỗi - Không tìm thấy tab có [{type}: {value}] sau {timeout}s.',
                show_log=show_log
            )
        except NoSuchWindowException as e:
            self.log(
                message=f'Tab hiện tại đã đóng: {current_title} ({current_url})',
                show_log=show_log
            )
        except Exception as e:
            self.log(message=f'Lỗi - Không xác định: {e}', show_log=show_log)

        return found

    def reload_tab(self, wait: float|None = None):
        '''
        Làm mới tab hiện tại

        Args:
            wait (float, optional): Thời gian chờ trước khi thực hiện reload, mặc định sử dụng giá trị `self.wait = 3`.
        '''
        wait = self._get_wait(wait)

        Utility.wait_time(wait)
                
        try:
            self._driver.refresh()
        except:
            self._driver.execute_script("window.location.reload();")
        
        self.log('Tab đã reload')


    def close_tab(self, value: str|None = None, type: str = 'url', wait: float|None = None, timeout: float|None = None) -> bool:
        '''
        Đóng tab hiện tại hoặc tab cụ thể dựa trên tiêu đề hoặc URL.

        Args:
            value (str, optional): Giá trị cần tìm kiếm (URL hoặc tiêu đề).
            type (str, optional): 'title' hoặc 'url' để xác định cách tìm kiếm tab. Mặc định: 'url'
            wait (float, optional): Thời gian chờ trước khi thực hiện hành động.
            timeout (float, optional): Tổng thời gian tối đa để tìm kiếm.

        Returns:
            bool: True nếu đóng tab thành công, False nếu không.
        '''

        timeout = self._get_timeout(timeout)
        wait = self._get_wait(wait)

        current_handle = self._driver.current_window_handle
        all_handles = self._driver.window_handles

        Utility.wait_time(wait)
        # Nếu chỉ có 1 tab, không thể đóng
        if len(all_handles) < 2:
            self.log(f'❌ Chỉ có 1 tab duy nhất, không thể đóng')
            return False

        # Nếu không nhập `value`, đóng tab hiện tại & chuyển về tab trước
        if not value:
            Utility.wait_time(wait)

            self.log(
                f'Đóng tab: {self._driver.title} ({self._driver.current_url})')
            self._driver.close()

            previous_index = all_handles.index(current_handle) - 1
            self._driver.switch_to.window(all_handles[previous_index])
            return True

        # Nếu có `value`, tìm tab theo tiêu đề hoặc URL
        if self.switch_tab(value=value, type=type, show_log=False):
            found_handle = self._driver.current_window_handle

            self.log(
                f'Đóng tab: {self._driver.title} ({self._driver.current_url})')
            self._driver.close()

            if current_handle == found_handle:
                previous_index = all_handles.index(current_handle) - 1
                self._driver.switch_to.window(all_handles[previous_index])
            else:
                self._driver.switch_to.window(current_handle)

            return True

        self.log(f"❌ Không tìm thấy tab có {type}: {value}.")
        return False
    
    def scroll_to_element(self, element: WebElement, wait: float|None = None):
        '''
        Phương thức cuộn đến phần tử cụ thể được chỉ định.

        Args:
            element (WebElement): Phần tử muốn cuộn tới.
            wait (float, optional): Thời gian chờ trước khi cuộn, mặc định là giá trị của `self.wait`.

        Returns:
            bool: True, cuộn thành công. False khi gặp lỗi
            
        Mô tả:
            Phương thức sẽ nhận vào 1 element cụ thể, sau đó dùng driver.execute_script() để thực thi script
        '''
        wait = self._get_wait(wait)

        Utility.wait_time(wait)
        try:
            self._driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            self.log(f'Cuộn đến {element} thành công')
            return True
        
        except NoSuchWindowException:
            self.log(f'Không thể cuộn. Cửa sổ đã đóng')
        except Exception as e:
            self.log(f'❌ Lỗi - không xác định khi cuộn: {e}')
            
        return False

    def scroll_to_position(self, position: str = "end", wait: float | None = None) -> bool:
        """
        Phương thức cuộn đến vị trí của trang.

        Args:
            position (str): Vị trí muốn cuộn đến. 
                            Có thể là "top", "middle", "end".
            wait (float, optional): Thời gian chờ trước khi cuộn, mặc định là giá trị của `self.wait

        Returns:
            bool: True nếu cuộn thành công, False nếu lỗi.

        Mô tả:
            Phương thức sẽ nhận vào 1 element cụ thể, sau đó dùng driver.execute_script() để thực thi script
        """
        wait = self._get_wait(wait)
        Utility.wait_time(wait)
        try:
            if position == "top":
                self._driver.execute_script("window.scrollTo(0, 0);")
            elif position == "middle":
                self._driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight/2);"
                )
            elif position == "end":
                self._driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
            else:
                self.log(f"Vị trí {position} không hợp lệ (chỉ hỗ trợ top/middle/end)")
                return False

            self.log(f"Cuộn đến vị trí {position} thành công")
            return True
        except NoSuchWindowException:
            self.log("Không thể cuộn. Cửa sổ đã đóng")
        except Exception as e:
            self.log(f"Lỗi khi cuộn trang: {e}")
        return False

    def ask_ai(self, prompt: str, is_image: bool = True, wait: float|None = None) -> str|None:
        '''
        Gửi prompt và hình ảnh (nếu có) đến AI để phân tích và nhận kết quả.

        Args:
            prompt (str): Câu hỏi hoặc yêu cầu gửi đến AI
            is_image (bool, optional):  Nếu True, sẽ chụp ảnh màn hình hiện tại và gửi kèm. 
                                        Nếu False, chỉ gửi prompt không kèm ảnh.
            wait (float, optional): Thời gian chờ trước khi thực hiện hành động.

        Returns:
            str: Kết quả phân tích từ AI. Trả về None nếu có lỗi xảy ra.
        '''
        wait = self._get_wait(wait)

        if not self._ai_bot or not self._ai_bot.valid:
            self.log(f'AI bot không hoạt động')
            return None
        
        self.log(f'AI đang suy nghĩ...')
        Utility.wait_time(wait)

        result, error = None, None
        if is_image:
            try:
                img_bytes = self._driver.get_screenshot_as_png()
                result, error = self._ai_bot.ask(prompt, img_bytes)
            except Exception as e:
                error = f'Không thể chụp hình ảnh gửi đến AI bot'
        else:   
            result, error =  self._ai_bot.ask(prompt)
        
        if error:
            self.log(message=f'{error}')
            return None
        
        if result:
            self.log(f'AI đã trả lời: "{result[:10]}{"..." if len(result) > 10 else ''}"')

        return result
        
    def _check_window_handles(self):
        Utility.wait_time(5, True)
        original_handle = self._driver.current_window_handle
        window_handles = self._driver.window_handles

        print("Danh sách các cửa sổ/tab đang hoạt động:", window_handles)
        # handle là ID, ví dụ có 2 page ['433E0A85799F602DFA5CE74CA1D00682', '2A6FD93FC931056CCF842DF11782C45B']
        for handle in self._driver.window_handles:
            self._driver.switch_to.window(handle)
            print(f'{self._driver.title} - {self._driver.current_url}')

        self._driver.switch_to.window(original_handle)
        print(f'Hiện đang ở {self._driver.title}')
