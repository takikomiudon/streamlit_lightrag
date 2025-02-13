import streamlit as st
import numpy as np
import pandas as pd
from PIL import Image
from lightrag.llm import gpt_4o_mini_complete, gpt_4o_complete
from streamlit_agraph import agraph, Node, Edge, Config
import os 

from src.components import neo4j_settings_container, file_settings_container, start_neo4j_in_browser, end_neo4j_in_browser
from pipeline import LightRAGIndexing, LightRAGQuery, VisualizeQuery
from neo4j import GraphDatabase


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
        st.session_state["openai_api_key"] = "sk-xxxxx"
    if "local" not in st.session_state:
        st.session_state["local"] = False

    # ユーザーにDocker上でNeo4jを起動するかどうかを選択させる
    st.session_state["local"] = st.checkbox("ローカル環境でNeo4jを起動", st.session_state["local"])

    # neo4j_settings_container を呼び出して、ユーザーに接続情報の入力を促す
    if st.session_state["local"] is True:
        uri, user, password  = neo4j_settings_container(st.session_state["neo4j_uri"], st.session_state["neo4j_user"], st.session_state["neo4j_password"])
    
    else:
        # ブラウザでNeo4jを起動する
        start_neo4j_in_browser()
        end_neo4j_in_browser()
        uri, user, password = "bolt://localhost:7687", "neo4j", ""

    # 入力された値をセッションステートに再保存
    st.session_state["neo4j_uri"] = uri
    st.session_state["neo4j_user"] = user
    st.session_state["neo4j_password"] = password

    # OpenAI API Key の入力欄
    if "openai_api_key" not in st.session_state:
        openai_api_key = st.text_input("OpenAI API Key", None, type="password")
        st.session_state["openai_api_key"] = openai_api_key


degradation_type = st.selectbox("劣化の種類を選択", ["アルカリ応力腐食割れ", "クリープ亀裂", "脆化"])
working_dir = f"./src/nuclear/{degradation_type}"
llm = st.selectbox("LLMモデルを選択", ["gpt_4o_mini_complete", "gpt_4o_complete"])
llm_model_mapping = {
    "gpt_4o_mini_complete": gpt_4o_mini_complete,
    "gpt_4o_complete": gpt_4o_complete
}
llm_function = llm_model_mapping.get(llm)  # 関数に変換する

# 入力ファイルが存在するか確認
# Work in progress

if button := st.button("ナレッジグラフ作成"):
    st.write("ナレッジグラフ作成中...")
    st.session_state["Indexing"] = LightRAGIndexing(working_dir, llm_function , st.session_state["openai_api_key"])
    st.session_state["Indexing"].run()
    st.write("ナレッジグラフ作成完了！")


# Chat interface
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "ナレッジグラフから回答を生成します！"}]

for msg in st.session_state["messages"]:
     st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input(placeholder="質問を入力してください"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    # クエリを実行
    Query = LightRAGQuery(working_dir, st.session_state["Indexing"].rag)
    response = Query.run(prompt)
    # アシスタントの回答をセッションに保存
    st.session_state["messages"].append({"role": "assistant", "content": response})
    # アシスタントの回答を表示
    st.chat_message("assistant").write(response)

    # 可視化
    working_dir = os.path.join(working_dir, Query.mode)
    if st.session_state["local"] is False:
        driver = GraphDatabase.driver(
            uri=st.session_state["neo4j_uri"],
            auth=None,
        )
    else:
        driver = GraphDatabase.driver(
            uri=st.session_state["neo4j_uri"],
            auth=(st.session_state["neo4j_user"], st.session_state["neo4j_password"]),
        )
    Visualizer = VisualizeQuery(working_dir, driver)
    Visualizer.run()
    if st.session_state["local"] is False:
        st.write("Neo4j Browser にアクセスする: [http://localhost:7474/browser/](http://localhost:7474/browser/)")








    # st.session_state["messages"].append({"role": "user", "content": prompt})
    # st.chat_message("user").write(prompt)

        

    #config = Config(height=600, width=800, directed=True, nodeHighlightBehavior=True, highlightColor="#F7A7A6")
        # Visualization
        #agraph(nodes=nodes, edges=edges, config=config)





