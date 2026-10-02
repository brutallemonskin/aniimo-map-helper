**[Download v0.4.1](https://github.com/brutallemonskin/aniimo-map-helper/releases/tag/v0.4.1).** Uses native capture exclusively, isolates capture failures, adds detailed diagnostics, improves overlay dragging/resizing and clears expedition records on confirmed map changes. The `0xC0000409` capture startup crash reported on some Windows 10 devices remains unresolved.

# Aniimo Map Navigator

A local map companion for Aniimo's Egg Heist mode on Windows 10/11 x64.

## Quick start

1. Extract the complete portable ZIP into a writable folder.
2. Double-click **启动助手.exe** (Start helper). No Python installation is required.
3. Open the helper in Chrome or Edge. Choose **English** in the top-right language menu.
4. Click **Local capture**, select the Aniimo window and connect. This is the only live capture method; screenshot import remains available.
5. Enter a dungeon and open the full game map to identify the map and calibrate your position.
6. Close the game map to continue tracking from the minimap. Keep the helper and screen sharing running.
7. Use **Game overlay** to display the translucent map over the game.
8. Confirmed map changes automatically clear old trails, collected markers, loot and routes. Use **New run** if the next run uses the same layout. Double-click **退出助手.exe** (Exit helper) when finished. It closes helper services and overlays across folders and versions in your current desktop session, including native capture; unrelated Python programs are preserved. Close the helper browser tabs or stop browser sharing separately.

The language menu switches instantly without resetting the current map or player position. Your selection is saved in this browser; first use defaults to Chinese.

## Overlay controls

- Drag the title bar to move the window. Drag an edge or corner to resize it proportionally.
- Use **− / +** to change opacity. Size, position and opacity are saved automatically.
- **Alt+Shift+M** toggles click-through; unlock it before moving or resizing.
- **Alt+Shift+H** shows or hides the overlay.
- **Alt+Shift+Up / Down** makes the overlay more opaque / more transparent.
- Expand **Keyboard shortcuts** below **Game overlay** to change all four combinations. Save applies immediately while the overlay is open, and preferences persist across restarts. If a combination is unavailable, the previous working shortcuts are restored and the page shows the conflict. **Restore defaults** resets these four shortcuts.

## Features and limits

Includes 32 maps (ordinary island mode only), map matching, automatic map switching, minimap position tracking, yellow-arrow and blue/white star-pattern egg recognition, island region views and marker filters. Choose a 0.25s, 0.5s, 1s, 2s or 3s scan interval; your choice is saved. First use defaults to 0.5 seconds. Legacy Automatic preferences migrate once to 0.5 seconds; other manual settings are retained. Automatic performance remains available as an optional setting. Unchanged minimap results are reused, egg detection searches smaller candidate regions, uniform frames are skipped early, and slow scans leave idle time. Processing time depends on hardware.

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

Matching currently uses CPU OpenCV/NumPy without GPU matching acceleration. Memory stores the map index and caches. Turning tracking off reduces ongoing processing but does not unload the index or stop local capture. Use Stop to end capture entirely. Default point size is 85%, with an additional 125% option.

## Overlay fit

The overlay adapts its aspect ratio to the map and removes external padding without cropping terrain or stretching it. Edge resizing preserves the current map ratio. Taller maps are constrained to the screen size.

## Saved marker visibility

Category visibility choices persist across recognition, map changes, manual confirmation, new runs and reloads. The web map and overlay share the same settings. Preferences are stored in the current browser. Choices from older versions must be set once after updating.

## Marker artwork sources

Blue-door and gold/purple/blue key-room markers come from AniimoTools. Rockling artwork comes from the official Aniimo wiki. Other maps and artwork come from Wikily. Downloaded asset bytes are unchanged; source URLs and SHA-256 hashes are recorded in data/icons/manifest.json.

Creature markers use matching base-species artwork, not dark-variant artwork. Assets load only when their category is enabled and are cached as 64px thumbnails. Saved visibility applies to both the web map and overlay.

## Trial changes

Improved sparse entrance alignment and blue-marker filtering. Failed minimap tracking now tries a throttled search on the current map and resumes only after confirmation across frames. Static map layers are cached; player movement sends coordinates to the overlay. Filters, icon size and map changes still refresh the base layer. Ambiguous terrain retains the last position.

## New expedition trial

The Automatic performance option adapts the scan interval using processing time and confirmed movement; manual intervals remain available. This estimates load, not CPU utilization. Position state and age are shown explicitly.

Optional red tours visit all unfinished egg nests along confirmed atlas passages, starting at your position without returning. Numbers indicate stop order; deep blue shows the traveled trail. Marker visibility does not filter the tour. Current atlas sizes use an exact shortest open tour; disconnected nests are explicitly counted. Locks, elevation and mechanisms must be checked in game; outdoor routing is not supported. Click markers to confirm collection; collection replans the remaining tour and supports undo. Traveled red segments disappear while blue trails remain. Sustained deviations trigger replanning with a 10-second minimum cooldown; lost positions and jumps do not erase unobserved segments. Trails contain at most 600 recent confirmed points. New runs, new capture sessions and reloads clear expedition data.

Validated with existing screenshots, movement replay, simulated slow processing and UI/package regression checks; no new live-game validation yet. Test assets are excluded from the portable package.

## v0.3.9 overlay and route fixes

Overlay mouse capture is released after interrupted dragging/resizing, missed mouse-up, hiding and closing. Simulated input regression passes; the reported Alt+Tab / Windows-key symptom still needs validation on affected hardware. Route progression and debounced deviation replanning are included. Nest collection remains manual; upper-floor support is deferred.

## Capture reliability and native capture (v0.3.9)
When the optional minimum update interval is unsupported, capture automatically retries in compatibility mode. Recognition remains paced, and interval changes do not restart that stream. The portable package includes a native patch that skips surplus frames before GPU readback, memory mapping and Python callbacks. It cannot limit Windows frame delivery; accepted frames still read the whole window, and actual savings depend on the device and driver. Windows 10 and 11 both try normal settings first. Only explicit unsupported-option errors disable the affected interval or cursor option; other failures remain visible. The 0xC0000409 startup crash reported on some Windows 10 devices remains unresolved. An unmodified capture library retains software pacing but does not provide the pre-readback optimization. Patch source and build instructions are in `native_build/`.
Local capture follows the selected recognition interval. Native frame sequences distinguish stale frames from new observations; 15-second match timeouts retry without queuing inference jobs. Moving recovery requires terrain agreement and, for larger steps, independent inter-frame motion evidence.
Choose **Local capture** and explicitly select the game window to use Windows Graphics Capture. Raw images go directly to the local matcher; the page receives results and a small preview at most once per second. The binding still maps the full window, so this is not GPU-only region capture and no performance gain is guaranteed. Unsupported minimum update intervals automatically use compatibility mode. For other errors, stop and reconnect. Native polling is paced by the server rather than background browser timers. Keep the page running; closing, freezing or discarding the tab releases capture after about 20 seconds.
Validated with an owned Windows window replaying game screenshots, including full-map to minimap transitions and DPI cropping. Live game fullscreen, different GPUs and low-end machines still need field testing.

## High-resolution overlay
Preserves the original map pixels up to a 2048px longest edge and renders directly at the physical window size. Marker display scale and filter synchronization are preserved. Cached map resizing and unchanged-frame skipping reduce repeated work; player movement still uses coordinate-only updates. Capture and recognition rates do not increase. Higher-resolution caches use some additional memory. Original asset detail remains the limit.

Native capture now runs in an isolated process. Library errors are shown directly; unexpected worker exits report the stage and exit code without terminating the HTTP service. Exit codes alone do not establish the root cause. Requests time out after 10 seconds. Frames use local shared memory plus a stable copy for recognition, adding memory/copy overhead. Network failures trigger an automatic service health check.
