# Attendance 画面仕様書

## 概要

勤怠管理画面。リアルタイム打刻（Clock In/Out）と自己申告による手動登録・編集・削除をサポートする。
複数休憩（最大3回）の記録に対応し、実労働時間を自動計算する。
出退勤は1日1回に制限され、退勤後の再出勤は不可。

---

## 画面構成

### 1. Clock In/Out カード（上部）

リアルタイムの打刻操作エリア。Presence ステータスと連携して状態を自動変更する。

| 要素 | 説明 |
|------|------|
| ステータス表示 | 現在の打刻状態（`Clocked In` / `Not Clocked In`） |
| 経過時間 | Clock In 中はリアルタイムで `HH:MM:SS` を表示（1秒更新） |
| アクティビティ選択 | セレクトボックス: 出退勤 / 休憩 / 外出中 / 会議中 |
| リモート勤務チェックボックス | ON にすると Presence ステータスが `remote` に設定される |
| Note 入力欄 | 任意のメモ（Clock In/Out 時に付与可能） |
| アクションボタン（左） | セレクトに応じてラベル変化（Clock In / 休憩開始 / 外出 / 会議開始） |
| アクションボタン（右） | セレクトに応じてラベル変化（Clock Out / 休憩終了 / 戻り / 会議終了） |

#### ボタンラベル変更ルール

| セレクト | 左ボタン | 右ボタン |
|---------|---------|---------|
| 出退勤 | Clock In | Clock Out |
| 休憩 | 休憩開始 | 休憩終了 |
| 外出中 | 外出 | 戻り |
| 会議中 | 会議開始 | 会議終了 |

#### Presence ステータス連携

**アクションボタン（左）押下時:**

| セレクト | リモート | 動作 | Presence |
|---------|---------|------|----------|
| 出退勤 | OFF | POST clock-in | `available` |
| 出退勤 | ON | POST clock-in | `remote` |
| 休憩 | - | POST break-start | `break` |
| 外出中 | - | （なし） | `out` |
| 会議中 | - | （なし） | `meeting` |

**アクションボタン（右）押下時:**

| セレクト | リモート | 動作 | Presence |
|---------|---------|------|----------|
| 出退勤 | - | POST clock-out | `offline` |
| 休憩 | OFF/ON | POST break-end | リモート→`remote` / 通常→`available` |
| 外出中 | OFF/ON | （なし） | リモート→`remote` / 通常→`available` |
| 会議中 | OFF/ON | （なし） | リモート→`remote` / 通常→`available` |

### 2. History セクション（下部）

勤怠履歴の一覧表示と操作ボタン。

#### ボタン

| ボタン | 説明 |
|--------|------|
| Default Set | 確認ダイアログ表示後、当日の勤怠をプリセット値（出退勤+休憩1件）で上書き |
| デフォルト変更 | プリセット選択モーダルを開き、ユーザのデフォルトプリセットを変更する |

#### History テーブル

| カラム | 説明 |
|--------|------|
| Date | 勤務日（YYYY-MM-DD） |
| Clock In | 出勤時刻（ローカルタイム HH:MM 表示） |
| Clock Out | 退勤時刻（未退勤の場合は `Active` バッジ表示） |
| Break | 休憩時間帯（複数休憩は改行で表示、`HH:MM - HH:MM`、未設定の場合は `-`） |
| Duration | 実労働時間（`Xh Ym` 形式、全休憩時間を減算） |
| 入力 | 入力タイプバッジ（WEB / IC / 管理者） |
| Note | メモ |
| Actions | 編集ボタン / 削除ボタン（管理者入力は無効化） |

### 3. モーダル

| モーダル | フィールド | 説明 |
|---------|-----------|------|
| Edit Modal | clock_in, clock_out, note | 既存レコードの時刻・メモ編集（date は変更不可、休憩はAPI経由で管理） |
| Delete Modal | （確認のみ） | 削除確認ダイアログ |
| Default Set Confirm Modal | （確認のみ） | 「勤怠をデフォルト値で上書きします。よろしいですか？」 |
| Preset Select Modal | プリセット一覧（ラジオ） | ユーザのデフォルトプリセットを選択・保存 |

---

## データモデル

### `attendances` テーブル

