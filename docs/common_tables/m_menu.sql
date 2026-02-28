DROP TABLE IF EXISTS m_menu;

-- 【テーブル】
CREATE TABLE m_menu	-- メニューマスタ
(
	lang_kbn character varying(5) NOT NULL,	-- 言語区分
	system_id character varying(2) NOT NULL,	-- システムID
	menu_id character varying(10) NOT NULL,	-- メニューID
	menu_nm character varying(20) NOT NULL,	-- メニュー名称
	menu_url character varying(255),	-- メニューURL
	max_hyoji_kensu numeric(3, 0) NOT NULL DEFAULT 0,	-- 最大表示件数
	max_kensaku_kensu numeric(5, 0) NOT NULL DEFAULT 0,	-- 最大検索件数
	menu_kbn numeric(1, 0) DEFAULT 0,	-- メニュー区分
	oya_menu_id character varying(10),	-- 親メニューID
	server_seiyaku numeric(1, 0) NOT NULL DEFAULT 0,	-- サーバー制約
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
ALTER TABLE m_menu
	ADD CONSTRAINT m_menu_pk PRIMARY KEY
	(
		lang_kbn,	-- 言語区分
		system_id,	-- システムID
		menu_id	-- メニューID
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE m_menu IS 'メニューマスタ';

COMMENT ON COLUMN m_menu.lang_kbn IS '言語区分';
COMMENT ON COLUMN m_menu.system_id IS 'システムID';
COMMENT ON COLUMN m_menu.menu_id IS 'メニューID';
COMMENT ON COLUMN m_menu.menu_nm IS 'メニュー名称';
COMMENT ON COLUMN m_menu.menu_url IS 'メニューURL';
COMMENT ON COLUMN m_menu.max_hyoji_kensu IS '最大表示件数';
COMMENT ON COLUMN m_menu.max_kensaku_kensu IS '最大検索件数';
COMMENT ON COLUMN m_menu.menu_kbn IS 'メニュー区分';
COMMENT ON COLUMN m_menu.oya_menu_id IS '親メニューID';
COMMENT ON COLUMN m_menu.server_seiyaku IS 'サーバー制約';
COMMENT ON COLUMN m_menu.tekiyo_kaishi_date IS '適用開始日';
COMMENT ON COLUMN m_menu.tekiyo_shuryo_date IS '適用終了日';
COMMENT ON COLUMN m_menu.sort_no IS '表示順';
COMMENT ON COLUMN m_menu.del_flg IS '削除フラグ';
COMMENT ON COLUMN m_menu.ins_date IS '作成日時';
COMMENT ON COLUMN m_menu.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN m_menu.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN m_menu.upd_date IS '更新日時';
COMMENT ON COLUMN m_menu.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN m_menu.upd_term IS '更新時コンピュータ名';
