DROP TABLE IF EXISTS t_pass;

-- 【テーブル】
CREATE TABLE t_pass	-- パスワード履歴テーブル
(
	user_id character varying(8) NOT NULL,	-- ユーザーID
	rireki_no numeric(3, 0) NOT NULL DEFAULT 0,	-- 履歴NO
	user_pass character varying(30) NOT NULL,	-- パスワード
	tekiyo_kaishi_date timestamp(0) without time zone NOT NULL,	-- 適用開始日
	tekiyo_shuryo_date timestamp(0) without time zone,	-- 適用終了日
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
ALTER TABLE t_pass
	ADD CONSTRAINT t_pass_pk PRIMARY KEY
	(
		user_id,	-- ユーザーID
		rireki_no	-- 履歴NO
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE t_pass IS 'パスワード履歴テーブル';

COMMENT ON COLUMN t_pass.user_id IS 'ユーザーID';
COMMENT ON COLUMN t_pass.rireki_no IS '履歴NO';
COMMENT ON COLUMN t_pass.user_pass IS 'パスワード';
COMMENT ON COLUMN t_pass.tekiyo_kaishi_date IS '適用開始日';
COMMENT ON COLUMN t_pass.tekiyo_shuryo_date IS '適用終了日';
COMMENT ON COLUMN t_pass.del_flg IS '削除フラグ';
COMMENT ON COLUMN t_pass.ins_date IS '作成日時';
COMMENT ON COLUMN t_pass.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN t_pass.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN t_pass.upd_date IS '更新日時';
COMMENT ON COLUMN t_pass.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN t_pass.upd_term IS '更新時コンピュータ名';
