# WebSocket `/ws/alerts` 仕様書

> 本ドキュメントは [SPEC_API.md](../../SPEC_API.md) の補足資料です。
> アラート API の詳細は [SPEC_alerts.md](../../api/alert/SPEC_alerts.md) を参照してください。

## 1. 概要

`/ws/alerts` は、アラートのリアルタイム配信用 WebSocket エンドポイントである。
アラート生成時（手動作成・ルール自動生成の両方）に、接続中の全クライアントに JSON 形式でアラートデータがブロードキャストされる。

主な用途:
- **Alerts画面** (`/alerts`): 新着アラートをリアルタイムに一覧へ追加
- **ナビバッジ** (全画面共通): 新着アラート検知時に未確認件数バッジを更新

---

## 2. 接続仕様

| 項目 | 値 |
|------|-----|
| エンドポイント | `/ws/alerts` |
| プロトコル | `ws://` (HTTP) / `wss://` (HTTPS) |
| 認証 | セッション Cookie 必須 |
| 未認証時の動作 | コード `4401` で切断（reason: `"Not authenticated"`） |

### 2.1 接続フロー

```
クライアント                          サーバー
    |                                    |
    |--- WebSocket UPGRADE ------------->|
    |<-- 101 Switching Protocols --------|  accept()
    |                                    |  active_connections に追加
    |    セッション Cookie 検証           |
    |    ├── user_id あり → 接続維持      |
    |    └── user_id なし → 4401 切断     |
    |                                    |
    |<-- JSON メッセージ (broadcast) -----|  アラート生成時
    |<-- JSON メッセージ (broadcast) -----|
    |    ...                             |
    |                                    |
    |--- 切断 -------------------------->|
    |                                    |  active_connections から除去
```

### 2.2 認証

WebSocket 接続はセッション Cookie を使用して認証される。

- `SessionMiddleware` が WebSocket のハンドシェイク時に Cookie からセッションを復元
- `_ws_get_user_id(websocket)` でセッションから `user_id` を取得
- `user_id` が取得できない場合（未ログイン）、コード `4401` で即座に切断

```python
async def websocket_alerts(websocket: WebSocket):
    await alert_ws_manager.connect(websocket)
    if not _ws_get_user_id(websocket):
        await websocket.close(code=4401, reason="Not authenticated")
        alert_ws_manager.disconnect(websocket)
        return
```

> **注意**: WebSocket エンドポイント `/ws/` は認証ミドルウェアの `public_prefixes` に含まれているため、HTTP レベルのリダイレクトは発生しない。認証チェックはハンドラ内で行われる。

---

## 3. メッセージ仕様

### 3.1 サーバー → クライアント

アラート生成時に以下の JSON メッセージがブロードキャストされる。

**メッセージ形式:**

```json
{
  "type": "new_alert",
  "alert": {
    "id": 1,
    "title": "ERROR in prod-server",
    "message": "Database connection failed",
    "severity": "critical",
    "source": "prod-server",
    "rule_id": 1,
    "is_active": true,
    "acknowledged": false,
    "created_at": "2026-02-12T10:30:00+09:00"
  }
}
```

**フィールド詳細:**

| フィールド | 型 | 説明 |
|------------|-----|------|
| type | string | メッセージ種別（常に `"new_alert"`） |
| alert.id | integer | アラートID |
| alert.title | string | アラートタイトル |
| alert.message | string | アラートメッセージ |
| alert.severity | string | 重要度（`info` / `warning` / `critical`） |
| alert.source | string \| null | アラートソース |
| alert.rule_id | integer \| null | 自動生成元ルールID（手動作成は null） |
| alert.is_active | boolean | アクティブフラグ（常に true） |
| alert.acknowledged | boolean | 確認済みフラグ（常に false） |
| alert.created_at | string | 発生日時（ISO 8601 形式） |

### 3.2 クライアント → サーバー

クライアントからサーバーへのメッセージ送信は行われない。サーバー側は `receive_text()` で待機するが、これは接続維持のためのループであり、受信データの処理は行わない。

---

## 4. ブロードキャスト仕様

### 4.1 トリガー

以下の操作でアラートが生成された際にブロードキャストが実行される:

| トリガー | API | 説明 |
|---------|-----|------|
| 手動作成 | `POST /api/alerts/` | ユーザーが手動でアラートを作成 |
| ルール自動生成 | `POST /api/logs/` | ログ登録時にアラートルール評価で条件一致 |

### 4.2 ブロードキャスト処理

`alert_ws_manager.broadcast(data)` が以下の処理を実行する:

1. `active_connections` リストの全接続に対して `send_json(data)` を実行
2. 送信失敗した接続（デッド接続）を検出してリストから自動除去
3. デッド接続の除去をログに記録

```python
async def broadcast(self, data: dict):
    disconnected = []
    for connection in self.active_connections[:]:
        try:
            await connection.send_json(data)
        except Exception:
            disconnected.append(connection)
    for conn in disconnected:
        self.active_connections.remove(conn)
```

### 4.3 配信フロー

```
[アラート生成]
  ↓
alert_service._broadcast_alert(alert)
  ↓
alert_ws_manager.broadcast({type: "new_alert", alert: {...}})
  ↓
全 active_connections に send_json
  ├── 成功 → 配信完了
  └── 失敗 → デッド接続を除去
```

---

## 5. 接続管理

### 5.1 WebSocketManager

`alert_ws_manager` は `WebSocketManager` クラスのインスタンスで、接続の管理を行う。

