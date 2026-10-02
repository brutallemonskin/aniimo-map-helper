## v0.4.1 · 本地采集隔离、错误诊断与悬浮窗交互

### 2026-10-02 · 同版本更新

- 海岛仅保留普通抢蛋模式，移除模式选择；不再索引小队海岛，当前共 32 张可识别地图。
- 默认识别间隔改为 0.5 秒。旧的“自动性能”偏好首次更新时切到 0.5 秒，其他手动间隔保留；之后仍可自行选择自动性能。
- 本次更新不包含 DXGI 测试采集。已下载此前 v0.4.1 的玩家需要重新下载并解压新版压缩包。

相比正式版 v0.4：

- **统一本地采集**：移除浏览器屏幕分享入口，保留截图导入。点击“本地采集”，手动选择伊莫窗口连接；画面仅在本机处理。
- **改善悬浮窗拖动和缩放**：补充拖动期间的鼠标位置与松键检查，减少丢失鼠标移动事件导致的卡住；仍需在关闭鼠标穿透后操作。
- **切换地宫清理旧记录**：确认识别到不同地图，或手动确认另一张地图后，清空旧轨迹、拾取记录、彩虹掉落标记及规划路线。候选预览、暂时遮挡和同图校准不会清空；同一布局的新一局仍需点“新一局”。
- **隔离采集故障**：本地采集运行在独立进程，采集库异常退出不会直接带走网页服务；启动或读取超时会终止该采集进程，允许重新连接。
- **直接显示错误原因**：显示采集库返回的错误；异常退出时显示阶段和退出码。网络请求失败后自动检查后台状态。阶段日志及时写入，便于反馈问题，不记录游戏截图。
- **按接口支持情况回退**：Win10 / Win11 均先尝试正常参数；只有明确提示不支持时才分别停用最小更新间隔或使用默认光标设置，保留原生读回前跳帧。
- **统一下载包命名**：ZIP 和内部文件夹均为 `aniimo_map_helper_v0.4.1`。

### 下载与更新

下载 **aniimo_map_helper_v0.4.1.zip**，适用于 Windows 10/11 x64，免安装、无需另装 Python。附带 SHA-256 校验文件。

1. 使用“退出助手.exe”退出旧版。
2. 完整解压到新文件夹，不要覆盖正在运行的目录。
3. 双击“启动助手.exe”，点击“本地采集”选择游戏窗口，再打开游戏大地图校准。

除上文所述自动性能偏好的迁移外，浏览器已有偏好保留；新目录不会自动迁移旧目录的悬浮窗位置及快捷键文件。

### 验证与已知限制

- 已验证参数回退、独立进程异常退出与超时、网页连接恢复、地图切换记录清理和悬浮窗拖动回归；使用自建样例窗口验证真实 WGC 采集、大地图校准转小地图追踪及间隔切换。
- **部分 Win10 设备的 `0xC0000409` 采集启动崩溃仍未解决。** 进程隔离和详细报错便于恢复及诊断，不代表已修复崩溃根因。DXGI 采集未包含在此版。
- 采集进程间使用本机共享内存，并在识别前复制稳定图像，会增加内存及复制开销；不承诺所有设备都更快。尚需不同设备的真实游戏复测。
- 发布包排除开发测试、测试截图、个人设置、日志与编译工具，保留素材来源及第三方许可。

### English

Same-version refresh (2026-10-02): ordinary island mode only, with 32 indexed maps; default scanning is now 0.5s. Legacy Auto preferences migrate once to 0.5s; other manual intervals are preserved. Re-download the portable ZIP to update. DXGI is not included.

v0.4.1 uses native window capture exclusively while retaining screenshot import. It improves overlay drag/resize recovery, clears expedition records on confirmed changes to a different map, isolates capture into a worker process, and shows original errors or crash stages and exit codes. Connection failures trigger an automatic service health check. Unsupported update-interval or cursor settings fall back individually, without a blanket Windows 10 profile; native pre-readback pacing remains enabled.

Download **aniimo_map_helper_v0.4.1.zip**, exit the old helper, extract into a new folder, run **启动助手.exe**, select the game window with Local capture, and open the full game map to calibrate. Use New run when a new match has the same layout. The `0xC0000409` startup crash on some Windows 10 devices remains unresolved; DXGI capture is not included. Process isolation adds memory/copy overhead. Private tests, screenshots, settings, logs and build tools are excluded.

---

## v0.4 · 采集性能优化、自定义快捷键与挑战点位

相比正式版 v0.3.9，本版包含以下更新：

