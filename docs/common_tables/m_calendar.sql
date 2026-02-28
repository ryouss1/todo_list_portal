DROP TABLE IF EXISTS m_calendar;

-- 【テーブル】
CREATE TABLE m_calendar	-- カレンダーマスタ
(
	calendar_kbn character varying(3) NOT NULL,	-- カレンダー区分
	nen numeric(4, 0) NOT NULL,	-- 年度
	nengappi character varying(8) NOT NULL,	-- 年月日
	jotai_kbn character varying(2) NOT NULL,	-- 状態区分
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
ALTER TABLE m_calendar
	ADD CONSTRAINT m_calendar_pk PRIMARY KEY
	(
		calendar_kbn,	-- カレンダー区分
		nen,	-- 年度
		nengappi	-- 年月日
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE m_calendar IS 'カレンダーマスタ';

COMMENT ON COLUMN m_calendar.calendar_kbn IS 'カレンダー区分';
COMMENT ON COLUMN m_calendar.nen IS '年度';
COMMENT ON COLUMN m_calendar.nengappi IS '年月日';
COMMENT ON COLUMN m_calendar.jotai_kbn IS '状態区分';
COMMENT ON COLUMN m_calendar.del_flg IS '削除フラグ';
COMMENT ON COLUMN m_calendar.ins_date IS '作成日時';
COMMENT ON COLUMN m_calendar.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN m_calendar.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN m_calendar.upd_date IS '更新日時';
COMMENT ON COLUMN m_calendar.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN m_calendar.upd_term IS '更新時コンピュータ名';
