# ComfyUI Prompt Preset Selector

[English](README.md) | [日本語](README_ja.md)

外部ファイルからテキストプリセットを選択できる、柔軟なComfyUIノードです。フィルタリング機能を備え、カメラアングル、服装、ライティング設定、キャラクターデータベースなど、あらゆるテキストベースのプリセット管理に最適です。

![Prompt Preset Selectorワークフロー例](./images/sample_workflow.webp)
![Prompt Preset Selector with Wildcardワークフロー例](./images/sample_workflow_wc.webp)

## 機能

- 📁 **外部ファイル管理**: `.txt`、`.yaml`、`.yml`ファイルでプリセットを保存
- 🌐 **絶対パス対応**: システム上のどこにあるファイルでも使用可能
- 📝 **複数のYAML形式対応**: リスト、ネスト辞書、フラット形式に対応
- 🔍 **高度なキーワードフィルタリング**: キーワードの包含・除外、フレーズ検索に対応
- 🎲 **複数の選択モード**: Manual、Sequential、Sequential (continue)、Random
- 🎰 **Wildcard展開機能**: `{A|B|C}`、`__filename__`、`{__key__|__key__}`構文に対応
- 🔄 **ComfyUI-Impact-Pack連携**: wildcardsフォルダとの互換性
- 📝 **簡単な編集**: 任意のテキストエディタでプリセットを編集可能（Pythonコードの変更不要）
- 🗂️ **複数のプリセットファイル**: カテゴリ別にプリセットを整理
- 💬 **コメント対応**: プリセットファイルにコメントや空行を追加可能
- 🔄 **動的読み込み**: プリセットファイル編集時にComfyUIの再起動不要

## ノード種類

このノードには2つのバージョンがあります：

### Prompt Preset Selector
基本的なプリセット選択機能を提供。Wildcard展開は不要な場合に使用。

### Prompt Preset Selector (Wildcard)
Wildcard展開機能付きバージョン。以下の構文に対応：
- `{A|B|C}` - 選択肢から1つを選択
- `__filename__` - wildcardsフォルダ内のファイルから1行を読み込み
- `{__key__|__key__}` - YAMLファイル内のキーから内容を選択（Impact Pack形式）

## インストール

1. ComfyUIのカスタムノードディレクトリに移動：
```bash
cd ComfyUI/custom_nodes
```

2. このリポジトリをクローン：
```bash
git clone https://github.com/YOUR_USERNAME/ComfyUI-Prompt-Preset-Selector.git
```

3. （オプション）PyYAMLをインストール（YAML対応用、未インストールの場合）：
```bash
pip install pyyaml
```

注意：PyYAMLは既に環境にインストールされている場合がほとんどです。YAMLファイルが読み込めない場合、ノードが警告を表示します。

4. ComfyUIを再起動

## 使い方

### 基本的な使い方

1. ワークフローに **"Prompt Preset Selector"** または **"Prompt Preset Selector (Wildcard)"** ノードを追加
2. **オプションA**: ドロップダウンからプリセットファイルを選択（例：`camera_angles.txt`）
   **オプションB**: `absolute_path`フィールドに絶対パスを入力（例：`/home/user/my_presets/styles.yaml`）
3. 実行モードを選択
4. `text`出力をプロンプトノードに接続

**注意**: `absolute_path`が指定されている場合、`preset_file`ドロップダウンより優先されます。

### ファイルの場所

プリセットファイルは以下の場所から読み込まれます（優先順位順）：

1. **絶対パス指定** - `absolute_path`フィールドに記入された場合
2. **presetsフォルダ** - `ComfyUI/custom_nodes/ComfyUI-Prompt-Preset-Selector/presets/`
3. **wildcardsフォルダ** - `ComfyUI/custom_nodes/ComfyUI-Impact-Pack/wildcards/`（Impact Packインストール時）

ドロップダウンには、presetsフォルダとwildcardsフォルダの両方のファイルが表示されます（重複は除外）。

### 絶対パスの使用

システム上のどこにあるプリセットファイルでも使用できます：

