import json
import os
import threading
import time
import tkinter as tk
import webbrowser
from json import JSONDecodeError
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

import requests


os.environ["NO_PROXY"] = "ehall.szu.edu.cn"

LOGIN_URL = "https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/*default/index.do"
SCORE_URL = "https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/modules/wdcj/xscjcx.do"
FALLBACK_SCORE_URL = "https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/wdcj/queryZhcjxx.do"
BROWSER_COOKIE_DOMAIN = "ehall.szu.edu.cn"
BROWSER_COOKIE_PATH = "/gsapp/sys/szdxwdcjapp/modules/wdcj/xscjcx.do"
AUTH_COOKIE_NAMES = ("MOD_AUTH_CAS", "JSESSIONID")
PLAYWRIGHT_PROFILE_DIR = Path(__file__).with_name(".playwright_score_profile")
COOKIE_WAIT_SECONDS = 180
GOTO_FIRST_PAGE_QUERY = json.dumps(
    [{"name": "_gotoFirstPage", "value": True, "linkOpt": "AND", "builder": "equal"}],
    ensure_ascii=False,
)
GRADE_POINT_THRESHOLDS = [4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0]


def build_cookie_header(cookies):
    matched_cookies = []
    for cookie in cookies:
        domain = cookie.get("domain", "").lstrip(".")
        path = cookie.get("path") or "/"
        domain_match = (
            domain == BROWSER_COOKIE_DOMAIN
            or BROWSER_COOKIE_DOMAIN.endswith("." + domain)
            or domain.endswith(".szu.edu.cn")
        )
        path_match = BROWSER_COOKIE_PATH.startswith(path)
        if domain_match and path_match:
            matched_cookies.append(cookie)

    matched_cookies.sort(key=lambda item: len(item.get("path") or "/"), reverse=True)
    return "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in matched_cookies)


def launch_persistent_browser(playwright):
    launch_options = [
        ("Edge", {"channel": "msedge"}),
        ("Chrome", {"channel": "chrome"}),
        ("Chromium", {}),
    ]
    errors = []

    for browser_name, browser_options in launch_options:
        try:
            context = playwright.chromium.launch_persistent_context(
                str(PLAYWRIGHT_PROFILE_DIR),
                headless=False,
                viewport={"width": 1280, "height": 900},
                args=["--start-maximized"],
                **browser_options,
            )
            return browser_name, context
        except Exception as exc:
            errors.append(f"{browser_name}: {exc}")

    raise RuntimeError("\n".join(errors))


def load_cookie_from_playwright(log_callback=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("缺少依赖 playwright，请先运行：pip install playwright") from exc

    def log(msg):
        if log_callback is not None:
            log_callback(msg)

    PLAYWRIGHT_PROFILE_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        context = None
        try:
            browser_name, context = launch_persistent_browser(p)
            log(f"已打开 {browser_name}，请在浏览器中手动登录。")

            page = context.pages[0] if context.pages else context.new_page()
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)

            deadline = time.time() + COOKIE_WAIT_SECONDS
            last_url = ""
            while time.time() < deadline:
                current_url = page.url
                if current_url != last_url:
                    log(f"当前页面: {current_url}")
                    last_url = current_url

                cookie_text = build_cookie_header(context.cookies(SCORE_URL))
                if cookie_text and all(name in cookie_text for name in AUTH_COOKIE_NAMES):
                    log(f"Cookie 获取完成，长度: {len(cookie_text)}")
                    return browser_name, cookie_text, current_url

                page.wait_for_timeout(1000)

            raise RuntimeError("等待登录超时，请在打开的浏览器中完成登录并进入成绩页面")
        except Exception as exc:
            raise RuntimeError(f"自动获取 Cookie 失败。\n{exc}") from exc
        finally:
            if context is not None:
                context.close()


