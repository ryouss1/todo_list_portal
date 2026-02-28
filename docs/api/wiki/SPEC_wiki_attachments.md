# WIKI 添付ファイル設計書（Phase 2）

> 本ドキュメントは [spec_wiki.md](../../spec_wiki.md) のサブ設計書です。
> 作成日: 2026-02-25
> **実装フェーズ: Phase 2**

---

## 1. 概要

WIKIページへのファイル添付機能（Phase 2）。画像・PDF・各種ファイルをサーバーにアップロードし、Tiptap エディタからインライン挿入または添付ファイルリストとして参照できるようにする。

### 1.1 Phase 2 のスコープ

| 機能 | 実装 |
|------|------|
| ファイルアップロード（任意ファイル）| ✅ Phase 2 |
| 画像のインライン挿入（エディタ内）| ✅ Phase 2 |
| 添付ファイル一覧表示 | ✅ Phase 2 |
| ファイル削除 | ✅ Phase 2 |
| ファイルプレビュー（画像・PDF）| ✅ Phase 2 |
| バージョン管理（ファイル履歴）| ❌ Phase 3 以降 |
| 外部ストレージ（S3等）| ❌ Phase 3 以降（Phase 2 はローカルディスク） |

---

## 2. データベース設計

### 2.1 wiki_attachments テーブル

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 添付ファイルID |
| page_id | Integer | FK(wiki_pages.id, CASCADE), NOT NULL, INDEX | 紐づくWIKIページID |
| file_name | String(500) | NOT NULL | オリジナルファイル名 |
| stored_name | String(500) | NOT NULL, UNIQUE | ストレージ上のファイル名（UUID + 拡張子） |
| file_size | BigInteger | NOT NULL | ファイルサイズ（バイト） |
| mime_type | String(200) | NOT NULL | MIMEタイプ |
| uploaded_by | Integer | FK(users.id, SET NULL), NULL許可 | アップロードユーザーID |
| created_at | DateTime(TZ) | DEFAULT now() | アップロード日時 |

- ページ削除時: CASCADE で添付ファイルレコードも削除（物理ファイルは別途削除処理が必要）
- `stored_name`: `{uuid4}.{ext}` 形式（例: `a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf`）

### 2.2 ER 図

```
wiki_pages (1) ──── (N) wiki_attachments.page_id (CASCADE)
users (1) ──── (N) wiki_attachments.uploaded_by (SET NULL)
```

---

## 3. ファイルストレージ設計

### 3.1 Phase 2: ローカルディスク

```
uploads/
└── wiki/
    └── {page_id}/
        ├── a1b2c3d4-...pdf
        ├── b2c3d4e5-...png
        └── ...
```

- **保存先**: プロジェクトルート `uploads/wiki/{page_id}/`
- **URL**: `/api/wiki/attachments/{attachment_id}/file`（認証必要）
- **最大サイズ**: 50MB（設定可能、環境変数 `WIKI_MAX_FILE_SIZE`）
- **許可拡張子**: 画像 (jpg, png, gif, webp, svg)、文書 (pdf, xlsx, docx, txt, md)、アーカイブ (zip)
- `uploads/` は `.gitignore` 登録（Git 管理外）

### 3.2 Phase 3 以降: 外部ストレージ

Phase 3 では S3 互換ストレージ（MinIO / AWS S3）への切り替えを想定。`StorageBackend` 抽象クラスを設け、Phase 2 は `LocalStorageBackend`、Phase 3 は `S3StorageBackend` を実装する。

```python
# app/services/wiki_storage.py（Phase 2 は LocalStorageBackend のみ実装）

from abc import ABC, abstractmethod

class StorageBackend(ABC):
    @abstractmethod
    async def save(self, page_id: int, stored_name: str, data: bytes) -> str: ...

    @abstractmethod
    async def load(self, page_id: int, stored_name: str) -> bytes: ...

    @abstractmethod
    async def delete(self, page_id: int, stored_name: str) -> None: ...
```

---

## 4. SQLAlchemy モデル

```python
# app/models/wiki_attachment.py

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from portal_core.database import Base


class WikiAttachment(Base):
    __tablename__ = "wiki_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    page_id = Column(Integer, ForeignKey("wiki_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(500), nullable=False)
    stored_name = Column(String(500), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(200), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    page = relationship("WikiPage", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])
```

---

## 5. Alembic マイグレーション

```python
# alembic/versions/xxxx_add_wiki_attachments.py

def upgrade():
    op.create_table(
        "wiki_attachments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("stored_name", sa.String(500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(200), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["wiki_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_name"),
    )
    op.create_index("ix_wiki_attachments_page_id", "wiki_attachments", ["page_id"])


def downgrade():
    op.drop_table("wiki_attachments")
```

---

## 6. API 設計

### 6.1 エンドポイント一覧

| メソッド | パス | 説明 | 権限 |
|---------|------|------|------|
| GET | `/api/wiki/pages/{id}/attachments` | 添付ファイル一覧取得 | 認証必須 |
| POST | `/api/wiki/pages/{id}/attachments` | ファイルアップロード | 認証必須 |
| GET | `/api/wiki/attachments/{attachment_id}/file` | ファイルダウンロード | 認証必須 |
| DELETE | `/api/wiki/attachments/{attachment_id}` | ファイル削除 | 認証必須（アップロード者 or admin） |

### 6.2 POST `/api/wiki/pages/{id}/attachments`

multipart/form-data でファイルをアップロードする。

**リクエスト**: `Content-Type: multipart/form-data`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| file | UploadFile | Yes | アップロードファイル |

