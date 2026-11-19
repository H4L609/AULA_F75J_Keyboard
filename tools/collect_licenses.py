"""exe に同梱する部品のライセンスの文を app/licenses/ に集める。

PyInstaller で exe にまとめると、Python 本体や pywebview などもいっしょに配ることになる。
それぞれのライセンスが求める「ライセンスの文を付ける」を満たすため、この PC に入っている
各部品のライセンスのファイルを写す。部品の版を上げたら、もう一度実行する。

使い方: python tools/collect_licenses.py
"""
import importlib.metadata as md
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'app' / 'licenses'

# (配布名, 書き出すファイル名の頭)。ライセンスのファイルは dist-info から探す
PACKAGES = [
    ('pywebview', 'pywebview'),
    ('bottle', 'bottle'),
    ('pythonnet', 'pythonnet'),
    ('clr_loader', 'clr_loader'),
    ('cffi', 'cffi'),
    ('pycparser', 'pycparser'),
    ('typing_extensions', 'typing_extensions'),
    ('setuptools', 'setuptools'),
    ('packaging', 'packaging'),
    ('pyinstaller', 'PyInstaller'),
]

MIT = """MIT License

{copyright}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# ライセンスのファイルを持っていない部品（配布物の情報に MIT とだけ書いてある）
EXTRA_MIT = {
    'proxy_tools': 'Copyright (c) Jonathan Tushman (https://github.com/jtushman/proxy_tools)',
    'dotnet-runtime': 'Copyright (c) .NET Foundation and Contributors\n'
                      '(pythonnet に同梱の System.*.dll / Microsoft.*.dll。https://github.com/dotnet/runtime)',
}

# setuptools / pkg_resources の中に入っている部品（ライセンスのファイルが付いていない）
VENDORED = """setuptools と pkg_resources の中に入っている部品（_vendor）

exe には setuptools と pkg_resources がいっしょに入っている。その中に、次の部品が含まれる。
いずれも、元の配布ではライセンスのファイルが付いていないため、名前・ライセンス・入手先を記す。

| 部品 | ライセンス | 入手先 |
|---|---|---|
| appdirs | MIT（Copyright (c) 2005-2010 ActiveState Software Inc., Copyright (c) 2013 Eddy Petrișor） | https://github.com/ActiveState/appdirs |
| pyparsing | MIT（Copyright (c) 2003-2022 Paul T. McGuire） | https://github.com/pyparsing/pyparsing |
| packaging | Apache-2.0 または BSD-2-Clause（packaging-LICENSE*.txt を参照） | https://github.com/pypa/packaging |
| more_itertools | MIT（Copyright (c) 2012 Erik Rose） | https://github.com/more-itertools/more-itertools |
| jaraco.text / jaraco.functools / jaraco.context | MIT（Copyright Jason R. Coombs） | https://github.com/jaraco |
| importlib_metadata / importlib_resources / zipp | Apache-2.0 | https://github.com/python/importlib_metadata ほか |
| ordered_set | MIT（Copyright (c) 2018 Elia Robyn Speer） | https://github.com/rspeer/ordered-set |
| tomli | MIT（Copyright (c) 2021 Taneli Hukkinen） | https://github.com/hukkin/tomli |
| typing_extensions | PSF-2.0（typing_extensions-LICENSE.txt を参照） | https://github.com/python/typing_extensions |

MIT ライセンスの文は、ほかの *-LICENSE.txt と同じ（著作権者の行だけが違う）。
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    written = []

    # Python 本体（同梱の OpenSSL・libffi・bzip2・expat・xz などのライセンスも、このファイルに入っている）
    py_lic = Path(sys.base_prefix) / 'LICENSE.txt'
    ver = '.'.join(map(str, sys.version_info[:3]))
    (OUT / 'Python-LICENSE.txt').write_text(py_lic.read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
    written.append(('Python', ver, 'Python-LICENSE.txt'))

    for dist, stem in PACKAGES:
        d = md.distribution(dist)
        files = [f for f in (d.files or []) if '.dist-info' in str(f) and
                 any(k in f.name.upper() for k in ('LICENSE', 'COPYING'))]
        for i, f in enumerate(sorted(files, key=lambda f: f.name)):
            name = f'{stem}-{f.name}' if f.name.upper() != 'LICENSE' else f'{stem}-LICENSE.txt'
            if not name.endswith('.txt'):
                name += '.txt'
            text = Path(d.locate_file(f)).read_text(encoding='utf-8', errors='replace')
            (OUT / name).write_text(text, encoding='utf-8')
            written.append((dist, d.version, name))

    for stem, cr in EXTRA_MIT.items():
        name = f'{stem}-LICENSE.txt'
        (OUT / name).write_text(MIT.format(copyright=cr), encoding='utf-8')
        ver = md.version(stem) if stem == 'proxy_tools' else ''
        written.append((stem, ver, name))

    (OUT / 'setuptools-vendored.txt').write_text(VENDORED, encoding='utf-8')
    written.append(('setuptools / pkg_resources の中の部品', '', 'setuptools-vendored.txt'))

    for w in written:
        print(*w)


if __name__ == '__main__':
    main()
