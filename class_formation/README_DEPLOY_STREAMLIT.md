# Streamlit Cloud へのデプロイ手順（class_formation）

このプロジェクトは Flask 版と Streamlit 版の両方のコードがあります。Streamlit Cloud では `streamlit_app.py` をエントリにして公開します。

## 前提
- GitHub リポジトリに `class_formation` ディレクトリ全体を push 済み
- Streamlit Community Cloud アカウント作成済み: https://streamlit.io/cloud

## 依存関係
`requirements.txt` に `streamlit`, `pandas` が含まれています（追加済み）。

## 起動エントリ
- `streamlit_app.py`

## ローカル動作確認（任意）
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## デプロイ手順
1. GitHub に本リポジトリを push（または最新化）
2. https://streamlit.io/cloud にアクセスし「New app」をクリック
3. Repository: 対象のリポジトリを選択
4. Branch: 公開したいブランチ（例: `main`）
5. Main file path: `streamlit_app.py`
6. Deploy を実行

初回起動時に `database.db` が作成され、画面上でCSVをアップロードして学級編成を操作できます（ファイルは環境内に保存されます）。

## 注意事項
- Streamlit Cloud のファイルシステムは永続ではありません。データ永続化が必要な場合は、外部DB（例: Cloud SQLite/Firestore/Postgres）や `st.secrets` を用いた接続設定をご検討ください。
- ドラッグ＆ドロップUIはStreamlit標準では難しいため、Streamlit版ではボタン/セレクトで割当・並び替えを操作できる形にしています。
- CSVの列は `name, student_id, gender`。genderは `M/F` または `男/女` を受け付けます。

