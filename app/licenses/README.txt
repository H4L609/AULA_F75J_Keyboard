AULA F75J キー配置エディタ に同梱しているもの

1. sinowisp.exe（書き込みツール）
   作者: Karolis Stasaitis（carlossless）
   入手先: https://github.com/carlossless/sinowealth-kb-tool
   ライセンス: MIT（sinowisp-LICENSE.txt）

2. firmware-base.hex（キーボードに書き込むファーム）
   SMK（https://github.com/carlossless/smk）の AULA F75 移植版
   （https://github.com/Thaolia/smk_aulaF75）を元に、AULA F75J（日本語配列）向けに変更したもの。
   ライセンス: GPL-2.0（SMK-LICENSE-GPL-2.0.txt）
   変更点を含むソースコード: https://github.com/H4L609/smk_aula_f75j （aula-f75j ブランチ）
   アプリ全体のソース: https://github.com/H4L609/AULA_F75J_Keyboard

3. アプリ本体（F75JKeymap.exe）に入っている部品
   アプリは PyInstaller で、Python と次の部品を 1 つの exe にまとめている。

   | 部品 | ライセンス | ファイル |
   |---|---|---|
   | Python 3.10（標準ライブラリ。OpenSSL・libffi・bzip2・expat・xz などを含む） | PSF ほか | Python-LICENSE.txt |
   | pywebview（アプリの窓） | BSD-3-Clause | pywebview-LICENSE.txt |
   | bottle | MIT | bottle-LICENSE.txt |
   | proxy_tools | MIT | proxy_tools-LICENSE.txt |
   | pythonnet | MIT | pythonnet-LICENSE.txt |
   | clr_loader | MIT | clr_loader-LICENSE.txt |
   | .NET の部品（pythonnet に同梱の System.*.dll など） | MIT | dotnet-runtime-LICENSE.txt |
   | cffi | MIT-0 | cffi-LICENSE.txt |
   | pycparser | BSD-3-Clause | pycparser-LICENSE.txt |
   | typing_extensions | PSF-2.0 | typing_extensions-LICENSE.txt |
   | setuptools / pkg_resources | MIT | setuptools-LICENSE.txt、setuptools-vendored.txt |
   | packaging | Apache-2.0 または BSD-2-Clause | packaging-LICENSE*.txt |
   | PyInstaller の起動部分 | GPL-2.0（起動部分は例外として、まとめたアプリにライセンスが及ばない） | PyInstaller-COPYING.txt |

   VCRUNTIME140.dll と api-ms-win-*.dll は、Microsoft が再配布を認めている Windows の部品。
   この一覧は tools/collect_licenses.py で作り直せる。

注意
- 自作ファームへの書き換えは、メーカーの保証の対象外。自分の責任で使うこと。
- 元のファームに戻すには、書き換え前に取ったバックアップを sinowisp で書き戻す。
