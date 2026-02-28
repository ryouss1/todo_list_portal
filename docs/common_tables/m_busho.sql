DROP TABLE IF EXISTS m_busho;

-- 【テーブル】
CREATE TABLE m_busho	-- 部署マスタ
(
	busho_cd character varying(8) NOT NULL,	-- 部署コード
	jigyobu_cd character varying(2) NOT NULL,	-- 事業部コード
	jigyobu_nm character varying(20) NOT NULL,	-- 事業部名
	jigyobu_ryaku character varying(10) NOT NULL,	-- 事業部略称
	center_cd character varying(2),	-- センターコード
	center_nm character varying(20),	-- センター名
	center_ryaku character varying(10),	-- センター略称
	ka_cd character varying(2),	-- 課コード
	ka_nm character varying(20),	-- 課名
	ka_ryaku character varying(10),	-- 課略称
	kakari_cd character varying(2),	-- 係コード
	kakari_nm character varying(20),	-- 係名
	kakari_ryaku character varying(10),	-- 係略称
	kintai_busho_nm character varying(40) NOT NULL,	-- 勤怠部署名称
	kintai_busho_ryaku character varying(20) NOT NULL,	-- 勤怠部署略称
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
ALTER TABLE m_busho
	ADD CONSTRAINT m_busho_pk PRIMARY KEY
	(
		busho_cd	-- 部署コード
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE m_busho IS '部署マスタ';

COMMENT ON COLUMN m_busho.busho_cd IS '部署コード';
COMMENT ON COLUMN m_busho.jigyobu_cd IS '事業部コード';
COMMENT ON COLUMN m_busho.jigyobu_nm IS '事業部名';
COMMENT ON COLUMN m_busho.jigyobu_ryaku IS '事業部略称';
COMMENT ON COLUMN m_busho.center_cd IS 'センターコード';
COMMENT ON COLUMN m_busho.center_nm IS 'センター名';
COMMENT ON COLUMN m_busho.center_ryaku IS 'センター略称';
COMMENT ON COLUMN m_busho.ka_cd IS '課コード';
COMMENT ON COLUMN m_busho.ka_nm IS '課名';
COMMENT ON COLUMN m_busho.ka_ryaku IS '課略称';
COMMENT ON COLUMN m_busho.kakari_cd IS '係コード';
COMMENT ON COLUMN m_busho.kakari_nm IS '係名';
COMMENT ON COLUMN m_busho.kakari_ryaku IS '係略称';
COMMENT ON COLUMN m_busho.kintai_busho_nm IS '勤怠部署名称';
COMMENT ON COLUMN m_busho.kintai_busho_ryaku IS '勤怠部署略称';
COMMENT ON COLUMN m_busho.tekiyo_kaishi_date IS '適用開始日';
COMMENT ON COLUMN m_busho.tekiyo_shuryo_date IS '適用終了日';
COMMENT ON COLUMN m_busho.sort_no IS '表示順';
COMMENT ON COLUMN m_busho.del_flg IS '削除フラグ';
COMMENT ON COLUMN m_busho.ins_date IS '作成日時';
COMMENT ON COLUMN m_busho.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN m_busho.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN m_busho.upd_date IS '更新日時';
COMMENT ON COLUMN m_busho.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN m_busho.upd_term IS '更新時コンピュータ名';
