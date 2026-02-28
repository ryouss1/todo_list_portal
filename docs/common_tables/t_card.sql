DROP TABLE IF EXISTS t_card;

-- 【テーブル】
CREATE TABLE t_card	-- ＩＣカード履歴テーブル
(
	ic_card_no character varying(16) NOT NULL,	-- ICカード番号
	renban character varying(3) NOT NULL,	-- 連番
	tekiyo_kaishi_date timestamp(0) without time zone NOT NULL,	-- 適用開始日
	tekiyo_shuryo_date timestamp(0) without time zone,	-- 適用終了日
	kaisha_cd character varying(8) NOT NULL,	-- 会社コード
	shain_cd character varying(7) NOT NULL,	-- 社員コード
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
ALTER TABLE t_card
	ADD CONSTRAINT t_card_pk PRIMARY KEY
	(
		ic_card_no,	-- ICカード番号
		renban	-- 連番
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE t_card IS 'ＩＣカード履歴テーブル';

COMMENT ON COLUMN t_card.ic_card_no IS 'ICカード番号';
COMMENT ON COLUMN t_card.renban IS '連番';
COMMENT ON COLUMN t_card.tekiyo_kaishi_date IS '適用開始日';
COMMENT ON COLUMN t_card.tekiyo_shuryo_date IS '適用終了日';
COMMENT ON COLUMN t_card.kaisha_cd IS '会社コード';
COMMENT ON COLUMN t_card.shain_cd IS '社員コード';
COMMENT ON COLUMN t_card.del_flg IS '削除フラグ';
COMMENT ON COLUMN t_card.ins_date IS '作成日時';
COMMENT ON COLUMN t_card.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN t_card.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN t_card.upd_date IS '更新日時';
COMMENT ON COLUMN t_card.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN t_card.upd_term IS '更新時コンピュータ名';