- **修复剩余红线消失**：标记蛋巢拾取或重新规划时保留最后有效的剩余路线。新路线暂不可用、请求超时或返回不完整时自动重试，避免还没走完的红线被直接清空。
- **网页自定义快捷键**：可设置悬浮窗鼠标穿透、隐藏／显示、增加不透明度、增加透明度。保存后立即生效并记忆，支持恢复默认；重复或被占用的组合会提示，应用失败时保留原来的可用快捷键。
- **精简悬浮窗**：移除底部快捷键提示，给地图更多显示空间；快捷键设置集中在网页“游戏悬浮窗”下方。拖动、缩放和标题栏按钮保留。
- **本地采集兼容修复**：遇到系统不支持 `minimum update interval` 的报错时自动进入兼容模式。兼容模式切换识别间隔无需重启采集；其他采集错误仍会提示。
- **降低本地采集开销**：内置原生采集节流补丁，在 GPU 画面读回、内存映射和 Python 回调之前跳过多余帧，减少无效复制与处理。保留帧仍读取整个窗口，不是纯小地图 GPU 采集；实际收益取决于设备及驱动。
- **特殊房间图标**：改用原始怪物图标，修复高清悬浮窗中文字标记和角标缩放过小的问题。特殊房间标记不代表该处必定出现 Boss。
- **新增限时挑战点位**：加入独立游戏图标与显示开关，默认开启。收录 21 张地宫、35 个参考位置，来自 AniimoTools 小队模式资料；多个候选位置不代表同时出现，以当前对局为准。未取得资料的地图不推测点位。
- **图标同步**：特殊房间和限时挑战沿用网页／悬浮窗实时同步，大小、显示选择及切换地图后的设置保持一致。

### 下载与更新

下载 **AniimoNavigator-Portable-v0.4.zip**，适用于 Windows 10/11 x64，免安装、无需另装 Python。附带 SHA-256 校验文件。

1. 先运行“退出助手.exe”退出旧版本。
2. 将新 ZIP 完整解压到新文件夹，不要覆盖正在运行的目录。
3. 双击“启动助手.exe”，重新选择游戏窗口，打开游戏大地图校准。
4. 快捷键在网页设置。默认鼠标穿透为 Alt+Shift+M，隐藏／显示为 Alt+Shift+H，透明度为 Alt+Shift+↑／↓。

浏览器内已有偏好保留；使用新文件夹时，旧目录中的悬浮窗位置和快捷键文件不会自动迁移。

### 验证与说明

- 已完成路线保留、快捷键、采集兼容、网页与悬浮窗图标同步回归，以及原生窗口采集验证；挑战点位通过底图地形配准，并用两门位置独立核对。
- 发布包经过独立运行库启动与地图索引检查、ZIP 完整性和素材校验，不含开发测试、测试截图、个人设置、日志或编译工具。
- 尚未完成不同配置电脑的真实游戏全屏复测，不承诺所有设备的性能提升幅度。
- 点位资料来源：https://aniimotools.dev/map/lost-sanctum/ 。保留原有地图素材来源及第三方许可说明。

### English

Compared with v0.3.9, v0.4 preserves remaining nest routes while replanning and retries failed requests; adds configurable overlay shortcuts in the web page; removes the overlay footer; handles unsupported capture update intervals automatically; and skips surplus native frames before GPU readback and Python callbacks. It also replaces special-room markers with original monster artwork, fixes high-resolution marker scaling, and adds 35 reference challenge positions across 21 layouts. Challenge data references Team Mode; multiple candidate markers are alternatives, not simultaneous challenges. Marker visibility and size synchronize with the overlay.

Extract the full ZIP into a new folder after closing the old helper. Run **启动助手.exe**, select the game window and reopen the full game map to calibrate. Native capture still reads retained full-window frames; performance and fullscreen compatibility vary by device. Private tests, screenshots, settings, logs and build tools are excluded.


---

## v0.3.9 · 跑图路线、定位恢复与高清悬浮窗

本版相较公开版 **v0.3.8** 汇总了近期本地测试版本的改进，正式版本号统一为 **v0.3.9**。本地 0.3.10～0.3.14 为开发测试编号，并非需要另外安装的前置版本。

### 退出工具补充修复

- 本次更新后的“退出助手.exe”可退出不同目录、不同版本及端口的地图助手，无需使用原目录。优先请求正常退出，等待后仅结束已确认属于助手的残留后台或悬浮窗；不批量结束 Python。
- 已验证多目录、多版本、卡住后台、重复退出及无关 Python 保留。附加独立退出工具，可单独下载使用。浏览器共享仍请手动停止或关闭助手标签页。

