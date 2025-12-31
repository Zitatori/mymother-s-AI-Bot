# 占い × AI「女神メッセージBot」Web版MVP（Flask）

白×ラベンダー×金の雰囲気で、**10往復で静かに予約に誘導する**Webチャットの最小実装。  
*本番はLINE移植を推奨。まずは会話体験を磨く用のMVPです。*

## ✨ 機能
- もりえみ風の口調（システムプロンプト）
- ユーザーごとに会話履歴を保存（SQLite）
- **10ラリー**で「予約へ」ボタンを表示
- リセットで会話を最初からやり直し

## 🌼 プレビュー

| UIイメージ |
|:--:|
| ![App Screenshot](emi1.png) |

> 🎨 テーマカラー：白 × ラベンダー × 金  
> 花モチーフ（ピオニー・桜・胡蝶蘭）をイメージ。

---

## 🧰 セットアップ
```bash
# 1) 環境準備
python -m venv .venv
source .venv/bin/activate  # Windowsは .venv\Scripts\activate

# 2) 依存ライブラリ
pip install -r requirements.txt

# 3) 設定
cp .env .env  # エディタで OPENAI_API_KEY を設定
# PowerShellなどで: copy .env .env

# 4) 起動
export $(grep -v '^#' .env | xargs)  # Windowsは set コマンドで環境変数を設定
python app.py
# ブラウザで http://localhost:8000 を開く
```

> Windowsで `.env` を読み込むのが面倒なら、`OPENAI_API_KEY` だけ一旦コマンドで設定してもOKです。

## 🧠 カスタマイズ
- **SYSTEM_PROMPT**：`app.py` の `SYSTEM_PROMPT` を編集して口調を微調整
- **MAX_TURNS**： `.env` の `MAX_TURNS` を変更（既定10）
- **RESERVATION_URL**： 予約リンクを差し替え

## 🚀 次のステップ（LINE移植）
- `Flask` の `/api/chat` ロジックをそのまま流用し、`line-bot-sdk-python` で Webhook を受ける構成に。  
- 10ラリーで同じメッセージ＋予約リンクを返せばOK。

---

作成者: あなた（提案者）
