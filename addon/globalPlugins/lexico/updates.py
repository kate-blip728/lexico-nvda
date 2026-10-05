"""Fetch public GitHub update metadata and verify the installer."""
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile

VERSION = '0.5.0'
BASE = 'https://raw.githubusercontent.com/kate-blip728/lexico-nvda/main/'

def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('Versión de actualización no válida.')
    return tuple(map(int, value.split('.')))

def fetch(url, maximum):
    with urlopen(Request(url, headers={'User-Agent': 'Lexico-NVDA/' + VERSION}), timeout=30) as response:
        if not response.geturl().startswith(BASE):
            raise ValueError('La descarga no procede del repositorio de Léxico.')
        data = response.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError('La descarga supera el tamaño permitido.')
        return data

def check():
    metadata = json.loads(fetch(BASE + 'update.json', 16384).decode('utf-8'))
    remote = metadata['version']
    if version_tuple(remote) <= version_tuple(VERSION):
        return None
    if metadata.get('filename') != 'lexico-' + remote + '.nvda-addon':
        raise ValueError('Nombre del instalador no válido.')
    if not re.fullmatch(r'[a-f0-9]{64}', metadata.get('sha256', '')):
        raise ValueError('Falta la suma de verificación del instalador.')
    return metadata

def download(metadata, directory):
    data = fetch(BASE + metadata['filename'], 20 * 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != metadata['sha256']:
        raise ValueError('La verificación de la descarga ha fallado.')
    path = Path(directory) / metadata['filename']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError('El instalador está dañado.')
        manifest = archive.read('manifest.ini').decode('utf-8')
        if not re.search(r'^name\s*=\s*lexico\s*$', manifest, re.M) or not re.search(
                r'^version\s*=\s*' + re.escape(metadata['version']) + r'\s*$', manifest, re.M):
            raise ValueError('El instalador no corresponde a esta actualización.')
    return path
