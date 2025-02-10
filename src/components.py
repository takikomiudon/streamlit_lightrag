""" コンポーネントを定義するモジュール"""

import streamlit as st
from typing import Optional
from neo4j import GraphDatabase
from pathlib import Path



def neo4j_settings_container(
        uri_value: Optional[str] = None,
        user_value: Optional[str] = None,
        password_value: Optional[str] = None,
) -> tuple[str, str, str]:
    """Neo4j 接続設定のコンテナを表示"""
    with st.expander("Neo4j 接続設定", expanded=True):
        uri = st.text_input("URI", uri_value, placeholder="bolt://localhost:7687")
        user = st.text_input("ユーザー名", user_value, placeholder="neo4j")
        password = st.text_input("パスワード", password_value, type="password", placeholder="password")
        if st.button("接続"):
            with GraphDatabase.driver(
                uri=uri,
                auth=(user, password),
            ) as driver:
                try:
                    driver.verify_connectivity()
                    st.success("接続に成功しました")
                except Exception as e:
                    st.error(f"接続に失敗しました: {e}")
    return uri, user, password


def file_settings_container(
    data_dir_value: str,
    output_dir_value: str,
) -> tuple[str, str]:
    """入出力ファイルの設定と確認.
    Parameters
    ----------
    data_dir : str, optional
        データディレクトリのデフォルト値, by default None
    output_dir : str, optional
        出力ディレクトリのデフォルト値, by default None

    Returns
    -------
    Path
        データディレクトリ.
    list[Path]
        PDFファイルのリスト.
    Path
        出力ディレクトリ.

    """
    with st.expander("入出力ファイルの設定", expanded=False):
        data_dir = st.text_input(
            label="データディレクトリ", 
            value=data_dir_value,
            placeholder="/path/to/txt_files",
            help="inputフォルダが格納されたディレクトリを指定してください"    
        )

        output_dir = st.text_input("出力ディレクトリ", output_dir_value)

        st.write(f"データディレクトリ: {data_dir}")
        st.write(f"出力ディレクトリ: {output_dir}")

        data_dir = Path(data_dir)

        txts = Path(data_dir).glob("*.txt")
        if len(list(txts)) > 0:
            st.success("有効なフォルダが指定されました")
        else:
            st.error("無効なフォルダ")

        
        # 出力ディレクトリ
        output_dir = st.text_input(
            label="出力ディレクトリ",
            value=output_dir_value,
            placeholder="/path/to/output",
            help="中間ファイルや最終的な結果ファイルを出力するフォルダを指定してください",
        )
        output_dir = Path(output_dir)
        if output_dir.exists():
            st.success("有効なフォルダ")
        else:
            st.error("無効なフォルダ")

    return data_dir, output_dir


        
if __name__ == "__main__":
    neo4j_settings_container("bolt://localhost:7687", "neo4j", "password")