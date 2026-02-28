DROP TABLE IF EXISTS m_role;
DROP SEQUENCE m_role_role_id_seq;

-- 【テーブル】
CREATE TABLE m_role	-- ロールマスタ
(
	role_id serial NOT NULL,	-- ロールID
	system_id character varying(2) NOT NULL,	-- システムID
	role_nm character varying(20) NOT NULL,	-- ロール名
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
ALTER TABLE m_role
	ADD CONSTRAINT m_role_pk PRIMARY KEY
	(
		role_id	-- ロールID
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE m_role IS 'ロールマスタ';

COMMENT ON COLUMN m_role.role_id IS 'ロールID';
COMMENT ON COLUMN m_role.system_id IS 'システムID';
COMMENT ON COLUMN m_role.role_nm IS 'ロール名';
COMMENT ON COLUMN m_role.tekiyo_kaishi_date IS '適用開始日';
COMMENT ON COLUMN m_role.tekiyo_shuryo_date IS '適用終了日';
COMMENT ON COLUMN m_role.sort_no IS '表示順';
COMMENT ON COLUMN m_role.del_flg IS '削除フラグ';
COMMENT ON COLUMN m_role.ins_date IS '作成日時';
COMMENT ON COLUMN m_role.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN m_role.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN m_role.upd_date IS '更新日時';
COMMENT ON COLUMN m_role.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN m_role.upd_term IS '更新時コンピュータ名';
