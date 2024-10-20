import os
from pathlib import Path
from SoccerNet.Downloader import getListGames


# 　分析対象のデータセットのパス
class Config:
    base_dir = (
        Path("/Users/heste/workspace/soccernet/SoccerNet_in_lrlab")
    )  # (project-root)/data
    target_base_dir = (
        Path(__file__).parent.parent.parent / "database"
    )  # (project-root)/database
    target_file_path = target_base_dir / "exist_targets.txt" # TODO: 削除する
    targets = getListGames("all")

    context_length = 2 # 自動ラベリングで何個前までのコメントを使うか


# 分析対象のカラム名
binary_category_name = "付加的情報か"
category_name = "大分類"
subcategory_name = "小分類"


# ターゲットの設定
random_seed = 10
half_number = 2

# 使用するLLMのモデル名
model_type = "gpt-3.5-turbo-1106"
#model_type = "gpt-4o-2024-05-13"
# model_type = "gpt-4-1106-preview"
# model_type = "meta-llama/Llama-2-70b-chat-hf"

if __name__ == "__main__":
    listdir = []
    for target in Config.targets:
        path = Config.base_dir / target
        if not Path(path).exists():
            listdir.append(target)

    all_gamedir = set(Config.targets)
    listdir = set(listdir)
    print(*(all_gamedir - listdir), sep="\n")