| カラム | 型 | NULL | 説明 |
|--------|-----|------|------|
| id | Integer | NO | PK, auto increment |
| user_id | Integer (FK → users.id) | NO | 所有ユーザ |
| clock_in | DateTime(tz) | NO | 出勤時刻 |
| clock_out | DateTime(tz) | YES | 退勤時刻 |
| date | Date | NO | 勤務日 |
| input_type | String(10) | NO | 入力タイプ（`web` / `ic_card` / `admin`）、デフォルト `web` |
| note | Text | YES | メモ |
| created_at | DateTime(tz) | NO | 作成日時（server_default） |
| updated_at | DateTime(tz) | YES | 更新日時（onupdate） |

### `attendance_breaks` テーブル

| カラム | 型 | NULL | 説明 |
|--------|-----|------|------|
| id | Integer | NO | PK, auto increment |
| attendance_id | Integer (FK → attendances.id, CASCADE) | NO | 親勤怠レコード |
| break_start | DateTime(tz) | NO | 休憩開始時刻 |
| break_end | DateTime(tz) | YES | 休憩終了時刻（NULL = 休憩中） |
| created_at | DateTime(tz) | NO | 作成日時（server_default） |

### `attendance_presets` テーブル

| カラム | 型 | NULL | 説明 |
|--------|-----|------|------|
| id | Integer | NO | PK, auto increment |
| name | String(100) | NO | 表示名（例: "9:00-18:00"） |
| clock_in | String(5) | NO | 出勤時刻 "HH:MM" |
| clock_out | String(5) | NO | 退勤時刻 "HH:MM" |
| break_start | String(5) | YES | 休憩開始 "HH:MM" |
| break_end | String(5) | YES | 休憩終了 "HH:MM" |

**シードデータ:**

| id | name | clock_in | clock_out | break_start | break_end |
|----|------|----------|-----------|-------------|-----------|
| 1 | 9:00-18:00 | 09:00 | 18:00 | 12:00 | 13:00 |
| 2 | 8:30-17:30 | 08:30 | 17:30 | 12:00 | 13:00 |

### `users` テーブル追加カラム

| カラム | 型 | NULL | 説明 |
|--------|-----|------|------|
| default_preset_id | Integer (FK → attendance_presets.id) | YES | ユーザのデフォルトプリセット（NULL時は id=1） |

---

## API エンドポイント

すべて認証必須（セッション認証）。自分のデータのみ操作可能。

### リアルタイム打刻

| メソッド | パス | 説明 | ステータス |
|---------|------|------|-----------|
| POST | `/api/attendances/clock-in` | 出勤打刻（現在時刻） | 201 |
| POST | `/api/attendances/clock-out` | 退勤打刻（現在時刻） | 200 |
| GET | `/api/attendances/status` | 現在の打刻状態を取得 | 200 |

### 休憩操作

| メソッド | パス | 説明 | ステータス |
|---------|------|------|-----------|
| POST | `/api/attendances/{id}/break-start` | 休憩開始（最大3回まで） | 200 |
| POST | `/api/attendances/{id}/break-end` | 休憩終了（アクティブな休憩を終了） | 200 |

### 手動操作

| メソッド | パス | 説明 | ステータス |
|---------|------|------|-----------|
| GET | `/api/attendances/` | 自分の勤怠一覧（日付降順） | 200 |
| GET | `/api/attendances/{id}` | 勤怠詳細取得 | 200 |
| POST | `/api/attendances/` | 手動登録 | 201 |
| PUT | `/api/attendances/{id}` | 勤怠編集（clock_in, clock_out, note） | 200 |
| DELETE | `/api/attendances/{id}` | 勤怠削除 | 204 |

### プリセット・デフォルトセット

| メソッド | パス | 説明 | ステータス |
|---------|------|------|-----------|
| GET | `/api/attendance-presets/` | プリセット一覧取得 | 200 |
| GET | `/api/attendances/my-preset` | 自分のデフォルトプリセットID取得 | 200 |
| PUT | `/api/attendances/my-preset` | 自分のデフォルトプリセットID変更 | 200 |
| POST | `/api/attendances/default-set` | 当日の勤怠をプリセット値（出退勤+休憩1件）で上書き | 200 |