```
/home/user/presets/camera_angles.txt
/mnt/shared/prompts/styles.yaml
C:\Users\YourName\Documents\presets\lighting.yml  (Windows)
```

対応ファイル形式：`.txt`、`.yaml`、`.yml`

### Wildcard機能（Wildcard版ノードのみ）

#### enable_wildcardパラメータ
- `true`（デフォルト）: Wildcard構文を展開
- `false`: Wildcard構文をそのままテキストとして出力

基本的に`true`のままで問題ありません。Wildcard記法がない場合は何も起きず、通常通りテキストが出力されます。

#### サポートされるWildcard構文

##### 1. 選択肢展開: `{A|B|C}`
```
{red|blue|green} dress
→ "red dress"、"blue dress"、または "green dress"
```

ネスト対応：
```
{red|{dark|light} blue} dress
→ "red dress"、"dark blue dress"、または "light blue dress"
```

##### 2. ファイル参照: `__filename__`
`presets/colors.txt` または `wildcards/colors.txt` の内容を参照：
```
__colors__ dress
→ colors.txtの1行をランダムに選択して展開
```

ファイル検索順序：
1. `presets/colors.txt`
2. `wildcards/colors.txt`（presetsになければ）

##### 3. YAMLキー選択: `{__key1__|__key2__}`
YAMLファイル内のキーから内容を選択（Impact Pack形式）：

```yaml
characters:
  heroes:
    - superman, cape, blue suit
    - batman, dark costume, mask
  villains:
    - joker, purple suit, green hair
    - riddler, question mark, green suit
```

使用例：
```
{__heroes__|__villains__}
→ heroesまたはvillainsキーの内容から1つを選択
```

**重要**: この構文は、選択されたプリセットファイル内のキーを参照します。

#### Selection Modeとwildcard展開の関係

| selection_mode | プリセット選択 | wildcard展開 |
|---|---|---|
| Manual | preset_indexで指定 | ランダム（seedベース） |
| Random | ランダム（seedベース） | ランダム（seedベース） |
| Sequential | preset_indexから順番 | シーケンシャル |
| Sequential (continue) | 前回の続きから | シーケンシャル |

**シーケンシャル展開**: wildcardの選択肢を順番に使用（次回実行時は次の選択肢）
**ランダム展開**: seedに基づいて毎回選択

### YAMLファイル形式

このノードは3つのYAML形式に対応しています：

#### 形式A: プリセットリスト
```yaml
presets:
  - front view, low-angle shot, close-up
  - back view, low-angle shot, close-up
  - side view, eye-level shot, medium shot
```

#### 形式B: フラットリスト
```yaml
- front view, low-angle shot, close-up
- back view, low-angle shot, close-up
- side view, eye-level shot, medium shot
```

#### 形式C: ネスト辞書
```yaml
camera_angles:
  close_up:
    - front view, low-angle shot, close-up
    - back view, low-angle shot, close-up
  wide_shot:
    - front view, high-angle shot, wide shot
    - back view, high-angle shot, wide shot

lighting:
  natural:
    - golden hour lighting, warm tones
    - overcast daylight, diffused light
  studio:
    - three-point lighting, neutral balance
```

**重要**: 形式Cでは、キー階層が各プリセットの先頭に追加されます：
- 結果：`camera_angles:close_up: front view, low-angle shot, close-up`
- これにより、キーで検索可能：`camera_angles:`、`close_up:`、`"camera angles":"close up"`
- スペースを含むキーはYAMLでクォートが必要：`"camera angles":`

すべての形式は自動的に単一のプリセットリストに変換されます。

### 実行モード

**Manual**
- `preset_index`を直接使用
- 特定のプリセットのテスト用

**Sequential**
- `preset_index`から開始、実行ごとにインクリメント
- ワークフロー再読み込み時に`preset_index`にリセット

**Sequential (continue)**
- 実行間で最後の位置から継続
- ワークフロー再読み込みまで状態を保持
- バッチ生成に便利

**Random**
- `seed`に基づいてランダムにプリセットを選択
- 同じseed = 同じ結果（再現可能）

### キーワードフィルタリング

