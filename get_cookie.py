import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys  # 引入键盘按键支持
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class UniversityLogin:
    def __init__(self, login_url):
        self.login_url = login_url
        self.driver = None

    def start_browser(self):
        """启动浏览器，并开启网络日志捕获功能"""
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless') # 调试阶段建议不要开启 headless
        options.add_argument('--disable-gpu')
        options.add_experimental_option("detach", True)
        options.add_argument('--disable-blink-features=AutomationControlled')

        # 【关键步骤】开启 Performance Log (性能日志)，这是截获 Network Header 的关键
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def get_cookie_from_network(self):
        """
        从网络日志中提取 Cookie (备选方案)
        """
        print("正在扫描后台网络日志...")
        logs = self.driver.get_log('performance')

        for entry in logs:
            try:
                message = json.loads(entry['message'])['message']
                if message['method'] == 'Network.requestWillBeSent':
                    request = message['params']['request']
                    url = request['url']
                    if "ehall.szu.edu.cn" in url:
                        headers = request.get('headers', {})
                        cookie_str = headers.get('Cookie') or headers.get('cookie')
                        if cookie_str and "JSESSIONID" in cookie_str:
                            print(f"🎯 捕获到请求: {url}")
                            return cookie_str
            except Exception:
                continue
        return None

    def login_and_sniff(self, username, password):
        if not self.driver:
            self.start_browser()

        print(f"正在打开页面: {self.login_url}")
        self.driver.get(self.login_url)

        # 【关键】等待页面彻底加载稳定，防止输入后被页面自动刷新清空
        print("等待页面加载稳定...")
        time.sleep(4)

        try:
            # --- 1. 登录流程 ---
            wait = WebDriverWait(self.driver, 15)
            print("正在定位输入框...")
            user_input = None

            try:
                user_input = wait.until(EC.element_to_be_clickable((By.ID, "username")))
            except:
                try:
                    user_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='username']")))
                except:
                    user_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='text']")))

            pwd_selectors = [(By.ID, "password"), (By.ID, "pwd"), (By.CSS_SELECTOR, "input[type='password']")]
            pwd_input = None
            for by, val in pwd_selectors:
                try:
                    elem = self.driver.find_element(by, val)
                    if elem.is_displayed() and elem.is_enabled():
                        pwd_input = elem;
                        break
                except:
                    continue

            if not user_input or not pwd_input:
                raise Exception("无法定位输入框")

            print("输入账号密码...")
            user_input.click()  # 先点一下，确保聚焦
            user_input.clear()
            user_input.send_keys(username)

            time.sleep(0.5)  # 稍微停顿，模拟真人

            pwd_input.click()
            pwd_input.clear()
            pwd_input.send_keys(password)

            # 【核心修改】不再寻找按钮，直接在密码框按回车
            print("尝试直接按回车键登录...")
            pwd_input.send_keys(Keys.ENTER)

            # --- 2. 登录后强制访问目标接口 ---
            print("提交完成，等待 5 秒...")
            time.sleep(5)

            target_api = "https://ehall.szu.edu.cn/gsapp/sys/gglglyy/qs/getUnReadMsgCount.do?appid=5101964191790615"
            print(f"🎣 正在主动访问数据接口: \n{target_api}")
            self.driver.get(target_api)

            # 等待一下加载
            time.sleep(3)

            # --- 3. 优先尝试直接提取 (最稳妥的方法) ---
            print("正在尝试直接读取浏览器 Cookie...")
            direct_cookies = self.driver.get_cookies()
            cookie_parts = []
            for c in direct_cookies:
                cookie_parts.append(f"{c['name']}={c['value']}")

            direct_cookie_str = "; ".join(cookie_parts)

            # 只要拿到了 JSESSIONID，或者能看到刚才的JSON，就说明成功了
            if "JSESSIONID" in direct_cookie_str or len(cookie_parts) > 2:
                print("\n" + "=" * 50)
                print("✅ 成功提取 Cookie!")
                print("💡 提示：浏览器显示 JSON 数据 {xxCount:0...} 是正常的，说明登录成功。")
                print("=" * 50)
                self.driver.quit()
                return direct_cookie_str

            # --- 4. 如果直接提取失败，再尝试 Network Log ---
            print("直接提取未包含关键信息，尝试分析网络日志...")
            final_cookie = self.get_cookie_from_network()

            if final_cookie:
                print("\n" + "=" * 50)
                print("✅ 成功截获 Cookie (Network Log):")
                print("=" * 50)
                self.driver.quit()
                return final_cookie
            else:
                print("\n⚠️  自动提取失败。")
                input("请检查浏览器是否已登录，然后按回车键结束...")
                return None

        except Exception as e:
            print(f"出错: {e}")
            return None


if __name__ == "__main__":
    # 你的链接会自动重定向到 authserver
    LOGIN_URL = "https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/*default/index.do"

    bot = UniversityLogin(LOGIN_URL)

    # 填入账号密码
    cookie = bot.login_and_sniff("2510103005", "773648415")

    if cookie:
        print("\n>>> 请复制下方字符串到你的脚本中: <<<\n")
        print(cookie)