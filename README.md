# Metro Builder

A mobile-first 3D city builder for Android and PC: sandbox and career modes, detailed buildings,
editable transit terminals, traffic with signals, people, day/night from your phone's clock, and synthesized sound.
The whole game is one HTML file (`game/index.html`) that runs offline in a full-screen Android WebView.

## Get the game
Every update to this repository builds the game automatically (Actions tab, about 5 minutes).
1. Open **Releases** (right side on desktop; scroll down on mobile).
2. On your **phone**, download **MetroBuilder.apk**, open it, and allow "Install unknown apps" for your browser.
3. On a **PC**, download **MetroBuilder-PC.html** and double-click it.

## Project layout
- `game/index.html` – the game (Three.js r128, vendored as `game/three.min.js`, MIT licence)
- `tools/build_game.py` – inlines three.js for the offline builds
- `app/` – Android WebView wrapper (no extra libraries, about 1 MB)
- `.github/workflows/build-apk.yml` – builds the APK and publishes a release

## Build locally (optional)
`python3 tools/build_game.py`, then open the folder in Android Studio and choose Build → Build APK(s).
Release builds are signed with the debug key so they install directly; use your own key for the Play Store.
