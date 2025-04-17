import os

import streamlit as st
from dotenv import load_dotenv
from neo4j import GraphDatabase
from streamlit_agraph import Config, agraph

from lightrag.llm import gpt_4o_complete, gpt_4o_mini_complete
from src.components import (
    end_neo4j_in_browser,
    neo4j_settings_container,
    start_neo4j_in_browser,
)
from src.pipeline import LightRAGIndexing, LightRAGQuery, VisualizeQuery

load_dotenv()

# -----------------------
# 初期設定
# -----------------------
st.set_page_config(page_title="KG AIAgent App", page_icon=":shark:", layout="wide")

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
    unsafe_allow_html=True,
)


# for key in ["neo4j_uri", "neo4j_user", "neo4j_password", "neo4j_auth"]:
#     if key not in st.session_state:
#         st.session_state[key] = None


# -----------------------
# サイドバー
# -----------------------
with st.sidebar:
    # セッションステートに初期値が設定されていなければ初期化
    if "neo4j_uri" not in st.session_state:
        st.session_state["neo4j_uri"] = "bolt://localhost:7687"
    if "neo4j_user" not in st.session_state:
        st.session_state["neo4j_user"] = "neo4j"
    if "neo4j_password" not in st.session_state:
        st.session_state["neo4j_password"] = ""
    if "local" not in st.session_state:
        st.session_state["local"] = False
    if "index_created" not in st.session_state:
        st.session_state["index_created"] = False
    if "current_degradation_type" not in st.session_state:
        st.session_state["current_degradation_type"] = ""
    if "current_llm" not in st.session_state:
        st.session_state["current_llm"] = ""

    # ユーザーにDocker上でNeo4jを起動するかどうかを選択させる
    st.session_state["local"] = st.checkbox(
        "ローカル環境でNeo4jを起動", st.session_state["local"]
    )

    # neo4j_settings_container を呼び出して、ユーザーに接続情報の入力を促す
    if st.session_state["local"] is True:
        uri, user, password = neo4j_settings_container(
            st.session_state["neo4j_uri"],
            st.session_state["neo4j_user"],
            st.session_state["neo4j_password"],
        )

    else:
        # ブラウザでNeo4jを起動する
        start_neo4j_in_browser()
        end_neo4j_in_browser()
        uri, user, password = "bolt://localhost:7687", "neo4j", ""

    # 入力された値をセッションステートに再保存
    st.session_state["neo4j_uri"] = uri
    st.session_state["neo4j_user"] = user
    st.session_state["neo4j_password"] = password


nuclear_dir = "./src/nuclear"
degradation_types = [
    d for d in os.listdir(nuclear_dir)
    if os.path.isdir(os.path.join(nuclear_dir, d))
]


degradation_type = st.selectbox(
    "劣化の種類を選択", degradation_types
)
working_dir = f"./src/nuclear/{degradation_type}"
llm = st.selectbox("LLMモデルを選択", ["gpt_4o_mini_complete", "gpt_4o_complete"])
llm_model_mapping = {
    "gpt_4o_mini_complete": gpt_4o_mini_complete,
    "gpt_4o_complete": gpt_4o_complete,
}
llm_function = llm_model_mapping.get(llm)  # 関数に変換する

current_type = st.session_state["current_degradation_type"]
is_degradation_type_changed = degradation_type != current_type
is_llm_changed = llm != st.session_state["current_llm"]
if is_degradation_type_changed or is_llm_changed:
    st.session_state["index_created"] = False
    st.session_state["current_degradation_type"] = degradation_type
    st.session_state["current_llm"] = llm


# Chat interface
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "ナレッジグラフから回答を生成します！質問を入力してください。"}
    ]

for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input(placeholder="質問を入力してください"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    if "Indexing" not in st.session_state or not st.session_state["index_created"]:
        with st.spinner("ナレッジグラフを確認中..."):
            st.session_state["Indexing"] = LightRAGIndexing(
                working_dir, llm_function
            )

            if st.session_state["Indexing"].index_exists:
                st.info("既存のナレッジグラフを再利用します")
            else:
                st.info("新しいナレッジグラフを作成します")

            st.session_state["Indexing"].run()
            st.session_state["index_created"] = True

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
    nodes, edges = Visualizer.run()
    if not st.session_state["local"] and Visualizer.neo4j_connection:
        st.write(
            "Neo4j Browser にアクセスする: "
            "[http://localhost:7474/browser/](http://localhost:7474/browser/)"
        )

    config = Config(
        height=600,
        width=1000,
        directed=True,
        nodeHighlightBehavior=False,
        highlightColor="#F7A7A6",
    )
    agraph(nodes, edges, config=config)
