# Aniimo Map Navigator

A local map companion for Aniimo's Egg Heist mode on Windows 10/11 x64.

## Quick start

1. Extract the complete portable ZIP into a writable folder.
2. Double-click **启动助手.exe** (Start helper). No Python installation is required.
3. Open the helper in Chrome or Edge. Choose **English** in the top-right language menu.
4. Click **Select game window** and share the full game window.
5. Enter a dungeon and open the full game map to identify the map and calibrate your position.
6. Close the game map to continue tracking from the minimap. Keep the helper and screen sharing running.
7. Use **Game overlay** to display the translucent map over the game.
8. Use **New run** when starting another run. Double-click **退出助手.exe** (Exit helper) when finished.

The language menu switches instantly without resetting the current map or player position. Your selection is saved in this browser; first use defaults to Chinese.

## Overlay controls

- Drag the title bar to move the window. Drag an edge or corner to resize it proportionally.
- Use **− / +** to change opacity. Size, position and opacity are saved automatically.
- **Alt+Shift+M** toggles click-through; unlock it before moving or resizing.
- **Alt+Shift+H** shows or hides the overlay.

## Features and limits

Includes 33 maps, map matching, automatic map switching, minimap position tracking, yellow-arrow and blue/white star-pattern egg recognition, island region views and marker filters. Choose a 0.25s, 0.5s, 1s, 2s or 3s scan interval; your choice is saved. The default is 0.25s. Unchanged minimap results are reused, egg detection searches smaller candidate regions, uniform frames are skipped early, and slow scans leave idle time. Processing time depends on hardware.

When the map is obscured or cannot be matched, the helper keeps the last known position. This is not a guarantee that the player has remained stationary. Reopen the full game map to recalibrate if tracking drifts.

English UI, status messages, categories and overlay controls are included. Unverified creature/item proper names keep their source spelling alongside an English category. Region names are descriptive translations, not verified official English names. Compatibility with English-language game capture has not yet been verified; screen layout and icon changes can affect matching.

Screenshots are processed on your own computer, not uploaded to a cloud service. The helper does not read game memory or control character movement. Closing the browser page ends its sharing and scans but leaves the local server running. Use 退出助手.exe to close the server and overlay and release memory and the local port. Keep the extracted folder intact. Window settings, logs and process IDs may be written locally.

## Source usage

On Windows x64 with Python 3.13, install `requirements.txt` and run `python server.py`. Open `http://127.0.0.1:18731`. See `build_portable.py` for the portable build allowlist and `THIRD_PARTY_NOTICES.md` for attribution and dependency notices.

Maps and points are sourced from Wikily. Aniimo and its artwork belong to their respective rights holders.
