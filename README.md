# 🚀LightRAG with Visualization

## 環境構築
1. レポジトリをcloneする。
```
git clone <repository_url>
```
2. 新しいconda環境を作成し、必要なパッケージをinstallする。
```
conda create --name lightrag python=3.11
conda activate lightrag
cd src
pip install -e .
cd .. # 元のレポジトリに戻る
```
3. 入力ファイル(txt形式)を適切なパスに配置する。デフォルトでは、`./src/nuclear/アルカリ応力腐食割れ/input`、`./src/nuclear/クリープ亀裂/input`、`./src/nuclear/脆化/input`に格納する必要がある。


## CUIで実行
1. Neo4jの認証情報を入力する。(356~359行目 in src/pipeline.py)
```
uri = "bolt://localhost:7687"
username = "neo4j"
password = "password"
```

2. OpenAI API keyをターミナル上でexportする。
```
export OPENAI_API_KEY="sk-xxxx"
```

3. クエリを入力する。(351行目 in src/pipeline.py)
```
response = Query.run("Please provide the conditions under which Caustic Stress-Corrosion Cracking (CSCC) occurs.")
```

4. コードを実行する。
```
python src/pipeline.py
```

4. 回答が`./src/nuclear/{劣化メカニズム}/hybrid/output.txt`に出力される。また、接続先のNeo4jを参照することで、回答根拠を確認できる。Used labelが付与されたノード、エッジが実際に回答根拠となったものである。
<img width="1559" alt="スクリーンショット 2025-02-17 14 44 04" src="https://github.com/user-attachments/assets/387f134c-7359-451d-a9bf-36da1dbc458f" />

## GUI(streamlitアプリ)で実行 
1. Neo4jを起動する。
   
Neo4jをローカル(Dockerを使わずに)実行する場合は、チェックボックスにチェックを入れ、ユーザー名、パスワードなどを入力する。
 <img width="1545" alt="スクリーンショット 2025-02-17 14 23 03" src="https://github.com/user-attachments/assets/1f42dc6b-ee72-45f0-98b5-43d760a12d45" />
 Docker上で起動する場合は、Docker Desktopを起動し、`Dockerでneo4jサービスを起動`を選択する。
<img width="1552" alt="スクリーンショット 2025-02-17 14 24 46" src="https://github.com/user-attachments/assets/3068e03f-2629-4680-831e-d83fc2710571" />

3. OpenAI API Keyを入力し、劣化の種類、LLMモデルをそれぞれ選択する。
4. `ナレッジグラフ作成`を選択する。
5. 質問を送信すると、ナレッジグラフを使って回答が生成される。
<img width="1551" alt="スクリーンショット 2025-02-17 14 29 28" src="https://github.com/user-attachments/assets/807c4ac8-2a92-40f4-98bb-53d9cf72ee3c" />
6. 回答とともに回答根拠となったグラフが表示される。
<img width="1525" alt="スクリーンショット 2025-02-17 14 34 45" src="https://github.com/user-attachments/assets/7dc59ab9-1718-4338-8570-bb7415298b39" />
より詳細なグラフ情報がみたい場合は、接続したNeo4jを参照する。Docker上にNeo4jを起動した場合は http://localhost:7474/browser にアクセスすれば良い。

7. Docker上でNeo4jを起動していた場合は、`Neo4jサービスを停止`を選択した後に、タブを閉じる。(次回接続した際に、エラーが発生するため。)

## (Option) RAGASでの評価
`src/evaluation_ragas.py`を実行すると、評価結果がcsv形式で出力される。




