from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import ast
import hashlib
import json
import re

root = Path(__file__).parent
addon = root / 'addon'
version = re.search(r'^version\s*=\s*(.+)$', (addon / 'manifest.ini').read_text(encoding='utf-8'), re.M).group(1).strip()
output = root.parent / ('lexico-' + version + '.nvda-addon')
for file in addon.rglob('*.py'):
    ast.parse(file.read_text(encoding='utf-8'), filename=str(file))
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for file in sorted(addon.rglob('*')):
        if file.is_file() and '__pycache__' not in file.parts and file.suffix != '.pyc':
            archive.write(file, file.relative_to(addon).as_posix())
with ZipFile(output) as archive:
    assert archive.testzip() is None
    assert 'manifest.ini' in archive.namelist()
metadata = dict(version=version, filename=output.name, sha256=hashlib.sha256(output.read_bytes()).hexdigest())
(root / 'update.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
(root.parent / 'update.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
print(output)
source = root.parent / 'lexico-nvda-codigo.zip'
with ZipFile(source, 'w', ZIP_DEFLATED) as archive:
    for file in sorted(root.rglob('*')):
        if file.is_file() and '__pycache__' not in file.parts and '.git' not in file.parts and file.suffix != '.pyc':
            archive.write(file, 'lexico-nvda/' + file.relative_to(root).as_posix())
print(source)