### 主要改动

- **蛋巢遍历路线**：以当前已确认的位置为起点，规划经过所有未完成蛋巢的红色参考路线，标出访问顺序；无需返回起点。深蓝色记录实际确认走过的轨迹。走完的红线路段逐步消退，持续偏航后自动重新规划；手动标记已拾取后重算剩余路线，支持撤销。网页与悬浮窗同步。
- **更稳妥的定位恢复**：补强刚进入地宫时的两门与地形对齐，减少部分蓝色队友标记干扰。小地图失去位置后限频搜索当前地图，连续确认后恢复；低频识别下较大的位移还需通过两帧地形运动校验。保留相似房间歧义检查，避免直接放宽阈值造成错误跳房间。
- **自动性能档**：根据近期处理耗时和静止状态调整识别间隔；首次使用默认自动，已有手动选择保留。仍可选择 0.25、0.5、1、2、3 秒。定位状态区分已确认、保留位置、重新定位和关闭，并显示上次确认时间。
- **采集卡帧与超时处理**：浏览器申请的采集帧率跟随识别间隔；没有新视频帧时保留位置，恢复后继续。识别请求超时后自动重试，服务端不堆积识别任务。
- **本地采集（试用）**：新增 Windows Graphics Capture 方式，手动选择游戏窗口后即可连接，无需浏览器屏幕共享。画面直接交给本机识别，网页只接收结果及小预览，减少浏览器图片编码与传输；原有分享方式仍保留。
- **高清悬浮窗**：底图保留原始像素，最长边上限 2048，并按悬浮窗实际像素绘制，改善放大后的模糊。人物移动只更新坐标和路线，静态底图与缩放结果复用缓存，未变化画面跳过重绘；图标大小与筛选继续同步。
- **交互与启动修复**：补上悬浮窗拖动、缩放中断或隐藏、关闭时的鼠标捕获释放保护；启动器检测到其他版本运行时提示切换，避免新页面误连旧服务。

### 下载与使用

下载 **AniimoNavigator-Portable-v0.3.9.zip**，Windows 10/11 x64 免安装，无需安装 Python。附带 SHA-256 校验文件。

1. 先退出旧版助手，将新 ZIP 完整解压到新的可写文件夹，不要覆盖正在运行的目录。
2. 双击 **启动助手.exe**，建议使用 Chrome / Edge。
3. 选择“选择游戏窗口”，或尝试“本地采集（试用）”并手动连接游戏窗口。
4. 进入地宫后打开一次大地图校准，再关闭大地图继续定位；需要时开启“游戏悬浮窗”。

已有浏览器偏好会保留，不会自动清空玩家设置。使用本地 0.3.14 测试版的用户也按以上步骤切换到正式 0.3.9。

### 验证与边界

- 发布前使用已有游戏截图、移动回放、低频识别模拟、路线与界面回归、独立 Windows 窗口采集，以及中文路径下的完整免安装包验证。源码和发布包不包含开发测试、测试截图、个人设置或诊断日志。
- 路线仅依据可确认连通的底图网格，未接入高台图层，不校验门锁、机关及高低差；无法确认连通的蛋巢会提示。经过附近不会自动算作拾取。
- 轨迹和拾取记录只属于当前页面会话，新一局、重新共享或刷新会清空。地图遮挡、无新帧或定位不确定时保留最后位置，不代表角色仍在原地。
- 本地采集仍映射整个窗口，识别主要使用 CPU；实际收益取决于 Windows、显卡驱动及机器配置。不兼容时可改回浏览器分享。高清缓存会增加部分内存占用，清晰度仍受原图素材限制。
- 本版未完成不同配置电脑的真实游戏全屏复测，不能承诺解决所有定位中断、白屏或快捷键反馈。截图仅在本机处理，不上传云端。

### English

Public v0.3.9 consolidates the local trials through 0.3.14. Compared with v0.3.8, it adds an egg-nest tour (red), confirmed travel history (dark blue), route progress and deviation recovery, automatic scan pacing, clearer tracking status, guarded minimap relocalization, capture-stall and timeout recovery, optional native Windows capture, and a high-resolution cached overlay. It also adds interrupted-drag capture-release protection and a launcher version-switch prompt.

Extract the full ZIP into a new folder, exit the previous helper, and run **启动助手.exe**. Reopen the full game map once to calibrate. Native capture remains experimental; real fullscreen compatibility and performance vary by hardware. Routes use the available atlas and do not account for upper floors, locks or mechanisms. Development tests, personal settings, screenshots and logs are excluded from the release.


---

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
