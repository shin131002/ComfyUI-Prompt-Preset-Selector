# v1.4.0 — Keyword Output, Additional Text & Strength, Fixes

## Release notes (English)

Every node now outputs the keywords the selected preset actually matched, and can append extra text and apply a weight to its output. `__filename__` wildcards that were silently left unexpanded in some cases now work, and a few output and YAML key issues are fixed.

### Added

- **`keyword` output** (all nodes): the include keywords the selected preset matched, joined with `_`
  - AND: all keywords (`front close-up` → `front_close-up`)
  - OR: only the keywords that matched (`front back` → `front` or `back`); if the line contains several, all of them are joined in input order
  - OFF: empty
  - Spaces inside a quoted phrase become `_` (`"front view" close-up` → `front_view_close-up`)
  - `:` in YAML key searches becomes `_` and a trailing `:` is dropped (`camera_angles:close_up:` → `camera_angles_close_up`), so the text can be used in a file name
  - Exclude keywords (`-wide`) are never output; case is kept as typed
- **Additional text & strength** (all nodes): three widgets at the bottom of each node
  - `enable_additional_text`: ON/OFF switch (default OFF)
  - `additional_text`: appended as `preset, additional_text` when ON. Lines starting with `#` are comments; empty lines are ignored; remaining lines are joined with `, `
  - Wildcards (`__filename__`, `{A|B}`, `{__key__|__key__}`) in `additional_text` are expanded on wildcard-capable nodes, following `enable_wildcard` and `selection_mode`. Random picks use a seed derived from `seed`, independent of the preset's own wildcards
  - `strength`: wraps the whole output as `(text:strength)`; 1.0 = no change
  - Processing order: preset selection → wildcard expansion → additional text → strength
  - `selected_info` notes when additional text or strength was applied; `keyword` is not affected

### Fixed

**Wildcards**

- `__portrait/lighting__` (file in a subfolder) now expands, as the v1.3.0 README described. `\` also works as a separator
- Non-ASCII names such as `__髪型__` now expand
- The Impact Pack wildcards folder is found even when Impact Pack is installed as `comfyui-impact-pack` (lowercase). Previously it was not found on Linux / macOS
- UTF-8 files with a BOM: a `# comment` on the first line is ignored instead of being output (preset files and wildcard files)
- Indented `  # comment` lines in wildcard files are treated as comments, as in preset files
- `__a____b__` is read as two wildcards instead of one
- Names pointing outside `presets` / `wildcards` (`__../xxx__`, drive letters) are refused
- `.txt` presets are no longer parsed as YAML. A line starting with `{` (e.g. `{red|blue} dress`) used to print a YAML parse error on every run, with a traceback on the Image node. `{__key__|__key__}` keys and `[image]` folders come only from `.yaml` / `.yml` files, as in the Multi-File / Folder nodes
- YAML keys with an image folder (`heroes[hero_poses]:`, used by the Image node) can now be referenced as `{__heroes__}`. The `[hero_poses]` part used to make the key unreachable

**Output text**

- A `.txt` preset line that starts with `word: ` (e.g. `style: watercolor, soft edges`) is now output in full. The `style: ` used to be cut off as if it were a YAML key (all nodes)
- Multi-File / Folder nodes: only the file prefix and, for YAML files, the key hierarchy are removed from the output. They used to remove every leading `word: `, which also cut quoted YAML values such as `"mood: calm"` down to `calm`

### Compatibility

- `keyword` is added as the last output, so existing workflow connections keep working. The selected preset, `preset_list` and `selected_info` are unchanged
- The new widgets are optional inputs with neutral defaults (OFF / empty / 1.0), so `text` is unchanged unless you use them
- Ordinary wildcards expand exactly as before; only the cases above, which used to stay unexpanded or output a comment line, change
- On Linux / macOS with a lowercase `comfyui-impact-pack` folder, its wildcard files now appear in the preset dropdown as well
- `.txt` preset lines starting with `word: ` now keep that part in `text`. YAML presets are output as before, except that in the Multi-File / Folder nodes a YAML value that itself starts with `word: ` is no longer cut

---

## リリースノート（日本語）

全ノードで、選ばれたプリセットが実際にマッチしたキーワードを出力できるようになりました。また、出力にテキストを追加したり、強度を指定したりできるようになりました。`__filename__` ワイルドカードが一部の条件で展開されなかった問題のほか、出力テキストとYAMLキーに関する不具合も修正しました。

### 追加

