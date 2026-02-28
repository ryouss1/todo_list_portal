DROP TABLE IF EXISTS t_oshirase;
DROP SEQUENCE t_oshirase_seq_no_seq;

-- 【テーブル】
CREATE TABLE t_oshirase	-- お知らせテーブル
(
	seq_no serial,	-- シーケンス番号
	system_id character varying(2) NOT NULL,	-- システムID
	lang_kbn character varying(5) NOT NULL,	-- 言語区分
	rinji_kbn character varying(1) NOT NULL,	-- 臨時区分
	title character varying(20),	-- タイトル
	oshirase text,	-- お知らせ
	tekiyo_kaishi_date timestamp(0) without time zone NOT NULL,	-- 適用開始日
	tekiyo_shuryo_date timestamp(0) without time zone,	-- 適用終了日
	ins_date timestamp(0) without time zone NOT NULL DEFAULT current_timestamp,	-- 作成日時
	ins_user character varying(10) NOT NULL,	-- 作成ユーザーID
	ins_term character varying(64) NOT NULL	-- 作成時コンピュータ名
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
ALTER TABLE t_oshirase
	ADD CONSTRAINT t_oshirase_pk PRIMARY KEY
	(
		seq_no,	-- シーケンス番号
		tekiyo_kaishi_date	-- 適用開始日
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE t_oshirase IS 'お知らせテーブル';

COMMENT ON COLUMN t_oshirase.seq_no IS 'シーケンス番号';
COMMENT ON COLUMN t_oshirase.system_id IS 'システムID';
COMMENT ON COLUMN t_oshirase.lang_kbn IS '言語区分';
COMMENT ON COLUMN t_oshirase.rinji_kbn IS '臨時区分';
COMMENT ON COLUMN t_oshirase.title IS 'タイトル';
COMMENT ON COLUMN t_oshirase.oshirase IS 'お知らせ';
COMMENT ON COLUMN t_oshirase.tekiyo_kaishi_date IS '適用開始日';
COMMENT ON COLUMN t_oshirase.tekiyo_shuryo_date IS '適用終了日';
COMMENT ON COLUMN t_oshirase.ins_date IS '作成日時';
COMMENT ON COLUMN t_oshirase.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN t_oshirase.ins_term IS '作成時コンピュータ名';
