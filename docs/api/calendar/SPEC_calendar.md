# SPEC: Calendar（カレンダー機能）

> **ステータス**: 提案段階（Phase 10 候補）
> **依存**: Phase 9（Task List）完了済み、WebSocket 基盤あり

---

## 1. 概要・設計思想

### 1.1 目的

チームメンバーの予定を可視化し、スケジュール共有・調整を容易にする。
既存の Task / DailyReport / Attendance と連携し、「いつ・誰が・何をしているか」を
一画面で把握できるカレンダーを提供する。

### 1.2 設計原則

| 原則 | 方針 |
|------|------|
| **閲覧性** | 多人数の予定が重なっても読める — ユーザー別カラーコード＋フィルタ＋複数ビュー |
| **登録しやすさ** | カレンダー上のクリック/ドラッグで即時作成、繰り返し予定にも対応 |
| **共有しやすさ** | デフォルト「チーム公開」、ワンクリックで共有範囲を変更 |
| **通知** | WebSocket リマインダー＋ブラウザ Notification API で予定前に告知 |
| **既存連携** | TaskListItem / DailyReport / Attendance を自動的にカレンダー上に表示 |

---

## 2. UI ライブラリ選定

### FullCalendar v6（MIT License）

| 項目 | 内容 |
|------|------|
| CDN | `https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js` |
| サイズ | ~50KB gzip |
| ビュー | Month / Week / Day / List（Agenda） |
| 機能 | ドラッグ&ドロップ作成・移動・リサイズ、イベント重複表示、カラーコード |
| Bootstrap連携 | テーマ CSS 上書きで統一可能 |
| ロケール | `ja` ロケール標準搭載 |

**選定理由**: 業界標準のカレンダー UI。Month/Week/Day/List の 4 ビューで閲覧性を確保。
ドラッグ操作で直感的な登録が可能。Bootstrap との親和性が高い。

---

## 3. データモデル

### 3.1 CalendarEvent（カレンダーイベント）

```
Table: calendar_events

id              : Integer, PK, autoincrement
title           : String(500), NOT NULL
description     : Text, nullable
event_type      : String(20), NOT NULL, default="event"
                  -- "event" | "meeting" | "deadline" | "reminder" | "out_of_office"
start_at        : DateTime(timezone=True), NOT NULL
end_at          : DateTime(timezone=True), nullable
                  -- NULL = ポイントイベント（終日の場合は all_day=true）
all_day         : Boolean, default=false
location        : String(200), nullable
color           : String(7), nullable
                  -- ユーザー指定色 (#RRGGBB)、NULL=ユーザーデフォルト色
visibility      : String(10), NOT NULL, default="public"
                  -- "public" | "private"
                  -- public: 全認証ユーザーから閲覧可能
                  -- private: 作成者のみ（他ユーザーには「予定あり」とだけ表示）
recurrence_rule : String(500), nullable
                  -- RFC 5545 RRULE 形式（例: "FREQ=WEEKLY;BYDAY=MO,WE,FR"）
                  -- NULL = 単発イベント
recurrence_end  : Date, nullable
                  -- 繰り返し終了日（NULL = 無制限）
source_type     : String(20), nullable
                  -- "task_list" | "attendance" | "report" | NULL（手動作成）
source_id       : Integer, nullable
                  -- 連携元レコードの ID
creator_id      : Integer, FK(users.id), NOT NULL
created_at      : DateTime(timezone=True), server_default=now()
updated_at      : DateTime(timezone=True), onupdate=now()
```

### 3.2 CalendarEventAttendee（イベント参加者）

```
Table: calendar_event_attendees

id              : Integer, PK, autoincrement
event_id        : Integer, FK(calendar_events.id, CASCADE), NOT NULL
user_id         : Integer, FK(users.id), NOT NULL
response_status : String(10), NOT NULL, default="pending"
                  -- "accepted" | "declined" | "tentative" | "pending"
created_at      : DateTime(timezone=True), server_default=now()

UNIQUE(event_id, user_id)
```

### 3.3 CalendarReminder（リマインダー）

