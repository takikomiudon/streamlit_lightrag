import os
from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete
from datetime import datetime
from components import neo4j_settings_container, file_settings_container, start_neo4j_in_browser
from neo4j import GraphDatabase
import xml.etree.ElementTree as ET
import re



#########
# Uncomment the below two lines if running in a jupyter notebook to handle the async nature of rag.insert()
# import nest_asyncio
# nest_asyncio.apply()
#########

class LightRAGIndexing:
    def __init__(self, working_dir, llm_model_func, api_key):
        """
        LightRAGの初期化
          - working_dir: 作業ディレクトリのパス(working_dir以下にinputフォルダを作成し、ドキュメントを格納する)
          - llm_model_func: LLMモデル
        """
        self.working_dir = working_dir
        self.rag = LightRAG(
            working_dir=self.working_dir,
            llm_model_func=llm_model_func
        )
        os.environ["OPENAI_API_KEY"] = api_key

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
        """
        self.load_documents()


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
                visualize_query_subgraph=True # クエリのサブグラフを可視化 context.gaphmlが出力される
            )
        )

        with open(os.path.join(output_dir, "output.txt"), "w", encoding="utf-8") as output_file:
            output_file.write(answer)
        with open(os.path.join(output_dir, "query.txt"), "w", encoding="utf-8") as output_file:
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
        with self.driver.session() as session:
            try:
                session.run("MATCH (n) RETURN n LIMIT 1")
            except Exception as e:
                raise ConnectionError("Failed to connect to Neo4j") from e

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
            print(sentence)
            # エンティティIDの抽出
            if "Entities" in sentence:
                entities_part = sentence.split("Entities")[1].split(";")[0]
                try:
                    # 余分な文字を取り除いた後、数値に変換してセットに追加
                    entity_ids.update(map(int, entities_part.strip(" ()[]").replace(")].", "").split(",")))
                except ValueError as e:
                    print("Error converting entity IDs to int:", e)

            # リレーションシップIDの抽出
            if "Relationships" in sentence:
                relationships_part = sentence.split("Relationships")[1].split(";")[0]
                try:
                    relationship_ids.update(map(int, relationships_part.strip(" ()[]").replace(")].", "").split(",")))
                except ValueError as e:
                    print("Error converting relationship IDs to int:", e)

            # ソース（文章）IDの抽出
            if "Sources" in sentence:
                sources_match = re.search(r"Sources \((.*?)\)", sentence)
                if sources_match:
                    sentence_id = ["sentence_" + s.strip() for s in sources_match.group(1).split(",")]
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
        namespace = root.tag.split('}')[0].strip('{')
        ns = {'ns': namespace}

        # --- ノードの処理 ---
        with self.driver.session() as session:
            # 既存のすべてのノードとエッジを削除
            session.run("MATCH (n) DETACH DELETE n")

            for node in root.findall(".//ns:node", ns):
                node_id = node.get("id")

                # ノードIDが数値でない場合
                if not node_id.isdigit():
                    properties = {}
                    labels = ["Node"]
                    for data in node.findall("ns:data", ns):
                        key = data.get("key")
                        value = data.text.strip('"') if data.text else ""
                        properties[key] = value
                        if properties.get("d1") == "text unit" and node_id in sentence_ids:
                            labels.append("UsedLabel")
                    if properties:
                        label_string = ":".join(labels)
                        session.run(
                            f"CREATE (n:{label_string} {{id: $id, {', '.join([f'{k}: ${k}' for k in properties.keys()])}}})",
                            id=node_id,
                            **properties
                        )
                    else:
                        session.run(
                            "CREATE (n:Node {id: $id})",
                            id=node_id
                        )
                    continue

                # ノードIDが数値の場合
                node_id_int = int(node_id)
                labels = ["Node"]
                if node_id_int in entity_ids:
                    labels.append("UsedLabel")
                else:
                    labels.append("NotUsedLabel")

                properties = {}
                for data in node.findall("ns:data", ns):
                    key = data.get("key")
                    value = data.text.strip('"') if data.text else ""
                    properties[key] = value

                label_string = ":".join(labels)
                session.run(
                    f"CREATE (n:{label_string} {{id: $id, {', '.join([f'{k}: ${k}' for k in properties.keys()])}}})",
                    id=node_id_int,
                    **properties
                )

        # --- エッジの処理 ---
        with self.driver.session() as session:
            for edge in root.findall(f".//{{{namespace}}}edge"):
                properties = {}
                edge_id = None
                for data in edge.findall(f"./{{{namespace}}}data"):
                    key = data.attrib["key"]
                    value = data.text.strip('"') if data.text else ""
                    properties[key] = value
                    if key == "d4" and value.isdigit():
                        edge_id = int(value)
                if edge_id in relationship_ids:
                    edge_labels = "UsedLabel"
                else:
                    edge_labels = "NotUsedLabel"

                source = edge.attrib["source"]
                target = edge.attrib["target"]
                if source.isdigit():
                    source = int(source)
                if target.isdigit():
                    target = int(target)

                # エッジのプロパティを再取得（必要に応じて）
                properties = {data.attrib["key"]: data.text for data in edge.findall(f"./{{{namespace}}}data")}
                session.run(
                    f"""
                    MATCH (source:Node {{id: $source}})
                    MATCH (target:Node {{id: $target}})
                    MERGE (source)-[r:{edge_labels}]->(target)
                    SET r += $properties
                    """,
                    source=source,
                    target=target,
                    properties=properties
                )

            print("Nodes and edges imported successfully!")
        
    
    def run(self):
        with open(self.txt_path, "r", encoding="utf-8") as file:
            sentences = file.readlines()
        sentences = [line for line in sentences if line.startswith("-")]
        
        entity_ids, relationship_ids, sentence_ids = self.extract_entity_relationship_ids(sentences)
        self.import_graphml_to_neo4j(entity_ids, relationship_ids, sentence_ids)
        self.driver.close()


# テスト
if __name__ == "__main__":
    # データディレクトリの設定
    working_dir = "./src/nuclear/脆化"
    assert os.path.exists(working_dir), f"Directory not found: {working_dir}"
    assert os.path.exists(working_dir + "/input"), f"Directory not found: {working_dir}/input"
    
    # LightRAGのIndexing
    Indexing = LightRAGIndexing(working_dir, gpt_4o_mini_complete, "api-key")
    Indexing.run()

    # LightRAGのQuerying
    Query = LightRAGQuery(working_dir, Indexing.rag)
    #response = Query.run("脆化の原因は何ですか？")
    #print(response)


    # 可視化
    ## Docker上でNeo4jを起動
    start_neo4j_in_browser()
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = ""
    driver = GraphDatabase.driver(uri, auth=None)
    

    ## 回答根拠の可視化
    working_dir = os.path.join(working_dir, Query.mode)
    Visualizer = VisualizeQuery(working_dir, driver)
    Visualizer.run()

    ## Neo4jブラウザにアクセス
    url = "http://localhost:7474/browser/"
    print(f"Neo4j Browser: {url}")

