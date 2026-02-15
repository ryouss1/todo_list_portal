# 勤怠管理 機能仕様書

> 勤怠管理機能の完全な仕様。出退勤打刻、休憩管理、プリセット、Excel エクスポートを含む。
>
> **ステータス: Feature Frozen** — 追加開発は凍結中。解除されるまで新規機能追加は行わない。

---

## 1. 概要

### 1.1 背景

ユーザーの日々の出退勤を記録し、休憩時間を含む実労働時間を管理する機能。
Web 画面からの手動打刻に加え、IC カードや管理者による一括入力にも対応する。

### 1.2 目的

- 出退勤時刻の記録（1日1回制限）
- 休憩の開始・終了を最大3回まで記録
- プリセットによる定型勤務パターンの一括適用
- 月次 Excel エクスポートによる勤怠月報出力

### 1.3 基本フロー

```
Clock In → (Break Start ↔ Break End) × 最大3回 → Clock Out
                                                     ↓
                                            月次 Excel 出力
```

### 1.4 既知の制限事項（FROZEN）

- 編集モーダルに休憩の編集機能がない（API 経由では可能）
- 出退勤・休憩の最小時間（1分未満）のバリデーションが未実装

---

## 2. データモデル

### 2.1 attendances テーブル

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 勤怠ID |
| user_id | INTEGER | FK → users.id, NOT NULL | ユーザーID |
| clock_in | DATETIME(TZ) | NOT NULL | 出勤時刻（UTC） |
| clock_out | DATETIME(TZ) | NULL 可 | 退勤時刻（UTC） |
| date | DATE | NOT NULL | 勤務日（クイックフィルター用） |
| input_type | VARCHAR(10) | DEFAULT "web" | 入力区分: `web` / `ic_card` / `admin` |
| note | TEXT | NULL 可 | 備考 |
| created_at | DATETIME(TZ) | server_default=now() | 作成日時 |
| updated_at | DATETIME(TZ) | server_default=now(), onupdate=now() | 更新日時 |

### 2.2 attendance_breaks テーブル

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 休憩ID |
| attendance_id | INTEGER | FK → attendances.id (CASCADE), NOT NULL | 勤怠ID |
| break_start | DATETIME(TZ) | NOT NULL | 休憩開始（UTC） |
| break_end | DATETIME(TZ) | NULL 可 | 休憩終了（UTC、NULL = 休憩中） |
| created_at | DATETIME(TZ) | server_default=now() | 作成日時 |

### 2.3 attendance_presets テーブル

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | プリセットID |
| name | VARCHAR(100) | NOT NULL | 名前（例: "9:00-18:00"） |
| clock_in | VARCHAR(5) | NOT NULL | 出勤時刻（HH:MM） |
| clock_out | VARCHAR(5) | NOT NULL | 退勤時刻（HH:MM） |
| break_start | VARCHAR(5) | NULL 可 | 休憩開始（HH:MM） |
| break_end | VARCHAR(5) | NULL 可 | 休憩終了（HH:MM） |

### 2.4 users テーブルとの連携

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| default_preset_id | INTEGER | FK → attendance_presets.id, NULL 可 | ユーザーのデフォルトプリセット |

---

## 3. 状態遷移

### 3.1 出退勤

```
未出勤 ──[Clock In]──▶ 出勤中 ──[Clock Out]──▶ 退勤済
                          │
                          └── 1日1回制限: 退勤後の再出勤は不可
```

### 3.2 休憩

```
出勤中 ──[Break Start]──▶ 休憩中 ──[Break End]──▶ 出勤中
   │                                                 │
   └── 最大3回まで ◄────────────────────────────────┘
```

**制約:**
- 退勤後は休憩開始不可
- 休憩中に新たな休憩開始不可（既存の休憩を終了してから）
- 休憩は1つの勤怠レコードにつき最大3回（`MAX_BREAKS = 3`）

---

## 4. API エンドポイント

認証: 全エンドポイントで必要（プリセット一覧を除く）
権限: ユーザーは自分の勤怠のみ操作可能

### 4.1 出退勤操作

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/attendances/clock-in` | 出勤打刻 | `201` AttendanceResponse |
| POST | `/api/attendances/clock-out` | 退勤打刻 | `200` AttendanceResponse |
| GET | `/api/attendances/status` | 現在の打刻状態 | `200` AttendanceStatus |

### 4.2 休憩操作

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/attendances/{id}/break-start` | 休憩開始 | `200` AttendanceResponse |
| POST | `/api/attendances/{id}/break-end` | 休憩終了 | `200` AttendanceResponse |