```
Table: calendar_reminders

id              : Integer, PK, autoincrement
event_id        : Integer, FK(calendar_events.id, CASCADE), NOT NULL
user_id         : Integer, FK(users.id), NOT NULL
minutes_before  : Integer, NOT NULL, default=10
                  -- イベント開始の N 分前に通知
remind_at       : DateTime(timezone=True), NOT NULL
                  -- 実際の通知予定時刻（start_at - minutes_before）
is_sent         : Boolean, default=false
created_at      : DateTime(timezone=True), server_default=now()

INDEX(remind_at, is_sent)  -- リマインダーチェッカーの検索用
```

### 3.4 UserCalendarSetting（ユーザーカレンダー設定）

```
Table: user_calendar_settings

id              : Integer, PK, autoincrement
user_id         : Integer, FK(users.id), UNIQUE, NOT NULL
default_color   : String(7), NOT NULL, default="#3788d8"
                  -- FullCalendar デフォルト青
default_view    : String(20), NOT NULL, default="dayGridMonth"
                  -- "dayGridMonth" | "timeGridWeek" | "timeGridDay" | "listWeek"
default_reminder_minutes : Integer, NOT NULL, default=10
show_task_list  : Boolean, default=true
show_attendance : Boolean, default=true
show_reports    : Boolean, default=false
working_hours_start : String(5), default="09:00"
working_hours_end   : String(5), default="18:00"
```

### 3.5 CalendarRoom（施設・会議室）

```
Table: calendar_rooms

id              : Integer, PK, autoincrement
name            : String(100), NOT NULL, UNIQUE
                  -- 施設名（例: "大会議室", "中会議室", "小会議室"）
description     : String(500), nullable
                  -- 備考（例: "3F 最大20名", "備品: プロジェクター"）
capacity        : Integer, nullable
                  -- 定員（NULL = 不明/設定なし）
color           : String(7), nullable
                  -- カレンダー上の表示色（NULL = デフォルト色）
sort_order      : Integer, NOT NULL, default=0
                  -- 表示順
is_active       : Boolean, NOT NULL, default=true
                  -- false = 選択肢に表示しない（論理削除）
created_at      : DateTime(timezone=True), server_default=now()
```

**初期シードデータ**:

| id | name | capacity | sort_order |
|----|------|----------|------------|
| 1 | 大会議室 | 20 | 1 |
| 2 | 中会議室 | 10 | 2 |
| 3 | 小会議室 | 4 | 3 |

`CalendarEvent` にカラム追加:

```
room_id : Integer, FK(calendar_rooms.id, SET NULL), nullable
          -- NULL = 施設予約なし（自由入力の location を使用）
```

**location と room_id の関係**:
- `room_id` が指定されている場合、`location` は自動的に施設名で上書きされる
- `room_id` が NULL の場合、`location` は自由テキスト入力（従来通り）
- 両方 NULL = 場所指定なし

### 3.6 施設の重複予約防止

同一施設・同一時間帯に複数イベントを登録できない。

**重複判定ロジック**:
```
既存イベント A と新規イベント B が重複 =
  A.room_id = B.room_id
  AND A.room_id IS NOT NULL
  AND A.start_at < B.end_at
  AND A.end_at > B.start_at
  AND A.id != B.id  (更新時の自己除外)
```

- 終日イベント（`all_day=true`）: その日の 00:00〜翌日 00:00 として判定
- `end_at` が NULL のイベント: 重複チェック対象外（ポイントイベント）
- 繰り返しイベント: 親イベントの時間帯で判定（展開後の個別オカレンスではなく）

重複時のレスポンス: `409 Conflict`

```json
{
  "detail": "この時間帯は「大会議室」が既に予約されています",
  "conflict_event_id": 42,
  "conflict_title": "週次定例",
  "conflict_start": "2026-03-01T10:00:00+09:00",
  "conflict_end": "2026-03-01T11:00:00+09:00"
}
```

### 3.7 ER 関係

