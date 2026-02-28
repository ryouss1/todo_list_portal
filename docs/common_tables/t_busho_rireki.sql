DROP TABLE IF EXISTS t_busho_rireki;

-- 【テーブル】
CREATE TABLE t_busho_rireki	-- 部署履歴テーブル
(
	old_busho_cd character varying(8) NOT NULL,	-- 旧部署コード
	old_jigyobu_cd character varying(2),	-- 旧事業部コード
	old_center_cd character varying(2),	-- 旧センターコード
	old_ka_cd character varying(2),	-- 旧課コード
	old_kakari_cd character varying(2),	-- 旧係コード
	new_busho_cd character varying(8) NOT NULL,	-- 新部署コード
	new_jigyobu_cd character varying(2),	-- 新事業部コード
	new_center_cd character varying(2),	-- 新センターコード
	new_ka_cd character varying(2),	-- 新課コード
	new_kakari_cd character varying(2),	-- 新係コード
	ido_hiritsu numeric(3, 0) DEFAULT 0,	-- 移動比率
	yusen_juni numeric(1, 0) NOT NULL DEFAULT 0,	-- 優先順位
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
ALTER TABLE t_busho_rireki
	ADD CONSTRAINT t_busho_rireki_pk PRIMARY KEY
	(
		old_busho_cd,	-- 旧部署コード
		new_busho_cd	-- 新部署コード
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE t_busho_rireki IS '部署履歴テーブル';

COMMENT ON COLUMN t_busho_rireki.old_busho_cd IS '旧部署コード';
COMMENT ON COLUMN t_busho_rireki.old_jigyobu_cd IS '旧事業部コード';
COMMENT ON COLUMN t_busho_rireki.old_center_cd IS '旧センターコード';
COMMENT ON COLUMN t_busho_rireki.old_ka_cd IS '旧課コード';
COMMENT ON COLUMN t_busho_rireki.old_kakari_cd IS '旧係コード';
COMMENT ON COLUMN t_busho_rireki.new_busho_cd IS '新部署コード';
COMMENT ON COLUMN t_busho_rireki.new_jigyobu_cd IS '新事業部コード';
COMMENT ON COLUMN t_busho_rireki.new_center_cd IS '新センターコード';
COMMENT ON COLUMN t_busho_rireki.new_ka_cd IS '新課コード';
COMMENT ON COLUMN t_busho_rireki.new_kakari_cd IS '新係コード';
COMMENT ON COLUMN t_busho_rireki.ido_hiritsu IS '移動比率';
COMMENT ON COLUMN t_busho_rireki.yusen_juni IS '優先順位';
COMMENT ON COLUMN t_busho_rireki.del_flg IS '削除フラグ';
COMMENT ON COLUMN t_busho_rireki.ins_date IS '作成日時';
COMMENT ON COLUMN t_busho_rireki.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN t_busho_rireki.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN t_busho_rireki.upd_date IS '更新日時';
COMMENT ON COLUMN t_busho_rireki.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN t_busho_rireki.upd_term IS '更新時コンピュータ名';