### 4.3 CRUD

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| GET | `/api/attendances/` | 勤怠一覧（月フィルター対応） | `200` AttendanceResponse[] |
| POST | `/api/attendances/` | 手動作成 | `201` AttendanceResponse |
| GET | `/api/attendances/{id}` | 勤怠取得 | `200` AttendanceResponse / `404` |
| PUT | `/api/attendances/{id}` | 勤怠更新 | `200` AttendanceResponse / `403` / `404` |
| DELETE | `/api/attendances/{id}` | 勤怠削除 | `204` / `403` / `404` |

**`GET /` クエリパラメータ:**
- `year` (任意): 年フィルター
- `month` (任意): 月フィルター（year と併用）

### 4.4 プリセット

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| GET | `/api/attendances/my-preset` | ユーザーのデフォルトプリセット取得 | `200` UserPresetResponse |
| PUT | `/api/attendances/my-preset` | デフォルトプリセット設定 | `200` UserPresetResponse |
| POST | `/api/attendances/default-set` | プリセットを今日の勤怠に適用 | `200` AttendanceResponse |
| GET | `/api/attendance-presets/` | プリセット一覧 | `200` AttendancePresetResponse[] |

### 4.5 エクスポート

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| GET | `/api/attendances/export` | 月次 Excel エクスポート | XLSX ファイル |

**`GET /export` クエリパラメータ:**
- `year` (必須): 対象年
- `month` (必須): 対象月

---

## 5. スキーマ

### ClockInRequest / ClockOutRequest
```json
{
  "note": "string (任意)"
}
```

### AttendanceCreate
```json
{
  "date": "date (必須, ISO format)",
  "clock_in": "string (必須, HH:MM)",
  "clock_out": "string (任意, HH:MM)",
  "breaks": [{"start": "HH:MM", "end": "HH:MM (任意)"}],
  "note": "string (任意)"
}
```

### AttendanceUpdate
```json
{
  "clock_in": "string (任意, HH:MM)",
  "clock_out": "string (任意, HH:MM)",
  "note": "string (任意)",
  "breaks": [{"start": "HH:MM", "end": "HH:MM (任意)"}]
}
```

### AttendanceResponse
```json
{
  "id": 1,
  "user_id": 1,
  "clock_in": "datetime",
  "clock_out": "datetime|null",
  "breaks": [
    {"id": 1, "break_start": "datetime", "break_end": "datetime|null"}
  ],
  "date": "date",
  "input_type": "web|ic_card|admin",
  "note": "string|null",
  "created_at": "datetime",
  "updated_at": "datetime|null"
}
```

### AttendanceStatus
```json
{
  "is_clocked_in": true,
  "current_attendance": "AttendanceResponse|null"
}
```

---

## 6. フロントエンド

### 6.1 画面構成（`/attendance`）

- テンプレート: `templates/attendance.html`
- JavaScript: `static/js/attendance.js?v=7`

```
勤怠管理ページ
├── 打刻カード
│   ├── アクティビティタイプ選択（勤務/休憩/外出/会議）
│   ├── リモートワークチェックボックス
│   ├── 備考入力欄
│   ├── Clock In / Clock Out ボタン
│   └── 経過時間表示（出勤中のみ）
├── 履歴セクション
│   ├── 月フィルター + 検索ボタン
│   ├── Excel エクスポートボタン
│   ├── プリセット変更ボタン / Default Set ボタン
│   └── 勤怠テーブル（日付, 出勤, 退勤, 休憩, 実労働時間, 入力区分, 備考, 操作）
└── モーダル群
    ├── 編集モーダル（出退勤時刻, 備考, 休憩編集）
    ├── 削除確認モーダル
    ├── Default Set 確認モーダル
    └── プリセット選択モーダル
```

### 6.2 アクティビティタイプとボタンラベル

| タイプ | In ボタン | Out ボタン | 勤怠操作 | プレゼンス更新 |
|--------|----------|-----------|---------|--------------|
| work | Clock In | Clock Out | clock-in / clock-out | available / offline |
| break | 休憩開始 | 休憩終了 | break-start / break-end | break / available |
| out | 外出 | 戻り | なし | out / available |
| meeting | 会議開始 | 会議終了 | なし | meeting / available |

