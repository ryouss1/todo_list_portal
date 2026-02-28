DROP TABLE IF EXISTS t_user_menu;

-- 【テーブル】
CREATE TABLE t_user_menu	-- ユーザーメニュー設定テーブル
(
	user_id character varying(8) NOT NULL,	-- ユーザーID
	system_id character varying(2) NOT NULL,	-- システムID
	menu_id character varying(10) NOT NULL,	-- メニューID
	kino_kbn numeric(1, 0) NOT NULL,	-- 機能区分
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
ALTER TABLE t_user_menu
	ADD CONSTRAINT t_user_menu_pk PRIMARY KEY
	(
		user_id,	-- ユーザーID
		system_id,	-- システムID
		menu_id	-- メニューID
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE t_user_menu IS 'ユーザーメニュー設定テーブル';

COMMENT ON COLUMN t_user_menu.user_id IS 'ユーザーID';
COMMENT ON COLUMN t_user_menu.system_id IS 'システムID';
COMMENT ON COLUMN t_user_menu.menu_id IS 'メニューID';
COMMENT ON COLUMN t_user_menu.kino_kbn IS '機能区分';
COMMENT ON COLUMN t_user_menu.ins_date IS '作成日時';
COMMENT ON COLUMN t_user_menu.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN t_user_menu.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN t_user_menu.upd_date IS '更新日時';
COMMENT ON COLUMN t_user_menu.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN t_user_menu.upd_term IS '更新時コンピュータ名';