キーワード検索でプリセットをフィルタ：

#### 基本モード
- **OFF**: フィルタなし（全プリセットを使用）
- **AND**: すべてのキーワードに一致
- **OR**: いずれかのキーワードに一致

#### 構文

**シンプルなキーワード**:
```
front                → "front"を含む行
front close-up       → AND: "front" かつ "close-up"
front, back          → OR: "front" または "back"
```

**フレーズ検索**（ダブルクォート使用）:
```
"low-angle shot"     → 完全フレーズに一致
front "eye-level"    → フレーズと単語の組み合わせ
```

**YAML キー階層検索**:

ネスト辞書を使用する場合、キーがプリセットテキストの先頭に追加されます：
```yaml
camera_angles:
  close_up:
    - front view, low-angle shot, close-up
```
結果：`camera_angles:close_up: front view, low-angle shot, close-up`

キーで検索：
```
camera_angles:              → camera_angles配下のすべてのプリセット
close_up:                   → 任意の階層のclose_upキー
camera_angles:close_up:     → 完全パス（ANDモードでスペース区切り）
"camera angles":            → スペースを含むキー（クォート使用）
"camera angles" "close up"  → 両方のキーが存在（ANDモード）
```

**⚠️ Wildcard選択肢の除外方法**:

ネストYAML構造でwildcard選択肢（`{__key1__|__key2__}`）を含む行がキーワード検索に引っかかる場合：

```yaml
characters:
  all:
    - {__heroes__|__villains__}
  heroes:
    - superman, cape, blue suit
  villains:
    - joker, purple suit
```

キーワード「heroes」で検索すると、`all`行も含まれてしまいます（wildcard内に「heroes」が含まれるため）。

**解決策**: コロン `:` を含めて検索
```
キーワード: heroes:
```

これにより、キー階層として検索され、wildcard選択肢の行は除外されます：
- ❌ `all: {...}` → マッチしない（「heroes:」という形式ではない）
- ✅ `heroes: superman, cape...` → マッチする

**その他の方法**:
```
キーワード: heroes -all
```
除外キーワードを使って`all`を明示的に除外。

**除外**（マイナス接頭辞使用）:
```
front -wide          → "front"を含み、"wide"を除外
front -wide -medium  → 複数の除外
-wide -back          → 除外のみ（すべてから削除）
"front view" -"wide shot" → フレーズによる除外
camera_angles: -wide_shot:  → キーフィルタ + キー除外
```

#### フィルタリング規則
- キーワードは**大文字小文字を区別しない**
- 除外は**OR論理**を使用（いずれかに一致で除外）
- 除外は包含フィルタリングの**後**に適用
- **記述の順序は関係なし**: `front -wide` = `-wide front`
- 区切り文字：カンマ`,`またはスペース
- **YAML辞書キーは検索可能**: キーマッチングには`:`接尾辞を使用（例：`close_up:`）
- **キー内のスペース**: ダブルクォート使用（例：`"camera angles":`）

#### 例

| キーワード | モード | 結果 |
|---------|------|--------|
| `front close-up -wide` | AND | "front" かつ "close-up"を含み、"wide"を含まない |
| `front back -medium` | OR | "front" または "back"を含み、"medium"を含まない |
| `"front view" -"wide shot"` | AND | フレーズ "front view"を含み、フレーズ "wide shot"を含まない |
| `-wide` | OFF | "wide"を含まないすべての行 |
| `camera_angles:` | AND | camera_anglesキー配下のすべてのプリセット（YAML） |
| `"close up":` | AND | "close up"キーを持つすべてのプリセット（YAML、キー内スペース） |
| `lighting: -dramatic:` | AND | lightingキーのプリセット、dramaticキーを除外 |
| `heroes:` | AND | heroesキーのみ（wildcard選択肢`{__heroes__|...}`を除外） |

### カスタムプリセットの作成

#### テキストファイル (.txt)

1. このノードディレクトリの`presets`フォルダに移動
2. 新しい`.txt`ファイルを作成（例：`my_presets.txt`）
3. プリセットを1行ずつ追加：

