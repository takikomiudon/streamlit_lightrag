import os
import re
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from neo4j import GraphDatabase
from streamlit_agraph import Edge, Node

from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete

load_dotenv()

#########
# Uncomment the below two lines if running in a jupyter notebook to handle the async nature of rag.insert()
# import nest_asyncio
# nest_asyncio.apply()
#########


class LightRAGIndexing:
    def __init__(self, working_dir, llm_model_func):
        """
        LightRAGの初期化
          - working_dir: 作業ディレクトリのパス
            (working_dir以下にinputフォルダを作成し、ドキュメントを格納する)
          - llm_model_func: LLMモデル
        """
        self.working_dir = working_dir
        self.rag = None
        self.llm_model_func = llm_model_func

        self.index_exists = self._check_index_exists()

    def _check_index_exists(self):
        """既存のインデックスファイルが存在するか確認する"""
        required_files = [
            "kv_store_full_docs.json",
            "kv_store_text_chunks.json",
            "graph_chunk_entity_relation.graphml",
            "vdb_entities.json",
            "vdb_relationships.json",
            "vdb_chunks.json"
        ]

        for file in required_files:
            if not os.path.exists(os.path.join(self.working_dir, file)):
                return False
        return True

    def load_documents(self):
        """
        ドキュメントを読み込み、LightRAGに挿入する
          - source_folder: ドキュメントのフォルダパス
        """
        source_folder = os.path.join(self.working_dir, "input")
        for file_name in os.listdir(source_folder):
            with open(os.path.join(source_folder, file_name), encoding="utf-8") as f:
                self.rag.insert(f.read())

    def run(self):
        """
        全体処理を実行する
        既存のインデックスがある場合は再利用し、なければ新規作成する
        """
        self.rag = LightRAG(
            working_dir=self.working_dir, 
            llm_model_func=self.llm_model_func
        )

        if not self.index_exists:
            print(f"Creating new index in {self.working_dir}")
            self.load_documents()
        else:
            print(f"Reusing existing index from {self.working_dir}")


class LightRAGQuery:
    def __init__(self, working_dir, rag, mode="hybrid"):
        """
        LightRAGの初期化
          - working_dir: 作業ディレクトリのパス
          - llm_model_func: LLMモデル
        """
        self.working_dir = working_dir
        self.rag = rag
        self.mode = mode

    def run(self, query, response_type="bullet points"):
        """
        クエリを実行する
          - mode: クエリの実行モード（"naive", "hybrid", "local", "global"）
          - response_type: レスポンスの形式（"bullet points"または"paragraph"）
        """
        output_dir = os.path.join(self.working_dir, self.mode)
        os.makedirs(output_dir, exist_ok=True)

        answer = self.rag.query(
            query,
            param=QueryParam(
                mode=self.mode,
                response_type=response_type,
                working_dir=self.working_dir,
                visualize_query_subgraph=True,  # クエリのサブグラフを可視化 context.gaphmlが出力される
            ),
        )

        with open(
            os.path.join(output_dir, "output.txt"), "w", encoding="utf-8"
        ) as output_file:
            output_file.write(answer)
        with open(
            os.path.join(output_dir, "query.txt"), "w", encoding="utf-8"
        ) as output_file:
            output_file.write(query)

        print(f"結果は '{output_dir}' に保存されました。\n")
        print("output.txtは回答、context.graphmlは回答根拠、query.txtはクエリです。")

        return answer


