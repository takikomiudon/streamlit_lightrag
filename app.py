import streamlit as st
import numpy as np
import pandas as pd
from PIL import Image
from streamlit_agraph import agraph, Node, Edge, Config
import os 

from src.components import neo4j_settings_container, file_settings_container
from src.nuclear_degradation import LightRAGIndexing


# -----------------------
# 初期設定
# -----------------------
st.set_page_config(
    page_title="KG AIAgent App",
    page_icon=":shark:",
    layout="wide"
)

# カスタムCSSを適用してサイドバーの幅を設定
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        min-width: 300px;
        max-width: 300px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# for key in ["neo4j_uri", "neo4j_user", "neo4j_password", "neo4j_auth"]:
#     if key not in st.session_state:
#         st.session_state[key] = None


# -----------------------
# サイドバー
# -----------------------
with st.sidebar:
    #セッションステートに初期値が設定されていなければ初期化
    if "neo4j_uri" not in st.session_state:
        st.session_state["neo4j_uri"] = "bolt://localhost:7687"
    if "neo4j_user" not in st.session_state:
        st.session_state["neo4j_user"] = "neo4j"
    if "neo4j_password" not in st.session_state:
        st.session_state["neo4j_password"] = ""
    if "openai_api_key" not in st.session_state:
        st.session_state["openai_api_key"] = ""

    # neo4j_settings_container を呼び出して、ユーザーに接続情報の入力を促す
    uri, user, password = neo4j_settings_container(st.session_state["neo4j_uri"], st.session_state["neo4j_user"], st.session_state["neo4j_password"])

    # 入力された値をセッションステートに再保存
    st.session_state["neo4j_uri"] = uri
    st.session_state["neo4j_user"] = user
    st.session_state["neo4j_password"] = password

    # OpenAI API Key の入力欄
    openai_api_key = st.text_input("OpenAI API Key", None, type="password")
    st.session_state["openai_api_key"] = openai_api_key

if button := st.button("ナレッジグラフ作成"):
    st.write("ナレッジグラフを作成します")
    # degradation_typeを選ぶ
    degradation_type = st.selectbox("劣化の種類を選択", ["アルカリ応力腐食割れ", "クリープ亀裂", "脆化"])
    # LightRAG_Indexingクラスの初期化
    # light_rag = LightRAG_Indexing(working_dir="./nuclear", llm_model_func=None, api_key=openai_api_key)


# Chat interface
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "こんにちは！"}]

for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input(placeholder="質問を入力してください"):
    if not openai_api_key:
        st.error("OpenAI API Keyを入力してください")
    else:
        st.session_state["messages"].append({"role": "user", "content": prompt})

        st.chat_message("user").write(prompt)
        

        config = Config(height=600, width=800, directed=True, nodeHighlightBehavior=True, highlightColor="#F7A7A6")
        # Visualization
        #agraph(nodes=nodes, edges=edges, config=config)





