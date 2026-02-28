DROP TABLE IF EXISTS t_user_role;

-- 【テーブル】
CREATE TABLE t_user_role	-- ユーザーロール設定テーブル
(
	user_id character varying(8) NOT NULL,	-- ユーザーID
	role_id integer NOT NULL,	-- ロールID
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
ALTER TABLE t_user_role
	ADD CONSTRAINT t_user_role_pk PRIMARY KEY
	(
		user_id,	-- ユーザーID
		role_id	-- ロールID
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE t_user_role IS 'ユーザーロール設定テーブル';

COMMENT ON COLUMN t_user_role.user_id IS 'ユーザーID';
COMMENT ON COLUMN t_user_role.role_id IS 'ロールID';
COMMENT ON COLUMN t_user_role.ins_date IS '作成日時';
COMMENT ON COLUMN t_user_role.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN t_user_role.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN t_user_role.upd_date IS '更新日時';
COMMENT ON COLUMN t_user_role.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN t_user_role.upd_term IS '更新時コンピュータ名';
