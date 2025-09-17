from selenium_browserkit import BrowserManager, Node, By, Utility

def auto(node: Node, profile: dict):
    # Điều hướng
    node.go_to("https://www.saucedemo.com")
    
    # Nhập text
    node.find_and_input(By.ID, "user-name", profile.get('username'))
    node.find_and_input(By.ID, "password", profile.get('password'))
    node.find_and_click(By.ID, "login-button")
    
    # Chụp màn hình và lưu lại
    node.snapshot()
    
    # Ghi log
    node.log("Đã đăng nhập thành công")
    Utility.wait_time(10)

def setup(node: Node, profile: dict):
    node.go_to("https://www.saucedemo.com")

manager = BrowserManager(auto_handler=auto, setup_handler=setup)
# Đọc file data.txt
profiles = Utility.read_data('profile_name','username','password')
manager.run_menu(profiles=profiles)