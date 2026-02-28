DROP INDEX IF EXISTS m_settei_idx2;

CREATE INDEX m_settei_idx2	-- 設定情報マスタ
	ON  m_settei
USING btree
	(
		lang_kbn,	-- 言語区分
		settei_kbn,	-- 設定情報区分
		oya_settei_cd,	-- 親設定情報コード
		settei_cd	-- 設定情報コード
	)
	TABLESPACE commondb_idx
;
