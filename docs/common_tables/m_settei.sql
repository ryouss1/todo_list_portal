DROP TABLE IF EXISTS m_settei;

-- 【テーブル】
CREATE TABLE m_settei	-- 設定情報マスタ
(
	lang_kbn character varying(5) NOT NULL,	-- 言語区分
	settei_kbn character varying(1) NOT NULL,	-- 設定情報区分
	settei_cd character varying(7) NOT NULL,	-- 設定情報コード
	settei_nm character varying(20) NOT NULL,	-- 設定情報名
	oya_settei_cd character varying(7),	-- 親設定情報コード
	zokusei character varying(10),	-- 値属性
	seisu_ketasu numeric(6, 0),	-- 値整数部桁数
	shosu_ketasu numeric(2, 0),	-- 値小数部桁数
	setteichi character varying(30),	-- 設定値
	biko character varying(100),	-- 備考
	tekiyo_kaishi_date timestamp(0) without time zone NOT NULL,	-- 適用開始日
	tekiyo_shuryo_date timestamp(0) without time zone,	-- 適用終了日
	sort_no numeric(3, 0) NOT NULL DEFAULT 999,	-- 表示順
	del_flg numeric(1, 0) NOT NULL DEFAULT 0,	-- 削除フラグ
	ins_date timestamp(0) without time zone NOT NULL,	-- 作成日時
	ins_user character varying(10) NOT NULL,	-- 作成ユーザーID
	ins_term character varying(64) NOT NULL,	-- 作成時コンピュータ名
	upd_date timestamp(0) without time zone NOT NULL,	-- 更新日時
	upd_user character varying(10) NOT NULL,	-- 更新ユーザーID
	upd_term character varying(64) NOT NULL	-- 更新時コンピュータ名
)

-- 【WITH句】
WITH
(
	FILLFACTOR = 90,
	OIDS = FALSE
)
TABLESPACE commondb_data
;

-- 【PK】
ALTER TABLE m_settei
	ADD CONSTRAINT m_settei_pk PRIMARY KEY
	(
		lang_kbn,	-- 言語区分
		settei_kbn,	-- 設定情報区分
		settei_cd	-- 設定情報コード
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE m_settei IS '設定情報マスタ';

COMMENT ON COLUMN m_settei.lang_kbn IS '言語区分';
COMMENT ON COLUMN m_settei.settei_kbn IS '設定情報区分';
COMMENT ON COLUMN m_settei.settei_cd IS '設定情報コード';
COMMENT ON COLUMN m_settei.settei_nm IS '設定情報名';
COMMENT ON COLUMN m_settei.oya_settei_cd IS '親設定情報コード';
COMMENT ON COLUMN m_settei.zokusei IS '値属性';
COMMENT ON COLUMN m_settei.seisu_ketasu IS '値整数部桁数';
COMMENT ON COLUMN m_settei.shosu_ketasu IS '値小数部桁数';
COMMENT ON COLUMN m_settei.setteichi IS '設定値';
COMMENT ON COLUMN m_settei.biko IS '備考';
COMMENT ON COLUMN m_settei.tekiyo_kaishi_date IS '適用開始日';
COMMENT ON COLUMN m_settei.tekiyo_shuryo_date IS '適用終了日';
COMMENT ON COLUMN m_settei.sort_no IS '表示順';
COMMENT ON COLUMN m_settei.del_flg IS '削除フラグ';
COMMENT ON COLUMN m_settei.ins_date IS '作成日時';
COMMENT ON COLUMN m_settei.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN m_settei.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN m_settei.upd_date IS '更新日時';
COMMENT ON COLUMN m_settei.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN m_settei.upd_term IS '更新時コンピュータ名';
