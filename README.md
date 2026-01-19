🎓 SZU Graduate Score Helper (深大研究生查分小助手)

<p align="center">
<img src="https://img.shields.io/badge/Python-3.8%252B-blue" alt="Python Version">
<img src="https://img.shields.io/badge/Platform-Windows-platform" alt="Platform">
<img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

# 📖  简介 | Introduction

深大研究生查分小助手 是一款专为深圳大学研究生开发的成绩查询工具。

由于教务系统在成绩录入期间可能会隐藏具体的卷面分数，但系统后台的筛选接口允许通过分数段进行查询。本工具利用这一机制，通过自动化二分查找算法，快速“探测”出你的具体分数，并计算 GPA。

# ✨ 核心亮点：

提前知晓：利用系统逻辑漏洞，在成绩正式公布前（或系统隐藏具体分数时）查询精确分数。

图形界面：提供友好的 Windows GUI 界面，无需懂代码即可使用。

自动登录：内置浏览器自动化模块，自动通过学校统一身份认证（CAS）。

智能统计：查询完成后自动计算总加权平均分和 GPA。

# 🛠️ 功能特性 | Features

自动登录：支持通过学号和密码自动登录 ehall.szu.edu.cn，自动处理重定向和 Cookie 获取。

二分查找：对每一门百分制课程进行高效的二分探测，精确到小数点后一位。

防封控机制：内置随机延时和浏览器模拟，防止因请求过快被系统拦截。

结果导出：程序界面通过表格清晰展示课程名、分数、学分及绩点。

# 🚀 使用方法 | Usage

## 方式一：直接运行 (推荐普通用户)

下载 Release 页面中的 深大查分助手.exe。

确保你的电脑上安装了 Google Chrome 浏览器。

双击运行软件，输入学号和密码。

点击“开始一键查分”，等待程序运行结束。

## 方式二：源码运行 (推荐开发者)

如果你想修改代码或自己打包，请按以下步骤操作：

克隆仓库

git clone [https://github.com/Georgeupup/szu-score-helper.git](https://github.com/Georgeupup/szu-score-helper.git) 

cd szu-score-helper


安装依赖

pip install requests selenium webdriver_manager
### 如果没有 tkinter (通常 Python 内置)，请自行安装


运行程序

python GUI.py


打包成 exe (可选)

pip install pyinstaller
pyinstaller --onefile --windowed --name="深大查分助手" GUI.py


# ⚠️ 注意事项 | Notes

Chrome 浏览器：本程序依赖 Chrome 浏览器及其驱动，请务必安装最新版 Chrome。

网络环境：建议在校内网或使用 VPN 访问，虽然脚本配置了绕过代理，但网络通畅是前提。

安全性：

本程序完全开源，所有代码均在本地运行。

你的账号密码仅用于登录学校教务系统，绝对不会上传到任何第三方服务器。

使用频率：请勿短时间内频繁、大量使用，以免对学校服务器造成压力。

# 🙌 致谢 | Acknowledgements

Core Logic: 本项目的核心“二分查找查分”算法逻辑源自深大研究生群体中流传的一份匿名 Python 脚本。在此向这位不知名的原作者致以诚挚的谢意！(Credit goes to the original anonymous author for the binary search logic).

GUI Framework: 基于 Python tkinter 构建。

Browser Automation: 由 Selenium 和 webdriver_manager 提供支持。

# 📜 许可证 | License

本项目采用 MIT License 开源许可证。
