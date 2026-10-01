# 第三方素材与运行库

地图和点位数据来源于 Wikily 的《伊莫》地图页面：

- https://wikily.gg/zh-cn/aniimo/map
- https://wikily.gg/zh-cn/aniimo/egg-heist
- https://wikily.gg/zh-cn/aniimo/egg-heist-team-mode

各地图 JSON 中保留具体来源链接。相关游戏素材、名称与标识归各自权利人所有。

便携版包含 Python、NumPy、OpenCV 和 Pillow。其许可及相关第三方声明保留于 `runtime/LICENSE.txt` 和 `runtime/Lib/site-packages/` 下相应的 `*.dist-info` 目录。地图素材不适用这些软件运行库的许可。

Map marker artwork: original image files referenced by Wikily Aniimo maps, downloaded unchanged. Per-asset URLs and SHA-256 checksums are in app/data/icons/manifest.json (data/icons/manifest.json in source). Artwork remains the property of its rights holders.

Additional original marker/species artwork is sourced from AniimoTools (https://aniimotools.dev/map/lost-sanctum/) and the official Aniimo wiki (https://wiki.yimo.com/item/070/basic-form). Exact source URLs and checksums are retained in data/icons/manifest.json. These assets remain subject to their respective rights holders.

## Windows Capture 2.0.1
Native capture uses the MIT-licensed windows-capture Python distribution by NiiightmareXD. Source: https://github.com/NiiightmareXD/windows-capture . Its license is retained in runtime/Lib/site-packages/windows_capture-2.0.1.dist-info/licenses/LICENCE.

The bundled distribution is locally modified to skip surplus frames before GPU readback. Upstream commit: c7d106448eb9d9b251345c39047711e1cd408ae2. The source patch and build instructions are in native_build/; runtime/Lib/site-packages/windows_capture/ANIIMO_PATCH.txt identifies the modification. Accepted frames still read the full window. Original third-party licenses remain applicable.

Limited-time challenge locations: 35 reference positions across 21 layouts from AniimoTools Team Mode data (https://aniimotools.dev/map/lost-sanctum/), retrieved 2026-10-01. Each supported map JSON retains its exact data URL, checksum and terrain-to-atlas coordinate transform. Multiple candidate rooms are alternatives for a single challenge. Other layouts have no inferred challenge positions. The original monster artwork is used as a special-room marker by user choice; this does not identify those rooms as guaranteed bosses.