**レスポンス**: `201 Created` - `WikiAttachmentResponse`

```json
{
  "id": 1,
  "page_id": 42,
  "file_name": "architecture.pdf",
  "file_size": 102400,
  "mime_type": "application/pdf",
  "url": "/api/wiki/attachments/1/file",
  "uploaded_by": 1,
  "uploader_name": "山田太郎",
  "created_at": "2026-02-25T10:00:00+09:00"
}
```

**エラー**:
- `400 Bad Request` - ファイルサイズ超過 / 許可されていない拡張子
- `404 Not Found` - ページ不存在

### 6.3 GET `/api/wiki/attachments/{attachment_id}/file`

ファイルを配信する。`Content-Disposition: inline` でブラウザプレビューを優先。

**レスポンス**: ファイルバイナリ（適切な `Content-Type`）

### 6.4 DELETE `/api/wiki/attachments/{attachment_id}`

ファイルレコードとストレージ上の物理ファイルを削除する。

**権限**: アップロード者 または admin
**レスポンス**: `204 No Content`

---

## 7. スキーマ定義

```python
# app/schemas/wiki.py（追記）

class WikiAttachmentResponse(BaseModel):
    id: int
    page_id: int
    file_name: str
    file_size: int
    mime_type: str
    url: str
    uploaded_by: Optional[int]
    uploader_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
```

---

## 8. サービス実装（概要）

```python
# app/services/wiki_attachment_service.py

import os
import uuid
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.models.wiki_attachment import WikiAttachment

WIKI_UPLOAD_DIR = os.environ.get("WIKI_UPLOAD_DIR", "uploads/wiki")
WIKI_MAX_FILE_SIZE = int(os.environ.get("WIKI_MAX_FILE_SIZE", str(50 * 1024 * 1024)))  # 50MB
ALLOWED_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "webp", "svg",
    "pdf", "xlsx", "xls", "docx", "doc", "txt", "md",
    "zip",
}


async def upload_attachment(
    db: Session, page_id: int, file: UploadFile, user_id: int
) -> WikiAttachment:
    # 拡張子チェック
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '.{ext}' is not allowed")

    # サイズチェック
    content = await file.read()
    if len(content) > WIKI_MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds limit")

    # ストレージ保存
    stored_name = f"{uuid.uuid4()}.{ext}"
    upload_dir = os.path.join(WIKI_UPLOAD_DIR, str(page_id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, stored_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # DB 保存
    attachment = WikiAttachment(
        page_id=page_id,
        file_name=file.filename,
        stored_name=stored_name,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=user_id,
    )
    db.add(attachment)
    db.flush()
    return attachment


def delete_attachment(db: Session, attachment_id: int, user_id: int, is_admin: bool) -> None:
    attachment = db.query(WikiAttachment).filter(WikiAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404)
    if not is_admin and attachment.uploaded_by != user_id:
        raise HTTPException(status_code=403)

    # 物理ファイル削除
    file_path = os.path.join(WIKI_UPLOAD_DIR, str(attachment.page_id), attachment.stored_name)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(attachment)
```

---

## 9. Tiptap エディタ統合（Phase 2）

Phase 2 では Tiptap の `Image` 拡張を有効化し、添付ファイルからインライン挿入できるようにする。

```javascript
// wiki.js への追記（Phase 2）

// 画像アップロード → エディタ挿入フロー
async function uploadAndInsertImage(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`/api/wiki/pages/${pageId}/attachments`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) { showToast("アップロード失敗", "danger"); return; }
  const data = await res.json();

  // Tiptap エディタに画像挿入
  editor.chain().focus().setImage({ src: data.url, alt: data.file_name }).run();
}

// ドラッグ&ドロップ対応
document.getElementById("editor-container").addEventListener("drop", async e => {
  e.preventDefault();
  const files = e.dataTransfer.files;
  for (const file of files) {
    if (file.type.startsWith("image/")) {
      await uploadAndInsertImage(file);
    }
  }
});
```

---

## 10. 設定管理

```python
# portal_core/portal_core/config.py への追加（Phase 2 実装時）

# Wiki Attachments
WIKI_UPLOAD_DIR: str = os.environ.get("WIKI_UPLOAD_DIR", "uploads/wiki")
WIKI_MAX_FILE_SIZE: int = int(os.environ.get("WIKI_MAX_FILE_SIZE", str(50 * 1024 * 1024)))
```

`.gitignore` 追記:
```
uploads/
```

---

## 11. 技術的負債・注意事項

| 項目 | 内容 | 優先度 |
|------|------|--------|
| 孤立ファイル | ページ CASCADE 削除時に wiki_attachments レコードは消えるが、物理ファイルは残る（DB イベントフック or 定期クリーンアップが必要） | 高 |
| ファイルサイズ制限 | 大ファイルを `await file.read()` で全読み込みするとメモリ消費が大きい。Phase 3 でストリーミング書き込みに変更推奨 | 中 |
| セキュリティ: Path Traversal | `stored_name` は UUID + 拡張子のみ許可し、`stored_name` を URL パラメータとして受け取らないことで防止 | 高（設計上対策済み） |
| MIME タイプの信頼性 | `file.content_type` はクライアント指定のため信頼性低。Phase 2 は許可拡張子チェックで代替。Phase 3 で `python-magic` による検証を追加推奨 | 中 |
| 外部ストレージ移行 | Phase 2 はローカルディスク。`StorageBackend` 抽象クラスを用意しているため Phase 3 で S3 移行時の変更が最小になる | 低（将来対応） |
