"""Package only addon contents, placing manifest.ini at archive root."""
import argparse
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tested-nvda-version', required=True,
                        help='Version actually checked on Windows/NVDA, e.g. 2025.3')
    args = parser.parse_args()
    version = args.tested_nvda_version
    if not re.fullmatch(r'\d{4}\.\d+(?:\.\d+)?', version):
        parser.error('Use a numeric NVDA version such as 2025.3 or 2025.3.1.')
    numeric = tuple(int(x) for x in version.split('.'))
    if numeric + (0,) * (3 - len(numeric)) < (2025, 1, 0):
        parser.error('The tested version must be at least 2025.1.')
    root = Path(__file__).resolve().parent
    addon = root / 'addon'
    destination = root / 'dist' / 'vocabularySaver-0.1.0-dev.nvda-addon'
    destination.parent.mkdir(exist_ok=True)
    manifest = (addon / 'manifest.ini').read_text(encoding='utf-8')
    manifest = re.sub(r'^lastTestedNVDAVersion\s*=.*$', f'lastTestedNVDAVersion = {version}', manifest, flags=re.MULTILINE)
    with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(addon.rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            relative = path.relative_to(addon).as_posix()
            if relative == 'manifest.ini':
                archive.writestr(relative, manifest.encode('utf-8'))
            else:
                archive.write(path, relative)
    print(destination)
    print('Package built with your supplied tested version. This does not perform runtime testing.')


if __name__ == '__main__':
    main()
