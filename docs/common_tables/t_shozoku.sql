DROP TABLE IF EXISTS t_shozoku;

-- 【テーブル】
CREATE TABLE t_shozoku	-- 所属管理テーブル
(
	kaisha_cd character varying(8) NOT NULL,	-- 会社コード
	shain_cd character varying(7) NOT NULL,	-- 社員コード
	busho_cd character varying(8) NOT NULL,	-- 部署コード
	tekiyo_kaishi_date timestamp(0) without time zone NOT NULL,	-- 適用開始日
	tekiyo_shuryo_date timestamp(0) without time zone,	-- 適用終了日
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
ALTER TABLE t_shozoku
	ADD CONSTRAINT t_shozoku_pk PRIMARY KEY
	(
		kaisha_cd,	-- 会社コード
		shain_cd,	-- 社員コード
		busho_cd,	-- 部署コード
		tekiyo_kaishi_date	-- 適用開始日
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE t_shozoku IS '所属管理テーブル';

COMMENT ON COLUMN t_shozoku.kaisha_cd IS '会社コード';
COMMENT ON COLUMN t_shozoku.shain_cd IS '社員コード';
COMMENT ON COLUMN t_shozoku.busho_cd IS '部署コード';
COMMENT ON COLUMN t_shozoku.tekiyo_kaishi_date IS '適用開始日';
COMMENT ON COLUMN t_shozoku.tekiyo_shuryo_date IS '適用終了日';
COMMENT ON COLUMN t_shozoku.ins_date IS '作成日時';
COMMENT ON COLUMN t_shozoku.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN t_shozoku.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN t_shozoku.upd_date IS '更新日時';
COMMENT ON COLUMN t_shozoku.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN t_shozoku.upd_term IS '更新時コンピュータ名';
