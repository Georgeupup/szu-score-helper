# ehall 研究生成绩/绩点查询
import json
import os
from json import JSONDecodeError

import requests


os.environ["NO_PROXY"] = "ehall.szu.edu.cn"

SCORE_URL = "https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/modules/wdcj/xscjcx.do"
FALLBACK_SCORE_URL = "https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/wdcj/queryZhcjxx.do"
DEFAULT_REFERER = "https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/*default/index.do"
GOTO_FIRST_PAGE_QUERY = json.dumps(
    [{"name": "_gotoFirstPage", "value": True, "linkOpt": "AND", "builder": "equal"}],
    ensure_ascii=False,
)
GRADE_POINT_THRESHOLDS = [4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0]

# 把 F12 请求头里的 Cookie 整行粘到这里，保留两边引号。
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


def request_headers():
    result = headers.copy()
    result["Referer"] = REFERER.strip() or os.environ.get("SZU_REFERER", DEFAULT_REFERER)
    return result


def to_float(value, default=0.0):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def query_all_scores():
    requests_to_try = [
        (
            SCORE_URL,
            {"pageSize": 200, "pageNumber": 1, "querySetting": GOTO_FIRST_PAGE_QUERY},
            "xscjcx",
        ),
        (FALLBACK_SCORE_URL, None, "queryZhcjxx"),
    ]
    errors = []

    for url, data, label in requests_to_try:
        try:
            rows = query_score_url(url, request_headers(), data)
            print(f"已通过 {label} 接口读取 {len(rows)} 条成绩")
            if rows:
                return rows
        except ScoreQueryError as exc:
            errors.append(f"{label}: {exc}")

    if errors:
        raise ScoreQueryError("\n".join(errors))
    return []


def query_filtered_scores(field, value, builder="moreEqual"):
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
    return query_score_url(SCORE_URL, request_headers(), data)


def query_score_url(url, request_headers_data, data):
    try:
        ret = requests.post(
            url,
            cookies=cookies,
            headers=request_headers_data,
            data=data,
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

    rows = extract_rows(res_json)
    if rows is None:
        preview = json.dumps(res_json, ensure_ascii=False)[:800]
        raise ScoreQueryError(
            "成绩接口返回了 JSON，但没有找到成绩列表。\n"
            f"返回字段: {list(res_json.keys())}\n"
            f"响应预览: {preview}"
        )

    return rows


def extract_rows(res_json):
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


def course_key(course):
    return course.get("WID") or "|".join(
        str(course.get(key, "")) for key in ("XNXQDM", "KCDM", "KCMC", "BJDM", "KSXZDM")
    )


def infer_grade_points(courses):
    inferred = {}
    pending = {}

    for course in courses:
        key = course_key(course)
        direct_grade = course.get("JDZ")
        if direct_grade not in (None, ""):
            inferred[key] = to_float(direct_grade)
        else:
            pending[key] = course

    if not pending:
        print("接口已直接返回绩点字段 JDZ，无需反推。")
        return inferred

    print(f"有 {len(pending)} 门课未直接返回绩点，开始按 JDZ 条件筛选反推绩点档位。")

    for threshold in GRADE_POINT_THRESHOLDS:
        rows = query_filtered_scores("JDZ", threshold)
        keys = {course_key(row) for row in rows}
        matched = 0
        for key in list(pending.keys()):
            if key in keys:
                inferred[key] = threshold
                pending.pop(key)
                matched += 1
        print(f"JDZ >= {threshold:g}: 命中 {matched} 门待推断课程")

    for key in pending:
        inferred[key] = 0.0

    if pending:
        print(f"{len(pending)} 门课未出现在 JDZ >= 1.0 结果中，按 0 或未通过处理。")

    return inferred


def main():
    cookies.update(parse_cookie(load_cookie()))
    if not cookies:
        raise SystemExit("未配置 Cookie。请把 F12 复制到的完整 Cookie 填到文件顶部的 COOKIE。")

    try:
        courses = query_all_scores()
    except ScoreQueryError as exc:
        raise SystemExit(f"查询失败: {exc}") from exc

    grade_points = infer_grade_points(courses)

    print(f"API 返回 {len(courses)} 条课程记录")
    print("----------成绩列表----------")

    total_credit = 0.0
    total_grade = 0.0
    total_score = 0.0

    for course in courses:
        name = course.get("KCMC", "")
        raw_score = course.get("DYBFZCJ", course.get("CJ"))
        raw_credit = course.get("XF")
        score = to_float(raw_score)
        credit = to_float(raw_credit)
        grade_point = grade_points.get(course_key(course), 0.0)
        term = course.get("XNXQDM_DISPLAY", "")
        status = course.get("BY1", "")
        score_display = f"{score:g}" if raw_score not in (None, "") else "-"
        credit_display = f"{credit:g}" if raw_credit not in (None, "") else "-"

        print(
            f"{name} | 分数: {score_display} | 学分: {credit_display} | 绩点: {grade_point:g}"
            + (f" | {term}" if term else "")
            + (f" | {status}" if status else "")
        )

        if raw_credit not in (None, ""):
            total_credit += credit
            total_grade += credit * grade_point
            if raw_score not in (None, ""):
                total_score += credit * score

    print("----------查询完毕----------")
    print(f"总学分: {total_credit:g}")
    if total_credit > 0:
        print(f"总GPA: {round(total_grade / total_credit, 4)}")
        if total_score > 0:
            print(f"总百分制分数: {round(total_score / total_credit, 4)}")
    else:
        print("没有找到可用于加权统计的学分数据，请检查接口返回内容。")


if __name__ == "__main__":
    main()