```
User 1──* CalendarEvent        (creator_id)
User 1──* CalendarEventAttendee (user_id)
User 1──1 UserCalendarSetting  (user_id)
CalendarEvent 1──* CalendarEventAttendee (event_id)
CalendarEvent 1──* CalendarReminder      (event_id)
CalendarRoom  1──* CalendarEvent         (room_id)
```

---

## 4. API 設計

### 4.1 イベント CRUD

| Method | Path | 説明 | 認可 |
|--------|------|------|------|
| `GET` | `/api/calendar/events` | イベント一覧（期間・ユーザー指定） | 全認証ユーザー |
| `POST` | `/api/calendar/events` | イベント作成 | 全認証ユーザー |
| `GET` | `/api/calendar/events/{id}` | イベント詳細 | 全認証ユーザー（private は作成者のみ詳細表示） |
| `PUT` | `/api/calendar/events/{id}` | イベント更新 | 作成者のみ |
| `DELETE` | `/api/calendar/events/{id}` | イベント削除 | 作成者のみ |

#### `GET /api/calendar/events` クエリパラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `start` | date | Yes | 取得開始日（inclusive） |
| `end` | date | Yes | 取得終了日（exclusive） |
| `user_ids` | string | No | カンマ区切りユーザーID（省略=全ユーザー） |
| `include_source` | bool | No | `true` = TaskList/Attendance/Report 連携イベントも含む（default: true） |

**レスポンス**: FullCalendar の Event Object 互換 JSON 配列

```json
[
  {
    "id": 1,
    "title": "チームミーティング",
    "start": "2026-02-11T10:00:00+09:00",
    "end": "2026-02-11T11:00:00+09:00",
    "allDay": false,
    "color": "#3788d8",
    "extendedProps": {
      "event_type": "meeting",
      "description": "週次定例",
      "location": "会議室A",
      "visibility": "public",
      "creator_id": 1,
      "creator_name": "Admin",
      "attendees": [
        {"user_id": 1, "display_name": "Admin", "response_status": "accepted"},
        {"user_id": 2, "display_name": "User2", "response_status": "pending"}
      ],
      "source_type": null,
      "source_id": null,
      "recurrence_rule": "FREQ=WEEKLY;BYDAY=WE"
    }
  }
]
```

**private イベントの他ユーザー向けレスポンス**:

```json
{
  "id": 5,
  "title": "予定あり",
  "start": "2026-02-11T14:00:00+09:00",
  "end": "2026-02-11T15:00:00+09:00",
  "color": "#999999",
  "extendedProps": {
    "event_type": "event",
    "visibility": "private",
    "creator_id": 2,
    "creator_name": "User2"
  }
}
```

### 4.2 参加者・回答

| Method | Path | 説明 |
|--------|------|------|
| `POST` | `/api/calendar/events/{id}/attendees` | 参加者追加（作成者のみ） |
| `DELETE` | `/api/calendar/events/{id}/attendees/{user_id}` | 参加者削除（作成者のみ） |
| `PATCH` | `/api/calendar/events/{id}/respond` | 参加回答（本人のみ） |

#### `PATCH /api/calendar/events/{id}/respond`

```json
{ "response_status": "accepted" }
```

### 4.3 リマインダー

| Method | Path | 説明 |
|--------|------|------|
| `PUT` | `/api/calendar/events/{id}/reminder` | リマインダー設定（本人のみ） |
| `DELETE` | `/api/calendar/events/{id}/reminder` | リマインダー解除 |

### 4.4 ユーザー設定

| Method | Path | 説明 |
|--------|------|------|
| `GET` | `/api/calendar/settings` | 自分の設定取得 |
| `PUT` | `/api/calendar/settings` | 自分の設定更新 |

### 4.5 施設（会議室）管理

| Method | Path | 説明 | 認可 |
|--------|------|------|------|
| `GET` | `/api/calendar/rooms` | 施設一覧（`is_active=true` のみ、`sort_order` 順） | 全認証ユーザー |
| `GET` | `/api/calendar/rooms/all` | 全施設一覧（非アクティブ含む） | Admin のみ |
| `POST` | `/api/calendar/rooms` | 施設作成 | Admin のみ |
| `PUT` | `/api/calendar/rooms/{id}` | 施設更新 | Admin のみ |
| `DELETE` | `/api/calendar/rooms/{id}` | 施設削除（論理削除: `is_active=false`） | Admin のみ |

