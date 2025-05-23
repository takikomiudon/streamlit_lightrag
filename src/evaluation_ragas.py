import os
import re
from typing import List

import openai
import openai.cli
from dotenv import load_dotenv
from ragas import evaluate
from ragas.dataset_schema import SingleTurnSample
from ragas.embeddings import OpenAIEmbeddings
from ragas.embeddings.base import BaseEmbeddings
from ragas.evaluation import EvaluationDataset
from ragas.llms import OpenAI as RagasOpenAI
from ragas.llms.base import BaseLLM
from ragas.metrics import (
    AnswerCorrectness,
    AnswerRelevancy,
    ContextRecall,
    Faithfulness,
    SemanticSimilarity,
)

load_dotenv()

evaluator_llm: BaseLLM = RagasOpenAI(model="gpt-4")
evaluator_embeddings: BaseEmbeddings = OpenAIEmbeddings()

metrics = [
    Faithfulness(),
    AnswerRelevancy(),
    ContextRecall(),
    SemanticSimilarity(),
    AnswerCorrectness(),
]

# DEGRATION_TYPE = "アルカリ応力腐食割れ"
# DEGRATION_TYPE = "クリープ亀裂"
DEGRATION_TYPE = "脆化"

# QUERY_MODE = "hybrid"
# QUERY_MODE = "local"
QUERY_MODE = "naive"

WORKING_DIR = f"./nuclear/{DEGRATION_TYPE}/"


if DEGRATION_TYPE == "アルカリ応力腐食割れ":
    reference_eng = (
        "- Austenitic stainless steel is unsuitable for SG because it has the potential "
        "to cause alkaline stress corrosion cracking (ASCC).\n"
        "- A study on cracking susceptibility was conducted on austenitic stainless steels "
        "(SUS304, SUS316, SUS321) by applying tensile loads in 10%-70% NaOH solutions at "
        "temperatures ranging from 150°C to 340°C. The cracking conditions exhibited material "
        "dependency.\n"
        "- High-nickel alloys are less susceptible to the effects of alkaline SCC.\n"
        "- At PFR, CSCC occurred at the tube-to-tube plate welds of austenitic steel superheaters "
        "and in low-alloy steel evaporators. Austenitic steel, in particular, is highly prone to "
        "CSCC, making it unsuitable for LMFR steam generators.\n"
        "- CSCC has been observed at NaOH concentrations of 55% and 75% and temperatures above "
        "100°C. It is not observed at 100% NaOH concentrations or below 75°C.\n"
        "- At Phenix, CSCC occurred in the tube-to-tube plate joints of the IHX due to residual "
        "sodium hydroxide.\n"
    )
    reference_jp = (
        "- オーステナイト系ステンレス鋼はアルカリ応力腐食割れを引き起こす可能性があるため、"
        "SGには不向きである。\n"
        "- オーステナイトステンレス鋼（SUS304, SUS316, SUS321）に対して10%～70%NaOH溶液中、"
        "温度150℃～340℃の範囲で引張荷重を加えた試験により、割れ感受性を調査。割れの発生条件には"
        "材料依存性が見られた。\n"
        "- 高ニッケル合金はアルカリSCCの影響を受けにくい。\n"
        "- PFRにて、オーステナイト鋼製の過熱器の管-管板溶接継手、低合金鋼製の蒸発器にてCSCCが発生。"
        "特にオーステナイト鋼は、CSCCのリスクが高いため、LMFR 蒸気発生器には適していない。\n"
        "- NaOH55%, 75%、温度100℃以上でCSCCが観察されている。NaOH100%濃度や75℃以下では"
        "観察されない。\n"
        "- Phenixにて、IHXの管-管板接合部に水酸化ナトリウムが残留したことによりCSCCが発生。\n"
    )

if DEGRATION_TYPE == "クリープ亀裂":
    reference_eng = (
        "- Crack growth under tensile load conditions at high temperatures has been reported "
        "for low-alloy steels, ferritic steels, and austenitic stainless steels.\n"
        "- Studies on controlling parameters for creep crack growth rate, such as stress "
        "intensity factors, net section stress, and modified J-integrals, have been reported. "
        "In later years, it was found that creep J-integrals show a good correlation.\n"
        "- There is no significant interaction between fatigue cracks and creep cracks.\n"
        "- In low-stress (long-duration) tests, crack growth rates increase for the same "
        "creep J-integral due to differences in fracture modes. However, considering creep "
        "rupture strain organizes the results well.\n"
        "- Under multiaxial stress conditions, crack growth rates become faster.\n"
    )

    reference_jp = (
        "- 低合金鋼、フェライト鋼、オーステナイトステンレス鋼を用いた高温クリープ条件下での"
        "引張荷重による亀裂成長が報告されている。\n"
        "- クリープ亀裂進展速度の支配パラメータについて、応力拡大係数や正味断面応力、修正J積分での"
        "検討報告もあるが、後年にはクリープJ積分と良い相関関係があることが報告されている。\n"
        "- 疲労亀裂とクリープ亀裂で大きい相互作用はない。\n"
        "- 低応力（長時間）試験では、破壊モードの違いにより、同じクリープJ積分に対して亀裂進展速度が"
        "速くなるが、クリープ破断ひずみを考慮することで良く整理できる。\n"
        "- 多軸応力下で亀裂進展速度は速くなる。\n"
    )