- `out` / `meeting` は勤怠レコードを変更せず、プレゼンスステータスのみ更新
- リモートワーク有効時は `available` の代わりに `remote` を送信

### 6.3 テーブル表示

| 列 | 説明 |
|------|------|
| 日付 | 勤務日 |
| 出勤 | 出勤時刻（ローカル時刻表示） |
| 退勤 | 退勤時刻（ローカル時刻表示） |
| 休憩 | `HH:MM-HH:MM` 形式、複数はカンマ区切り、休憩中は「On Break」バッジ |
| 実労働 | (退勤 - 出勤 - 休憩合計) を `Xh Ym` 形式で表示 |
| 入力区分 | バッジ表示: web(グレー), ic_card(水色), admin(赤) |
| 備考 | テキスト |
| 操作 | Edit / Delete ボタン（admin ロック時は無効化） |

---

## 7. ビジネスルール

### 7.1 出退勤制限

| ルール | 説明 |
|--------|------|
| 1日1回制限 | 同日に退勤後の再出勤は不可（`get_attendance_by_date()` でチェック） |
| 重複チェック | 出勤中に再度の出勤は不可 |
| 退勤前提 | 出勤していない状態での退勤は不可 |

### 7.2 休憩制限

| ルール | 説明 |
|--------|------|
| 最大3回 | `MAX_BREAKS = 3`、4回目以降は拒否（400） |
| 単一アクティブ | 休憩中に新たな休憩開始は不可 |
| 退勤後不可 | 退勤済みのレコードに対する休憩開始は不可 |

### 7.3 管理者ロック（input_type）

| input_type | 説明 | 操作制限 |
|------------|------|---------|
| `web` | Web 画面からの入力（デフォルト） | 制限なし |
| `ic_card` | IC カード打刻 | 制限なし |
| `admin` | 管理者入力 | **更新・削除・休憩操作・Default Set すべて 403** |

`_check_admin_lock(att)` でチェックし、`ForbiddenError` を送出。

### 7.4 所有権

| ルール | 説明 |
|--------|------|
| 自分のみ | 勤怠の取得・更新・削除はレコードの `user_id` が一致するユーザーのみ |
| 不一致時 | `NotFoundError` (404) を返す（存在を隠す） |

### 7.5 時刻の扱い

| ルール | 説明 |
|--------|------|
| 入力 | HH:MM 形式のローカル時刻（サーバーのタイムゾーン） |
| 保存 | UTC に変換して保存 |
| 表示 | フロントエンドで `toLocaleTimeString()` によりローカル時刻表示 |
| 変換関数 | `_parse_time(target_date, time_str)`: ローカル HH:MM → UTC datetime |

### 7.6 プリセット・Default Set

| ルール | 説明 |
|--------|------|
| プリセット選択 | ユーザーは `default_preset_id` でデフォルトプリセットを保存 |
| フォールバック | `default_preset_id` 未設定時はプリセット #1 を使用 |
| 新規作成 | 今日のレコードが無い場合、プリセットから新規作成 |
| 既存更新 | 今日のレコードがある場合、出退勤時刻を上書き＋休憩を置換 |
| 管理者ロック | 今日のレコードが admin ロックの場合は 403 |
| 休憩置換 | 既存の休憩をすべて削除し、プリセットの休憩を1件作成 |

### 7.7 更新時の休憩処理

| ルール | 説明 |
|--------|------|
| 全置換方式 | PUT 時に既存の休憩をすべて削除し、リクエストの休憩を新規作成 |
| 最大3件 | 入力が3件を超える場合は先頭3件のみ作成 |
| end 省略可 | 休憩の end を省略した場合は `break_end = NULL`（休憩中扱い） |

---

## 8. Excel エクスポート

### 8.1 出力仕様

| 項目 | 値 |
|------|------|
| タイトル | `{year}年{month}月 勤怠月報` |
| ファイル名 | `attendance_{year}_{month:02d}.xlsx` |
| ライブラリ | openpyxl |

### 8.2 列定義

| 列 | ヘッダー | 幅 | 内容 |
|------|---------|------|------|
| A | 日付 | 12 | date 値 |
| B | 出勤 | 10 | clock_in をローカル HH:MM:SS |
| C | 退勤 | 10 | clock_out をローカル HH:MM:SS |
| D | 休憩 | 20 | `HH:MM-HH:MM` 形式、複数はカンマ区切り |
| E | 実労働時間 | 14 | `Xh Ym` 形式（退勤 - 出勤 - 休憩合計） |
| F | 入力区分 | 10 | web→"WEB", ic_card→"IC", admin→"管理者" |
| G | 備考 | 20 | note 値 |