#### `GET /api/calendar/rooms/{id}/availability` — 空き状況確認

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `date` | date | Yes | 確認日 |

レスポンス: その日の予約済み時間帯リスト

```json
{
  "room_id": 1,
  "room_name": "大会議室",
  "date": "2026-03-01",
  "reservations": [
    {
      "event_id": 10,
      "title": "週次定例",
      "start": "10:00",
      "end": "11:00",
      "creator_name": "Admin"
    },
    {
      "event_id": 15,
      "title": "顧客打合せ",
      "start": "14:00",
      "end": "16:00",
      "creator_name": "UserA"
    }
  ]
}
```

#### イベント作成・更新時の `room_id` パラメータ

`POST /api/calendar/events` および `PUT /api/calendar/events/{id}` のリクエストボディに追加:

```json
{
  "title": "チームミーティング",
  "start_at": "2026-03-01T10:00:00+09:00",
  "end_at": "2026-03-01T11:00:00+09:00",
  "room_id": 1
}
```

- `room_id` 指定時、重複チェックを実行 → 重複あれば `409 Conflict`
- `room_id` 指定時、`location` は自動的に施設名で上書き

### 4.6 繰り返しイベント

| Method | Path | 説明 |
|--------|------|------|
| `PUT` | `/api/calendar/events/{id}?scope=this` | この回のみ変更 |
| `PUT` | `/api/calendar/events/{id}?scope=future` | この回以降を変更 |
| `PUT` | `/api/calendar/events/{id}?scope=all` | 全回変更 |
| `DELETE` | `/api/calendar/events/{id}?scope=this` | この回のみ削除 |
| `DELETE` | `/api/calendar/events/{id}?scope=future` | この回以降を削除 |
| `DELETE` | `/api/calendar/events/{id}?scope=all` | 全回削除 |

**繰り返し展開**: サーバー側で RRULE を解析し、リクエストされた期間内のオカレンスを生成。
`scope=this` の変更は `CalendarEventException` レコードで管理（後述）。

---

## 5. 既存機能との連携

### 5.1 自動連携イベント（ソースイベント）

既存データを読み取り専用でカレンダー上に表示する。

| 連携元 | 表示条件 | 表示内容 | スタイル |
|--------|---------|---------|---------|
| **TaskListItem** | `scheduled_date` が非 NULL | `[Task] {title}` | 終日、担当者の色、斜体 |
| **Attendance** | `clock_in` 〜 `clock_out` | `[出勤] {user_name}` | 時間帯、グレー |
| **DailyReport** | `report_date` | `[日報] {task_name}` | 終日、薄緑、折りたたみ |

- ソースイベントは CalendarEvent テーブルには保存しない（API クエリ時に動的生成）
- `include_source=false` で非表示にできる
- ユーザー設定 `show_task_list` / `show_attendance` / `show_reports` でカテゴリ別 ON/OFF

### 5.2 カレンダーからの Task 作成

カレンダーイベント作成時に `event_type=deadline` を選択すると、
自動的に TaskListItem も作成される（双方向リンク: `source_type="task_list"`, `source_id`）。

---

## 6. 通知・リマインダー

### 6.1 アーキテクチャ

```
[バックグラウンドタスク: reminder_checker]
    │ 60秒ごとに remind_at <= now() AND is_sent=false を検索
    │
    ▼
[WebSocket /ws/calendar]
    │ 対象ユーザーに JSON push
    │
    ▼
[ブラウザ JS]
    │ Notification API でデスクトップ通知
    │ + Toast 表示
    │ + 通知音（オプション）
    ▼
[ユーザー]
```

### 6.2 WebSocket メッセージ形式

```json
{
  "type": "calendar_reminder",
  "event_id": 42,
  "title": "チームミーティング",
  "start": "2026-02-11T10:00:00+09:00",
  "minutes_before": 10,
  "location": "会議室A"
}
```

