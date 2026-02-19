# Todo List Portal - 実装進捗管理

> spec_roadmap.md に基づく機能実装の進捗を管理するドキュメント

---

## 進捗サマリー

| # | 機能 | 状態 | テスト数 | 備考 |
|---|------|------|---------|------|
| 1 | ログイン機能 | **完了** | 9 | セッション認証、bcryptハッシュ |
| 2 | 勤怠管理（出勤・退勤拡張） | **完了** | 9 | マルチユーザー対応済み |
| 3 | 在籍記録 | **完了** | 10 | WebSocketリアルタイム更新 |
| 4 | プライベート/公開 Todo | **完了** | 13 | visibility カラム、公開一覧 |
| 5 | 日報登録 | **完了** | 12 | CRUD + 日付重複防止 + 認可 |
| 6 | 業務サマリー画面 | **完了** | 6 | 週次/月次集計 |
| 7 | ログファイル収集 | **完了** | 16 | バックグラウンド収集、正規表現パーサー、ローテーション検出 |
| 8 | システムアラート表示 | **完了** | 25 | ルール評価エンジン、WebSocket通知、ナビバッジ |

**全体進捗: 8/8 機能完了（100%）、テスト: 151件 全パス**

---

## 完了済み機能の詳細

### #1 ログイン機能 [完了]
- セッション認証（SessionMiddleware + 署名Cookie）
- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- パスワードハッシュ: passlib + bcrypt
- 認証ミドルウェア: 未認証→ `/login` リダイレクト
- Alembic: `7e3eabbd85e8` (password_hash追加)

### #2 勤怠管理 [完了]
- 出勤・退勤の打刻、履歴表示
- `get_current_user_id` で自動ユーザー識別
- 二重打刻防止（ConflictError）

### #3 在籍記録 [完了]
- ステータス: available / away / out / break / offline
- `PUT /api/presence/status` + WebSocket `/ws/presence` ブロードキャスト
- `presence_statuses` (現在値) + `presence_logs` (変更履歴) テーブル
- Alembic: `29148e04951a` (presence tables)

### #4 プライベート/公開 Todo [完了]
- `todos.visibility` カラム (private/public, デフォルト private)
- `GET /api/todos/public` — 全ユーザーの公開Todo一覧
- 公開Todoは閲覧のみ、操作は所有者のみ
- Alembic: `86da56d0b359` (visibility追加)

### #5 日報登録 [完了]
- `daily_reports` テーブル (user_id + report_date にUNIQUE制約)
- 項目: work_content(必須), achievements, issues, next_plan, remarks
- 全ユーザー閲覧可 / 編集・削除は所有者のみ
- Alembic: `c3790ffa7e38` (daily_reports)

### #6 業務サマリー画面 [完了]
- `GET /api/summary/?period=weekly|monthly&ref_date=YYYY-MM-DD`
- ユーザー別提出状況、日報トレンド、課題集約、最近の日報

### #7 ログファイル収集 [完了]
- `log_sources` テーブル: 監視対象パス、正規表現パーサー設定、ポーリング間隔、読取位置追跡
- バックグラウンド asyncio タスクによるファイル監視（5秒メインループ、各ソースは個別間隔）
- ファイルローテーション検出（current_size < last_file_size → position=0）
- 正規表現の名前付きグループで message, severity 等を抽出
- REST API: `GET/POST/PUT/DELETE /api/log-sources/`, `GET /api/log-sources/status`
- ログ画面にLog Sources管理パネル追加
- Alembic: `6ee8442a6984` (log_sources)
- テスト: 9件 (CRUD) + 7件 (collector logic) = 16件

### #8 システムアラート表示 [完了]
- `alert_rules` テーブル: 条件(JSON)、タイトル/メッセージテンプレート、重要度
- `alerts` テーブル: タイトル、メッセージ、重要度、ルールFK、確認済みフラグ
- ルール評価エンジン: 完全一致、`$in`(リスト包含)、`$contains`(部分一致)、全条件AND
- ログ→アラート連携: `log_service.create_log()` 内でルール評価→アラート自動生成
- 手動アラート作成: `POST /api/alerts/`
- アラート確認: `PATCH /api/alerts/{id}/acknowledge`
- アラート非活性化: `PATCH /api/alerts/{id}/deactivate`
- WebSocket `/ws/alerts` でリアルタイム通知
- ナビバーにアラートバッジ（未確認件数）+ WebSocket自動更新
- ダッシュボードにアラートカード追加
- Alembic: `82739a6351f7` (alert_rules, alerts)
- テスト: 9件 (alerts API) + 13件 (rules CRUD + 評価エンジン) + 3件 (統合) = 25件

---

## 将来検討（残タスク）

| # | 項目 | 説明 | 優先度 |
|---|------|------|--------|
| 1 | `users.email` | メールアドレス（UNIQUE）カラム追加 | 低 |
| 2 | `users.role` | ユーザー権限（user/admin）RBAC対応 | 中 |
| 3 | 管理者向け全ユーザー勤怠閲覧 | RBAC対応後に実装 | 低 |
| 4 | 日報へのタスク・勤怠データ自動取り込み | 日報作成時に自動連携 | 低 |
| 5 | WebSocket認証対応 | `/ws/*` は現在公開パス、トークン認証等の導入 | 中 |
| 6 | CSRF対策 | フォーム送信時のCSRFトークン検証 | 中 |
| 7 | 外部通知連携 | アラートのメール/Slack通知 | 低 |
| 8 | ログ収集パフォーマンス改善 | 大量ログファイルの分割取り込み、バッチ処理 | 低 |
| 9 | アラート条件の高度化 | 時間ベース閾値（N分間にM件）等 | 低 |
