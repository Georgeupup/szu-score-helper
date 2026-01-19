import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import os
import time
import requests
import webbrowser  # 新增：用于打开浏览器链接
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# ---------------------- 核心逻辑类 ----------------------

class ScoreLogic:
    def __init__(self, log_callback):
        self.log = log_callback
        self.cookies = {}
        self.headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }
        # 绕过代理，防止抓包工具导致连接失败
        os.environ["NO_PROXY"] = "ehall.szu.edu.cn"

    def parse_cookie_str(self, cookie_str):
        self.cookies = {}
        items = cookie_str.split(';')
        for item in items:
            if '=' in item:
                k, v = item.strip().split('=', 1)
                self.cookies[k] = v

    def query_gte(self, score):
        """查询大于等于某分数的课程"""
        data = {
            "querySetting": '[{"name":"DYBFZCJ","linkOpt":"AND","builderList":"cbl_Other","builder":"moreEqual","value":'
                            + str(score)
                            + '},{"name":"CJFZDM","linkOpt":"AND","builderList":"cbl_m_List","builder":"m_value_equal","value":"1","value_display":"百分制"}]',
            "pageSize": 99,
            "pageNumber": 1,
        }
        try:
            url = "https://ehall.szu.edu.cn/gsapp/sys/xscjglapp/modules/xscjcx/xscjcx_dqx.do"
            ret = requests.post(url, cookies=self.cookies, headers=self.headers, data=data, timeout=10)
            if ret.status_code != 200:
                return []

            res_json = json.loads(ret.text)
            if "datas" not in res_json:
                return []
            return res_json["datas"]["xscjcx_dqx"]["rows"]
        except Exception as e:
            self.log(f"请求出错: {e}")
            return []

    def binary_search_score(self, course_name):
        """二分查找具体分数"""
        lScore = 0
        rScore = 100

        # 优化：先快速缩小范围
        if not self.check_exists(course_name, 60):
            rScore = 60
        elif self.check_exists(course_name, 90):
            lScore = 90

        while lScore <= rScore:
            mid = round((lScore + rScore) / 2, 1)
            # self.log(f"  正在二分探测: {course_name} >= {mid}?") # 日志太多可以注释掉

            if self.check_exists(course_name, mid):
                lScore = mid
            else:
                rScore = mid

            if rScore - lScore <= 0.11:
                if self.check_exists(course_name, rScore):
                    return rScore
                else:
                    return lScore
        return lScore

    def check_exists(self, course_name, score):
        rows = self.query_gte(score)
        return any(c['KCMC'] == course_name for c in rows)

    def get_grade_point(self, score):
        """计算绩点"""
        s = round(score)
        if s >= 90:
            return 4.0
        elif s >= 85:
            return 3.5
        elif s >= 80:
            return 3.0
        elif s >= 75:
            return 2.5
        elif s >= 70:
            return 2.0
        elif s >= 65:
            return 1.5
        elif s >= 60:
            return 1.0
        else:
            return 0.0


