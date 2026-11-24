"""Inline three.js into the game so the Windows app and the PC file run fully offline."""
import pathlib, sys
root = pathlib.Path(__file__).resolve().parent.parent
html = (root / 'game/index.html').read_text(encoding='utf-8')
three = (root / 'game/three-r170.min.js').read_text(encoding='utf-8')
tag = '<script src="three-r170.min.js"></script>'
if html.count(tag) != 1:
    sys.exit('three.js script tag not found in game/index.html')
out = html.replace(tag, '<script>/* three.js r170 + post-processing add-ons, MIT licence (see THREE-LICENSE.txt) */\n' + three.replace('</script>', '<\\/script>') + '</script>')
ptag = '<script src="texpack.js"></script>'
if out.count(ptag) != 1:
    sys.exit('texpack.js script tag not found in game/index.html')
out = out.replace(ptag, '<script>' + (root / 'game/texpack.js').read_text(encoding='utf-8') + '</script>')
mtag = '<script src="modelpack.js"></script>'
if out.count(mtag) != 1:
    sys.exit('modelpack.js script tag not found in game/index.html')
out = out.replace(mtag, '<script>' + (root / 'game/modelpack.js').read_text(encoding='utf-8') + '</script>')
(root / 'windows/app').mkdir(parents=True, exist_ok=True)
(root / 'windows/app/index.html').write_text(out, encoding='utf-8')
(root / 'MetroBuilder-PC.html').write_text(out, encoding='utf-8')
print(f'Game built: {len(out)//1024} KB')
