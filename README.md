# Metro Builder

A 3D city builder for Windows: sandbox and career modes, land to buy, curved roads, detailed buildings,
editable transit terminals, traffic with signals and through traffic, people, day/night and synthesized sound.
The whole game is one HTML file (`game/index.html`); the Windows app is a small Electron window around it.

## Get the game
Every update to this repository builds the game automatically (Actions tab, about 5–8 minutes).
1. Open **Releases**.
2. Download **MetroBuilder.exe** and double-click it (portable, no install). If SmartScreen warns, choose *More info → Run anyway*.
3. Or download **MetroBuilder-PC.html** and open it in Chrome or Edge.

## Project layout
- `game/index.html` – the game (Three.js r170 with post-processing add-ons, bundled as `game/three-r170.min.js`, MIT licence in `game/THREE-LICENSE.txt`)
- `tools/build_game.py` – inlines three.js for the offline builds
- `windows/` – Electron wrapper (`main.js`, `package.json`); `F11` toggles full screen
- `.github/workflows/build-windows.yml` – builds `MetroBuilder.exe` and publishes a release

## Build locally (optional)
`python tools/build_game.py`, then in `windows/`: `npm install` and `npx electron-builder --win portable`.
