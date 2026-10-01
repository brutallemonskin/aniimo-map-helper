## v0.3.8 · 小地图性能优化与悬浮窗更新

### 更新内容

- 跑图时优先传送小地图裁切图；小地图消失后，本轮自动补读完整画面。打开大地图仍可正常识别和校准，并定期进行完整画面检查。
- 游戏预览最长边限制为 800 像素；彩虹掉落检测使用低分辨率预览，减少图片传输与解码开销。浏览器仍需共享完整游戏窗口，实际收益取决于设备和画面。
- 新增“实时定位”开关；关闭后保留最后位置，暂停小地图追踪和彩虹检测，大地图识别继续可用。保留 0.25 / 0.5 / 1 / 2 / 3 秒间隔选择。
- 打开背包等遮挡地图的界面时保留最后位置，返回游戏后自动恢复小地图追踪。传送、切换地宫或移动过远后，请重新打开大地图校准。
- 点位图标大小可调并立即同步悬浮窗；类别显示选择自动保存，下一次识别、地图切换及刷新后继续生效。
- 补齐蓝门、金紫蓝钥匙房及对应伊莫物种的原始素材；伊莫使用普通形态图片。悬浮窗按地图内容调整比例，减少留白并保留拖动缩放。
- 改善偏暗、较小窗口的入口识别兼容性，未降低这次版本的地图确认阈值。
- 新增试用彩虹掉落提示：连续确认光柱且定位有效时，记录发现时玩家所在位置附近；并非掉落物精确坐标，可手动移除或清空。

### 下载与更新

下载 **AniimoNavigator-Portable-v0.3.8.zip**，无需安装 Python。

1. 先运行旧版“退出助手.exe”。
2. 将新压缩包完整解压到新文件夹，不要覆盖正在运行的目录。
3. 双击“启动助手.exe”，使用 Chrome / Edge 选择游戏窗口。
4. 进入地宫后打开一次大地图校准，再关闭大地图继续跑图。

附带 SHA-256 校验文件。源码和便携包不包含开发测试、测试截图、个人日志或临时诊断文件。

### English

This release adds adaptive minimap-only tracking with automatic full-frame fallback, a smaller scene preview, an optional live-tracking switch, persistent marker visibility and size settings, original marker artwork, an adaptive overlay layout, entrance compatibility improvements and experimental nearby rainbow-loot markers. Map-obscuring menus retain the last known position; tracking resumes when the minimap returns. Screen sharing still captures the full game window.

Exit the previous helper, extract the complete ZIP into a new folder, then run **启动助手.exe**. Open the full game map once to calibrate. The in-app English interface remains available.

---

# v0.3.6 · 简化启动文件与中文默认界面

- 便携包根目录仅保留“启动助手.exe”和“退出助手.exe”，移除重复的英文启动、退出文件。
- 首次使用默认中文，不再跟随系统或浏览器语言；手动选择的英文偏好仍会保存。
- 启动器提示使用中文。界面中的 English 切换保留。
- 补充退出说明：关闭网页停止该页面的共享与识别，“退出助手”关闭后台服务和悬浮窗，释放内存及端口。

## English

The portable package now uses only the Chinese-named start and exit launchers. First use defaults to Chinese; an explicitly saved English preference is preserved. English UI switching remains available.

---

# v0.3.5 · 低频识别与更便捷的自动确认

- 新增 2 秒、3 秒间隔，与 0.25 秒、0.5 秒、1 秒一起提供；自动保存，默认值仍是 0.25 秒。
- 更长间隔通常降低平均 CPU 占用，但位置更新更慢，单次识别开销不变。
- 独立黄门可见时，地形确认最低分由 60 调为 50，领先差由 12 调为 10，同时要求超过次选的 1.3 倍。
- 首选明显领先时，两次不同探索画面即可累积确认；相同静止画面不重复计票，接近的候选继续观察。
- 保留黄门碎块修复、未确认悬浮预览、性能优化及画面共享修复。

## English

Adds saved 2s and 3s scan intervals. Longer intervals usually lower average CPU usage at the cost of less frequent position updates. Moderately relaxes automatic confirmation for a distinct orange entrance and clearly leading terrain match. Two distinct explored views can also confirm a clear leader; repeated identical images and close alternatives do not force a match.

---

# v0.3.4 · 黄门识别与悬浮预览修复

- 修复黄门内部白色图案把橙色区域分成多个碎块时，入口误用人物箭头的问题。
- 悬浮窗同步网页正在显示的地宫预览；未确认的地图明确标注“尚未确认”，不冒充已定位。
- 保留原有确认门槛；迷雾较多时需继续探索或手动核对候选。
- 包含 v0.3.3 的性能优化和画面连接修复。

退出旧版后完整解压新包。测试画面和临时诊断不包含在公开包中。

## English

Fixes fragmented orange gate detection. The overlay now shows the displayed dungeon preview with an explicit unconfirmed label, while player tracking still requires confirmation. Confidence thresholds are unchanged. Includes the performance and capture fixes from v0.3.3.

---

# v0.3.3 · 识别性能优化与画面连接修复

- 缩小蓝白星纹蛋的搜索范围，减少地宫大地图定位耗时。
- 小地图图像、角色点与定位条件未变化时复用结果；地形或定位条件变化后重新计算。
- 纯色画面快速跳过；耗时较长的识别留出休息时间，减少连续占用。
- 共享启动不再被视频播放等待阻塞，增加首帧超时提示，并正确清理取消和结束的共享。
- 完整打包中英文界面文件，避免旧后台与新页面混用导致 t is not defined。
- 保留 0.25 秒、0.5 秒、1 秒间隔选择、悬浮窗及自动定位。

本机固定样例测量：地宫大地图耗时约减少一半；实际收益取决于画面和电脑性能。静止小地图的缓存加速不代表移动时也有同样速度。

请先退出旧版，再完整解压 AniimoNavigator-Portable-v0.3.3.zip 到新文件夹，运行“启动助手.exe”。不要覆盖正在运行的旧目录。公开包不包含开发测试、测试截图、个人日志或临时连接诊断。

## English

Improves egg detection performance, reuses unchanged minimap results, skips uniform frames early and adds idle time after slow scans. Capture startup remains cancellable while waiting for the first frame and reports startup timeouts. Includes the complete bilingual UI. Scan intervals remain adjustable at 0.25s, 0.5s and 1s.

Exit the previous version, extract the entire ZIP into a new folder, then run Start Navigator.exe. Do not overwrite a running copy. Development tests, sample screenshots and temporary diagnostics are excluded.
