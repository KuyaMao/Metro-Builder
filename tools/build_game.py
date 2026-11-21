"""Inline three.js into the game so the Android app and the PC file run fully offline."""
import pathlib, sys
root = pathlib.Path(__file__).resolve().parent.parent
html = (root / 'game/index.html').read_text(encoding='utf-8')
three = (root / 'game/three.min.js').read_text(encoding='utf-8')
tag = '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>'
if html.count(tag) != 1:
    sys.exit('three.js script tag not found in game/index.html')
out = html.replace(tag, '<script>' + three.replace('</script>', '<\\/script>') + '</script>')
assets = root / 'app/src/main/assets'
assets.mkdir(parents=True, exist_ok=True)
(assets / 'index.html').write_text(out, encoding='utf-8')
(root / 'MetroBuilder-PC.html').write_text(out, encoding='utf-8')
print(f'Game built: {len(out)//1024} KB')