if DEGRATION_TYPE == "脆化":
    reference_eng = (
        "- The occurrence condition of liquid metal embrittlement (LME) is that the "
        "grain-boundary adsorption energy between the liquid metal and structural material "
        "is close to zero.\n"
        "- LME has been observed under the following conditions:\n"
        "  - Ferritic steel, especially when appropriate SR treatment (stress-relief heat "
        "treatment) or PWHT (post-weld heat treatment) has not been performed.\n"
        "  - Contact with or wetting by liquid sodium with high dissolved oxygen content.\n"
        "  - Presence of notches or stress concentration areas.\n"
        "  - Plastic deformation under low strain rate loading at temperatures below 500°C.\n"
        "- When liquid metal embrittlement occurs, the ductility of the base material "
        "decreases.\n"
        "- Embrittlement susceptibility increases with a temperature rise in the range of "
        "150–450°C. LME does not occur at temperatures above this range.\n"
        "- There are no reported cases for austenitic stainless steels.\n"
    )

    reference_jp = (
        "- 液体金属と構造材のgrain-boundary adsorption energyがゼロに近いことが液体金属脆化の"
        "発生条件。\n"
        "- 以下を満たした条件で発生が確認されている。\n"
        "  - フェライト鋼で、特に適切なSR処理（応力除去熱処理）が行われていないもしくは"
        "PWHT（溶接後熱処理）が行われていない\n"
        "  - 溶存酸素量の多い液体ナトリウムとの接触、濡れている\n"
        "  - 切欠きや応力集中部\n"
        "  - 500℃未満での低ひずみ速度負荷による塑性変形中\n"
        "- 液体金属脆化が生じた場合、母材の延性が低下する。\n"
        "- 脆化感受性は、150～450℃の温度上昇に伴い増加する。これ以上の温度ではLMEは"
        "発生しない。\n"
        "- オーステナイトステンレス鋼での報告例はない。\n"
    )

if DEGRATION_TYPE == "テスト":
    reference_eng = "hoge fuga piyo foo bar"
    reference_jp = "ほげ ふが ぴよ ふー ばー"

if DEGRATION_TYPE == "歌詞":
    reference_eng = "hoge fuga piyo foo bar"
    reference_jp = "ほげ ふが ぴよ ふー ばー"


def clean_text(input_text: str) -> List[str]:
    # 改行コードを保持しながらセクションを分割
    lines = input_text.splitlines()
    # 不要な記号やフォーマットを削除
    cleaned_lines = [
        re.sub(r'[^\w\s,.:"\'()\-]', "", line.strip()) for line in lines if line.strip()
    ]
    return cleaned_lines


with open(os.path.join(WORKING_DIR + QUERY_MODE + "/output.txt"), "r") as f:
    response_eng = f.read()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    from openai import OpenAI

    client = OpenAI(api_key=openai.api_key)

    system_prompt = "You are a helpful assistant."
    question = (
        "Please translate the following English text to Japanese:\n\n" + response_eng
    )

    response_jp = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": [{"type": "text", "text": question}],
            }
        ],
        temperature=0.0,
    )

    response_jp = response_jp.choices[0].message.content

with open(os.path.join(WORKING_DIR + QUERY_MODE + "/context.txt"), "r") as f:
    retrieved_contexts = f.read()

retrieved_contexts = clean_text(retrieved_contexts)

with open(os.path.join(WORKING_DIR + QUERY_MODE + "/query.txt"), "r") as f:
    user_input = f.read()
    print(user_input)

sample_eng = SingleTurnSample(
    user_input=user_input,
    response=response_eng,
    reference=reference_eng,
    retrieved_contexts=retrieved_contexts,
)
sample_jp = SingleTurnSample(
    user_input=user_input,
    response=response_jp,
    reference=reference_jp,
    retrieved_contexts=retrieved_contexts,
)

datasets = EvaluationDataset(samples=[sample_eng, sample_jp])
result = evaluate(datasets, metrics, llm=evaluator_llm, embeddings=evaluator_embeddings)
result.to_pandas().to_csv(os.path.join(WORKING_DIR + QUERY_MODE + "/ragas.csv"))
