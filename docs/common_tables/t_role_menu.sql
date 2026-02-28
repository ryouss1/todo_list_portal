DROP TABLE IF EXISTS t_role_menu;

-- 【テーブル】
CREATE TABLE t_role_menu	-- ロールメニュー設定テーブル
(
	role_id integer NOT NULL,	-- ロールID
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
ALTER TABLE t_role_menu
	ADD CONSTRAINT t_role_menu_pk PRIMARY KEY
	(
		role_id,	-- ロールID
		system_id,	-- システムID
		menu_id	-- メニューID
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE t_role_menu IS 'ロールメニュー設定テーブル';

COMMENT ON COLUMN t_role_menu.role_id IS 'ロールID';
COMMENT ON COLUMN t_role_menu.system_id IS 'システムID';
COMMENT ON COLUMN t_role_menu.menu_id IS 'メニューID';
COMMENT ON COLUMN t_role_menu.kino_kbn IS '機能区分';
COMMENT ON COLUMN t_role_menu.ins_date IS '作成日時';
COMMENT ON COLUMN t_role_menu.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN t_role_menu.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN t_role_menu.upd_date IS '更新日時';
COMMENT ON COLUMN t_role_menu.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN t_role_menu.upd_term IS '更新時コンピュータ名';
