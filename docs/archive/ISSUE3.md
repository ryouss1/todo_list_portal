# 仕様・実装 Issue 一覧 (カテゴリ最適化・Backlog URL 変更完了時点)

> Business Summary カテゴリ表示最適化（インラインバー化）・Backlog URL `.backlog.com` 移行完了時点での問題点を整理したもの。
> [ISSUE.md](./ISSUE.md)（Phase 1）、[ISSUE2.md](./ISSUE2.md)（Phase 7-8）の続編。
> 重要度: **Critical** > **High** > **Medium** > **Low**

---

## 1. フロントエンド

### ISSUE-043: `window.__backlogSpace` が未初期化 [Medium] ✅ 解決済み

**現象**: `tasks.js` が `window.__backlogSpace || 'ottsystems'` を参照するが、どのテンプレートにもこの変数を初期化するコードがない。`app/config.py` に `BACKLOG_SPACE` 設定があるが、テンプレートに渡されていない。

**対処**: `pages.py` で `templates.env.globals["backlog_space"] = BACKLOG_SPACE` を設定し、`base.html` に `<script>window.__backlogSpace = "{{ backlog_space }}";</script>` を追加。全ページで自動的に利用可能。

---

### ISSUE-044: `presence.js` の Backlog URL がハードコード [Low] ✅ 解決済み

**現象**: `presence.js:20` で `https://ottsystems.backlog.com/view/` がハードコードされている。

**対処**: `presence.js` を `window.__backlogSpace || 'ottsystems'` を使う形に修正。ISSUE-043 の解決と合わせて全ページで設定値が反映される。キャッシュバスト: `presence.js?v=3` → `v=4`。

---

### ISSUE-045: JS キャッシュバスト版数が不統一 [Low] ✅ 解決済み

**現象**: 各テンプレートの JS 読み込みで `?v=` パラメータの値がバラバラ。

**対処**: 変更のあったファイルのバージョンをインクリメント済み。現在の状態:

| テンプレート | JS ファイル | バージョン |
|------------|-----------|----------|
| `tasks.html` | `tasks.js` | v=8 |
| `attendance.html` | `attendance.js` | v=7 |
| `summary.html` | `summary.js` | v=5 |
| `reports.html` | `reports.js` | v=5 |
| `report_detail.html` | `report_detail.js` | v=4 |
| `presence.html` | `presence.js` | v=4 |
| `task_list.html` | `task_list.js` | v=6 |

---

## 2. テスト

### ISSUE-046: テスト4件が stale DB データで常時失敗 [Medium] ✅ 解決済み

**現象**: テスト DB に残存するデータ（トランザクションロールバック外でコミットされたデータ）により常時失敗するテストがあった。

**対処**:
- `test_summary_empty`: `ref_date=2020-01-06` を指定し、stale データのない期間でテスト
- `test_list_public_todos_empty` / `test_list_public_todos`: テスト内で stale な public todos を `db_session.query().delete()` でクリーンアップ
- `test_summary_has_issues`: 以前の修正で解決済み

**結果**: 324 passed, 0 failed（4件の常時失敗が全て解消）

---

### ISSUE-047: DeprecationWarning — Starlette `TemplateResponse` パラメータ順序 [Low] ✅ 解決済み

**現象**: テスト実行時に `DeprecationWarning: The 'name' is not the first parameter anymore.` が出力される。

**対処**: `pages.py` の全 `TemplateResponse` 呼び出しを `TemplateResponse(request=request, name="xxx.html")` のキーワード引数形式に変更。DeprecationWarning が解消。

---

### ISSUE-048: SAWarning — トランザクション関連の警告 [Low] ✅ 解決済み

**現象**: `test_create_user_duplicate_email` 実行時に以下の SQLAlchemy 警告が出力される:
```
SAWarning: transaction already deassociated from connection
```

**影響**: テスト結果に影響なし。トランザクションロールバックパターンのエッジケース。

**対処**: `conftest.py` の `db_session` フィクスチャで `transaction.rollback()` 前に `transaction.is_active` チェックを追加。IntegrityError 等でトランザクションが既にロールバック済みの場合は再度 rollback を呼ばない。

---

## 3. 仕様書の記述問題

### ISSUE-049: SPEC_NONFUNC.md のテスト件数が古い [Medium] ✅ 解決済み

**現象**: `docs/SPEC_NONFUNC.md` のテストケース数が 228件 と記載されていたが、実際は 324件だった。

**対処**: `SPEC_NONFUNC.md` のテストカバレッジ表（6.2）とテストケース一覧（6.3）を全面更新。17ファイル・324件の正確な内容に反映。新規追加されたテストクラス（Breaks、Presets、InputType、RBAC、条件検証等）も全てリストアップ。

---

### ISSUE-050: docs/Task.md のテスト件数が古い [Low] ✅ 解決済み

**現象**: `docs/Task.md` にテスト件数が「28件」と記載されていたが、実際は 33件。

**対処**: ファイルは `docs/SPEC_Tasks.md` にリネーム済みで、テスト件数は 33件と正しく記載されていることを確認。

---

### ISSUE-051: CategoryCount スキーマの仕様書反映が一部のみ [Low] ✅ 解決済み

**現象**: `docs/BussinessSummary.md` の `category_breakdown` の説明が作業時間集計を含まない記載だった。

**対処**: `docs/SPEC_BussinessSummary.md` にリネーム済みで、`category_breakdown` の説明は「分類別レポート数・作業時間」と正しく記載されていることを確認。

---

## 4. 設計上の課題

### ISSUE-052: Attendance システムの feature freeze が長期化 [Low] ✅ 解決済み

**現象**: Attendance システムは「feature frozen」状態だが、以下の既知制限が残っていた:
- Edit モーダルに休憩編集機能なし
- 1分未満の休憩/勤怠の最小時間制限なし

**解消**:
- 休憩編集: `AttendanceUpdate.breaks` フィールドで編集モーダルから休憩の追加・置換・削除が可能（実装済み）
- 1分未満制限: `attendance_service.py` に `_validate_min_duration()` を追加。勤務時間・休憩時間ともに1分未満の登録を拒否（手動作成・更新・リアルタイム clock-out/break-end の全経路で検証）

---

## まとめ

### 重要度別件数

| 重要度 | 件数 | 解決済み | 未解決 | Issue番号 |
|--------|------|---------|--------|-----------|
| Medium | 4 | 4 | 0 | 043✅, 046✅, 049✅, 051✅ |
| Low | 6 | 6 | 0 | 044✅, 045✅, 047✅, 048✅, 050✅, 052✅ |
| **合計** | **10** | **10** | **0** | |

### カテゴリ別件数

| カテゴリ | 件数 | 解決済み | 未解決 |
|---------|------|---------|--------|
| フロントエンド | 3 | 3 | 0 |
| テスト | 3 | 3 | 0 |
| 仕様書の記述問題 | 3 | 3 | 0 |
| 設計上の課題 | 1 | 1 | 0 |

### 残件

なし（全10件解決済み）
