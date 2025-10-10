# app.py — Streamlit × static 画像完全対応版
import os, base64
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ===== 基本設定 =====
load_dotenv()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
API_KEY = os.getenv("OPENAI_API_KEY")

# API未設定でもUI確認できるように
client = OpenAI(api_key=API_KEY) if API_KEY else None

st.set_page_config(
    page_title="占い×AI 女神メッセージBot by もりえみ",
    page_icon="🧚‍♀️",
    layout="centered"
)

# ===== 画像ローダ（static優先・複数ファイル名に対応） =====
def find_asset(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# タイトル画像優先順（ご指定の titleq.png / title1.png / title.png）
TITLE_IMG = find_asset([
    os.path.join("static", "titleq.png"),
    os.path.join("static", "title1.png"),
    os.path.join("static", "title.png"),
])

# 背景画像
BG_IMG = find_asset([os.path.join("static", "bg.png")])

# ===== 背景CSS（Streamlitの正しいターゲットに適用） =====
def apply_background():
    bg_css = ""
    if BG_IMG:
        bg_css = f"background-image: url('data:image/png;base64,{b64(BG_IMG)}');"  # base64埋め込みで確実反映
    st.markdown(
        f"""
        <style>
        /* アプリ全体の背景（body ではなく AppViewContainer を狙うのがコツ） */
        [data-testid="stAppViewContainer"] {{
            {bg_css}
            background-size: cover;
            background-position: center top;
            background-attachment: fixed;
        }}
        /* ヘッダーを透明に */
        [data-testid="stHeader"] {{ background: transparent; }}
        /* サイドバーがある場合も馴染ませる */
        section[data-testid="stSidebar"] > div {{
            background: rgba(255,255,255,0.65);
            backdrop-filter: blur(8px);
        }}

        /* ===== 入力欄が黒くならないよう強制上書き ===== */
        :root {{
            --ink: #3b2a57;
            --soft-bg: rgba(255,255,255,0.88);
            --soft-border: #e6d7ff;
        }}
        /* 入力ボックスの外枠 */
        .stChatInput > div {{
            background: var(--soft-bg) !important;
            border: 1px solid var(--soft-border) !important;
            border-radius: 14px !important;
            box-shadow: 0 4px 16px rgba(107,78,161,0.08) !important;
        }}
        /* 実際のテキストエリア（複数パターンに対応） */
        .stChatInput textarea,
        .stChatInput [contenteditable="true"],
        div[data-baseweb="textarea"] textarea {{
            background: transparent !important;
            color: var(--ink) !important;
            caret-color: var(--ink) !important;
        }}
        .stChatInput textarea::placeholder {{
            color: #7b669b !important;
            opacity: .8 !important;
        }}
        /* 送信ボタン */
        button[kind="primary"] {{
            background: linear-gradient(90deg, #d9c3ff, #ffe99b) !important;
            color: var(--ink) !important;
            font-weight: 700 !important;
            border: 1px solid var(--soft-border) !important;
            border-radius: 12px !important;
        }}
        button[kind="primary"]:hover {{
            transform: translateY(-1px) scale(1.02);
            box-shadow: 0 0 10px rgba(200,170,255,.45);
        }}

        /* 吹き出し */
        .bubble-user {{
            text-align:right;
            background:#f2eaff;
            border:1px solid #dcd0ff;
            border-radius:12px; padding:10px 14px; margin:8px 0; display:inline-block;
            color:#45335a;
        }}
        .bubble-bot {{
            text-align:left;
            background:#fff9f3;
            border:1px solid #f4dccf;
            border-radius:12px; padding:10px 14px; margin:8px 0; display:inline-block;
        }}

        /* 中央カードの半透明オーバーレイ */
        .glass {{
            background: rgba(255,255,255,0.65);
            backdrop-filter: blur(8px);
            border-radius: 20px;
            box-shadow: 0 8px 30px rgba(160,130,255,.18);
            padding: 14px 18px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

apply_background()

# ===== タイトル（画像優先、なければテキスト） =====
if TITLE_IMG:
    st.image(TITLE_IMG, use_container_width=True)
else:
    st.markdown(
        "<h2 style='text-align:center;color:#6b4ea1;margin:10px 0 6px;'>占い×AI 女神メッセージBot by もりえみ</h2>",
        unsafe_allow_html=True
    )
st.markdown("<div style='text-align:center;color:#4b306e;'>🪶 女神があなたに今必要なメッセージを届けます 🌙</div>", unsafe_allow_html=True)

# ===== 会話セッション =====
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role":"assistant","content":"いま、少し切り替え期のエネルギーを感じます🌙 最近いちばん気になっているテーマは何ですか？（恋愛・仕事・お金など）"}
    ]
if "turn" not in st.session_state:
    st.session_state.turn = 0

# 中央にガラス風カードを作ってチャットを載せる
with st.container():
    st.markdown("<div class='glass'>", unsafe_allow_html=True)

    # 履歴表示（アバター感は絵文字で）
    for m in st.session_state.messages:
        if m["role"] == "user":
            st.markdown(f"<div style='text-align:right;'>🧑‍💼<div class='bubble-user'>{m['content']}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div>🧚‍♀️<div class='bubble-bot'>{m['content']}</div></div>", unsafe_allow_html=True)

    # 入力
    prompt = st.chat_input("ここに入力してください…（例：仕事の流れを整えたい）")
    if prompt:
        st.session_state.messages.append({"role":"user","content":prompt})
        st.session_state.turn += 1

        # OpenAI呼び出し（未設定ならデモ文）
        if client is None:
            reply = "（デモ応答）テーマは“自己価値の整え直し”。今週できる小さな一歩を一つだけ挙げてみてください🌙"
        else:
            try:
                msgs = [{"role":"system","content":
                         "あなたは『もりえみ』の世界観で話すAIです。やわらかく、断定しすぎず、気づきを促す。医療/法律の断言、恐怖訴求、過度な金銭約束は禁止。各返信は120字前後、絵文字は1つまで、最後に短い質問を1つ。"}] + st.session_state.messages
                resp = client.chat.completions.create(model=MODEL, messages=msgs, temperature=0.7)
                reply = resp.choices[0].message.content.strip()
            except Exception as e:
                reply = f"⚠️ AI応答でエラー：{e}"

        st.session_state.messages.append({"role":"assistant","content":reply})
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