class VisualizeQuery:
    def __init__(self, working_dir, driver):
        self.working_dir = working_dir
        self.driver = driver
        self.graphml_path = os.path.join(self.working_dir, "output.graphml")
        self.txt_path = os.path.join(self.working_dir, "output.txt")

        # ファイルが存在するか確認
        if not os.path.exists(self.graphml_path):
            raise FileNotFoundError(f"GraphML file not found: {self.graphml_path}")
        if not os.path.exists(self.txt_path):
            raise FileNotFoundError(f"Text file not found: {self.txt_path}")

        # 正しくNeo4jに接続できるか確認
        self.neo4j_connection = False
        with self.driver.session() as session:
            try:
                session.run("MATCH (n) RETURN n LIMIT 1")
                self.neo4j_connection = True
            except Exception as e:
                print(f"Neo4jの接続に失敗しました: {e}")
                self.neo4j_connection = False  # 失敗した場合

    def extract_entity_relationship_ids(self, sentences):
        """
        テキストからエンティティ、リレーションシップ、ソース（文章）ID を抽出する

        :param sentences: 各行が文になっているリスト
        :return: (entity_ids, relationship_ids, sentence_ids) のタプル
        """
        entity_ids = set()
        relationship_ids = set()
        sentence_ids = set()

        for sentence in sentences:
            # エンティティIDの抽出
            if "Entities" in sentence:
                entities_part = sentence.split("Entities")[1].split(";")[0]
                try:
                    # 余分な文字を取り除いた後、数値に変換してセットに追加
                    entity_ids.update(
                        map(
                            int,
                            entities_part.strip(" ()[]").replace(")].", "").split(","),
                        )
                    )
                except ValueError as e:
                    print("Error converting entity IDs to int:", e)

            # リレーションシップIDの抽出
            if "Relationships" in sentence:
                relationships_part = sentence.split("Relationships")[1].split(";")[0]
                try:
                    relationship_ids.update(
                        map(
                            int,
                            relationships_part.strip(" ()[]")
                            .replace(")].", "")
                            .split(","),
                        )
                    )
                except ValueError as e:
                    print("Error converting relationship IDs to int:", e)

            # ソース（文章）IDの抽出
            if "Sources" in sentence:
                sources_match = re.search(r"Sources \((.*?)\)", sentence)
                if sources_match:
                    sentence_id = [
                        "sentence_" + s.strip()
                        for s in sources_match.group(1).split(",")
                    ]
                    sentence_ids.update(sentence_id)

        print("Entity IDs:", entity_ids)
        print("Relationship IDs:", relationship_ids)
        print("Sentence IDs:", sentence_ids)
        return entity_ids, relationship_ids, sentence_ids

    def import_graphml_to_neo4j(self, entity_ids, relationship_ids, sentence_ids):
        """
        GraphML ファイルを解析し、Neo4j にインポートする

        :param entity_ids: 使用するエンティティのID集合
        :param relationship_ids: 使用するリレーションシップのID集合
        :param sentence_ids: 使用するソース（文章）のID集合
        """
        tree = ET.parse(self.graphml_path)
        root = tree.getroot()

        # 名前空間の取得
        namespace = root.tag.split("}")[0].strip("{")
        ns = {"ns": namespace}

        # --- ノードの処理 ---
        with self.driver.session() as session:
            # 既存のすべてのノードとエッジを削除
            session.run("MATCH (n) DETACH DELETE n")

            for node in root.findall(".//ns:node", ns):
                node_id = node.get("id")
                # ノードのプロパティ抽出
                properties = self._extract_properties(node, ns)

                if not node_id.isdigit():
                    # 数値でないノードIDの場合
                    labels = ["Node"]
                    if properties.get("d1") == "text unit" and node_id in sentence_ids:
                        labels.append("UsedLabel")
                    self._create_node(session, node_id, properties, labels)
                else:
                    # ノードIDが数値の場合
                    node_id_int = int(node_id)
                    labels = [
                        "Node",
                        "UsedLabel" if node_id_int in entity_ids else "NotUsedLabel",
                    ]
                    self._create_node(session, node_id_int, properties, labels)

        # --- エッジの処理 ---
        with self.driver.session() as session:
            for edge in root.findall(f".//{{{namespace}}}edge"):
                self._process_edge(session, edge, namespace, relationship_ids)

        print("Nodes and edges imported successfully!")

    def _extract_properties(self, node, ns):
        """
        ノード内の <data> 要素からプロパティを抽出して辞書で返す
        """
        return {
            data.get("key"): data.text.strip('"') if data.text else ""
            for data in node.findall("ns:data", ns)
        }

    def _create_node(self, session, node_id, properties, labels):
        """
        指定されたプロパティとラベルでノードを作成する
        """
        label_string = ":".join(labels)
        if properties:
            property_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
            query = f"CREATE (n:{label_string} {{id: $id, {property_str}}})"
            params = {"id": node_id, **properties}
        else:
            query = "CREATE (n:Node {id: $id})"
            params = {"id": node_id}
        session.run(query, **params)

    def _process_edge(self, session, edge, namespace, relationship_ids):
        """
        エッジ（リレーションシップ）を作成する

        :param session: Neo4jセッション
        :param edge: XML要素 edge
        :param namespace: XML名前空間
        :param relationship_ids: 使用するリレーションシップのID集合
        """
        # エッジのプロパティを抽出
        properties = {
            data.attrib["key"]: data.text.strip('"') if data.text else ""
            for data in edge.findall(f"./{{{namespace}}}data")
        }
        # エッジIDはプロパティ 'd4' から取得（数値の場合のみ）
        edge_id = int(properties["d4"]) if properties.get("d4", "").isdigit() else None
        edge_label = "UsedLabel" if edge_id in relationship_ids else "NotUsedLabel"

        # source と target の取得（数値なら int に変換）
        source = edge.attrib["source"]
        target = edge.attrib["target"]
        source = int(source) if source.isdigit() else source
        target = int(target) if target.isdigit() else target

        query = f"""
            MATCH (source:Node {{id: $source}})
            MATCH (target:Node {{id: $target}})
            MERGE (source)-[r:{edge_label}]->(target)
            SET r += $properties
            """
        session.run(query, source=source, target=target, properties=properties)

    def import_graphml_to_streamlit(self, entity_ids, relationship_ids, sentence_ids):
        """
        GraphML ファイルを解析し、Streamlit にインポートする
        """
        tree = ET.parse(self.graphml_path)
        root = tree.getroot()

        # 名前空間の取得
        namespace = root.tag.split("}")[0].strip("{")
        ns = {"ns": namespace}

        nodes = []
        nodes_name = {}

        for node in root.findall(".//ns:node", ns):
            node_id = node.get("id")
            properties = {}
            properties["id"] = node_id
            for data in node.findall("ns:data", ns):
                key = data.get("key")
                value = data.text.strip('"') if data.text else ""
                properties[key] = value
            nodes.append(properties)

        fixed_nodes = []
        for node in nodes:
            if node["id"].isdigit():
                nodes_name[node["id"]] = value = node["d0"]
            else:
                nodes_name[node["id"]] = value = node["id"]
            if node["id"].isdigit() and int(node["id"]) in entity_ids:
                fixed_nodes.append(
                    Node(id=node["id"], label=node["d0"], shape="circle", color="pink")
                )
            elif node["id"] in sentence_ids:
                fixed_nodes.append(
                    Node(id=node["id"], label=node["id"], shape="circle", color="pink")
                )

        edges = []
        for edge in root.findall(f".//{{{namespace}}}edge"):
            edge_source = edge.attrib["source"]
            edge_target = edge.attrib["target"]
            properties = {}
            properties["source"] = edge_source
            properties["target"] = edge_target
            for data in edge.findall(f"./{{{namespace}}}data"):
                key = data.attrib["key"]
                value = data.text.strip('"') if data.text else ""
                properties[key] = value
            edges.append(properties)

        fixed_edges = []
        for edge in edges:
            if int(edge["d4"]) in relationship_ids:
                source = edge["source"]
                target = edge["target"]
                if source not in [node.id for node in fixed_nodes]:
                    fixed_nodes.append(Node(id=source, label=nodes_name[source]))
                if target not in [node.id for node in fixed_nodes]:
                    fixed_nodes.append(Node(id=target, label=nodes_name[target]))
                fixed_edges.append(Edge(source=edge["source"], target=edge["target"]))

        return fixed_nodes, fixed_edges

    def run(self):
        with open(self.txt_path, "r", encoding="utf-8") as file:
            sentences = file.readlines()
        sentences = [line for line in sentences if line.startswith("-")]

        entity_ids, relationship_ids, sentence_ids = (
            self.extract_entity_relationship_ids(sentences)
        )
        if self.neo4j_connection:
            self.import_graphml_to_neo4j(entity_ids, relationship_ids, sentence_ids)
        nodes, edges = self.import_graphml_to_streamlit(
            entity_ids, relationship_ids, sentence_ids
        )
        self.driver.close()

        return nodes, edges


# テスト
if __name__ == "__main__":
    # データディレクトリの設定
    working_dir = "./src/nuclear/アルカリ応力腐食割れ"
    assert os.path.exists(working_dir), f"Directory not found: {working_dir}"
    assert os.path.exists(
        working_dir + "/input"
    ), f"Directory not found: {working_dir}/input"

    # LightRAGのIndexing
    API_KEY = os.getenv("OPENAI_API_KEY")
    Indexing = LightRAGIndexing(working_dir, gpt_4o_mini_complete)
    # Indexing.run()

    # LightRAGのQuerying
    Query = LightRAGQuery(working_dir, Indexing.rag)
    response = Query.run(
        "Please provide the conditions under which Caustic Stress-Corrosion Cracking (CSCC) occurs."
    )
    # print(response)

    # 可視化
    # Dockerで起動する場合以下を実行
    # start_neo4j_in_browser()
    # Neo4jの設定
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = ""
    driver = GraphDatabase.driver(uri, auth=None)

    # 回答根拠の可視化
    working_dir = os.path.join(working_dir, Query.mode)
    Visualizer = VisualizeQuery(working_dir, driver)
    nodes, edges = Visualizer.run()
