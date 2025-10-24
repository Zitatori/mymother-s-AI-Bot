# summary_mailer.py
import os, smtplib, textwrap, base64
from email.mime.text import MIMEText
from data_store import read_log
from typing import Tuple
from typing import Optional
import streamlit as st





# --- OpenAIは“あれば使う”オプション ---
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# ===== 環境変数 =====
GMAIL_FROM = os.getenv("GMAIL_FROM")                  # 送信元（あなたのGmail）
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")  # アプリパスワード
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")        # 受信先（もりえみさん）
BOOKING_URL = os.getenv("BOOKING_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

def _supabase_client():
    # .env と Secrets の両対応
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE", {}).get("URL")
    key = os.getenv("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE", {}).get("ANON_KEY")
    if not url or not key:
        return None
    from supabase import create_client
    return create_client(url, key)

def fetch_summaries_from_supabase(limit: int = 100, nickname: Optional[str] = None):
    """Supabase から要約一覧を取得。失敗時は空配列を返す。"""
    sb = _supabase_client()
    if not sb:
        st.warning("Supabase未設定（SUPABASE_URL / SUPABASE_ANON_KEY または Secrets）")
        return []
    try:
        q = sb.table("summaries").select("*").order("created_at", desc=True).limit(limit)
        if nickname:
            q = q.eq("nickname", nickname)
        res = q.execute()
        return res.data or []
    except Exception as e:
        st.warning(f"Supabase 取得失敗: {e}")
        return []

def save_summary_to_supabase(*, nickname: str, turns: int, summary: str, transcript: str) -> bool:
    """要約を Supabase に保存。成功 True / 失敗 False。"""
    sb = _supabase_client()
    if not sb:
        st.error("Supabase未設定（SUPABASE_URL / SUPABASE_ANON_KEY または Secrets）")
        return False
    try:
        sb.table("summaries").insert({
            "nickname": nickname or "",
            "turns": int(turns),
            "summary": summary,
            "transcript": transcript
        }).execute()
        return True
    except Exception as e:
        st.error(f"Supabase 保存失敗: {e}")
        return False

def summarize_and_store(messages, nickname: str, turns: int) -> str:
    """
    既存の _summarize(messages) を使って要約→Supabase 保存。
    返り値は summary（UIで使いたい場合に備えて返す）。
    """
    summary, transcript = _summarize(messages)  # ←あなたの既存関数をそのまま利用
    ok = save_summary_to_supabase(nickname=nickname, turns=turns,
                                  summary=summary, transcript=transcript)
    st.toast("Supabaseに保存しました" if ok else "Supabase保存に失敗", icon="✅" if ok else "⚠️")
    return summary
_client = None
if OPENAI_API_KEY and OpenAI:
    _client = OpenAI(api_key=OPENAI_API_KEY)

def _send_email(to, subject, body):
    if not (GMAIL_FROM and GMAIL_APP_PASSWORD):
        raise RuntimeError("GMAIL_FROM / GMAIL_APP_PASSWORD が未設定です。")
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_FROM
    msg["To"] = to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_FROM, GMAIL_APP_PASSWORD)
        smtp.sendmail(GMAIL_FROM, [to], msg.as_string())

def _summarize(messages):
    """st.session_state.messages を要約（OpenAIが無ければ簡易）。"""
    lines = []
    for m in messages[-40:]:  # 直近40件だけ見る
        role = "ユーザー" if m["role"] == "user" else "Bot"
        lines.append(f"{role}: {m['content']}")
    transcript = "\n".join(lines)

    if not _client:
        # 簡易サマリ：先頭抜粋
        head = "\n".join(lines[:12])
        return f"【簡易要約（APIキー未設定）】\n{head}\n…（続く）", transcript

    prompt = f"""以下は会話ログです。日本語で：
1) 重要ポイントを箇条書きで5つ以内
2) 次の一歩を3つ提案
---
{transcript}
"""
    try:
        r = _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role":"user","content":prompt}],
            max_tokens=400,
            temperature=0.4
        )
        summary = r.choices[0].message.content.strip()
        return summary, transcript
    except Exception as e:
        return f"（要約失敗: {e}）\n\n{transcript}", transcript

