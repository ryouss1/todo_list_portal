DROP INDEX IF EXISTS m_user_idx1;

CREATE INDEX m_user_idx1	-- ユーザーマスタ
	ON  m_user
USING btree
	(
		kaisha_cd	-- 会社コード
	)
	TABLESPACE commondb_idx
;
