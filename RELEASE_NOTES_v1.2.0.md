# v1.2.0 — Multi-File and Folder Search

## Release notes (English)

Two new nodes for searching presets across multiple files, so preset files with different formats no longer have to be merged into one by hand.

### Added

**Prompt Preset Selector (Multi-File, Wildcard)**
- Searches up to 3 preset files at the same time
- Each slot has its own `enabled` toggle, dropdown, and absolute path field, so a file can be turned off without clearing its settings
- Lines are prefixed with their file name, so a keyword search can narrow results to a single file

**Prompt Preset Selector (Folder, Wildcard)**
- Recursively searches every `.txt` / `.yaml` / `.yml` file under a folder
- `exclude_pattern` field accepts comma-separated glob patterns for skipping backups, drafts, and similar
- Lines are prefixed with the path relative to the folder, so identically named files in different subfolders don't collide
- Files load in alphabetical order of relative path, keeping `preset_index` stable between runs

**Both nodes**
- Full wildcard support: `{A|B|C}`, `__filename__`, `{__key__|__key__}`
- `{__key__|__key__}` now searches keys across every loaded file, so keys defined in separate YAML files can reference each other
- When no source is active, the node outputs an empty string and the workflow continues rather than raising an error; the reason appears in `selected_info`

### Changed

- README (EN/JA): added sections for the new nodes, parameter tables, a detailed `exclude_pattern` reference, tips, and troubleshooting entries
- README (EN/JA): fixed the placeholder clone URL in the install instructions

### Compatibility

The existing **Prompt Preset Selector** and **Prompt Preset Selector (Wildcard)** nodes are unchanged. `nodes.py` was not modified; the new nodes live in `multi_source_nodes.py` and inherit from the existing classes. Existing workflows are unaffected.

---

## リリースノート（日本語）

複数ファイルを横断してプリセットを検索する新ノードを2つ追加しました。書式の異なるプリセットファイルを手動で1つに統合する必要がなくなります。

### 追加

**Prompt Preset Selector (Multi-File, Wildcard)**
- 最大3つのプリセットファイルを同時に検索
- 各スロットに個別の `enabled` トグル、ドロップダウン、絶対パス欄を装備。設定を消さずにファイルのON/OFFが可能
- 各行にファイル名がプレフィックスとして付くため、キーワード検索でファイル単位に絞り込める

**Prompt Preset Selector (Folder, Wildcard)**
- 指定フォルダ配下の `.txt` / `.yaml` / `.yml` をサブフォルダ含め再帰的に検索
- `exclude_pattern` 欄でglobパターン（カンマ区切り）を指定し、バックアップや下書きを除外可能
- 各行にフォルダからの相対パスが付くため、別サブフォルダの同名ファイルも衝突しない
- 相対パスのアルファベット順に読み込むため、実行間で `preset_index` が安定

**両ノード共通**
- Wildcard構文にフル対応：`{A|B|C}`、`__filename__`、`{__key__|__key__}`
- `{__key__|__key__}` は読み込んだ全ファイルを横断してキーを検索。別々のYAMLファイルに定義したキー同士の相互参照が可能に
- 有効なソースが無い場合はエラーを出さず空文字列を返し、ワークフローはそのまま継続。理由は `selected_info` に表示

### 変更

- README（英/日）：新ノードの解説、パラメータ表、`exclude_pattern` の詳細リファレンス、ヒント、トラブルシューティングを追加
- README（英/日）：インストール手順のクローンURLがプレースホルダのままだった点を修正

### 互換性

既存の **Prompt Preset Selector** と **Prompt Preset Selector (Wildcard)** は変更していません。`nodes.py` は無変更で、新ノードは `multi_source_nodes.py` に配置し既存クラスを継承しています。既存ワークフローへの影響はありません。

---

## Files to commit

| File | Action |
|------|--------|
| `multi_source_nodes.py` | New |
| `__init__.py` | Replace |
| `pyproject.toml` | Replace (version 1.1.0 → 1.2.0) |
| `README.md` | Replace |
| `README_ja.md` | Replace |

## Commands

```bash
git add multi_source_nodes.py __init__.py pyproject.toml README.md README_ja.md
git commit -m "Add Multi-File and Folder preset selector nodes (v1.2.0)"
git tag v1.2.0
git push origin main --tags
```

Then create the release on GitHub from the `v1.2.0` tag and paste the notes above.

If the ComfyUI Registry is set to publish on tag, the version bump in `pyproject.toml` is what it picks up — make sure that file is included in the commit.