def ensure_registration(st):
    """
    いまはニックネームだけ必須。登録完了後は rerun して即チャット画面へ。
    """
    # すでに登録済みなら何もしない
    if "nickname" in st.session_state:
        return

    # --- 登録フォーム ---
    with st.form("register"):
        st.subheader("🧍最初にニックネームだけ教えてね")
        nickname = st.text_input("ニックネーム（必須）")
        submitted = st.form_submit_button("はじめる")  # ← フォーム用のフラグは submitted で固定

    # --- フォーム直下に“目立たない”管理者ログイン ---
    with st.expander("管理者ログインはこちら", expanded=False):
        admin_token = st.text_input("管理者トークン", type="password", key="adm_tok", placeholder="●●●●●")
        if st.button("ログイン", key="adm_btn"):
            # .envの値を優先
            valid_token = ADMIN_TOKEN or (("ADMIN" in st.secrets) and st.secrets["ADMIN"].get("TOKEN"))
            admin_ok = (admin_token == valid_token)
            st.session_state["is_admin"] = bool(admin_ok)
            st.success("管理者ログイン成功 ✅") if admin_ok else st.error("認証失敗 ❌")

    # --- フォームの判定は管理者かどうかに関係なく実行する（←重要） ---
    if submitted:
        if nickname.strip():
            st.session_state["nickname"] = nickname.strip()
            # 初期メッセージが無ければ入れる
            st.session_state.setdefault(
                "messages",
                [{"role": "assistant", "content": f"{nickname.strip()} さん、どんなことでも相談してみて✨もりえみAIが答えるよ✨"}]
            )
            st.session_state.setdefault("mail_sent", False)
            st.rerun()  # 登録後に即進める
        else:
            st.warning("ニックネームを入れてください。")

    # --- 管理者パネル（ログ閲覧/ダウンロード） ---
    # --- 管理者パネル（要約一覧：Supabase） ---
    if st.session_state.get("is_admin"):
        st.divider()
        st.subheader("📚 要約ログ（Supabase）")

        import pandas as pd, io

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            nick = st.text_input("ニックネームで絞り込み（任意）", key="adm_nick", placeholder="例: みすず")
        with col2:
            limit = st.number_input("取得件数", min_value=10, max_value=1000, value=100, step=10, key="adm_limit")
        with col3:
            refresh = st.button("最新を取得", key="adm_refresh", use_container_width=True)

        if refresh or st.session_state.get("_adm_first", True):
            rows = fetch_summaries_from_supabase(limit=int(limit), nickname=(nick or "").strip() or None)
            st.session_state["_adm_rows"] = rows
            st.session_state["_adm_first"] = False
        else:
            rows = st.session_state.get("_adm_rows", [])

        st.caption(f"取得件数: {len(rows)} 件")

        if not rows:
            st.info("データがありません。送信後に要約保存が走っているか確認してください。")
        else:
            df = pd.DataFrame(rows)
            cols = [c for c in ["created_at", "nickname", "turns", "summary", "transcript", "id"] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, height=420)

            buf = io.StringIO()
            df[cols].to_csv(buf, index=False)
            st.download_button(
                "CSVをダウンロード",
                buf.getvalue().encode("utf-8"),
                file_name="summaries_admin.csv",
                mime="text/csv"
            )

    # 未登録の間はここで止める
    st.stop()


def maybe_send_summary_email(st, threshold:0):
    if not st.session_state.get("messages"):
        return

    user_cnt = sum(1 for m in st.session_state["messages"] if m["role"]=="user")
    if user_cnt < threshold or st.session_state.get("mail_sent"):
        return

    if not RECIPIENT_EMAIL:
        st.error("RECIPIENT_EMAIL が未設定のためメール送信できません。")
        return

    with st.spinner("要約してメール送信中…"):
        summary, transcript = _summarize(st.session_state["messages"])
        nickname = st.session_state.get('nickname','(無名)')
        user_email = st.session_state.get('user_email')  # いまは無い想定

        subject = f"[{nickname}] 会話要約＋ご予約のご案内"

        email_line = f"\nメール: {user_email}\n" if user_email else ""
        body = (
            "受信者：もりえみ様\n\n"
            "▼ユーザー情報\n"
            f"ニックネーム: {nickname}\n"
            f"{email_line}"
            "\n▼要約\n"
            f"{summary}\n\n"
            "▼直近ログ（抜粋）\n"
            f"{transcript}\n\n"
            "▼予約フォーム\n"
            f"{BOOKING_URL or '（未設定）'}\n\n"
            "※このメールはシステムから自動送信されています。"
        )

        try:
            _send_email(RECIPIENT_EMAIL, subject, body)
            st.session_state["mail_sent"] = True
            st.success("✅ 要約をメールで送信しました！")
        except Exception as e:
            st.error(f"メール送信に失敗：{e}")



