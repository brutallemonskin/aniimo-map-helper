# v0.3.1 · 中文路径修复 / Unicode path fix

## 更新内容
- 修复解压目录或 Windows 用户目录包含中文时，地图图片读取失败、出现“识别引擎异常”的问题。
- 地图、门位置索引、小地图底图和蛋形态模板统一支持 Unicode 路径。
- 素材缺失、空文件或损坏时显示具体文件名和重新解压提示。
- 包含中英文界面切换、英文悬浮窗和英文启动入口；默认识别间隔仍为 0.25 秒。

## 下载与升级
下载 **AniimoNavigator-Portable-v0.3.1.zip**。先双击旧版“退出助手.exe”，再将新版完整解压到新目录，运行“启动助手.exe”或 **Start Navigator.exe**。无需安装 Python。

已验证：在包含中文和空格的目录中解压并使用包内运行库启动，33 张地图和门位置索引全部正常；缺失、空白、损坏素材提示及定位回归检查通过。公开源码与压缩包不包含开发测试、实机截图和个人日志。

## English
Fixes map initialization failures when the extracted folder or Windows user path contains non-ASCII characters. All image readers now support Unicode paths and report missing or corrupt assets by filename.

Includes the Chinese/English interface, localized overlay, English launchers and README_EN.md. Exit the old helper, extract the entire new ZIP, then run **Start Navigator.exe**. The bundled runtime was verified under a Chinese path containing spaces with all 33 maps indexed successfully.

English-language game capture compatibility has not yet been verified. Unknown creature/item proper names retain their original spelling alongside an English category.