### リクエスト/レスポンス

**AttendanceCreate（POST /）**
```json
{
  "date": "2025-01-15",
  "clock_in": "09:00",
  "clock_out": "18:00",
  "breaks": [
    {"start": "12:00", "end": "13:00"}
  ],
  "note": "Normal day"
}
```
- `date` と `clock_in` は必須。他は任意。
- 時刻は `"HH:MM"` 形式の文字列。
- `breaks` は最大3件。各要素に `start`（必須）と `end`（任意）を持つ。

**AttendanceUpdate（PUT /{id}）**
```json
{
  "clock_out": "18:00",
  "note": "Updated"
}
```
- すべて任意。指定したフィールドのみ更新。
- 休憩は break-start/break-end API で個別管理。

**AttendanceResponse**
```json
{
  "id": 1,
  "user_id": 1,
  "clock_in": "2025-01-15T09:00:00+00:00",
  "clock_out": "2025-01-15T18:00:00+00:00",
  "breaks": [
    {
      "id": 1,
      "break_start": "2025-01-15T12:00:00+00:00",
      "break_end": "2025-01-15T13:00:00+00:00"
    }
  ],
  "date": "2025-01-15",
  "input_type": "web",
  "note": "Normal day",
  "created_at": "2025-01-15T09:00:00+00:00",
  "updated_at": null
}
```

---

## ビジネスルール

| ルール | 説明 |
|--------|------|
| 所有権制限 | 自分の勤怠のみ閲覧・操作可能。他ユーザのデータは 404 を返す |
| 日付重複禁止 | 同一ユーザ・同一日付で複数の手動登録は不可（400 エラー） |
| 出退勤1日1回制限 | 退勤後の同日再出勤は不可（400: "Already clocked in today"） |
| Clock In 重複禁止 | 未退勤（clock_out が NULL）のレコードがある場合、Clock In は拒否（400） |
| Clock Out 前提 | Clock In 中でなければ Clock Out は拒否（400） |
| 休憩最大3回 | 1つの勤怠レコードにつき休憩は最大3回まで（4回目は 400: "Maximum 3 breaks allowed"） |
| 休憩重複禁止 | アクティブな休憩（break_end IS NULL）がある間は新しい休憩を開始不可（400: "Break already active"） |
| 休憩終了前提 | アクティブな休憩がなければ break-end は拒否（400: "No active break"） |
| 退勤後休憩禁止 | 退勤済み（clock_out IS NOT NULL）のレコードでは break-start 不可（400: "Already clocked out"） |
| 時刻パース | `"HH:MM"` + date → ローカル時刻として解釈し UTC datetime に変換して保存 |
| Duration 計算 | `(clock_out - clock_in) - Σ(break_end - break_start)`、フロントエンドで計算・表示 |
| Default Set 上書き | 当日のレコードが存在すれば clock_in/clock_out をプリセット値で上書きし、既存休憩を削除してプリセット休憩1件を再作成。存在しなければプリセット値で新規作成 |
| 入力タイプ | レコードごとに入力方法を記録: `web`（WEB入力）、`ic_card`（ICカード入力）、`admin`（管理者入力） |
| 管理者入力ロック | `input_type = "admin"` のレコードは編集・削除・休憩開始不可（403 エラー） |
| プリセット未選択時 | `users.default_preset_id` が NULL の場合、id=1 のプリセットを使用 |
| 削除後ステータスリセット | Clock In 中のレコードを削除した場合、ステータスは自動的に `Not Clocked In` に戻る |

---

## ファイル構成

