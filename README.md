# SZU Graduate Score Helper

深圳大学研究生成绩/绩点查询小助手。当前版本通过浏览器手动登录获取本机 Cookie，然后调用成绩页面使用的接口读取课程列表；如果接口不直接返回 `JDZ` 绩点字段，会通过 `JDZ >= 4/3.5/3/...` 的条件筛选结果反推每门课的绩点档位。

## 功能

- 图形界面：基于 `tkinter`，点击按钮后自动打开浏览器。
- 手动登录：账号密码只在学校统一认证页面中输入，程序不保存、不自动填写账号密码。
- 自动获取 Cookie：登录完成后通过 Playwright 读取本机浏览器 Cookie。
- 成绩读取：调用成绩页面接口 `xscjcx.do`，读取返回数据中的 `datas.xscjcx.rows`。
- 绩点推断：如果返回数据隐藏 `JDZ`，会按 `JDZ >= 4/3.5/3/...` 的筛选结果推断每门课绩点。
- 统计汇总：在接口返回学分时自动计算总学分和平均绩点；若接口返回百分制成绩，也会计算平均百分制分数。
- 命令行模式：`get_score.py` 支持手动粘贴 Cookie 后查询。

## 环境要求

使用 Release 中的 exe：

- Windows
- Microsoft Edge 或 Google Chrome
- 可访问 `ehall.szu.edu.cn` 的网络环境

源码运行额外需要：

- Python 3.8+
- `requests`
- `playwright`

## 使用方法

### 方式一：下载 exe 直接运行（推荐）

最简单的方式是到 GitHub Release 页面下载打包好的 exe 文件：

```text
深大查分助手.exe
```

下载后双击运行即可，不需要安装 Python，也不需要手动配置 Cookie。

使用步骤：

1. 双击打开 `深大查分助手.exe`。
2. 点击“打开浏览器并查询绩点”。
3. 在弹出的 Edge/Chrome 中手动完成统一身份认证登录。
4. 登录进入成绩页面后，程序会自动读取 Cookie、查询课程列表并推断绩点。
5. 查询结果会显示在表格中，并弹出统计汇总。

### 方式二：源码运行（开发者）

安装依赖：

```bash
pip install requests playwright
```

如果你在 Anaconda 环境中安装 `playwright` 遇到 `greenlet` 编译失败，优先使用 conda-forge：

```bash
conda install -n cl -c conda-forge greenlet playwright
```

运行 GUI：

```bash
python GUI.py
```

## 命令行使用方法

如果只想运行脚本查询，可以使用 `get_score.py`。

打开浏览器 F12，在成绩接口请求中复制完整 `Cookie`，然后填入 [get_score.py](./get_score.py) 顶部：

```python
COOKIE = "EMAP_LANG=zh; THEME=cherry; _WEU=...; JSESSIONID=...; route=..."
```

运行：

```bash
python get_score.py
```

如果不想写进文件，也可以运行后按提示粘贴 Cookie。

## 当前接口

当前版本使用成绩页面中的接口：

```text
https://ehall.szu.edu.cn/gsapp/sys/szdxwdcjapp/modules/wdcj/xscjcx.do
```

程序会解析返回数据中的 `datas.xscjcx.rows`，同时保留旧接口 `wdcj/queryZhcjxx.do` 作为兼容回退。

主要读取字段：

- `KCMC`：课程名称
- `CJ` / `DYBFZCJ`：成绩
- `XF`：学分
- `JDZ`：绩点
- `XNXQDM_DISPLAY`：学期
- `CJFZDM_DISPLAY`：成绩分制

如果 `JDZ` 被隐藏但仍允许作为筛选字段，程序会批量请求：

```text
JDZ >= 4
JDZ >= 3.5
JDZ >= 3
JDZ >= 2.5
JDZ >= 2
JDZ >= 1.5
JDZ >= 1
```

然后根据每门课首次命中的最高档位反推出对应绩点。

## 注意事项

- 本工具只在本机运行，不会上传账号、密码或 Cookie。
- GUI 登录时请只在学校统一认证页面输入账号密码。
- Cookie 有时效性，失效后需要重新登录获取。
- 学校接口或页面结构调整后，程序可能需要同步更新。
- 请勿高频请求学校系统。

## 打包 exe

可选使用 PyInstaller：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name="深大查分助手" GUI.py
```

## 致谢

- GUI：`tkinter`
- 浏览器登录与 Cookie 获取：`Playwright`
- HTTP 请求：`requests`

## License

MIT License
