DROP TABLE IF EXISTS m_shain;
DROP SEQUENCE m_shain_shain_uid_seq;

-- 【テーブル】
CREATE TABLE m_shain	-- 社員マスタ
(
	shain_uid serial NOT NULL,	-- 社員UID
	kaisha_cd character varying(8) NOT NULL,	-- 会社コード
	shain_cd character varying(7) NOT NULL,	-- 社員コード
	shain_nm character varying(40) NOT NULL,	-- 社員名（母国語）
	shain_nm_eng character varying(40) NOT NULL,	-- 社員名（英語）
	shain_kana character varying(40),	-- 社員名（カナ）
	shain_kbn character varying(1) NOT NULL,	-- 社員区分
	shokushu_kbn character varying(1) NOT NULL,	-- 職種区分
	nyusha_date timestamp(0) without time zone NOT NULL,	-- 入社日
	taisha_date timestamp(0) without time zone,	-- 退社日
	tekiyo_kaishi_date timestamp(0) without time zone NOT NULL,	-- 適用開始日
	tekiyo_shuryo_date timestamp(0) without time zone,	-- 適用終了日
	sort_no numeric(3, 0) NOT NULL DEFAULT 999,	-- 表示順
	gyosha_cd character varying(8),	-- 業者コード
	eigyosho_cd character varying(5),	-- 営業所コード
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
ALTER TABLE m_shain
	ADD CONSTRAINT m_shain_pk PRIMARY KEY
	(
		shain_uid	-- 社員UID
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE m_shain IS '社員マスタ';

COMMENT ON COLUMN m_shain.shain_uid IS '社員UID';
COMMENT ON COLUMN m_shain.kaisha_cd IS '会社コード';
COMMENT ON COLUMN m_shain.shain_cd IS '社員コード';
COMMENT ON COLUMN m_shain.shain_nm IS '社員名（母国語）';
COMMENT ON COLUMN m_shain.shain_nm_eng IS '社員名（英語）';
COMMENT ON COLUMN m_shain.shain_kana IS '社員名（カナ）';
COMMENT ON COLUMN m_shain.shain_kbn IS '社員区分';
COMMENT ON COLUMN m_shain.shokushu_kbn IS '職種区分';
COMMENT ON COLUMN m_shain.nyusha_date IS '入社日';
COMMENT ON COLUMN m_shain.taisha_date IS '退社日';
COMMENT ON COLUMN m_shain.tekiyo_kaishi_date IS '適用開始日';
COMMENT ON COLUMN m_shain.tekiyo_shuryo_date IS '適用終了日';
COMMENT ON COLUMN m_shain.sort_no IS '表示順';
COMMENT ON COLUMN m_shain.gyosha_cd IS '業者コード';
COMMENT ON COLUMN m_shain.eigyosho_cd IS '営業所コード';
COMMENT ON COLUMN m_shain.del_flg IS '削除フラグ';
COMMENT ON COLUMN m_shain.ins_date IS '作成日時';
COMMENT ON COLUMN m_shain.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN m_shain.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN m_shain.upd_date IS '更新日時';
COMMENT ON COLUMN m_shain.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN m_shain.upd_term IS '更新時コンピュータ名';