| ファイル | 役割 |
|---------|------|
| `app/models/attendance.py` | SQLAlchemy モデル定義（attendances テーブル） |
| `app/models/attendance_break.py` | SQLAlchemy モデル定義（attendance_breaks テーブル） |
| `app/schemas/attendance.py` | Pydantic スキーマ（Create/Update/Response/Status/BreakInput/BreakResponse） |
| `app/crud/attendance.py` | DB 操作関数（勤怠 CRUD） |
| `app/crud/attendance_break.py` | DB 操作関数（休憩 CRUD） |
| `app/services/attendance_service.py` | ビジネスロジック（バリデーション、所有権チェック、休憩管理） |
| `app/routers/api_attendances.py` | API ルーター（薄い HTTP ラッパー） |
| `templates/attendance.html` | Jinja2 テンプレート（モーダル含む） |
| `static/js/attendance.js` | フロントエンド JavaScript |
| `app/models/attendance_preset.py` | プリセット SQLAlchemy モデル |
| `app/schemas/attendance_preset.py` | プリセット Pydantic スキーマ |
| `app/crud/attendance_preset.py` | プリセット DB 操作関数 |
| `app/routers/api_attendance_presets.py` | プリセット API ルーター |
| `tests/test_attendances.py` | テスト（43件） |

---

## テストケース一覧

### TestAttendanceAPI（リアルタイム打刻: 11件）

| テスト | 説明 |
|--------|------|
| test_status_not_clocked_in | 未打刻時のステータス確認 |
| test_clock_in | 出勤打刻の成功確認 |
| test_clock_in_without_note | メモなしでの打刻 |
| test_status_after_clock_in | 打刻後のステータス変化 |
| test_clock_in_duplicate_rejected | 二重打刻の拒否（400） |
| test_clock_in_after_clock_out_same_day_rejected | 退勤後の同日再出勤拒否（400） |
| test_clock_out | 退勤打刻の成功確認 |
| test_clock_out_without_clock_in | 未打刻時の退勤拒否（400） |
| test_list_attendances | 一覧取得（breaks フィールド確認） |
| test_get_attendance | 個別取得（breaks フィールド確認） |
| test_get_attendance_not_found | 存在しない勤怠の取得（404） |

### TestAttendanceManual（手動操作: 9件）

| テスト | 説明 |
|--------|------|
| test_create_attendance_full | 全フィールド指定（breaks 配列含む）での手動登録 |
| test_create_attendance_duplicate_date | 同一日付の重複登録拒否（400） |
| test_create_attendance_no_break | 休憩なしでの登録（breaks = []） |
| test_create_attendance_no_clock_out | 退勤なしでの登録 |
| test_update_attendance | 勤怠の部分更新 |
| test_update_attendance_other_user | 他ユーザの勤怠編集拒否（404） |
| test_delete_attendance | 自分の勤怠削除（204） |
| test_delete_attendance_other_user | 他ユーザの勤怠削除拒否（404） |
| test_default_set_data | デフォルトセット相当データの登録確認 |

### TestAttendanceBreaks（複数休憩: 9件）

| テスト | 説明 |
|--------|------|
| test_start_break | 休憩開始の成功確認 |
| test_end_break | 休憩終了の成功確認 |
| test_multiple_breaks | 3回休憩の成功確認 |
| test_fourth_break_rejected | 4回目の休憩開始拒否（400） |
| test_break_without_clock_in | 未出勤時の休憩開始拒否（404） |
| test_break_already_active | 休憩中の再開始拒否（400） |
| test_end_break_no_active | アクティブ休憩なしでの終了拒否（400） |
| test_break_after_clock_out | 退勤後の休憩開始拒否（400） |
| test_break_other_user | 他ユーザの勤怠への休憩開始拒否（404） |

### TestAttendancePresets（プリセット: 7件）

| テスト | 説明 |
|--------|------|
| test_list_presets | プリセット一覧（シードデータ確認） |
| test_get_my_preset_default | 未設定時は null |
| test_set_my_preset | デフォルトプリセット設定 |
| test_set_my_preset_not_found | 存在しないプリセット設定拒否（404） |
| test_default_set_creates_today | Default Set で当日レコード作成（breaks 1件含む） |
| test_default_set_overwrites_existing | Default Set で既存レコード上書き（breaks 再作成） |
| test_default_set_uses_user_preset | ユーザ選択プリセットの適用確認 |

### TestAttendanceInputType（入力タイプ・管理者ロック: 7件）

| テスト | 説明 |
|--------|------|
| test_input_type_default_web | デフォルト input_type = "web" |
| test_clock_in_input_type_web | Clock In の input_type = "web" |
| test_admin_lock_update | 管理者入力の編集拒否（403） |
| test_admin_lock_delete | 管理者入力の削除拒否（403） |
| test_admin_lock_default_set | 管理者入力の Default Set 拒否（403） |
| test_web_record_editable | WEB 入力は編集可能 |
| test_admin_lock_break_start | 管理者入力の休憩開始拒否（403） |

