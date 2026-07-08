# ehall 研究生成绩查询
import json
import os
from json import JSONDecodeError

import requests

os.environ["NO_PROXY"] = "ehall.szu.edu.cn"

SCORE_URL = "https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/wdcj/queryZhcjxx.do"
DEFAULT_REFERER = "https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/*default/index.do"

# 把 F12 请求头里的 cookie 整行粘到这里，保留两边引号。
# 例：COOKIE = "EMAP_LANG=zh; THEME=cherry; _WEU=...; JSESSIONID=...; route=..."
COOKIE = ""

# 一般不用填。若提示登录态失效，再把 F12 请求头里的 referer 整行粘到这里。
REFERER = ""

headers = {
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
cookies = {}


class ScoreQueryError(RuntimeError):
    pass


def parse_cookie(cookie_str: str) -> dict:
    result = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        result[key] = value
    return result


def load_cookie() -> str:
    if COOKIE.strip():
        return COOKIE.strip()

    env_cookie = os.environ.get("SZU_COOKIE", "").strip()
    if env_cookie:
        return env_cookie

    cookie_file = "cookie.txt"
    if os.path.exists(cookie_file):
        with open(cookie_file, "r", encoding="utf-8") as f:
            return f.read().strip()

    return input("请粘贴 F12 请求头里的完整 Cookie 后回车: ").strip()


def to_float(value, default=0.0):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def query_all_scores():
    request_headers = headers.copy()
    request_headers["Referer"] = REFERER.strip() or os.environ.get(
        "SZU_REFERER", DEFAULT_REFERER
    )

    try:
        ret = requests.post(
            SCORE_URL,
            cookies=cookies,
            headers=request_headers,
            timeout=15,
            allow_redirects=False,
        )
        if 300 <= ret.status_code < 400:
            location = ret.headers.get("Location", "")
            raise ScoreQueryError(
                "成绩接口把请求重定向走了，登录态大概率已经失效。"
                "请重新登录获取完整 Cookie 后再试。\n"
                f"HTTP {ret.status_code}, Location: {location}"
            )
        ret.raise_for_status()
    except requests.RequestException as exc:
        raise ScoreQueryError(f"请求成绩接口失败: {exc}") from exc

    try:
        res_json = ret.json()
    except JSONDecodeError as exc:
        content_type = ret.headers.get("Content-Type", "")
        preview = ret.text[:500].replace("\n", "\\n").replace("\r", "\\r")
        if not preview:
            preview = "<空响应>"
        raise ScoreQueryError(
            "成绩接口没有返回 JSON。通常是 Cookie 已过期、被重定向到登录页，"
            "或当前网络不能访问 ehall。\n"
            f"HTTP {ret.status_code}, Content-Type: {content_type}\n"
            f"最终 URL: {ret.url}\n"
            f"响应预览: {preview}"
        ) from exc

    rows = res_json.get("zhcjInfo")
    if not isinstance(rows, list):
        preview = json.dumps(res_json, ensure_ascii=False)[:800]
        raise ScoreQueryError(
            "成绩接口返回了 JSON，但没有找到 zhcjInfo 列表。\n"
            f"返回字段: {list(res_json.keys())}\n"
            f"响应预览: {preview}"
        )

    return rows


def main():
    cookies.update(parse_cookie(load_cookie()))
    if not cookies:
        raise SystemExit(
            "未配置 Cookie。请把浏览器 F12 里复制到的完整 Cookie 填到文件顶部的 COOKIE。"
        )

    try:
        courses = query_all_scores()
    except ScoreQueryError as exc:
        raise SystemExit(f"查询失败: {exc}") from exc

    percent_courses = [
        c for c in courses if c.get("CJFZDM") == "1" or c.get("CJFZDM_DISPLAY") == "百分制"
    ]

    print(f"API 返回 {len(courses)} 条成绩，其中百分制课程 {len(percent_courses)} 门")
    print("----------成绩列表----------")

    total_credit = 0.0
    total_grade = 0.0
    total_score = 0.0

    for course in percent_courses:
        name = course.get("KCMC", "")
        score = to_float(course.get("DYBFZCJ", course.get("CJ")))
        credit = to_float(course.get("XF"))
        grade_point = to_float(course.get("JDZ"))
        term = course.get("XNXQDM_DISPLAY", "")
        status = course.get("BY1", "")

        print(
            f"{name} | 分数: {score:g} | 学分: {credit:g} | 绩点: {grade_point:g}"
            + (f" | {term}" if term else "")
            + (f" | {status}" if status else "")
        )

        total_credit += credit
        total_grade += credit * grade_point
        total_score += credit * score

    print("----------查询完毕----------")
    print(f"总学分: {total_credit:g}")
    if total_credit > 0:
        print(f"总GPA: {round(total_grade / total_credit, 4)}")
        print(f"总百分制分数: {round(total_score / total_credit, 4)}")
    else:
        print("没有找到百分制课程数据，请检查 Cookie 或接口返回内容。")


if __name__ == "__main__":
    main()
