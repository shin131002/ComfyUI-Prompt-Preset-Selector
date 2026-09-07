# v1.3.0 — Subfolder Support

## Release notes (English)

The preset dropdown now reads subfolders, so preset files can be organised into folders instead of piling up in a single flat list.

### Added

- **Subfolder support**: the `presets` folder and the Impact Pack `wildcards` folder are now scanned recursively. Files inside a subfolder appear in the dropdown as a path relative to that folder (e.g. `portrait/lighting.txt`).
- `__filename__` wildcard syntax accepts subfolder paths: `__portrait/lighting__`

### Changed

- **Dropdown sort order**: entries are now sorted case-insensitively, with top-level files first and each subfolder's files grouped together. The previous ordering was by character code, which scattered uppercase, underscore and non-ASCII file names into positions that made them easy to overlook.
- README (EN/JA): added a subfolder section, a feature entry, and a troubleshooting entry for files not appearing in the dropdown

### Compatibility

Existing workflows are unaffected. Files directly inside `presets` are still listed and saved under their bare file name, and path resolution is unchanged. Subfolders are opt-in.

One visible difference: if your `presets` or `wildcards` folder already contained subfolders, those files now appear in the dropdown for the first time, so the list may be longer than before.

---

## リリースノート（日本語）

プリセットのドロップダウンがサブフォルダを読むようになりました。ファイルが一列に並ぶのではなく、フォルダで分類して整理できます。

### 追加

- **サブフォルダ対応**：`presets`フォルダとImpact Packの`wildcards`フォルダを再帰的にスキャンするようになりました。サブフォルダ内のファイルは、そのフォルダからの相対パス（例：`portrait/lighting.txt`）でドロップダウンに表示されます
- `__filename__`形式のwildcard構文がサブフォルダのパスに対応：`__portrait/lighting__`

### 変更

- **ドロップダウンの並び順**：大文字小文字を区別しない名前順に変更し、直下のファイルを先に、その後サブフォルダごとにグループ化するようにしました。従来は文字コード順だったため、大文字始まり・アンダースコア始まり・日本語名のファイルが想定外の位置に並び、見落としやすい状態でした
- README（英/日）：サブフォルダの解説、機能一覧への追記、ドロップダウンに出てこない場合のトラブルシューティングを追加

### 互換性

既存のワークフローへの影響はありません。`presets`直下のファイルは従来通りファイル名のみで表示・保存され、パス解決のロジックも変更していません。サブフォルダは任意機能です。

一点だけ見た目が変わる場合があります。すでに`presets`や`wildcards`にサブフォルダがあった場合、その中のファイルが初めてドロップダウンに現れるため、リストが以前より長くなります。

---

## Files to commit

| File | Action |
|------|--------|
| `nodes.py` | Replace (`get_preset_files` rewritten) |
| `pyproject.toml` | Replace (version 1.2.0 → 1.3.0) |
| `README.md` | Replace |
| `README_ja.md` | Replace |

`multi_source_nodes.py` and `__init__.py` are unchanged from v1.2.0.

## Commands

```bash
git add nodes.py pyproject.toml README.md README_ja.md
git commit -m "Add subfolder support to preset dropdown (v1.3.0)"
git tag -a v1.3.0 -m "v1.3.0"
git push origin main
git push origin v1.3.0
```