---

## 既知の制限事項（凍結時点）

| 項目 | 説明 |
|------|------|
| Edit Modal に休憩編集なし | 履歴の編集ボタンでは clock_in, clock_out, note のみ編集可能。休憩の追加・編集・削除は break-start/break-end API 経由のみ |
| 1分未満の休憩 | 1分以内の休憩は登録しないものとする（未実装：将来バリデーション追加予定） |
| 1分未満の出退勤 | 1分以内の出退勤は登録しないものとする（未実装：将来バリデーション追加予定） |
| Duration 表示 | JS キャッシュバージョン `?v=5`。ブラウザキャッシュクリアが必要な場合あり |

---

## 追加機能計画

> **注意**: Attendance 機能は現在凍結中。以下は将来の拡張計画。

### Phase A: バリデーション強化

| 項目 | 説明 | 優先度 |
|------|------|--------|
| 1分未満チェック | 休憩時間が1分未満の場合は登録拒否。出退勤時間差が1分未満の場合も拒否 | 高 |
| 時刻整合性チェック | clock_in < clock_out, break_start < break_end, 休憩が勤務時間内に収まるか検証 | 高 |
| 時刻フォーマット検証 | `"HH:MM"` 形式以外を弾くバリデータ追加（Pydantic validator） | 高 |
| Edit Modal 休憩編集 | 編集モーダルに休憩の追加・削除・時刻変更機能を追加 | 高 |

### Phase B: 月次集計・レポート

| 項目 | 説明 | 優先度 |
|------|------|--------|
| 月次サマリーAPI | `GET /api/attendances/summary?month=2025-01` で総勤務時間・総休憩時間・出勤日数を返す | 高 |
| 月次サマリー画面 | カレンダー形式 or テーブル形式で月間の勤怠状況を表示 | 高 |
| CSV エクスポート | 月次データの CSV ダウンロード機能 | 中 |

### Phase D: 管理者機能

| 項目 | 説明 | 優先度 |
|------|------|--------|
| 管理者による全ユーザ閲覧 | admin ロールのユーザが全ユーザの勤怠を閲覧可能 | 高 |
| 管理者による編集 | admin が他ユーザの勤怠を編集・承認する機能 | 中 |
| 承認ワークフロー | 自己申告 → 管理者承認のフロー（status: pending/approved/rejected） | 低 |

### Phase E: UI/UX 改善

| 項目 | 説明 | 優先度 |
|------|------|--------|
| カレンダービュー | 月間カレンダーで打刻状況を視覚的に表示 | 中 |
| ページネーション | 履歴テーブルにページネーション追加（大量データ対応） | 中 |
| 日付フィルタ | 期間指定で履歴を絞り込み | 中 |
| ~~Default Set カスタマイズ~~ | ~~ユーザごとにデフォルト値（勤務時間・休憩時間）を設定可能に~~ | ~~実装済み~~ |
| ~~リアルタイム打刻に休憩ボタン~~ | ~~Clock In 中に Break Start / Break End ボタンを追加~~ | ~~実装済み~~ |
| ~~複数休憩対応~~ | ~~attendance_breaks テーブルで最大3回の休憩に対応~~ | ~~実装済み~~ |

### Phase F: 通知・連携

| 項目 | 説明 | 優先度 |
|------|------|--------|
| 打刻リマインダー | 退勤未打刻時に通知（WebSocket or メール） | 低 |
| ~~Presence 連携~~ | ~~打刻状態を Presence ステータスに自動反映（Clock In → available, Clock Out → offline）~~ | ~~実装済み~~ |
| Daily Report 連携 | 勤怠データを日報の勤務時間欄に自動入力 | 低 |

### 実装優先順位

1. **Phase A**（バリデーション強化）— データ品質の確保が最優先
2. **Phase B**（月次集計）— 実用上の必要性が高い
3. **Phase E**（UI/UX 改善）— 使い勝手の向上
4. **Phase D**（管理者機能）— チーム運用に必要
5. **Phase F**（通知・連携）— 他機能との統合