# --- 予約フォーム（または外部予約リンク）をチャット内に出す ---
def maybe_show_booking_cta(st, *, threshold:int=10, embed_iframe:bool=False):
    """
    ユーザー発話が threshold に達したら一度だけ、
    チャット内に「ここから予約できます」のUIを出す。
    - embed_iframe=True なら iframe でフォームを埋め込む（URLが埋め込み対応のとき）
    - False ならリンクボタンを表示（安全）
    """
    if not st.session_state.get("messages"):
        return

    user_cnt = sum(1 for m in st.session_state["messages"] if m["role"] == "user")
    if user_cnt < threshold:
        return
    if st.session_state.get("booking_shown"):
        return

    # チャット履歴にも「案内メッセージ」を残す
    bot_text = (
        "ここまでお話しありがとう！\n\n"
        "▶ ご予約は下のフォーム（またはボタン）からどうぞ。"
    )
    st.session_state["messages"].append({"role": "assistant", "content": bot_text})
    st.session_state["booking_shown"] = True

    # 画面に実UIを出す（チャット気泡として）
    with st.chat_message("assistant"):
        st.markdown("**ご予約はこちらから**")

        if embed_iframe and BOOKING_URL:
            # 埋め込み（予約サービスが iframe 許可していれば）
            from streamlit.components.v1 import html
            html(f"""
                <iframe src="{BOOKING_URL}"
                        style="width:100%; height:720px; border:none; border-radius:12px;"
                        allowfullscreen></iframe>
            """, height=740, scrolling=True)
        else:
            # 安全なリンクボタン
            if BOOKING_URL:
                st.link_button("📅 予約フォームを開く", BOOKING_URL, use_container_width=True)
            else:
                st.info("予約URLが未設定です（.env の BOOKING_URL を設定してください）。")

# --- 10発話以降は常に表示される予約CTA（UIのみ。messagesは触らない） ---
def render_booking_cta_persistent(st, *, threshold:int=3, embed_iframe:bool=False, place:str="main"):
    """
    threshold 到達後は毎回レンダーで '置いておく' 予約CTA。
    - place="main"  : チャット欄の下に表示
      place="sidebar": サイドバー固定表示
    - embed_iframe=True なら iframe 埋め込み（予約サービスが許可している場合のみ）
    """
    if not st.session_state.get("messages"):
        return

    user_cnt = sum(1 for m in st.session_state["messages"] if m["role"] == "user")
    if user_cnt < threshold:
        return

    container = st.sidebar if place == "sidebar" else st

    # 見出し＋区切り
    if place == "sidebar":
        container.header("📅 ご予約")
    else:
        container.divider()
        container.subheader("📅 ご予約")

    if not BOOKING_URL:
        container.info("予約URLが未設定です（.env の BOOKING_URL を設定してください）。")
        return

    if embed_iframe:
        # 予約サービスが iframe 許可している場合のみ
        from streamlit.components.v1 import html
        html(f"""
            <iframe src="{BOOKING_URL}"
                    style="width:100%; height:720px; border:none; border-radius:12px;"
                    allowfullscreen></iframe>
        """, height=740, scrolling=True)
    else:
        container.link_button("予約フォームを開く", BOOKING_URL, use_container_width=True)


def _supabase_client():
    # .env と Secrets の両対応
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE", {}).get("URL")
    key = os.getenv("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE", {}).get("ANON_KEY")
    if not url or not key:
        return None
    from supabase import create_client
    return create_client(url, key)

def save_summary_to_supabase(*, nickname: str, turns: int, summary: str, transcript: str) -> bool:
    sb = _supabase_client()
    if not sb:
        st.error("Supabase未設定（SUPABASE_URL / SUPABASE_ANON_KEY）")
        return False
    try:
        sb.table("summaries").insert({
            "nickname": nickname or "",
            "turns": int(turns),
            "summary": summary,
            "transcript": transcript
        }).execute()
        return True
    except Exception as e:
        st.error(f"Supabase 保存失敗: {e}")
        return False

def summarize_and_store(messages, nickname: str, turns: int) -> str:
    # 既存の _summarize(messages) を利用（要約, 全文）
    summary, transcript = _summarize(messages)
    ok = save_summary_to_supabase(
        nickname=nickname, turns=turns,
        summary=summary, transcript=transcript
    )
    if ok:
        st.toast("Supabaseに保存しました", icon="✅")
    else:
        st.toast("Supabase保存に失敗", icon="⚠️")
    return summary
