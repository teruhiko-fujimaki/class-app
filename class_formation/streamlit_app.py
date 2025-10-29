import sqlite3
from contextlib import closing
from typing import Iterable

import pandas as pd
import streamlit as st


DB_PATH = "database.db"


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                student_id TEXT UNIQUE NOT NULL,
                gender TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                display_order INTEGER DEFAULT 0
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS student_classes (
                student_id INTEGER,
                class_id INTEGER,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (class_id) REFERENCES classes (id),
                PRIMARY KEY (student_id, class_id)
            )
            """
        )
        conn.commit()


def read_csv_fallback(file, encodings: Iterable[str] = ("utf-8-sig", "utf-8", "cp932")) -> pd.DataFrame:
    last = None
    for enc in encodings:
        try:
            if hasattr(file, "seek"):
                try:
                    file.seek(0)
                except Exception:
                    pass
            return pd.read_csv(file, encoding=enc)
        except UnicodeDecodeError as e:
            last = e
    if last:
        raise last
    raise ValueError("CSV読み込みに失敗しました")


def load_students() -> pd.DataFrame:
    with closing(get_conn()) as conn:
        return pd.read_sql_query("SELECT id, name, student_id, gender FROM students", conn)


def load_classes() -> list[dict]:
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT c.id, c.name, s.id, s.name, s.student_id, s.gender
            FROM classes c
            LEFT JOIN student_classes sc ON c.id = sc.class_id
            LEFT JOIN students s ON sc.student_id = s.id
            ORDER BY c.display_order
            """
        )
        classes: dict[int, dict] = {}
        for row in c.fetchall():
            class_id, class_name, student_id, student_name, student_number, gender = row
            if class_id not in classes:
                classes[class_id] = {"id": class_id, "name": class_name, "students": []}
            if student_id is not None:
                classes[class_id]["students"].append(
                    {"id": student_id, "name": student_name, "student_id": student_number, "gender": gender}
                )
        return list(classes.values())


def add_class(name: str) -> dict:
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO classes (name) VALUES (?)", (name,))
        class_id = c.lastrowid
        conn.commit()
        return {"id": class_id, "name": name, "students": []}


def move_student(student_id: int, class_id: int):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM student_classes WHERE student_id = ?", (student_id,))
        c.execute("INSERT OR REPLACE INTO student_classes (student_id, class_id) VALUES (?, ?)", (student_id, class_id))
        conn.commit()


def remove_student(student_id: int, class_id: int):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM student_classes WHERE student_id = ? AND class_id = ?", (student_id, class_id))
        conn.commit()


def update_class_order(order: list[int]):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        for idx, cid in enumerate(order):
            c.execute("UPDATE classes SET display_order = ? WHERE id = ?", (idx, cid))
        conn.commit()


def reset_all():
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM student_classes")
        c.execute("DELETE FROM students")
        c.execute("DELETE FROM classes")
        conn.commit()


def upsert_students_from_df(df: pd.DataFrame) -> tuple[int, int]:
    if not all(col in df.columns for col in ["name", "student_id", "gender"]):
        raise ValueError("CSVには name, student_id, gender の列が必要です")

    # 正規化（性別）
    df = df.copy()
    df["gender"] = df["gender"].map({"M": "男", "m": "男", "F": "女", "f": "女"}).fillna(df["gender"])
    valid = {"男", "女"}
    if not set(df["gender"].unique()).issubset(valid):
        raise ValueError("gender は M/F または 男/女 を使用してください")

    with closing(get_conn()) as conn:
        cur = conn.cursor()
        # 既存の student_id を取得
        cur.execute("SELECT student_id FROM students")
        existing = {row[0] for row in cur.fetchall()}
        new_df = df[~df["student_id"].astype(str).isin(existing)].copy()
        inserted = 0
        if not new_df.empty:
            new_df.to_sql("students", conn, if_exists="append", index=False)
            inserted = len(new_df)
        skipped = len(df) - inserted
        return inserted, skipped


