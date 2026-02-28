DROP INDEX IF EXISTS m_settei_idx1;

CREATE INDEX m_settei_idx1	-- 設定情報マスタ
	ON  m_settei
USING btree
	(
		lang_kbn,	-- 言語区分
		settei_kbn,	-- 設定情報区分
		oya_settei_cd,	-- 親設定情報コード
		setteichi	-- 設定値
	)
	TABLESPACE commondb_idx
;
