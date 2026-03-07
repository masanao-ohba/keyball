# Keyball44 via_custom キーマップ

`via` キーマップをベースに、Auto Mouse Layer上でCtrl+Tabなどの修飾キー操作を可能にするカスタムファームウェア。

## 変更内容

`keymap.c` に `is_mouse_record_user()` 関数を追加。

```c
bool is_mouse_record_user(uint16_t keycode, keyrecord_t* record) {
    switch (keycode) {
        case KC_TAB:
        case KC_LCTL:
        case KC_RCTL:
            return true;
        default:
            return false;
    }
}
```

### 効果

- Auto Mouse Layer (Layer 1) 上で **Tab, 左Ctrl, 右Ctrl** を押してもレイヤーが解除されなくなる
- これにより、トラックボール操作中に右手だけで **Ctrl+Tab** (タブ切替) が可能になる

### 影響範囲

- REMAPで設定したキーマップ (EEPROM) には影響しない
- Layer構造、マトリクス構造は変更なし
- Tab/Ctrlのキーとしての機能は従来通り（修飾キーの組み合わせも正常に動作）
- 変わるのは「Auto Mouse Layerの解除判定」のみ

---

## ビルド

```bash
cd /Users/masanao.oba/workspace/qmk
qmk compile -kb keyball/keyball44 -km via_custom
```

成功すると `keyball_keyball44_via_custom.hex` が生成される。

## 書き込み (Flash)

### 手順

1. キーボードの**左手側**をUSBでMacに接続
2. ブートローダーモードに入る（以下のいずれか）:
   - Pro Microの**リセットボタンを素早く2回押す**
   - REMAPの Layer 3 にある **QK_BOOT** キーを押す
3. 書き込みコマンドを実行:

```bash
cd /Users/masanao.oba/workspace/qmk
qmk flash -kb keyball/keyball44 -km via_custom
```

4. `Detecting USB port, reset your controller now...` と表示されたら、再度リセットボタンを押す（自動検出される場合もある）
5. 書き込み完了後、キーボードが自動的に再接続される

### 右手側について

Keyball44は左右で同じファームウェアが動作するため、**左手側への書き込みのみで完了**。右手側への個別書き込みは不要。

---

## 動作確認

1. トラックボールを動かす → Auto Mouse Layer (Layer 1) が有効になる
2. REMAPでLayer 1に配置したTabキーを押す → **レイヤーが維持されたまま**Tabが入力される
3. 右親指のCtrl (Space/*Ctrl) をHoldしながらTabを押す → **Ctrl+Tab** が送信される
4. Ctrlを押したままTab連打 → タブ一覧UIでタブを巡回できる

---

## トラブルシューティング

### 書き込み後にキーが効かない / 挙動がおかしい

**原因の切り分け:**

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

ファームウェア再ビルド時にVIAのビルド日マジックが変わるとEEPROMがリセットされ、キーマップが初期状態に戻る。

**対策**: VIAでキーマップをJSONエクスポートし、`keymap.c` に変換して埋め込んでおけば、リセット後もデフォルトが自分の設定になる。手順は下記「VIAキーマップを keymap.c に反映する」を参照。

**応急処置**: VIAまたはREMAPで再接続し、手動でキーを再設定する。各レイヤーの設定は `remap.pdf` を参照。VIAでバックアップJSONがあれば Load で即復元可能。

---

## VIAキーマップを keymap.c に反映する

VIA (usevia.app) でキーマップをJSON export し、QMK CLI で `keymap.c` に変換する手順。

### 前提条件

- QMK CLI がセットアップ済み (`qmk setup`)
- usevia.app でキーボードに接続できる状態

### Step 1: usevia.app で接続・エクスポート

Keyball44は VIA V3 の公式データベースに未登録のため、カスタム定義の読み込みが必要。

1. usevia.app の **Settings（歯車アイコン）** → "Show Design tab" を ON
2. **Design タブ** → "Use V2 definitions" が **OFF** であることを確認
3. `via_v3.json` をアップロードエリアにドロップ
4. **Configure タブ** → "Authorize device +" → Keyball44 を選択して接続
5. キーマップが表示されたら、上部メニューの **Save/Load** → JSON でエクスポート

> **注意**: Keyball44 ファームウェアは VIA プロトコル v12 を報告するため、V3形式の定義JSONが必須。V2定義 (`via.json`) は接続後に無視される。

### Step 2: VIA JSON → QMK JSON → keymap.c

```bash
cd /Users/masanao.oba/workspace/qmk

# VIA JSON → QMK Configurator JSON
qmk via2json -kb keyball/keyball44 -l LAYOUT_no_ball -o qmk_keymap.json keymap.json

# QMK JSON → keymap.c
qmk json2c -o keymap_generated.c qmk_keymap.json
```

### Step 3: keymap.c にマージ

`keymap_generated.c` の `keymaps[]` 配列を既存の `keymap.c` にコピーする。

**CUSTOM(N) の置換が必要**: VIA は Keyball 固有キーコードを `CUSTOM(N)` として出力する。ビルド前に以下の対応表で置き換えること:

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

### Step 4: ビルド・書き込み

```bash
qmk compile -kb keyball/keyball44 -km via_custom
qmk flash -kb keyball/keyball44 -km via_custom
```

### 同梱ファイル

| ファイル | 用途 |
|----------|------|
| `via_v3.json` | usevia.app 用 V3 定義 (customKeycodes付き) |
| `keymap.json` | VIA エクスポートのバックアップ |

---

## 切り戻し（元のviaファームウェアに戻す）

元の `via` キーマップで再ビルド・書き込みするだけで戻せる:

```bash
cd /Users/masanao.oba/workspace/qmk
qmk flash -kb keyball/keyball44 -km via
```

書き込み手順は上記と同じ（リセットボタン2回 → 自動書き込み）。

REMAPのキーマップ (EEPROM) は切り戻し後も保持される。

---

## 今後の拡張

`is_mouse_record_user()` に他のキーコードを追加することで、Auto Mouse Layer上で
解除されないキーを増やせる:

```c
bool is_mouse_record_user(uint16_t keycode, keyrecord_t* record) {
    switch (keycode) {
        case KC_TAB:
        case KC_LCTL:
        case KC_RCTL:
        // 例: Shiftも追加する場合
        // case KC_LSFT:
        // case KC_RSFT:
            return true;
        default:
            return false;
    }
}
```

変更後は再ビルド＆書き込みが必要。