### 6.3 リマインダーチェッカー

既存の `log_collector.py` と同じパターン:

- `start_reminder_checker(app)` / `stop_reminder_checker(app)` を lifespan に追加
- `app.state.reminder_task` に asyncio.Task を保持
- 有効化: `CALENDAR_REMINDER_ENABLED` 環境変数（default: true）
- チェック間隔: `CALENDAR_REMINDER_INTERVAL` 環境変数（default: 60 秒）

### 6.4 ブラウザ通知

```javascript
// calendar.js
function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function showDesktopNotification(data) {
    if (Notification.permission === 'granted') {
        new Notification(data.title, {
            body: `${data.minutes_before}分後に開始`,
            icon: '/static/img/calendar-icon.png',
            tag: `event-${data.event_id}`
        });
    }
    showToast(`${data.title} — ${data.minutes_before}分後`, 'info');
}
```

---

## 7. フロントエンド設計

### 7.1 画面レイアウト

```
┌──────────────────────────────────────────────────────┐
│ [◀ 前] [今日] [次 ▶]   2026年2月    [月][週][日][一覧] │
├──────────┬───────────────────────────────────────────┤
│ サイドバー │                                           │
│          │                                           │
│ [+ 予定]  │                                           │
│          │                                           │
│ グループ  │        FullCalendar メイン領域              │
│ [全員 ▼]  │        （Month / Week / Day / List）       │
│          │                                           │
│ ユーザー  │                                           │
│ ■ 自分   │                                           │
│ ■ UserA  │                                           │
│ ■ UserB  │                                           │
│          │                                           │
│ ──────── │                                           │
│ 表示設定  │                                           │
│ ☑ Tasks  │                                           │
│ ☑ 出勤   │                                           │
│ □ 日報   │                                           │
└──────────┴───────────────────────────────────────────┘
```

### 7.2 カラーコードルール

| ユーザー | デフォルト色 | 変更 |
|---------|------------|------|
| 自分 | `#3788d8`（青） | ユーザー設定で変更可 |
| 他ユーザー | 自動割当（12色パレット） | 各ユーザーの設定色を使用 |
| TaskListItem | `#6c757d`（グレー） | 固定 |
| Attendance | `#adb5bd`（薄グレー） | 固定 |
| DailyReport | `#198754`（緑） | 固定 |
| Private (他人) | `#dee2e6`（非常に薄いグレー） | 固定 |

### 7.3 イベント作成フロー

**方法 1: カレンダー上でドラッグ**

1. Month ビュー: 日付範囲をドラッグ → 終日イベント作成モーダル
2. Week/Day ビュー: 時間帯をドラッグ → 時間指定イベント作成モーダル

**方法 2: 「+ 予定」ボタン**

サイドバーのボタンからモーダルを開く。

**方法 3: クイック作成**

日付セルをクリック → インライン入力欄が表示 → タイトル入力＋Enter で即座に作成。
詳細は後から編集。

### 7.4 イベント作成・編集モーダル（タブ切替レイアウト）

13 個のフィールド群を 3 タブに分割し、各タブがスクロール不要な高さに収まるよう設計。
Bootstrap 5 の `nav-pills nav-fill` を使用したピル型タブで、アクティブタブは青 (`#0d6efd`)、非アクティブはグレー背景。

#### レイアウト概要

```
┌─────────────────────────────────────┐
│ New Event (dark header)         [×] │
├─────────────────────────────────────┤
│ [ ✏ Basic ] [ 📍 Location ] [ 👥 Attendees ] │  ← nav-pills
│ ┌─────────────────────────────────┐ │
│ │  (アクティブなタブの内容)       │ │  ← 薄グレー背景 (#f8f9fa)
│ │  各フィールドは青い左ボーダー   │ │
│ │  ラベルは青色太字 + アイコン    │ │
│ └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│ [🗑 Delete]          [Cancel] [Save] │  ← footer (タブ外)
└─────────────────────────────────────┘
```

#### Tab 1: Basic（デフォルト表示）

