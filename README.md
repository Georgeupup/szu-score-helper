# SZU Score Helper

深圳大学成绩查询小助手。适合想更方便查看课程成绩、学分和绩点的同学使用。

程序在本机运行，点击按钮后会打开浏览器，由你自己在学校统一认证页面完成登录。登录完成后，工具会自动读取本机登录状态并展示成绩结果。

## 功能

- 图形界面，双击即可使用。
- 自动打开浏览器，手动完成学校统一认证登录。
- 查询并展示课程名称、成绩、学分、绩点、学期等信息。
- 自动汇总总学分和平均绩点。
- 支持源码运行，也支持打包后的 exe 直接运行。

## 最简单的使用方法

到 GitHub Release 页面下载打包好的 exe：

```text
深大查分助手.exe
```

下载后双击运行即可，不需要安装 Python，也不需要手动配置任何信息。

使用步骤：

1. 双击打开 `深大查分助手.exe`。
2. 点击“打开浏览器并查询绩点”。
3. 在弹出的 Edge 或 Chrome 中完成学校统一认证登录。
4. 登录完成后等待程序自动查询。
5. 查询结果会显示在窗口表格中，并弹出汇总信息。

## 源码运行

如果你想直接运行源码，需要 Python 3.8+。

安装依赖：

```bash
pip install requests playwright
```

如果在 Anaconda 环境中安装 `playwright` 遇到 `greenlet` 编译失败，可以优先使用 conda-forge：

```bash
conda install -n cl -c conda-forge greenlet playwright
```

运行：

```bash
python GUI.py
```

## 命令行版本

项目里也保留了 `get_score.py`，适合熟悉 Python 的同学手动运行。

普通用户建议直接使用 Release 里的 exe。

## 打包 exe

使用 PyInstaller：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "深大查分助手" GUI.py
```

打包完成后，文件在：

```text
dist/深大查分助手.exe
```

## 注意事项

- 本工具只在本机运行，不会上传账号、密码或登录信息。
- 登录时请确认浏览器页面是学校统一认证页面。
- 登录状态有时效性，失效后重新运行并登录即可。
- 学校页面调整后，工具可能需要同步更新。
- 请勿高频刷新或频繁请求学校系统。

## License

MIT License
