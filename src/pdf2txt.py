import os
import subprocess

# 入力フォルダと出力フォルダを指定
source_folder = ""
destination_folder = ""

# 出力フォルダが存在しない場合は作成
os.makedirs(destination_folder, exist_ok=True)

def pdf_to_txt_with_pdftotext(pdf_path, txt_path):
    """pdftotext を使って PDF をテキストに変換"""
    try:
        # pdftotext コマンド実行（-layout オプションを指定）
        subprocess.run(["pdftotext", "-layout", pdf_path, txt_path], check=True)
        print(f"Converted: {pdf_path} -> {txt_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting {pdf_path}: {e}")
    except FileNotFoundError:
        print("pdftotext がインストールされていません。インストールしてください。")

# PDFフォルダ内のすべてのファイルを処理
for file_name in os.listdir(source_folder):
    if file_name.endswith(".pdf"):
        pdf_path = os.path.join(source_folder, file_name)
        txt_name = os.path.splitext(file_name)[0] + ".txt"
        txt_path = os.path.join(destination_folder, txt_name)
        pdf_to_txt_with_pdftotext(pdf_path, txt_path)

print("全てのPDFをテキストに変換しました。")