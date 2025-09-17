from selenium_browserkit import BrowserManager, Node, By, Utility
from selenium_browserkit.utils.core import DIR_PATH

class Auto:
    def __init__(self, node: Node, profile: dict) -> None:
        self.node = node
        self.profile = profile
    
        self.logic()
    def logic(self):
        # Điều hướng
        self.node.go_to("https://www.saucedemo.com")
        
        # Nhập text
        self.node.find_and_input(By.ID, "user-name", self.profile.get('username'))
        self.node.find_and_input(By.ID, "password", self.profile.get('password'))
        self.node.find_and_click(By.ID, "login-button")
        
        # Chụp màn hình và lưu lại
        self.node.snapshot()
        
        # Ghi log
        self.node.log("Đã đăng nhập thành công")
        Utility.wait_time(10)

class Setup:
    def __init__(self, node: Node, profile: dict) -> None:
        self.node = node
        self.profile = profile
    
        self.logic()
    def logic(self):
        self.node.go_to("https://www.saucedemo.com")

manager = BrowserManager(auto_handler=Auto, setup_handler=Setup)
# Đọc file data.txt
profiles = Utility.read_data('profile_name','username','password')
manager.run_menu(profiles=profiles)