def render_ui():
    st.set_page_config(page_title="学級編成ツール (Streamlit)", layout="wide")
    st.title("学級編成ツール")
    st.caption("CSVアップロード → 学級作成 → 生徒の割当/除外。学級の順序変更も可能。")

    col_left, col_right = st.columns([2, 1])

    # 右: CSVとリセット
    with col_right:
        st.subheader("未割当 生徒一覧 / CSV")
        up = st.file_uploader("CSVを選択 (name, student_id, gender)", type=["csv"])
        if st.button("アップロード", use_container_width=True, type="primary"):
            if up is None:
                st.warning("CSVファイルを選択してください")
            else:
                try:
                    df = read_csv_fallback(up)
                    ins, skip = upsert_students_from_df(df)
                    st.success(f"取り込み: {ins} 件、スキップ: {skip} 件")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        if st.button("全データをリセット", use_container_width=True):
            reset_all()
            st.success("初期化しました")
            st.rerun()

    # 左: 学級・生徒
    with col_left:
        st.subheader("学級一覧")
        # 次回リラン前にテキスト入力をクリアするためのフラグ処理
        if st.session_state.get("clear_new_class"):
            st.session_state["clear_new_class"] = False
            st.session_state["new_class"] = ""
        new_name = st.text_input("学級名（例: 1年A組）", key="new_class")
        if st.button("学級を追加"):
            if new_name.strip():
                add_class(new_name.strip())
                # 即時に値を書き換えるとエラーになるため、フラグで次回リラン時にクリア
                st.session_state["clear_new_class"] = True
                st.rerun()

    # データ読み込み
    classes = load_classes()
    students_df = load_students()

    # 未割当計算
    assigned_ids = {s["id"] for c in classes for s in c.get("students", [])}
    unassigned_df = students_df[~students_df["id"].isin(assigned_ids)].copy()

    # 左: 学級描画（並べ替え、割当/除外）
    with col_left:
        order_ids = [c["id"] for c in classes]
        for c in classes:
            with st.expander(f"{c['name']} (人数: {len(c.get('students', []))})", expanded=True):
                # 並び順調整
                idx = order_ids.index(c["id"]) if c["id"] in order_ids else -1
                cols = st.columns(3)
                with cols[0]:
                    if st.button("▲", key=f"up_{c['id']}") and idx > 0:
                        order_ids[idx - 1], order_ids[idx] = order_ids[idx], order_ids[idx - 1]
                        update_class_order(order_ids)
                        st.rerun()
                with cols[1]:
                    if st.button("▼", key=f"down_{c['id']}") and idx < len(order_ids) - 1:
                        order_ids[idx + 1], order_ids[idx] = order_ids[idx], order_ids[idx + 1]
                        update_class_order(order_ids)
                        st.rerun()

                # 生徒一覧（除外ボタン）
                for s in c.get("students", []):
                    scols = st.columns([3, 2, 1])
                    scols[0].markdown(f"**{s['name']}**  ")
                    scols[1].write(f"{s['gender']} / {s['student_id']}")
                    if scols[2].button("外す", key=f"rm_{c['id']}_{s['id']}"):
                        remove_student(s["id"], c["id"])
                        st.rerun()

                # 未割当からこの学級に追加
                if not unassigned_df.empty:
                    choices = {f"{r.name} ({r.gender}/{r.student_id})": int(r.id) for r in unassigned_df.itertuples()}
                    selected = st.selectbox("未割当から追加", options=["-- 選択 --", *choices.keys()], key=f"sel_{c['id']}")
                    if st.button("追加", key=f"add_{c['id']}"):
                        if selected and selected != "-- 選択 --":
                            move_student(choices[selected], c["id"])
                            st.rerun()

    # 右: 未割当一覧（簡易表示）
    with col_right:
        st.markdown("---")
        st.write(f"未割当: {len(unassigned_df)} 名")
        if not unassigned_df.empty:
            st.dataframe(unassigned_df[["name", "gender", "student_id"]], use_container_width=True, hide_index=True)


def main():
    init_db()
    render_ui()


if __name__ == "__main__":
    main()