```
│ TITLE *          [________________________]  │
│ TYPE             [event ▼]     ☐ All Day     │  ← 横並び (col-8 / col-4)
│ START  [date][time]   END  [date][time]      │  ← 1行に Start/End 横並び
│ DESCRIPTION      [________________________]  │  ← textarea rows=2
```

- Start / End は 1 行で横並び表示（`row > col + col`）
- date 入力: `max-width: 130px`, time 入力: `max-width: 90px`
- All Day チェック時は time 入力を `d-none` で非表示

#### Tab 2: Location（場所・繰り返し）

```
│ LOCATION   ◉ Room  ○ Free text               │
│            [大会議室 ▼] / [自由入力テキスト]   │
│ RECURRENCE [None ▼]                           │
│ RECURRENCE END  [date]  ← Recurrence選択時のみ │
```

#### Tab 3: Attendees（参加者・表示設定）

```
│ ATTENDEES  [multi-select size=4]              │
│ VISIBILITY [Public ▼]   REMINDER [10min ▼]    │  ← 横並び
│ COLOR      [■] ☑ Use default                  │  ← カラーピッカー + チェック横並び
```

#### デザイン仕様

| 要素 | スタイル |
|------|---------|
| modal-header | `background: #212529`, 白文字 |
| タブ（非アクティブ） | `background: #edf0f3`, `color: #495057`, `border-radius: 6px` |
| タブ（アクティブ） | `background: #0d6efd`, `color: #fff` |
| タブ（ホバー） | `background: #dde2e7` |
| タブアイコン | Basic=`bi-pencil-square`, Location=`bi-geo-alt`, Attendees=`bi-people` |
| タブコンテンツ領域 | `background: #f8f9fa`, `border-radius: 6px`, `padding: 8px 10px` |
| フィールドグループ | `border-left: 3px solid #0d6efd`, `padding-left: 8px`, `margin-bottom: 6px` |
| ラベル | `font-size: 0.72rem`, `font-weight: 700`, `color: #0d6efd`, `text-transform: uppercase` |
| ラベルアイコン | Title=`bi-type-bold`, Type=`bi-tag`, Start=`bi-play-circle`, End=`bi-stop-circle`, Description=`bi-text-left`, Location=`bi-geo-alt-fill`, Recurrence=`bi-arrow-repeat`, Recurrence End=`bi-calendar-x`, Attendees=`bi-people-fill`, Visibility=`bi-eye`, Reminder=`bi-bell`, Color=`bi-palette` |
| 入力コントロール | `form-control-sm` / `form-select-sm` (`font-size: 0.82rem`, `padding: 3px 8px`) |
| modal-footer | `padding: 6px 16px` |

#### JS 動作

- `openCreateModal()` / `openEditModal()`: モーダル表示前にタブ 1（Basic）をアクティブにリセット
  ```javascript
  const firstTab = document.querySelector('#eventTabs .nav-link');
  if (firstTab) bootstrap.Tab.getOrCreateInstance(firstTab).show();
  ```
- `toggleAllDay()`: time 入力要素に直接 `d-none` を toggle（ラッパー div 不要）
- 全 `getElementById` 呼び出しはタブを跨いで同一 ID で動作（DOM 構造に依存しない）

#### 関連ファイル

| ファイル | 内容 |
|---------|------|
| `templates/calendar.html` | モーダル HTML（タブ構造 + フィールド配置） |
| `static/css/calendar.css` | タブ・フィールドグループ・ラベルのスタイル定義 |
| `static/js/calendar.js` | タブリセット + toggleAllDay 修正 |

### 7.5 Multi-User 閲覧性の工夫

| 機能 | 説明 |
|------|------|
| **ユーザーフィルタ** | サイドバーで表示/非表示を切替。チェックボックスで即時反映 |
| **カラーコード** | ユーザーごとに異なる色。一目で誰の予定か識別可能 |
| **List ビュー** | 予定が多い場合は一覧表示に切替。ユーザー名 + 時間で整列 |
| **Week ビュー** | 時間軸で重複が見える。空き時間の確認に最適 |
| **Private マスク** | 非公開イベントは「予定あり」のみ表示。時間帯は見えるがタイトル・詳細は非表示 |
| **ソースイベント折畳** | TaskList / Attendance は折りたたんで表示。展開で詳細表示 |
| **レスポンシブ** | モバイルでは List ビューをデフォルト表示 |

