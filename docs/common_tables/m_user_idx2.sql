DROP INDEX IF EXISTS m_user_idx2;

CREATE INDEX m_user_idx2	-- ユーザーマスタ
	ON  m_user
USING btree
	(
		shain_cd	-- 社員コード
	)
	TABLESPACE commondb_idx
;
