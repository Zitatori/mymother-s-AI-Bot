# summary_mailer.py
import os, smtplib, textwrap, base64
from email.mime.text import MIMEText

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

    with st.form("register"):
        st.subheader("🧍最初にニックネームだけ教えてね")
        nickname = st.text_input("ニックネーム（必須）")
        ok = st.form_submit_button("はじめる")
        if ok:
            if nickname.strip():
                st.session_state["nickname"] = nickname.strip()
                # 初期メッセージが無ければ入れる
                st.session_state.setdefault(
                    "messages",
                    [{"role":"assistant","content":f"{nickname} さん、どんなことでも相談してみて✨もりえみAIが答えるよ✨"}]
                )
                # メール送信はするが、ユーザー側メールは不要に
                st.session_state.setdefault("mail_sent", False)
                # 登録後に即進める
                st.rerun()
            else:
                st.warning("ニックネームを入れてください。")

    # フォーム表示中はここで停止（未登録時のみ）
    st.stop()


def maybe_send_summary_email(st, *, threshold:int=10):
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