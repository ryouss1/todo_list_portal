DROP TABLE IF EXISTS m_user;

-- 【テーブル】
CREATE TABLE m_user	-- ユーザーマスタ
(
	user_id character varying(8) NOT NULL,	-- ユーザーID
	user_nm character varying(40) NOT NULL,	-- ユーザー名
	user_kbn character varying(1) NOT NULL,	-- ユーザー区分
	kaisha_cd character varying(8) NOT NULL,	-- 会社コード
	shain_cd character varying(7) NOT NULL,	-- 社員コード
	mail_address character varying(255) NOT NULL,	-- メールアドレス
	pass_err_count numeric(1, 0) NOT NULL DEFAULT 0,	-- パスワードエラー回数
	account_lock numeric(1, 0) NOT NULL DEFAULT 0,	-- アカウントロック
	account_lock_date timestamp(0) without time zone,	-- アカウントロック日時
	kari_pass_flg numeric(1, 0) NOT NULL DEFAULT 1,	-- 仮パスワードフラグ
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
ALTER TABLE m_user
	ADD CONSTRAINT m_user_pk PRIMARY KEY
	(
		user_id	-- ユーザーID
	)
	USING INDEX TABLESPACE commondb_idx
;

-- 【コメント】
COMMENT ON TABLE m_user IS 'ユーザーマスタ';

COMMENT ON COLUMN m_user.user_id IS 'ユーザーID';
COMMENT ON COLUMN m_user.user_nm IS 'ユーザー名';
COMMENT ON COLUMN m_user.user_kbn IS 'ユーザー区分';
COMMENT ON COLUMN m_user.kaisha_cd IS '会社コード';
COMMENT ON COLUMN m_user.shain_cd IS '社員コード';
COMMENT ON COLUMN m_user.mail_address IS 'メールアドレス';
COMMENT ON COLUMN m_user.pass_err_count IS 'パスワードエラー回数';
COMMENT ON COLUMN m_user.account_lock IS 'アカウントロック';
COMMENT ON COLUMN m_user.account_lock_date IS 'アカウントロック日時';
COMMENT ON COLUMN m_user.kari_pass_flg IS '仮パスワードフラグ';
COMMENT ON COLUMN m_user.tekiyo_kaishi_date IS '適用開始日';
COMMENT ON COLUMN m_user.tekiyo_shuryo_date IS '適用終了日';
COMMENT ON COLUMN m_user.sort_no IS '表示順';
COMMENT ON COLUMN m_user.del_flg IS '削除フラグ';
COMMENT ON COLUMN m_user.ins_date IS '作成日時';
COMMENT ON COLUMN m_user.ins_user IS '作成ユーザーID';
COMMENT ON COLUMN m_user.ins_term IS '作成時コンピュータ名';
COMMENT ON COLUMN m_user.upd_date IS '更新日時';
COMMENT ON COLUMN m_user.upd_user IS '更新ユーザーID';
COMMENT ON COLUMN m_user.upd_term IS '更新時コンピュータ名';
