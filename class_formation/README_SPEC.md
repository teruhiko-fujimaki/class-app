## class_formation — 概要仕様書

以下はリポジトリ内のアプリケーション（学級編成ツール）の解析に基づく概要仕様書です。

## 1. 目的
- CSV で生徒一覧を投入し、クラスを作成→未割当の生徒をドラッグ＆ドロップでクラスに割り当てる学級編成支援ツール。

## 2. 技術スタック
- サーバ: Python + Flask (requirements.txt に `flask==3.0.2`)
- データ処理: pandas (`pandas==2.2.1`)
- DB: SQLite (`database.db`)
- フロントエンド: 単一 HTML (`templates/index.html`) + vanilla JS + CSS (`styles.css`)

## 3. データモデル（SQLite）
- `students`
  - id INTEGER PRIMARY KEY AUTOINCREMENT
  - name TEXT NOT NULL
  - student_id TEXT UNIQUE NOT NULL
  - gender TEXT NOT NULL
- `classes`
  - id INTEGER PRIMARY KEY AUTOINCREMENT
  - name TEXT NOT NULL
  - display_order INTEGER DEFAULT 0
- `student_classes`
  - student_id INTEGER (FK → students.id)
  - class_id INTEGER (FK → classes.id)
  - PRIMARY KEY (student_id, class_id)

※ 運用上は 1 人の生徒が 1 クラスに所属する想定（多対多スキーマだが移動時は既存レコードを削除してから追加）。

## 4. REST API（主要エンドポイント）
- GET / -> `index.html`
- GET /students -> JSON list of students: [{id, name, student_id, gender}, ...]
- GET /classes -> JSON list of classes: [{id, name, students: [{id,name,student_id,gender}, ...]}, ...]
- POST /classes -> body: {name} -> 新規クラスを作成して返却
- POST /move-student -> body: {student_id, class_id} -> student_classes を更新
- POST /remove-student -> body: {student_id, class_id} -> student_classes から削除
- POST /upload -> multipart file (.csv)。必須カラム: name, student_id, gender。gender は M/F → 日本語に正規化。pandas.to_sql により `students` に追加
- POST /reset -> DB 内の students, classes, student_classes を削除
- POST /update-class-order -> body: {order: [class_id,...]} -> display_order を更新

## 5. フロントエンド挙動
- 右列: 未割当生徒一覧（CSV アップロードで追加）
- 左列: クラス一覧（カード）。カード間のドラッグでクラス順を入れ替え可能。
- 生徒カードをクラスカードへドラッグで /move-student 呼び出し。カード内の × で /remove-student。
- 注意点: `createStudentCard` 内の remove-button の onclick に `student.class_id` を参照するコードがあり、未割当の場合は undefined となる可能性がある（軽微なバグ）。

## 6. CSV 仕様
- 必須ヘッダ: `name`, `student_id`, `gender`
- gender の入力許容値: `M`/`m` → 男, `F`/`f` → 女。未正規化の値があるとアップロード失敗。
- 注意: `students.student_id` に UNIQUE 制約があるため重複があると挿入時にエラーになる可能性がある（現行の実装では詳細ハンドリングが限定的）。

## 7. エラー処理と制約
- サーバ側で必要なフィールドチェックはあるが、CSV 挿入時の一意制約違反などの細かな整合性処理は限定的。
- 認証・認可は無し。アクセス制限がないため閉域での利用を推奨。

## 8. 運用と起動手順（最小）
1. Python 環境を用意（推奨: 3.8+）
2. 依存をインストール: `pip install -r requirements.txt`
3. サーバ起動: `python app.py`（開発用: debug=True）
4. ブラウザ: http://127.0.0.1:5000 にアクセス

## 9. セキュリティ／運用上の注意
- 認証がないため運用環境ではアクセス制御を追加すること
- CSV のサイズ上限チェックやチャンク処理を導入してメモリ不足を防ぐこと
- アップロード時の重複 student_id の扱い（スキップ／更新）を明確にすること

## 10. 既知の問題と改善案（優先度付）
- 高優先: CSV アップロードで重複 student_id を適切にハンドルする（現在は to_sql による挿入でエラー）
- 中優先: フロントの remove-btn の onclick 参照バグを修正
- 中優先: ファイルサイズ検査、アップロードの段階的処理、エラーメッセージの行番号化
- 低優先: 認証の追加、操作ログ、単体/統合テストの追加

## 11. テスト提案（最小セット）
- DB 初期化テスト: テーブル作成の確認
- API テスト: /classes POST, /move-student, /upload（正常/異常ケース）
- E2E: CSV アップロード→未割当反映→ドラッグでクラス割当

---

作成: リポジトリ内の解析結果を元に自動生成。

次のアクション候補:
- フロントの軽微バグ修正パッチの追加
- /upload の重複処理実装
- README_SPEC.md の拡張や自動テスト追加