### 7.6 グループフィルタ

サイドバーの「Users」セクション上部にグループドロップダウンを配置し、グループ単位でユーザーを絞り込む。

| 項目 | 仕様 |
|------|------|
| 配置 | サイドバー「Users」見出しの直下、ユーザーチェックボックスの直上 |
| UI | `<select>` ドロップダウン (`form-select-sm`) |
| 選択肢 | 「All」（デフォルト） + 各グループ名（`GET /api/groups/` から取得） |
| 動作 | グループ選択 → ユーザーチェックボックスをグループメンバーのみに絞り込み表示 → 表示中ユーザーを全チェック → イベント再取得 |
| 「All」選択時 | 全ユーザーのチェックボックスを表示・全チェック（初期状態に戻す） |
| データソース | `GET /api/users/` の `group_id` でユーザーをグループに関連付け |

**動作フロー:**

1. ページロード時に `GET /api/groups/` でグループ一覧取得
2. ドロップダウンに「All」+ 各グループ名を設定
3. グループ選択時:
   - 選択グループに属するユーザーのチェックボックスのみ表示（`d-none` で非表示切替）
   - 表示中のユーザーを全チェック ON
   - `selectedUserIds` を更新
   - `reloadEvents()` を呼び出してイベント再取得
4. 「All」選択時: 全ユーザーを表示・全チェック ON

**API変更**: なし（クライアントサイドのみ。`GET /api/users/` の `group_id` と `GET /api/groups/` を活用）

---

## 8. 繰り返しイベント詳細設計

### 8.1 RRULE 対応範囲

| パターン | RRULE 例 | UI 表示 |
|---------|---------|--------|
| 毎日 | `FREQ=DAILY` | 毎日 |
| 毎週（曜日指定） | `FREQ=WEEKLY;BYDAY=MO,WE,FR` | 毎週 月・水・金 |
| 毎月（日付指定） | `FREQ=MONTHLY;BYMONTHDAY=15` | 毎月 15日 |
| 毎月（曜日指定） | `FREQ=MONTHLY;BYDAY=2TU` | 毎月 第2火曜 |
| 毎年 | `FREQ=YEARLY` | 毎年 |

### 8.2 例外処理（CalendarEventException）

繰り返しの一部を変更・削除する場合:

```
Table: calendar_event_exceptions

id                : Integer, PK
parent_event_id   : Integer, FK(calendar_events.id, CASCADE), NOT NULL
original_date     : Date, NOT NULL
                    -- 変更対象のオカレンス日付
is_deleted        : Boolean, default=false
                    -- true = この回を削除（skip）
override_event_id : Integer, FK(calendar_events.id, SET NULL), nullable
                    -- 差し替えイベント（変更の場合）

UNIQUE(parent_event_id, original_date)
```

### 8.3 サーバー側展開ロジック

```python
def expand_recurring_events(events, start_date, end_date):
    """RRULE を解析して期間内のオカレンスを生成"""
    # python-dateutil の rrulestr() を使用
    # exceptions テーブルで削除・変更を反映
    # 各オカレンスに virtual_id を付与（"{event_id}_{date}"）
```

ライブラリ: `python-dateutil`（既存依存に含まれているか確認、なければ追加）

---

## 9. ファイル構成

