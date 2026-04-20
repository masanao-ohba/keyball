# Keyball44 via_custom キーマップ

`via` キーマップをベースにしたカスタムファームウェア。

## 変更内容

### キーマップ再設計

レイヤー構成を見直し、数字・記号・矢印へのアクセスを改善した。

| Layer | 用途 | アクセス方法 |
|-------|------|-------------|
| 0 | ベース（QWERTY） | — |
| 1 | Auto Mouse Layer | トラックボール操作で自動切替 |
| 2 | 数字 + 矢印 | TG(2) でトグル / MO(2) で一時切替 |
| 3 | 記号（Shift不要化） | LT(3,ESC) / LT(3,BS) でホールド |

設計原則:
- **反対の手でレイヤー切替**（Miryoku方式）: ホールドする手と打鍵する手を分ける
- **数字はトグル**（TG）: 連続入力に対応
- **記号はホールド**（LT）: 単発入力が主のため
- **Shift不要化**: 記号レイヤーに S(KC_1) 等を直接配置し、Shift+Hold+Key の三重押しを回避

### Auto Mouse Layer の改善

2つの仕組みで、Ctrl+Tab（ブラウザタブ切替）がLayer 1上で途切れなくなる。

1. **`is_mouse_record_user()`**: Tab キーとモディファイアキーを「マウスキー」として扱い、押下時にレイヤーが即座に解除されるのを防ぐ
2. **`matrix_scan_user()`**: Ctrl 保持中に Auto Mouse Layer のタイムアウトを無効化し、Tab 連打間のタイムアウトによるレイヤー解除を防ぐ

### 起動時の初期化

`keyboard_post_init_user()` で以下を設定:
- スクロールスナップモード: FREE
- Auto Mouse Layer: 有効

これにより EEPROM の状態に関わらず、起動時に常にこれらが有効になる。

---

## ビルド

```bash
cd ../qmk
uv run --active qmk compile -kb keyball/keyball44 -km via_custom
```

成功すると `keyball_keyball44_via_custom.hex` が生成される。

### 環境セットアップ（初回のみ）

```bash
cd ../qmk
uv venv .venv --python 3.8
uv pip install -r requirements.txt
```

## 書き込み (Flash)

### 手順

1. キーボードの**左手側**をUSBでMacに接続
2. ブートローダーモードに入る（以下のいずれか）:
   - Pro Microの**リセットボタンを素早く2回押す**
   - REMAPの Layer 3 にある **QK_BOOT** キーを押す
3. 書き込みコマンドを実行:

```bash
cd ../qmk
uv run --active qmk flash -kb keyball/keyball44 -km via_custom
```

4. `Detecting USB port, reset your controller now...` と表示されたら、再度リセットボタンを押す（自動検出される場合もある）
5. 書き込み完了後、キーボードが自動的に再接続される

### 右手側について

Keyball44は左右で同じファームウェアが動作するため、**左手側への書き込みのみで完了**。右手側への個別書き込みは不要。

### keymap.c の変更を反映するには

VIA 対応ファームウェアでは EEPROM に保存されたキーマップが `keymap.c` のデフォルトより優先される。`keymap.c` を変更した場合、通常のフラッシュだけでは反映されない。

Bootmagic Lite（`rules.mk` で有効化済み）を使って EEPROM をクリアする:

1. USBケーブルを抜く
2. **左上キー（マトリクス [0,0]）を押しながら** USBケーブルを接続
3. EEPROM がクリアされる
4. ケーブルを抜いて再接続 → `keymap.c` のデフォルトが反映される

クリアにより以下の設定がデフォルト値に戻る:

- **キーマップ（全レイヤー）** — `keymap.c` のデフォルトに戻る
- **CPI（トラックボール感度）**
- **スクロール除数（scroll divider）**
- **Auto Mouse Layer 有効/無効** — `keyboard_post_init_user` で起動時に再有効化される
- **Auto Mouse Layer タイムアウト**
- **スクロールスナップモード** — `keyboard_post_init_user` で起動時に FREE に再設定される

---

## トラブルシューティング

### 書き込み後にキーが効かない / 挙動がおかしい

1. **REMAPに接続して確認** → キーマップが表示されれば、ファームウェア自体は正常
2. **Layer 1以外のキーで問題が出るか確認** → Layer 0で通常入力できればOK
3. **OLEDにレイヤー番号が表示されるか確認** → 表示されていればファームウェアは動作中

### Auto Mouse Layerが全く動かなくなった

config.h の以下の設定が残っているか確認:

```c
#define POINTING_DEVICE_AUTO_MOUSE_ENABLE
#define AUTO_MOUSE_DEFAULT_LAYER 1
```

### EEPROMが壊れた（キーマップが初期化された）

ファームウェア再ビルド時にVIAのビルド日マジックが変わるとEEPROMがリセットされ、キーマップが初期状態に戻ることがある。

`keymap.c` に自分の設定を反映しておけば、リセットされてもデフォルトが自分の設定になる。手順は下記「VIAキーマップを keymap.c に反映する」を参照。

---

## VIAキーマップを keymap.c に反映する

VIA (usevia.app) でキーマップをJSON export し、**`via2keymap.py` スクリプト**で `keymap.c` に反映する。これが本リポジトリの正式運用。`qmk via2json` / `qmk json2c` の手動経由は使わない。

### 運用ルール