最終行に合計実労働時間を表示。

---

## 9. エラーハンドリング

| エラー | ステータス | 条件 |
|--------|----------|------|
| ConflictError | 400 | 出勤済み / 同日再出勤 / 未出勤で退勤 / 休憩アクティブ中 / 休憩上限超過 / 退勤後の休憩 / 同日レコード重複 |
| NotFoundError | 404 | 勤怠レコード未存在 / 所有権不一致 / プリセット未存在 |
| ForbiddenError | 403 | 管理者入力レコードへの変更操作 |

---

## 10. ファイル構成

### 10.1 バックエンド

| ファイル | 内容 |
|---------|------|
| `app/models/attendance.py` | Attendance モデル |
| `app/models/attendance_break.py` | AttendanceBreak モデル |
| `app/models/attendance_preset.py` | AttendancePreset モデル |
| `app/schemas/attendance.py` | 勤怠スキーマ（リクエスト/レスポンス） |
| `app/schemas/attendance_preset.py` | プリセットスキーマ |
| `app/crud/attendance.py` | 勤怠 CRUD 操作 |
| `app/crud/attendance_break.py` | 休憩 CRUD 操作 |
| `app/crud/attendance_preset.py` | プリセット CRUD 操作 |
| `app/services/attendance_service.py` | ビジネスロジック（打刻・休憩・プリセット・Excel） |
| `app/routers/api_attendances.py` | 勤怠 API エンドポイント |
| `app/routers/api_attendance_presets.py` | プリセット API エンドポイント |

### 10.2 フロントエンド

| ファイル | 内容 |
|---------|------|
| `templates/attendance.html` | 勤怠管理画面テンプレート |
| `static/js/attendance.js` | フロントエンド JS（v=7） |

---

## 11. テスト

`tests/test_attendances.py` に 43 テストケース。

### 出退勤テスト（13 件）
- 未出勤時のステータス確認
- 出勤打刻（備考あり/なし）
- 出勤後のステータス確認
- 重複出勤の拒否
- 1日1回制限（退勤後の再出勤拒否）
- 退勤打刻（備考更新）
- 未出勤状態での退勤拒否
- 勤怠一覧取得（breaks フィールド含む）
- 単一レコード取得
- 存在しないレコードの 404

### 手動作成テスト（8 件）
- 全フィールド指定での手動作成（休憩含む）
- 同日レコード重複の拒否
- 休憩なしでの作成
- 退勤なしでの作成
- レコード更新
- 他ユーザーレコードへのアクセス拒否
- レコード削除
- Default Set データ構造の確認

### 休憩テスト（9 件）
- 休憩開始・終了の基本動作
- 3回までの複数休憩
- 4回目の休憩拒否
- 未出勤時の休憩開始拒否
- 休憩中の重複開始拒否
- アクティブ休憩なしでの終了拒否
- 退勤後の休憩開始拒否
- 他ユーザーの休憩操作拒否

### プリセットテスト（9 件）
- プリセット一覧取得
- デフォルトプリセット取得（未設定時は null）
- プリセット設定・変更
- 存在しないプリセットの設定拒否
- Default Set による新規作成
- Default Set による既存レコード更新
- ユーザー選択プリセットの適用確認

### input_type テスト（6 件）
- デフォルト値が "web" であること
- admin ロックレコードの更新拒否（403）
- admin ロックレコードの削除拒否（403）
- admin ロックレコードへの Default Set 拒否（403）
- admin ロックレコードの休憩操作拒否（403）
- web レコードが正常に更新可能であること

### 月フィルター・更新テスト（8 件）
- 月フィルターでの一覧取得
- フィルターなしでの全件取得
- Excel エクスポート（正常/空データ）
- 休憩付きレコードの更新（置換/クリア/最大3件制限/end省略）

---

## 12. 初期データ

`init_db.py` の `seed_default_presets()` で起動時に自動シード。

| ID | 名前 | 出勤 | 退勤 | 休憩開始 | 休憩終了 |
|----|------|------|------|---------|---------|
| 1 | 9:00-18:00 | 09:00 | 18:00 | 12:00 | 13:00 |
| 2 | 8:30-17:30 | 08:30 | 17:30 | - | - |