| メソッド | 説明 |
|---------|------|
| `connect(websocket)` | WebSocket を accept し、`active_connections` に追加 |
| `disconnect(websocket)` | `active_connections` から除去 |
| `broadcast(data)` | 全接続に JSON を送信、デッド接続を自動除去 |

### 5.2 接続ライフサイクル

1. **接続**: `connect()` で accept → `active_connections` に追加
2. **認証チェック**: セッションから `user_id` を取得、未認証なら 4401 で切断
3. **待機ループ**: `receive_text()` で待機（接続維持）
4. **切断検知**: `WebSocketDisconnect` 例外をキャッチ → `disconnect()` で除去

### 5.3 デッド接続の除去

ブロードキャスト時に `send_json()` が失敗した接続は自動的にリストから除去される。これにより、明示的に切断されなかった接続（ネットワーク障害等）もクリーンアップされる。

---

## 6. クライアント実装

### 6.1 ナビバッジ（全画面共通）

`base.html` のグローバルスクリプトで、全ページに共通のバッジ更新処理が実装されている。

**実装場所**: `templates/base.html`

```javascript
function connectAlertBadgeWs() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${location.host}/ws/alerts`);
    ws.onmessage = () => { loadAlertCount(); };
    ws.onclose = () => { setTimeout(connectAlertBadgeWs, 5000); };
    ws.onerror = () => { ws.close(); };
}
```

**動作:**

1. ページロード時に `/ws/alerts` に接続
2. メッセージ受信時に `GET /api/alerts/count` を呼び出して未確認件数を再取得
3. 件数 > 0 → バッジ表示、件数 = 0 → バッジ非表示
4. 切断時は **5秒後** に自動再接続

**バッジ HTML:**

```html
<span class="badge bg-danger rounded-pill d-none" id="alert-badge">0</span>
```

### 6.2 Alerts画面

`static/js/alerts.js` で、Alerts画面専用の WebSocket 接続が実装されている。

**実装場所**: `static/js/alerts.js`

```javascript
function connectAlertWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    alertWs = new WebSocket(`${protocol}//${location.host}/ws/alerts`);

    alertWs.onopen = () => {
        // 接続状態バッジを "Connected"（緑）に更新
    };

    alertWs.onclose = () => {
        // 接続状態バッジを "Disconnected"（赤）に更新
        setTimeout(connectAlertWebSocket, 3000);
    };

    alertWs.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'new_alert') {
            allAlerts.unshift(data.alert);  // リスト先頭に追加
            renderAlerts();                  // 再描画
        }
    };
}
```

**動作:**

1. Alerts画面表示時に `/ws/alerts` に接続
2. 接続状態バッジ（`#alert-ws-status`）を Connected(緑) / Disconnected(赤) に切替
3. 新着アラート受信時にクライアント側の `allAlerts` 配列の先頭に追加して再描画
4. 切断時は **3秒後** に自動再接続

### 6.3 同時接続

Alerts画面を開いている場合、1つのブラウザタブから **2つの接続** が同時に存在する:

| 接続元 | 目的 | 再接続間隔 |
|--------|------|-----------|
| `base.html` (ナビバッジ) | 未確認件数バッジの更新 | 5秒 |
| `alerts.js` (Alerts画面) | アラートリストのリアルタイム更新 | 3秒 |

---

## 7. エラーハンドリング

### 7.1 未認証接続

| 状況 | 動作 |
|------|------|
| セッション Cookie なし | コード 4401 で切断 |
| 無効なセッション | コード 4401 で切断 |
| セッションに user_id なし | コード 4401 で切断 |

### 7.2 接続障害

| 状況 | 動作 |
|------|------|
| ネットワーク切断 | クライアント側で自動再接続 |
| サーバー再起動 | クライアント側で自動再接続 |
| ブロードキャスト送信失敗 | デッド接続を自動除去 |

---

## 8. 実装ファイル一覧

| ファイル | 役割 |
|---------|------|
| `main.py` | `/ws/alerts` エンドポイントハンドラ、認証チェック |
| `app/services/websocket_manager.py` | `WebSocketManager` クラス、`alert_ws_manager` インスタンス |
| `app/services/alert_service.py` | `_broadcast_alert()` — アラート生成後にブロードキャスト呼び出し |
| `templates/base.html` | ナビバッジ用 WebSocket クライアント（全画面共通） |
| `static/js/alerts.js` | Alerts画面用 WebSocket クライアント |
| `tests/test_websocket.py` | WebSocket テスト（4件、`/ws/logs` 対象だが接続管理は共通） |

---

## 9. テスト

WebSocket のテストは `tests/test_websocket.py` に実装されている。テスト対象は `/ws/logs` エンドポイントだが、接続管理（`WebSocketManager`）は `/ws/alerts` と同一クラスを使用しているため、動作は同等である。

| テストケース | 検証内容 |
|-------------|---------|
| test_websocket_connect | WebSocket 接続成功 |
| test_websocket_broadcast_on_log_create | ログ作成時にブロードキャスト受信 |
| test_websocket_disconnect_cleanup | 切断後の active_connections クリーンアップ |
| test_websocket_unauthenticated_disconnect | 未認証接続でコード 4401 切断 |

**テスト実行:**

```bash
pytest tests/test_websocket.py -q
```

---

## 10. 関連ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [SPEC_alerts.md](../../api/alert/SPEC_alerts.md) | Alerts API 仕様（REST エンドポイント） |
| [SPEC_alert-rules.md](../../api/alert-rules/SPEC_alert-rules.md) | Alert Rules API 仕様（自動アラート生成の条件定義） |
| [SPEC_API.md](../../SPEC_API.md) | API仕様（全エンドポイント概要） |