```txt
# これはコメントです - 無視されます

front view, low-angle shot, close-up
side view, eye-level shot, medium shot
back view, high-angle shot, wide shot

# 別のセクション
overhead view, bird's-eye view, establishing shot
```

#### YAMLファイル (.yaml / .yml)

構造化されたプリセットファイルをYAMLで作成：

```yaml
# ネスト辞書形式
camera_angles:
  close_up:
    - front view, low-angle shot, close-up
    - side view, low-angle shot, close-up
  
  medium_shot:
    - front view, eye-level shot, medium shot
    - side view, eye-level shot, medium shot
```

またはシンプルなリスト形式：

```yaml
presets:
  - front view, low-angle shot, close-up
  - side view, eye-level shot, medium shot
```

4. ComfyUIをリフレッシュまたは再起動
5. 新しいプリセットファイルがドロップダウンに表示されます

## プリセットファイル形式

### テキストファイル (.txt)
- **1行に1プリセット**
- **`#`で始まる行はコメント**（無視されます）
- **空行は無視**
- **UTF-8エンコーディング**対応（日本語などの国際文字）

### YAMLファイル (.yaml, .yml)
- **3つの対応形式**: プリセットリスト、フラットリスト、ネスト辞書
- **すべての形式が単一のプリセットリストに変換**されます
- **コメント対応**（`#`使用）
- **UTF-8エンコーディング**対応

## ノードパラメータ

### Prompt Preset Selector（基本版）

| パラメータ | 型 | 説明 |
|-----------|------|-------------|
| `preset_file` | ドロップダウン | presetsまたはwildcardsディレクトリから使用するファイルを選択 |
| `absolute_path` | 文字列 | オプション：プリセットファイルへの絶対パス（preset_fileより優先） |
| `keyword` | 文字列 | フィルタリング用キーワード（フレーズと除外に対応） |
| `keyword_mode` | ドロップダウン | フィルタモード：OFF、AND、OR |
| `selection_mode` | ドロップダウン | プリセットの選択方法：Manual、Sequential、Sequential (continue)、Random |
| `preset_index` | 整数 | Manual/Sequentialモードの開始インデックス（0始まり） |
| `seed` | 整数 | 再現可能なランダム選択用のランダムシード |

### Prompt Preset Selector (Wildcard)（Wildcard版）

基本版のすべてのパラメータに加えて：

| パラメータ | 型 | 説明 |
|-----------|------|-------------|
| `enable_wildcard` | ブール値 | wildcard展開のON/OFF（デフォルト：true） |

## ノード出力

| 出力 | 型 | 説明 |
|--------|------|-------------|
| `text` | STRING | 選択されたプリセットテキスト（wildcard展開済み） |
| `preset_list` | STRING | すべての利用可能なプリセットの番号付きリスト（参照用） |
| `selected_info` | STRING | 選択の詳細（インデックス、モード、フィルタ統計、wildcard展開情報） |

## 使用例

### Wildcard活用例

#### 動的キャラクター選択
```yaml
characters:
  all_characters:
    - {__heroes__|__villains__|__sidekicks__}
  heroes:
    - superman, red cape, blue suit
    - batman, dark costume, utility belt
  villains:
    - joker, purple suit, green hair
  sidekicks:
    - robin, red vest, yellow cape
```

`all_characters`を選択すると、3つのカテゴリからランダムに選択され、さらにそのカテゴリ内からキャラクターが選択されます。

#### 色とスタイルの組み合わせ
presetsフォルダに`colors.txt`を作成：
```txt
red
blue
green
yellow
```

プリセット：
```
__colors__ {dress|suit|jacket}
→ "red dress"、"blue suit"、"green jacket"など
```

### プロンプトライブラリとして使用

過去に生成した良い画像のプロンプトをキー付きで保存・再利用：