- **`keymap.c` は手で書き換えない**。VIA 側 → `via_backup.json` → `via2keymap.py` → `keymap.c` の一方通行で同期する
- コミット時は `via_backup.json` と `keymap.c` を**常にペアで**含める(片方だけ更新しない)
- `keymaps[][]` 配列**以外**のコード(`matrix_scan_user` / `is_mouse_record_user` / OLED 等)はスクリプトが保持するため手編集可

### 前提条件

- `python3` が使えること(外部依存ライブラリなし、標準ライブラリのみ)
- usevia.app でキーボードに接続できる状態

### Step 1: usevia.app で接続・エクスポート

Keyball44は VIA V3 の公式データベースに未登録のため、カスタム定義の読み込みが必要。

1. usevia.app の **Settings(歯車アイコン)** → "Show Design tab" を ON
2. **Design タブ** → "Use V2 definitions" が **OFF** であることを確認
3. `via_v3.json` をアップロードエリアにドロップ
4. **Configure タブ** → "Authorize device +" → Keyball44 を選択して接続
5. キーマップが表示されたら、上部メニューの **Save/Load** → JSON でエクスポートし、本ディレクトリの `via_backup.json` を上書き保存

> **注意**: Keyball44 ファームウェアは VIA プロトコル v12 を報告するため、V3形式の定義JSONが必須。V2定義 (`via.json`) は接続後に無視される。

### Step 2: via2keymap.py で keymap.c に反映

本ディレクトリで以下を実行するだけ:

```bash
python3 via2keymap.py
```

スクリプトが自動で以下を行う:

- `via_backup.json` を読み込み、マトリクス順 → `LAYOUT_universal` 引数順に並び替え
- `via_v3.json` の `customKeycodes` を参照し `CUSTOM(N)` を実際のキーコード名(`SCRL_MO` 等)に解決
- VIA 特有のエイリアスを QMK 名に正規化(`KC_MS_BTN1` → `KC_BTN1`、`KC_HAEN` → `KC_LNG1`、`MT(MOD_LCTL,…)` → `LCTL_T(…)` 等)
- `keymap.c` の `// clang-format off` ～ `// clang-format on` で囲まれた `keymaps[][]` ブロックをインプレースで置換(外側のコードは保持)

主なオプション:

| オプション | 用途 |
|----------|------|
| `--dry-run` | 書き込まず生成結果を標準出力に表示。差分確認用 |
| `--via-backup PATH` | 入力 JSON を明示指定(デフォルト `./via_backup.json`) |
| `--via-def PATH` | CUSTOM(N) 定義元を明示指定(デフォルト `./via_v3.json`) |
| `--keymap PATH` | パッチ対象を明示指定(デフォルト `./keymap.c`) |

### Step 3: ビルド・書き込み

```bash
cd ../qmk
uv run --active qmk compile -kb keyball/keyball44 -km via_custom
uv run --active qmk flash -kb keyball/keyball44 -km via_custom
```

EEPROM 上の VIA キーマップが優先されるため、`keymap.c` のデフォルトを実機に反映させたい場合は本 README 上部「keymap.c の変更を反映するには」の Bootmagic Lite 手順で EEPROM をクリアする。

### CUSTOM(N) 参照表(手動確認用)

スクリプトが自動解決するため通常は不要だが、`via_backup.json` を目視確認するときのリファレンス:

| VIA 表記 | keymap.c での記述 | 説明 |
|----------|-------------------|------|
| `CUSTOM(0)` | `KBC_RST` | 設定リセット |
| `CUSTOM(1)` | `KBC_SAVE` | 設定EEPROM保存 |
| `CUSTOM(2)` | `CPI_I100` | CPI +100 |
| `CUSTOM(3)` | `CPI_D100` | CPI -100 |
| `CUSTOM(4)` | `CPI_I1K` | CPI +1000 |
| `CUSTOM(5)` | `CPI_D1K` | CPI -1000 |
| `CUSTOM(6)` | `SCRL_TO` | スクロールモード Toggle |
| `CUSTOM(7)` | `SCRL_MO` | スクロールモード Momentary |
| `CUSTOM(8)` | `SCRL_DVI` | スクロール除数 +1 (遅く) |
| `CUSTOM(9)` | `SCRL_DVD` | スクロール除数 -1 (速く) |
| `CUSTOM(10)` | `AML_TO` | Auto Mouse Layer Toggle |
| `CUSTOM(11)` | `AML_I50` | Auto Mouse timeout +50ms |
| `CUSTOM(12)` | `AML_D50` | Auto Mouse timeout -50ms |
| `CUSTOM(13)` | `SSNP_VRT` | スクロールスナップ: 垂直 |
| `CUSTOM(14)` | `SSNP_HOR` | スクロールスナップ: 水平 |
| `CUSTOM(15)` | `SSNP_FRE` | スクロールスナップ: 無効 |

### 同梱ファイル

| ファイル | 用途 |
|----------|------|
| `via2keymap.py` | **VIA backup → keymap.c 変換スクリプト(正式運用の中核)** |
| `via_v3.json` | usevia.app 用 V3 定義 (customKeycodes付き) |
| `via_backup.json` | VIA エクスポートのバックアップ(keymap.c の「上流」) |

---

## 切り戻し（元のviaファームウェアに戻す）

元の `via` キーマップで再ビルド・書き込みするだけで戻せる:

```bash
cd ../qmk
uv run --active qmk flash -kb keyball/keyball44 -km via
```

書き込み手順は上記と同じ（リセットボタン2回 → 自動書き込み）。

REMAPのキーマップ (EEPROM) は切り戻し後も保持される。
