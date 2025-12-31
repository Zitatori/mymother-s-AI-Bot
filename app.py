# app.py — Streamlit × static 画像完全対応版（OpenAIなしでも動く）
import os
import base64
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import time
from summary_mailer import ensure_registration, render_booking_cta_persistent


# --- OpenAIをオプション扱い ---
try:
    from dotenv import load_dotenv
    from openai import OpenAI
except ImportError:
    OpenAI = None
    load_dotenv = lambda: None



# --- 無操作タイムスタンプを初期化 ---
if "last_activity_ts" not in st.session_state:
    st.session_state["last_activity_ts"] = time.time()

def touch():#なんかこれがないとチャットが動かない
    """ユーザー操作があった瞬間に呼んで、最終操作時刻を更新"""
    st.session_state["last_activity_ts"] = time.time()

# ===== 基本設定 =====
load_dotenv()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

# APIキーがなければ None にして「ダミーモード」扱い
client = OpenAI(api_key=API_KEY) if (API_KEY and OpenAI) else None

st.set_page_config(
    page_title="占い×AI 女神メッセージBot by もりえみ",
    page_icon="🧚‍♀️",
    layout="centered"
)
# --- 離脱合図を受け取ったら要約メール送信 ---
params = getattr(st, "query_params", None)
if params is None:
    params = st.experimental_get_query_params()



ensure_registration(st)  # ← 未登録ならフォームを出して停止



# ===== 外部スタイル & few-shot ローダ（追加） =====

APP_DIR = Path(__file__).parent


def _pick_first_exist(cands):
    for p in cands:
        p = APP_DIR / p
        if p.exists():
            return p
    return None


def load_style():
    # ファイル名ゆらぎ対応（半角/全角/先頭アンダーバー）
    path = _pick_first_exist(["style_mother.txt", "_style_mother.txt", "＿style_mother.txt"])
    if not path:
        return ""  # 無くても動く
    return path.read_text(encoding="utf-8").strip()


