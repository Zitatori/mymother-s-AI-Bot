# app.py — Streamlit × static 画像完全対応版（OpenAIなしでも動く）
import os
import base64
import streamlit as st
from pathlib import Path

# --- OpenAIをオプション扱い ---
try:
    from dotenv import load_dotenv
    from openai import OpenAI
except ImportError:
    OpenAI = None
    load_dotenv = lambda: None

# ===== 基本設定 =====
load_dotenv()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
API_KEY = os.getenv("OPENAI_API_KEY")

# APIキーがなければ None にして「ダミーモード」扱い
client = OpenAI(api_key=API_KEY) if (API_KEY and OpenAI) else None

st.set_page_config(
    page_title="占い×AI 女神メッセージBot by もりえみ",
    page_icon="🧚‍♀️",
    layout="centered"
)
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
                role = obj.get("role"); content = (obj.get("content") or "").strip()
                if role in ("user","assistant") and content:
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
            role = obj.get("role"); content = (obj.get("content") or "").strip()
            if role in ("user","assistant") and content:
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
    os.path.join("static", "titleq.png"),
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

# ===== 女神画像（タイトル上配置版）＋ 吹き出し尻尾 =====
st.markdown("""
<style>
/* --- 女神PNG：タイトルの上側に重ねる --- */
#goddess-ornament {
  position: fixed;
  top: 400px;          
  left: 40px;          
  width: min(35vw, 900px);
  max-width: 900px;
  opacity: 0.95;
  z-index: 4;          
  pointer-events: none;
  filter: drop-shadow(0 12px 40px rgba(120, 90, 160, .18));
}

/* モバイル調整 */
@media (max-width: 640px) {
  #goddess-ornament { top: 76px; left: 12px; width: 58vw; opacity: .9; }
}

/* 吹き出し尻尾 */
.bubble-bot, .bubble-user { position: relative; }
.bubble-bot::after {
  content: "";
  position: absolute;
  left: -8px;
  top: 18px;
  border-width: 8px;
  border-style: solid;
  border-color: transparent #f4dccf transparent transparent;
}
.bubble-bot::before {
  content: "";
  position: absolute;
  left: -6px;
  top: 19px;
  border-width: 7px;
  border-style: solid;
  border-color: transparent #fff9f3 transparent transparent;
}
.bubble-user::after {
  content: "";
  position: absolute;
  right: -8px;
  top: 18px;
  border-width: 8px;
  border-style: solid;
  border-color: transparent transparent transparent #dcd0ff;
}
.bubble-user::before {
  content: "";
  position: absolute;
  right: -6px;
  top: 19px;
  border-width: 7px;
  border-style: solid;
  border-color: transparent transparent transparent #f2eaff;
}
</style>
""", unsafe_allow_html=True)

# ===== 女神画像のbase64埋め込み表示 =====
GODDESS_IMG = find_asset([os.path.join("static", "goddess.png")])
if GODDESS_IMG:
    goddess_b64 = b64(GODDESS_IMG)
    st.markdown(
        f"<img id='goddess-ornament' src='data:image/png;base64,{goddess_b64}' alt='goddess' />",
        unsafe_allow_html=True
    )
else:
    st.warning("⚠️ static/goddess.png が見つかりません。")

# ===== タイトル =====
if TITLE_IMG:
    st.image(TITLE_IMG, use_container_width=True)
else:
    st.markdown(
        "<h2 style='text-align:center;color:#6b4ea1;margin:10px 0 6px;'>占い×AI 女神メッセージBot by もりえみ</h2>",
        unsafe_allow_html=True
    )
st.markdown("<div style='text-align:center;color:#4b306e;'>🪶 女神があなたに今必要なメッセージを届けます 🌙</div>", unsafe_allow_html=True)

# ===== 会話管理 =====
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role":"assistant","content":"どんなことでも相談してみて✨もりえみAIが答えるよ✨"}
    ]

# ===== チャットUI =====
with st.container():
    st.markdown("<div class='glass'>", unsafe_allow_html=True)

    for m in st.session_state.messages:
        if m["role"] == "user":
            st.markdown(f"<div style='text-align:right;'>🧑‍💼<div class='bubble-user'>{m['content']}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div>🧚‍♀️<div class='bubble-bot'>{m['content']}</div></div>", unsafe_allow_html=True)

    prompt = st.chat_input("ここに入力してください…（例：流れを整えたい）")
    if prompt:
        st.session_state.messages.append({"role":"user","content":prompt})

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

        st.session_state.messages.append({"role":"assistant","content":reply})
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
