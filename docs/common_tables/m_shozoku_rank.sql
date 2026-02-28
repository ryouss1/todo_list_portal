DROP TABLE IF EXISTS m_shozoku_rank;

-- 【テーブル】
CREATE TABLE m_shozoku_rank	-- 所属ランクマスタ
(
	rank_kbn character varying(1) NOT NULL,	-- 所属ランク区分
	rank_cd character varying(2) NOT NULL,	-- 所属ランクコード
	rank_nm character varying(20) NOT NULL,	-- 所属ランク名
	rank_ryaku character varying(10) NOT NULL,	-- 所属ランク略称
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
ALTER TABLE m_shozoku_rank
	ADD CONSTRAINT m_shozoku_rank_pk PRIMARY KEY
	(
		rank_kbn,	-- 所属ランク区分
		rank_cd	-- 所属ランクコード
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE m_shozoku_rank IS '所属ランクマスタ';

COMMENT ON COLUMN m_shozoku_rank.rank_kbn IS '所属ランク区分';
COMMENT ON COLUMN m_shozoku_rank.rank_cd IS '所属ランクコード';
COMMENT ON COLUMN m_shozoku_rank.rank_nm IS '所属ランク名';
COMMENT ON COLUMN m_shozoku_rank.rank_ryaku IS '所属ランク略称';
COMMENT ON COLUMN m_shozoku_rank.sort_no IS '表示順';
COMMENT ON COLUMN m_shozoku_rank.del_flg IS '削除フラグ';
COMMENT ON COLUMN m_shozoku_rank.ins_date IS '作成日時';
COMMENT ON COLUMN m_shozoku_rank.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN m_shozoku_rank.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN m_shozoku_rank.upd_date IS '更新日時';
COMMENT ON COLUMN m_shozoku_rank.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN m_shozoku_rank.upd_term IS '更新時コンピュータ名';