def load_fewshot():
    import json
    shots = []
    path = _pick_first_exist(["examples_mother.jsonl", "example_mother.jsonl"])
    if not path:
        return shots

    buf = path.read_text(encoding="utf-8").strip()
    # 誤って配列JSONで保存しても読めるように
    if buf.startswith("["):
        try:
            arr = json.loads(buf)
            for obj in arr:
                role = obj.get("role");
                content = (obj.get("content") or "").strip()
                if role in ("user", "assistant") and content:
                    shots.append({"role": role, "content": content})
        except Exception as e:
            st.warning(f"{path.name} の解析に失敗: {e}")
        return shots

    # 正式: JSONL（1行=1JSON）
    for lineno, line in enumerate(buf.splitlines(), 1):
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
            role = obj.get("role");
            content = (obj.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                shots.append({"role": role, "content": content})
            else:
                st.warning(f"{path.name}:{lineno} 不正（role/content）→スキップ")
        except Exception as e:
            st.error(f"{path.name}:{lineno} JSONエラー: {e}")
    return shots


# ===== ファイル探索 & base64 =====
def find_asset(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# タイトル画像優先順
TITLE_IMG = find_asset([
    os.path.join("static", "title2.png"),
    os.path.join("static", "title1.png"),
    os.path.join("static", "title.png"),
])

# 背景画像
BG_IMG = find_asset([os.path.join("static", "bg.png")])


# ===== 背景CSS =====
def apply_background():
    bg_css = ""
    if BG_IMG:
        bg_css = f"background-image: url('data:image/png;base64,{b64(BG_IMG)}');"
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            {bg_css}
            background-size: cover;
            background-position: center top;
            background-attachment: fixed;
        }}
        [data-testid="stHeader"] {{ background: transparent; }}
        footer {{ visibility: hidden; }}

        /* 入力欄デザイン */
        .stChatInput > div {{
            background: rgba(255,255,255,0.85) !important;
            border: 1px solid #e3d4ff !important;
            border-radius: 14px !important;
        }}
        .stChatInput textarea {{
            background: transparent !important;
            color: #3b2a57 !important;
        }}
        .stChatInput textarea::placeholder {{
            color: #856fa5 !important;
        }}


        button[kind="primary"] {{
            background: linear-gradient(90deg, #d9c3ff, #ffe99b) !important;
            color: #3b2a57 !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }}

        /* 吹き出し */
        .bubble-user {{
            text-align:right;
            background:#f2eaff;
            border:1px solid #dcd0ff;
            border-radius:12px;
            padding:10px 14px;
            margin:8px 0;
            display:inline-block;
            color:#45335a;
        }}
        .bubble-bot {{
            text-align:left;
            background:#fff9f3;
            border:1px solid #f4dccf;
            border-radius:12px;
            padding:10px 14px;
            margin:8px 0;
            display:inline-block;
        }}
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

# ===== 追加のスタイル（明るい入力欄や全体トーン） =====
st.markdown("""
<style>
[data-testid="stAppViewContainer"] * {
  color: #2f2447 !important;
}
.stImage img {
  border-radius: 18px !important;
  box-shadow: 0 12px 40px rgba(120, 90, 160, 0.18) !important;
  position: relative;
  z-index: 3;
}
.bubble-bot {
  background: rgba(255, 249, 243, 0.95) !important;
  border: 1px solid #f0d8c9 !important;
  color: #2f2447 !important;
}
.bubble-user {
  background: rgba(242, 234, 255, 0.96) !important;
  border: 1px solid #d6c8ff !important;
  color: #2f2447 !important;
}
[data-testid="stBottomBlockContainer"] {
  background: transparent !important;
  padding-bottom: 12px !important;
}
.stChatInput > div {
  background: rgba(255,255,255,0.95) !important;
  border: 1px solid #e3d4ff !important;
  border-radius: 14px !important;
  box-shadow: 0 6px 22px rgba(110, 80, 160, 0.12) !important;
}
/* ===== 入力欄の文字を明るくして見えるように ===== */
.stChatInput textarea,
.stChatInput [contenteditable="true"],
div[data-baseweb="textarea"] textarea {
  color: #2f2447 !important;          /* PCの暗背景でも読める濃い紫グレー */
  caret-color: #2f2447 !important;
  background: rgba(255,255,255,0.85) !important;  /* 半透明の白背景を常に敷く */
  font-size: 16px !important;
  font-weight: 500 !important;
  border-radius: 10px !important;
}


/* プレースホルダー（入力前の薄文字） */
.stChatInput textarea::placeholder {
  color: #e5d8ff !important;        /* 淡い紫 */
  opacity: 0.9 !important;
}

.stChatInput, .stChatInput > div,
.bubble-user, .bubble-bot, .glass {
  position: relative !important;
  z-index: 10 !important;  /* 女神(4)より上 */
}

.glass {
  background: rgba(255,255,255,0.78) !important;
}
</style>
""", unsafe_allow_html=True)



# ===== タイトル =====
if TITLE_IMG:
    st.image(TITLE_IMG, use_container_width=True)
else:
    st.markdown(
        "<h2 style='text-align:center;color:#6b4ea1;margin:10px 0 6px;'>占い×AI 女神メッセージBot by もりえみ</h2>",
        unsafe_allow_html=True
    )
st.markdown("<div style='text-align:center;color:#4b306e;'>🪶 あなたに今必要なメッセージを届けます 🌙</div>",
            unsafe_allow_html=True)

# ===== 会話管理 =====
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "どんなことでも相談してみて✨もりえみAIが答えるよ✨"}
    ]

# ===== チャットUI =====
with st.container():

    for m in st.session_state.messages:
        if m["role"] == "user":
            st.markdown(f"<div style='text-align:right;'>🧑‍💼<div class='bubble-user'>{m['content']}</div></div>",
                        unsafe_allow_html=True)
        else:
            st.markdown(f"<div>🧚‍♀️<div class='bubble-bot'>{m['content']}</div></div>", unsafe_allow_html=True)

    render_booking_cta_persistent(st, threshold=10, embed_iframe=False, place="main")

    prompt = st.chat_input("ここに入力してください…（例：流れを整えたい）", key="main_chat_input")
    if prompt:
        touch()
        st.session_state.messages.append({"role": "user", "content": prompt})

        if client is None:
            reply = "（デモ応答）運命はいつでもあなたの味方です🌙 小さな喜びを選ぶと、流れは自然と整っていきます。"
        else:
            try:
                # --- ここに追加 ---
                STYLE_FILE = "style_mother.txt"
                if os.path.exists(STYLE_FILE):
                    with open(STYLE_FILE, "r", encoding="utf-8") as f:
                        style_prompt = f.read().strip()
                else:
                    style_prompt = "あなたは優しく包み込むように話すAIです。"

                # --- 既存のここを置き換える ---
                msgs = [{"role": "system", "content": style_prompt}] + st.session_state.messages

                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=msgs,
                    temperature=0.7,
                )
                reply = resp.choices[0].message.content.strip()
            except Exception as e:
                reply = f"⚠️ AI応答エラー：{e}"

        st.session_state.messages.append({"role": "assistant", "content": reply})
        # ✅ 要約→Supabase保存（必ずこの位置）
        from summary_mailer import summarize_and_store

        nickname = st.session_state.get("nickname") or st.session_state.get("user_id") or ""
        turns = sum(1 for m in st.session_state.messages if m["role"] == "user")
        summary = summarize_and_store(st.session_state.messages, nickname, turns)

        # デバッグ：保存が呼ばれたことを画面に小さく出す

        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
BOOKING_URL = os.getenv("BOOKING_URL")

# 画像をbase64で埋め込む
img_path = Path("static/reservation.png")
with open(img_path, "rb") as f:
    img_data = f.read()
img_base64 = base64.b64encode(img_data).decode()

# クリックでURLを開くHTML生成
st.markdown(
    f"""
    <style>
    .clickable {{
        transition: transform 0.2s;
    }}
    .clickable:hover {{
        transform: scale(1.05);
    }}
    </style>

    <a href="{BOOKING_URL}" target="_blank">
        <img class="clickable" src="data:image/png;base64,{img_base64}" width="300" style="cursor: pointer; border-radius: 12px;">
    </a>
    """,
    unsafe_allow_html=True
)