class AutoLogin:
    def __init__(self, log_callback):
        self.log = log_callback
        self.driver = None

    def login(self, username, password):
        try:
            self.log("正在启动浏览器...")
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')  # 最终发布时开启 headless
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-blink-features=AutomationControlled')

            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            login_url = "https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/*default/index.do"
            self.log(f"打开登录页: {login_url}")
            self.driver.get(login_url)

            time.sleep(3)  # 等待重定向

            wait = WebDriverWait(self.driver, 15)

            # 定位用户名
            user_input = None
            try:
                user_input = wait.until(EC.element_to_be_clickable((By.ID, "username")))
            except:
                user_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")

            # 定位密码
            pwd_input = self.driver.find_element(By.ID, "password")

            self.log("正在输入账号密码...")
            # 模拟点击和输入
            user_input.click()
            user_input.clear()
            user_input.send_keys(username)
            time.sleep(0.5)
            pwd_input.click()
            pwd_input.clear()
            pwd_input.send_keys(password)

            self.log("提交登录...")
            pwd_input.send_keys(Keys.ENTER)

            time.sleep(3)
            self.log("等待系统跳转...")

            # 访问数据接口确保 Cookie 生成
            target_api = "https://ehall.szu.edu.cn/gsapp/sys/gglglyy/qs/getUnReadMsgCount.do?appid=5101964191790615"
            self.driver.get(target_api)
            time.sleep(2)

            cookies = self.driver.get_cookies()
            cookie_parts = [f"{c['name']}={c['value']}" for c in cookies]
            cookie_str = "; ".join(cookie_parts)

            if "JSESSIONID" in cookie_str:
                self.log("✅ 成功获取 Cookie!")
                return cookie_str
            else:
                self.log("❌ Cookie 获取失败，未找到 JSESSIONID")
                return None

        except Exception as e:
            self.log(f"登录过程出错: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()


# ---------------------- GUI 界面类 ----------------------

class GradeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("深大研究生查分小助手 v1.0")
        self.root.geometry("800x650")  # 稍微调高一点高度，给底部留空间

        # 变量
        self.user_var = tk.StringVar()
        self.pwd_var = tk.StringVar()

        self.setup_ui()

    def setup_ui(self):
        # 0. 顶部重要提示区 (新增)
        tk.Label(
            self.root,
            text="⚠️ 提示：本程序依赖 Google Chrome 浏览器，请确保电脑已安装最新版 Chrome",
            fg="#D32F2F",
            bg="#FFEBEE",
            font=("微软雅黑", 10),
            pady=5
        ).pack(fill="x", pady=(0, 5))

        # 1. 登录信息区
        frame_login = tk.LabelFrame(self.root, text="登录信息", padx=10, pady=10)
        frame_login.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_login, text="学号:").grid(row=0, column=0, padx=5)
        tk.Entry(frame_login, textvariable=self.user_var, width=20).grid(row=0, column=1, padx=5)

        tk.Label(frame_login, text="密码:").grid(row=0, column=2, padx=5)
        tk.Entry(frame_login, textvariable=self.pwd_var, show="*", width=20).grid(row=0, column=3, padx=5)

        self.btn_start = tk.Button(frame_login, text="开始一键查分", command=self.start_thread, bg="#4CAF50",
                                   fg="white", font=("微软雅黑", 10, "bold"))
        self.btn_start.grid(row=0, column=4, padx=20)

        # 2. 中间表格区
        frame_table = tk.LabelFrame(self.root, text="成绩列表", padx=10, pady=10)
        frame_table.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("课程名称", "百分制成绩", "学分", "绩点")
        self.tree = ttk.Treeview(frame_table, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.column("课程名称", width=250, anchor="w")  # 课程名宽一点，靠左

        ysb = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")

        # 3. 底部日志区
        frame_log = tk.LabelFrame(self.root, text="运行日志", padx=10, pady=10)
        frame_log.pack(fill="x", padx=10, pady=5)

        self.txt_log = scrolledtext.ScrolledText(frame_log, height=8, state='disabled', font=("Consolas", 9))
        self.txt_log.pack(fill="both")

        # 4. 底部开源信息 (新增)
        # 请将下方的 URL 替换为你真实的 GitHub 仓库地址
        github_url = "https://github.com/Georgeupup/szu-score-helper"

        frame_footer = tk.Frame(self.root)
        frame_footer.pack(fill="x", pady=10)

        lbl_link = tk.Label(
            frame_footer,
            text=f"本项目已开源: {github_url}",
            fg="blue",
            cursor="hand2",
            font=("微软雅黑", 9, "underline")
        )
        lbl_link.pack()
        # 绑定点击事件，调用浏览器打开链接
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open(github_url))

    def log(self, msg):
        """线程安全的日志输出"""
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.txt_log.configure(state='normal')
        self.txt_log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.txt_log.see(tk.END)
        self.txt_log.configure(state='disabled')

    def start_thread(self):
        username = self.user_var.get()
        password = self.pwd_var.get()

        if not username or not password:
            messagebox.showerror("错误", "请输入学号和密码")
            return

        self.btn_start.config(state="disabled", text="正在运行...")
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)

        threading.Thread(target=self.run_task, args=(username, password), daemon=True).start()

    def run_task(self, username, password):
        try:
            # 1. 登录获取 Cookie
            login_bot = AutoLogin(self.log)
            cookie_str = login_bot.login(username, password)

            if not cookie_str:
                self.log("登录失败，流程终止。")
                self.reset_btn()
                return

            # 2. 开始查分
            score_bot = ScoreLogic(self.log)
            score_bot.parse_cookie_str(cookie_str)

            self.log("正在获取课程列表...")
            # 先用 score=0 获取所有及格课程
            all_courses = score_bot.query_gte(0)

            if not all_courses:
                self.log("未查询到百分制课程数据 (或Cookie已过期)")
                self.reset_btn()
                return

            self.log(f"共发现 {len(all_courses)} 门百分制课程，开始二分查找分数...")

            total_credit = 0
            total_grade_point = 0
            total_score_val = 0

            for idx, course in enumerate(all_courses):
                name = course['KCMC']
                credit = float(course['XF'])
                self.log(f"[{idx + 1}/{len(all_courses)}] 正在分析: {name}")

                # 执行二分查找
                score = score_bot.binary_search_score(name)
                gp = score_bot.get_grade_point(score)

                # 插入表格
                # [修复] 使用 lambda 包装，解决 after 不支持关键字参数的问题
                self.root.after(0, lambda n=name, s=score, c=credit, g=gp: self.tree.insert("", "end",
                                                                                            values=(n, s, c, g)))

                # 统计
                total_credit += credit
                total_grade_point += credit * gp
                total_score_val += credit * score

            self.log("---------- 查询完毕 ----------")

            if total_credit > 0:
                avg_gpa = round(total_grade_point / total_credit, 4)
                avg_score = round(total_score_val / total_credit, 4)
                summary = f"总学分: {total_credit} | 平均百分制: {avg_score} | 平均绩点(GPA): {avg_gpa}"
                self.log(summary)
                messagebox.showinfo("查询成功", summary)

        except Exception as e:
            self.log(f"发生未知错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.reset_btn()

    def reset_btn(self):
        self.root.after(0, lambda: self.btn_start.config(state="normal", text="开始一键查分"))


if __name__ == "__main__":
    root = tk.Tk()
    app = GradeApp(root)
    root.mainloop()