class ScoreLogic:
    def __init__(self, log_callback):
        self.log = log_callback
        self.cookies = {}
        self.referer = LOGIN_URL
        self.headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://ehall.szu.edu.cn",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

    def parse_cookie_str(self, cookie_str):
        self.cookies = {}
        for item in cookie_str.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                self.cookies[key] = value

    def set_referer(self, referer):
        if referer:
            self.referer = referer

    def query_all_scores(self):
        request_headers = self.headers.copy()
        request_headers["Referer"] = self.referer

        requests_to_try = [
            (
                SCORE_URL,
                {"pageSize": 200, "pageNumber": 1, "querySetting": GOTO_FIRST_PAGE_QUERY},
                "xscjcx",
            ),
            (FALLBACK_SCORE_URL, None, "queryZhcjxx"),
        ]

        for url, data, label in requests_to_try:
            rows = self._query_score_url(url, request_headers, data, label)
            if rows:
                return rows

        return []

    def query_filtered_scores(self, field, value, builder="moreEqual"):
        request_headers = self.headers.copy()
        request_headers["Referer"] = self.referer
        query_setting = json.dumps(
            [
                {
                    "name": field,
                    "value": value,
                    "linkOpt": "AND",
                    "builder": builder,
                }
            ],
            ensure_ascii=False,
        )
        data = {"pageSize": 200, "pageNumber": 1, "querySetting": query_setting}
        return self._query_score_url(SCORE_URL, request_headers, data, f"{field}>={value}")

    def _query_score_url(self, url, request_headers, data, label):
        try:
            ret = requests.post(
                url,
                cookies=self.cookies,
                headers=request_headers,
                data=data,
                timeout=15,
                allow_redirects=False,
            )
            if 300 <= ret.status_code < 400:
                location = ret.headers.get("Location", "")
                self.log(f"{label} 接口发生跳转: HTTP {ret.status_code}, Location={location}")
                return []
            ret.raise_for_status()
        except requests.RequestException as exc:
            self.log(f"请求 {label} 接口失败: {exc}")
            return []

        try:
            res_json = ret.json()
        except JSONDecodeError:
            content_type = ret.headers.get("Content-Type", "")
            preview = ret.text[:300].replace("\n", "\\n").replace("\r", "\\r")
            self.log(f"{label} 接口没有返回 JSON: Content-Type={content_type}, 响应={preview}")
            return []

        rows = self._extract_rows(res_json)
        if isinstance(rows, list):
            self.log(f"已通过 {label} 接口读取 {len(rows)} 条成绩。")
            return rows

        preview = json.dumps(res_json, ensure_ascii=False)[:300]
        self.log(f"{label} 返回 JSON 中没有找到成绩列表: {preview}")
        return []

    @staticmethod
    def _extract_rows(res_json):
        for key in ("zhcjInfo", "hcjInfo"):
            rows = res_json.get(key)
            if isinstance(rows, list):
                return rows

        datas = res_json.get("datas")
        if isinstance(datas, dict):
            xscjcx = datas.get("xscjcx")
            if isinstance(xscjcx, dict):
                rows = xscjcx.get("rows")
                if isinstance(rows, list):
                    return rows

        return None

    @staticmethod
    def to_float(value, default=0.0):
        if value is None or value == "":
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def course_key(course):
        return (
            course.get("WID")
            or "|".join(
                str(course.get(key, ""))
                for key in ("XNXQDM", "KCDM", "KCMC", "BJDM", "KSXZDM")
            )
        )

    def infer_grade_points(self, courses):
        inferred = {}
        pending = {}

        for course in courses:
            key = self.course_key(course)
            direct_grade = course.get("JDZ")
            if direct_grade not in (None, ""):
                inferred[key] = self.to_float(direct_grade)
            else:
                pending[key] = course

        if not pending:
            self.log("接口已直接返回绩点字段 JDZ，无需反推。")
            return inferred

        self.log(
            f"有 {len(pending)} 门课未直接返回绩点，开始按 JDZ 条件筛选反推绩点档位。"
        )

        for threshold in GRADE_POINT_THRESHOLDS:
            rows = self.query_filtered_scores("JDZ", threshold)
            keys = {self.course_key(row) for row in rows}
            matched = 0
            for key in list(pending.keys()):
                if key in keys:
                    inferred[key] = threshold
                    pending.pop(key)
                    matched += 1
            self.log(f"JDZ >= {threshold:g}: 命中 {matched} 门待推断课程。")

        for key in pending:
            inferred[key] = 0.0

        if pending:
            self.log(f"{len(pending)} 门课未出现在 JDZ >= 1.0 结果中，按 0 或未通过处理。")

        return inferred


class BrowserLogin:
    def __init__(self, log_callback):
        self.log = log_callback

    def login(self):
        try:
            _, cookie_str, referer = load_cookie_from_playwright(self.log)
            return cookie_str, referer
        except Exception as exc:
            self.log(f"浏览器登录过程出错: {exc}")
            return None, None


class GradeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("深大研究生成绩小助手 v1.2")
        self.root.geometry("920x680")
        self.setup_ui()

    def setup_ui(self):
        tk.Label(
            self.root,
            text="提示：点击按钮后会弹出浏览器，请在浏览器中自行登录，程序只读取本机浏览器 Cookie。",
            fg="#D32F2F",
            bg="#FFEBEE",
            font=("微软雅黑", 10),
            pady=6,
        ).pack(fill="x", pady=(0, 5))

        frame_login = tk.LabelFrame(self.root, text="登录", padx=10, pady=10)
        frame_login.pack(fill="x", padx=10, pady=5)

        self.btn_start = tk.Button(
            frame_login,
            text="打开浏览器并查询绩点",
            command=self.start_thread,
            bg="#4CAF50",
            fg="white",
            font=("微软雅黑", 10, "bold"),
        )
        self.btn_start.pack(side="left", padx=5)

        tk.Label(
            frame_login,
            text="浏览器登录完成后无需操作，程序会自动继续查询。",
            fg="#555555",
            font=("微软雅黑", 9),
        ).pack(side="left", padx=12)

        frame_table = tk.LabelFrame(self.root, text="成绩列表", padx=10, pady=10)
        frame_table.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("课程名称", "成绩", "学分", "绩点", "学期", "状态")
        self.tree = ttk.Treeview(frame_table, columns=columns, show="headings")

        widths = {
            "课程名称": 260,
            "成绩": 90,
            "学分": 70,
            "绩点": 70,
            "学期": 180,
            "状态": 110,
        }
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], anchor="center")
        self.tree.column("课程名称", anchor="w")

        ysb = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")

        frame_log = tk.LabelFrame(self.root, text="运行日志", padx=10, pady=10)
        frame_log.pack(fill="x", padx=10, pady=5)

        self.txt_log = scrolledtext.ScrolledText(
            frame_log, height=8, state="disabled", font=("Consolas", 9)
        )
        self.txt_log.pack(fill="both")

        github_url = "https://github.com/Georgeupup/szu-score-helper"
        frame_footer = tk.Frame(self.root)
        frame_footer.pack(fill="x", pady=10)

        lbl_link = tk.Label(
            frame_footer,
            text=f"项目地址: {github_url}",
            fg="blue",
            cursor="hand2",
            font=("微软雅黑", 9, "underline"),
        )
        lbl_link.pack()
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open(github_url))

    def log(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.txt_log.configure(state="normal")
        self.txt_log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.txt_log.see(tk.END)
        self.txt_log.configure(state="disabled")

    def start_thread(self):
        self.btn_start.config(state="disabled", text="等待浏览器登录...")
        for item in self.tree.get_children():
            self.tree.delete(item)

        threading.Thread(target=self.run_task, daemon=True).start()

    def run_task(self):
        try:
            login_bot = BrowserLogin(self.log)
            cookie_str, referer = login_bot.login()

            if not cookie_str:
                self.log("未获取到 Cookie，流程终止。")
                return

            score_bot = ScoreLogic(self.log)
            score_bot.parse_cookie_str(cookie_str)
            score_bot.set_referer(referer)

            self.log("正在读取成绩接口...")
            all_courses = score_bot.query_all_scores()

            if not all_courses:
                self.log("未查询到课程数据，请确认网页登录后能看到成绩列表。")
                return

            self.log(f"共读取 {len(all_courses)} 条课程记录，开始推断绩点。")
            grade_points = score_bot.infer_grade_points(all_courses)

            total_credit = 0.0
            total_grade_point = 0.0
            total_score_val = 0.0

            for course in all_courses:
                name = course.get("KCMC", "")
                raw_score = course.get("DYBFZCJ", course.get("CJ"))
                raw_credit = course.get("XF")
                score = score_bot.to_float(raw_score)
                credit = score_bot.to_float(raw_credit)
                grade_point = grade_points.get(score_bot.course_key(course), 0.0)
                term = course.get("XNXQDM_DISPLAY", "")
                status = course.get("BY1", "")
                score_display = f"{score:g}" if raw_score not in (None, "") else "-"
                credit_display = f"{credit:g}" if raw_credit not in (None, "") else "-"

                self.root.after(
                    0,
                    lambda n=name, s=score_display, c=credit_display, g=grade_point, t=term, st=status: self.tree.insert(
                        "",
                        "end",
                        values=(n, s, c, f"{g:g}", t, st),
                    ),
                )

                if raw_credit not in (None, ""):
                    total_credit += credit
                    total_grade_point += credit * grade_point
                    if raw_score not in (None, ""):
                        total_score_val += credit * score

            if total_credit > 0:
                avg_gpa = round(total_grade_point / total_credit, 4)
                msg = f"查询完成。\n总学分: {total_credit:g}\n平均绩点: {avg_gpa}"
                if total_score_val > 0:
                    avg_score = round(total_score_val / total_credit, 4)
                    msg += f"\n平均百分制分数: {avg_score}"
                self.log(msg.replace("\n", " | "))
                self.root.after(0, lambda m=msg: messagebox.showinfo("查询完成", m))
            else:
                self.log("查询完成，但接口没有返回可用于加权统计的学分。")
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "查询完成",
                        "已显示课程绩点，但接口没有返回可用于加权统计的学分。",
                    ),
                )
        except Exception as exc:
            self.log(f"发生未知错误: {exc}")
            self.root.after(0, lambda e=str(exc): messagebox.showerror("错误", e))
        finally:
            self.root.after(
                0,
                lambda: self.btn_start.config(state="normal", text="打开浏览器并查询绩点"),
            )


def main():
    root = tk.Tk()
    app = GradeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
