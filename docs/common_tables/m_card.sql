DROP TABLE IF EXISTS m_card;

-- 【テーブル】
CREATE TABLE m_card	-- ＩＣカードマスタ
(
	ic_card_no character varying(16) NOT NULL,	-- ICカード番号
	konyu_date date,	-- 購入日
	ic_card_label character varying(7),	-- ICカードラベル
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
ALTER TABLE m_card
	ADD CONSTRAINT m_card_pk PRIMARY KEY
	(
		ic_card_no	-- ICカード番号
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE m_card IS 'ＩＣカードマスタ';

COMMENT ON COLUMN m_card.ic_card_no IS 'ICカード番号';
COMMENT ON COLUMN m_card.konyu_date IS '購入日';
COMMENT ON COLUMN m_card.ic_card_label IS 'ICカードラベル';
COMMENT ON COLUMN m_card.sort_no IS '表示順';
COMMENT ON COLUMN m_card.del_flg IS '削除フラグ';
COMMENT ON COLUMN m_card.ins_date IS '作成日時';
COMMENT ON COLUMN m_card.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN m_card.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN m_card.upd_date IS '更新日時';
COMMENT ON COLUMN m_card.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN m_card.upd_term IS '更新時コンピュータ名';