```yaml
portraits:
  "girl_soft_lighting_20250115": masterpiece, best quality, 1girl, soft lighting, gentle smile, pastel colors, bokeh background, natural pose, detailed eyes, flowing hair
  "boy_dramatic_20250116": high contrast, 1boy, dramatic lighting, intense gaze, dark background, cinematic composition, sharp focus
  "fantasy_elf_20250117": fantasy art, elf girl, pointed ears, ethereal beauty, magic glow, forest background, detailed costume

landscapes:
  "sunset_beach_20250114": beautiful sunset, golden hour, ocean waves, dramatic sky, vibrant colors, peaceful atmosphere, photorealistic
  "cyberpunk_city_20250115": cyberpunk cityscape, neon lights, rain reflections, futuristic architecture, night scene, highly detailed

experimental:
  "abstract_colors_20250113": abstract art, vibrant colors, flowing shapes, dreamlike, artistic composition
```

**活用例**:
- `"girl_soft_lighting_20250115":` → 特定のプロンプト全文を呼び出し
- `portraits:` + Sequential → ポートレート系プロンプトを順番に試す
- `portraits:` + Random → 過去のポートレート作品からランダムに選択
- `lighting -dramatic` → "lighting"を含み、"dramatic"を含まないプロンプト

**メリット**:
- ✅ 成功したプロンプトを日付付きで記録
- ✅ 同じ設定で別バリエーションを簡単に生成
- ✅ 何が良かったか後から振り返りやすい
- ✅ チームで良いプロンプトを共有可能

過去の良い結果を体系的に管理し、創作活動を効率化できます！

### カメラアングルバリエーション
フィルタリングを使用してカメラアングルのバリエーションを体系的に生成：
```
Keyword: "close-up" -back
Mode: Sequential
→ バックビューを除くすべてのクローズアップショットを順番に選択
```

### アニメキャラクターデータベース
シリーズ別にキャラクタープロンプトを整理：
```yaml
anime:
  shonen:
    - luffy, straw hat, scar under eye, determined expression
    - naruto, blonde hair, whisker marks, orange jacket
    - goku, spiky black hair, orange gi, martial arts pose
  seinen:
    - spike spiegel, green hair, brown suit, cigarette
    - guts, black armor, huge sword, intense gaze
  slice_of_life:
    - yui hirasawa, brown hair, school uniform, guitar
```

**検索例**:
- `anime:` → すべてのアニメキャラクター
- `shonen:` → 少年漫画キャラクターのみ
- `shonen: -naruto` → NARUTO以外の少年漫画キャラクター
- `blonde -naruto` → NARUTO以外の金髪キャラクター
- `"slice_of_life":` → 日常系キャラクターのみ

特定のカテゴリからランダムに選択したい大規模なキャラクターデータベース管理に最適です！

### YAMLベースのスタイルライブラリ
複雑なスタイル階層を整理：
```yaml
styles:
  anime:
    - vibrant colors, bold outlines, expressive eyes
    - pastel tones, soft shading, cute aesthetic
  
  realistic:
    - photographic quality, detailed textures
    - high dynamic range, natural lighting
  
  artistic:
    - watercolor effect, soft edges, dreamy atmosphere
    - oil painting style, thick brushstrokes, rich colors
```

### 共有プリセットの絶対パス
チーム共有のプリセットファイルを使用：
```
absolute_path: /mnt/shared/company_presets/brand_styles.yaml
keyword: professional
→ 一元化されたプリセットライブラリにアクセス
```

### LoRA組み合わせ
```txt
<lora:style1:0.8>, anime style, vibrant colors
<lora:style2:1.0>, realistic, detailed
<lora:style3:0.9>, watercolor, soft edges
```

**注意**: このノードはLoRA構文を通常のテキストとして出力します。実際にLoRAを読み込んで適用するには、出力を`<lora:name:weight>`構文を解析できるLoRA対応ノードに接続してください。このノード自体はLoRA構文を処理せず、単にテキストを後段のノードに提供するだけです。

## ヒント

### preset_list出力の使用
`preset_list`を表示ノードに接続して、インデックス付きのすべての利用可能なプリセットを確認。用途：
- キーワードに一致するプリセットの確認
- 正しい`preset_index`値の検索
- フィルタ結果の検証