- **`keyword`出力**（全ノード）：選ばれたプリセットがマッチした包含キーワードを`_`で連結して出力
  - AND：全キーワード（`front close-up` → `front_close-up`）
  - OR：マッチしたものだけ（`front back` → `front`または`back`）。行が複数を含む場合は、すべて入力順に連結
  - OFF：空
  - フレーズ内のスペースは`_`になります（`"front view" close-up` → `front_view_close-up`）
  - YAMLキー検索の`:`は`_`に置き換え、末尾の`:`は外します（`camera_angles:close_up:` → `camera_angles_close_up`）。ファイル名にそのまま使えます
  - 除外キーワード（`-wide`）は出力しません。大文字小文字は入力どおりです
- **追加テキストと強度**（全ノード）：各ノードの下部に3つのウィジェットを追加
  - `enable_additional_text`：ON/OFFスイッチ（デフォルトOFF）
  - `additional_text`：ON時、`プリセット, 追加テキスト` の形で追加。行頭が`#`の行はコメント、空行は無視し、残りの行は`, `で連結
  - `additional_text`内のワイルドカード（`__filename__`、`{A|B}`、`{__key__|__key__}`）も展開します（ワイルドカード対応ノードのみ。`enable_wildcard`と`selection_mode`に従う）。ランダム選択には`seed`から派生したシードを使うので、プリセット側のワイルドカードとは独立に選ばれます
  - `strength`：出力全体を`(text:strength)`形式で囲む。1.0で変更なし
  - 処理順：プリセット選択 → ワイルドカード展開 → 追加テキスト → 強度
  - 適用時は`selected_info`に表示します。`keyword`出力には影響しません

### 修正

**ワイルドカード**

- サブフォルダ内のファイルを`__portrait/lighting__`で展開できるようになりました（v1.3.0のREADMEの記載どおり）。区切りは`\`でも可
- `__髪型__`のような日本語などの名前を展開できるようになりました
- Impact Packが`comfyui-impact-pack`（小文字）でインストールされていても、wildcardsフォルダを見つけられるようになりました。これまではLinux / macOSで見つかりませんでした
- BOM付きUTF-8のファイルで、1行目の`# コメント`が出力されてしまう問題を修正しました（プリセットファイル・ワイルドカードファイルとも）
- ワイルドカードファイルの行頭に空白がある`  # コメント`を、プリセットファイルと同じくコメントとして扱うようにしました
- `__a____b__`を、1つではなく2つのワイルドカードとして読むようにしました
- `presets`／`wildcards`の外を指す名前（`__../xxx__`、ドライブ指定）は拒否します
- `.txt`のプリセットをYAMLとして読まないようにしました。これまでは`{red|blue} dress`のように`{`で始まる行があると、実行のたびにYAMLの解析エラーがコンソールに出ていました（Imageノードではトレースバックも表示）。`{__key__|__key__}`のキーと`[image]`フォルダは、Multi-File版・Folder版と同じく`.yaml`／`.yml`ファイルからのみ読み込みます
- 画像フォルダ付きのYAMLキー（Imageノード用の`heroes[hero_poses]:`）を、`{__heroes__}`で参照できるようになりました。これまでは`[hero_poses]`が付いているために参照できませんでした

**出力テキスト**

- `.txt`のプリセットで`style: watercolor, soft edges`のように`単語: `で始まる行を、そのまま出力するようにしました。これまではYAMLキーとみなして`style: `を削っていました（全ノード）
- Multi-File版・Folder版：出力から削るのを、ファイル名のプレフィックスと、YAMLファイルの場合のキー階層だけにしました。これまでは行頭の`単語: `をすべて削っていたため、`"mood: calm"`のようなYAMLの値も`calm`になっていました

### 互換性

- `keyword`は出力の末尾に追加したので、既存のワークフローの接続はそのまま使えます。選ばれるプリセット、`preset_list`、`selected_info`は変わりません
- 追加したウィジェットはoptional入力で、デフォルト（OFF／空／1.0）では`text`は変わりません
- 通常のワイルドカードの展開結果は以前と同じです。変わるのは、上記の展開されなかったケースやコメント行が出力されていたケースだけです
- Linux / macOSで`comfyui-impact-pack`（小文字）の場合、そのwildcardsフォルダのファイルがプリセットのドロップダウンにも表示されるようになります
- `.txt`のプリセットで`単語: `で始まる行は、その部分も`text`に出力されるようになります。YAMLのプリセットの出力は変わりません。ただしMulti-File版・Folder版では、値自体が`単語: `で始まるものは削られなくなります