```
app/
├── models/
│   ├── calendar_event.py           # CalendarEvent, CalendarEventException
│   ├── calendar_event_attendee.py  # CalendarEventAttendee
│   ├── calendar_reminder.py        # CalendarReminder
│   ├── calendar_room.py            # CalendarRoom（施設・会議室）
│   └── user_calendar_setting.py    # UserCalendarSetting
├── schemas/
│   └── calendar.py                 # 全スキーマ
├── crud/
│   ├── calendar_event.py
│   ├── calendar_attendee.py
│   ├── calendar_reminder.py
│   └── calendar_room.py
├── services/
│   ├── calendar_service.py         # イベント CRUD + 繰り返し展開 + ソース連携
│   └── reminder_checker.py         # バックグラウンドリマインダー
├── routers/
│   └── api_calendar.py             # 全エンドポイント
templates/
│   └── calendar.html               # カレンダーページ
static/
├── js/
│   └── calendar.js                 # FullCalendar 初期化 + UI ロジック
└── css/
    └── calendar.css                # FullCalendar テーマ上書き
```

---

## 10. 設定項目（`app/config.py` 追加分）

| 環境変数 | デフォルト | 用途 |
|---------|-----------|------|
| `CALENDAR_REMINDER_ENABLED` | `true` | リマインダーチェッカー有効化 |
| `CALENDAR_REMINDER_INTERVAL` | `60` | チェック間隔（秒） |
| `CALENDAR_DEFAULT_COLOR` | `#3788d8` | ユーザーデフォルト色 |
| `CALENDAR_MAX_RECURRENCE_EXPAND` | `365` | 繰り返し展開の最大日数 |
| `FULLCALENDAR_JS_URL` | `https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js` | FullCalendar CDN |

---

## 11. マイグレーション

```
alembic revision --autogenerate -m "add_calendar_tables"
```

新規テーブル 6 つ:
1. `calendar_events`
2. `calendar_event_attendees`
3. `calendar_event_exceptions`
4. `calendar_reminders`
5. `user_calendar_settings`
6. `calendar_rooms`（施設マスタ）

追加カラム:
- `calendar_events.room_id` — FK(calendar_rooms.id, SET NULL)

インデックス:
- `calendar_events(creator_id)`
- `calendar_events(start_at, end_at)` — 期間検索用
- `calendar_events(room_id)` — 施設別検索・重複チェック用
- `calendar_event_attendees(user_id, event_id)`
- `calendar_reminders(remind_at, is_sent)` — チェッカー用

シードデータ: `seed_default_rooms()` で大会議室・中会議室・小会議室を初期投入

---

## 12. 実装フェーズ

### Phase 10a: 基本カレンダー（MVP）

- CalendarEvent モデル + CRUD + API
- FullCalendar 導入（Month / Week / Day / List ビュー）
- イベント作成・編集・削除（モーダル）
- ドラッグ&ドロップ作成（Week/Day ビュー）
- ユーザー別カラーコード
- ナビゲーションバーに追加

### Phase 10b: 共有・マルチユーザー

- CalendarEventAttendee モデル + API
- 参加者追加・回答（accepted / declined / tentative）
- サイドバーのユーザーフィルタ
- Private / Public 表示切替
- UserCalendarSetting（デフォルト色・ビュー）

### Phase 10c: 繰り返し・既存連携

- RRULE パーサー + 展開ロジック
- CalendarEventException（個別変更・削除）
- TaskListItem / Attendance / DailyReport のソースイベント表示
- 繰り返し作成 UI

### Phase 10d: 通知・リマインダー

- CalendarReminder モデル + API
- `reminder_checker.py` バックグラウンドタスク
- WebSocket `/ws/calendar` + ブラウザ Notification API
- リマインダー設定 UI

---

## 13. テスト計画

| テストファイル | 対象 | 想定テスト数 |
|--------------|------|------------|
| `tests/test_calendar_events.py` | イベント CRUD + 権限 + private 表示 | ~25 |
| `tests/test_calendar_attendees.py` | 参加者追加・削除・回答 | ~10 |
| `tests/test_calendar_recurrence.py` | 繰り返し展開・例外処理 | ~15 |
| `tests/test_calendar_reminders.py` | リマインダー CRUD + 送信チェック | ~10 |
| `tests/test_calendar_source.py` | 既存連携（TaskList, Attendance, Report） | ~10 |
| `tests/test_calendar_rooms.py` | 施設 CRUD + 重複予約防止 + 空き状況 | ~15 |
| **合計** | | **~85** |