### selected_info出力の使用
実行の詳細を表示：
```
Selected: 5: front view, eye-level shot, close-up
Mode: Sequential (continue)
Filtered: 24/96 presets
[Wildcards expanded: sequential]
```

### バッチ生成
キーワードフィルタリングとSequential (continue)モードを使用：
1. キーワードフィルタを設定（例：`"close-up" -back`）
2. Sequential (continue)モードを選択
3. 複数の生成をキューに追加
→ 各生成で次の一致するプリセットを使用

### 再現可能な結果
ランダム選択の場合：
1. Randomモードを使用
2. 良い結果が得られたらseed値をメモ
3. 同じseedを使用して完全に再現

### Wildcard使用のコツ
- `enable_wildcard=true`を推奨（wildcard記法がなければ通常通り動作）
- Sequential modeでwildcardもシーケンシャルに展開
- `{__key__|__key__}`は同じYAMLファイル内のキーを参照
- `__filename__`はpresetsとwildcardsフォルダの両方を検索

## トラブルシューティング

**Q: プリセットのドロップダウンが空？**
A: このノードは整数の`preset_index`を使用し、テキストドロップダウンではありません。`preset_list`出力で利用可能なプリセットを確認してください。

**Q: キーワードが機能しない？**
A: `keyword_mode`がOFFではなく、ANDまたはORに設定されていることを確認してください。キーワードがプリセットファイルの実際のテキストと一致するか確認してください。

**Q: Sequential (continue)モードが継続しない？**
A: このモードはワークフローの再読み込み時にリセットされます。状態はアクティブなワークフロー実行中のみ保持されます。

**Q: 除外が機能しない？**
A: マイナス接頭辞を使用していることを確認：`-wide`（`- wide`ではない）。マイナスの後にスペースなし。

**Q: YAMLファイルが読み込まれない？**
A: PyYAMLがインストールされていることを確認：`pip install pyyaml`。YAML構文が有効か確認してください。ノードは3つの形式に対応（YAML形式セクション参照）。

**Q: 絶対パスが機能しない？**
A: 
- ファイルが指定されたパスに存在するか確認
- Windowsでもフォワードスラッシュ`/`を使用（またはバックスラッシュをエスケープ`\\`）
- ファイルが対応する拡張子を持つか確認：`.txt`、`.yaml`、`.yml`
- ファイルの読み取り権限があるか確認

**Q: Wildcardが展開されない？**
A: 
- `enable_wildcard`が`true`になっているか確認
- Wildcard版ノード（"Prompt Preset Selector (Wildcard)"）を使用しているか確認
- `__filename__`の場合、ファイルがpresetsまたはwildcardsフォルダに存在するか確認
- `{__key__|__key__}`の場合、キーが選択されたYAMLファイル内に存在するか確認

**Q: Wildcard選択肢がフィルタに含まれてしまう？**
A: キーワードにコロン`:`を付けて検索してください。例：`heroes:`ではなく`heroes`で検索すると、`{__heroes__|...}`もマッチしてしまいます。コロンを付けることでキー階層として検索され、wildcard選択肢を除外できます。

**Q: YAMLネスト辞書の順序が違う？**
A: Python辞書は挿入順序を維持（Python 3.7+）しますが、変換処理は構造を走査します。順序はYAML構造の走査に依存します。

## 免責事項とサポートポリシー

### 免責事項

- このノードは**技術サポートなし**で提供されます
- 機能の保証はありません
- 将来のComfyUIアップデートとの互換性は保証されません
- バグレポートや機能リクエストに対応しない場合があります
- 自己責任で使用してください

### サポート状況

- ❌ issueやメールでの個別サポートなし
- ❌ バグ修正や機能追加の保証なし
- ✅ コードはオープンソース - 自由にフォーク・修正可能
- ✅ コミュニティディスカッション歓迎（返答の約束なし）

### 問題の報告

サポートは保証されませんが、以下が可能です:
1. リポジトリの既存issueを確認
2. このREADMEとトラブルシューティングセクションを確認
3. issueを開く（対応されない場合があります）
4. 自分でフォークして修正

## ライセンス

MIT License - 自由に使用、変更、配布できます。
