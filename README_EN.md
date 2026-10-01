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

## Rainbow loot hints (experimental)

Two consecutive gameplay detections of a tall pink/purple beam, together with a fresh minimap position, record a **player discovery location**, not the exact loot coordinates. The web map and dungeon overlay show matching markers. Distant beams are also recorded at the player’s position. Similar effects may trigger false detections; small, obscured or edge-of-screen beams can be missed. Approach to verify. Pause automatic marking, remove collected/false entries, or clear all entries in the panel. New run, restarting sharing, and page reload clear this page session. Imported still images do not create discoveries.

Validated on two reference images at multiple scales and automated state/rendering checks; live gameplay validation is still needed.

## Entrance compatibility

Compensates for uniformly dim map captures and normalizes smaller window sizes for door/terrain analysis, without relaxing confirmation thresholds. Regression checks cover 24 variants of three entrance references, including resolution, JPEG compression and dimming. This is not HDR decoding and does not establish a fix for every reported failure. Keep both doors and the entrance room visible on the full map; adjust map zoom or explore further if necessary.

## Map icon size

Chests, doors and other map points default to 85% of their previous size with translucent backgrounds. Under Map markers → Icon size, choose 50%, 70%, 85%, 100% (original) or 125%. The web map and overlay share the saved preference. The player position remains prominent.

## Original marker assets and live settings

Uses original icon files referenced by Wikily Aniimo maps; provenance and hashes are included in data/icons/manifest.json. No new point artwork is generated. Blue-door and key-room artwork is included; unavailable room artwork uses text. Shared chest artwork retains quality colors and letter badges. Same-name, same-category records within four map pixels are merged. Other types/names/sites remain separate. Icon size and category changes immediately publish to the overlay, with a trailing refresh for rapid changes even when recognition is paused. Native polling remains approximately 0.25 seconds.

## Live tracking switch

During gameplay, tracking sends a lossless minimap crop. If the HUD disappears, the same scan requests a full frame. A full-frame check also runs approximately every five seconds (at the next scheduled scan), on capture resolution changes and for Recognize now. Full-map identification and calibration retain their original resolution.

The browser preview is limited to an 800px longest edge. When rainbow-loot detection is enabled, this small scene is also sent for beam detection. Screen sharing still captures the entire game window; this optimization reduces local image transport, decoding and preview processing, rather than eliminating full-window capture. Game FPS improvements are not guaranteed.

Game capture includes a saved Live tracking switch, enabled by default. Turning it off retains the last position and skips minimap matching and rainbow-loot detection. Full-map checks continue at no more than once per second (a selected 2s/3s interval remains in effect). Reopen the full map to calibrate after enabling again.

Matching currently uses CPU OpenCV/NumPy without GPU matching acceleration. Memory stores the map index and caches. Turning tracking off reduces ongoing processing but does not unload the index or stop the browser capture stream. Use Stop to end capture entirely. Default point size is 85%, with an additional 125% option.

## Overlay fit

The overlay adapts its aspect ratio to the map and removes external padding without cropping terrain or stretching it. Edge resizing preserves the current map ratio. Taller maps are constrained to the screen size.

## Saved marker visibility

Category visibility choices persist across recognition, map changes, manual confirmation, new runs and reloads. The web map and overlay share the same settings. Preferences are stored in the current browser. Choices from older versions must be set once after updating.

## Marker artwork sources

Blue-door and gold/purple/blue key-room markers come from AniimoTools. Rockling artwork comes from the official Aniimo wiki. Other maps and artwork come from Wikily. Downloaded asset bytes are unchanged; source URLs and SHA-256 hashes are recorded in data/icons/manifest.json.

Creature markers use matching base-species artwork, not dark-variant artwork. Assets load only when their category is enabled and are cached as 64px thumbnails. Saved visibility applies to both the web map and overlay.
