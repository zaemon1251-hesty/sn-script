import json
import os

import pandas as pd
from loguru import logger

try:
    from sn_script.config import (
        Config,
        binary_category_name,
        category_name,
        half_number,
        model_type,
        random_seed,
        subcategory_name,
    )
    from sn_script.llm_anotator import create_target_prompt
except ModuleNotFoundError:
    import sys

    sys.path.append(".")
    from src.sn_script.config import (  # noqa
        Config,
        binary_category_name,
        category_name,
        subcategory_name,
        random_seed,
        half_number,
        model_type,
    )
    from src.sn_script.llm_anotator import create_target_prompt


LLM_ANOTATION_CSV_ALL_PATH = (
    Config.target_base_dir / f"{model_type}_500game_{half_number}_llm_annotation.csv"
)
SUP_SUBCATEGORY_COMMENTS_TXT_PATH = (
    Config.target_base_dir / f"{half_number}_{random_seed}_supplementary_comments.txt"
)
SUBCATEGORY_COMMENTS_JSONL_PATH = (
    Config.target_base_dir / f"{half_number}_{random_seed}_supplementary_comments.jsonl"
)

SUBCATEGORY_ANNOTATION_CSV_PATH = (
    Config.target_base_dir
    / f"{half_number}_{random_seed}_val_subcategory_annotation.csv"
)
SUBCATEGORY_LLM_CSV_PATH = (
    Config.target_base_dir / "{file_name_prefix}_{model_type}_subcategory_llm_annotation.csv"
)


def sample_supplementary_comments(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """
    与えられたデータフレームから、付加的情報か」が1のコメントをランダムにn個サンプリングする
    """
    return df[df[binary_category_name] == 1].sample(n=n, random_state=random_seed)


def write_supplementary_comments_txt(df: pd.DataFrame, path: str) -> None:
    """
    与えられたデータフレームをtxtファイルに書き出す
    """
    supplementary_comments_df = sample_supplementary_comments(df, 100)

    comment_ids = supplementary_comments_df.index.tolist()

    targe_prompt_list = []
    for comment_id in comment_ids:
        targe_prompt_list.append(create_target_prompt(comment_id))

    with open(path, "w") as f:
        f.write("\n".join(targe_prompt_list))


def run_write_supplementary_comments_txt() -> None:
    """
    アノテーション済みcsv;SUP_SUBCATEGORY_COMMENTS_TXT_PATH をtxtファイルに書き出す
    """
    all_comment_df = pd.read_csv(LLM_ANOTATION_CSV_ALL_PATH)
    write_supplementary_comments_txt(all_comment_df, SUP_SUBCATEGORY_COMMENTS_TXT_PATH)
    logger.info("Done writing supplementary_comments")


def generate_subcategory_jsonlines():

    def read_and_convert_to_jsonl(input_file_path, output_file_path):
        """
        ...
        id => 12121
        game => hogehoge
        previous comments => これは前のコメントです
        comment => これはコメントです
        output: {"category": 1}
        id => 12122
        game=> fugafuga
        ...

        のようなテキストファイルを読み込んで、以下のようなJSON Lines形式のファイルに変換する
        {"id": "12121", "game": "hogehoge", "previous_comments": "これは前のコメントです",
            "comment": "これはコメントです", "output": {"category": 1}}
        {"id": "12122", "game": "fugafuga", ...}
        """
        with open(input_file_path, encoding="utf-8") as file:
            lines = file.readlines()

        output_data = []
        current_entry = {}

        for idx, line in enumerate(lines):
            # 新しいエントリの開始
            if "id =>" in line:
                # 前のエントリにoutputが含まれていれば、出力データに追加
                if current_entry:
                    output_data.append(current_entry)
                # 新しいエントリの準備
                current_entry = {"id": line.split("=>")[1].strip()}
            elif "game =>" in line:
                # 不要（かもしれない）な情報なのでスキップ
                # current_entry["game"] = line.split("=>")[1].strip()
                pass
            elif "previous comments =>" in line:
                current_entry["previous_comments"] = line.split("=>")[1].strip()
            elif "comment =>" in line:
                current_entry["comment"] = line.split("=>")[1].strip()
            elif "start gap (seconds) from previous =>" in line:
                current_entry["start gap (seconds) from previous"] = line.split("=>")[
                    1
                ].strip()
            elif "output:" in line:
                # JSON形式の出力をパースして辞書に追加し、エントリを出力データに追加するフラグを立てる
                output_json = line.split("output:")[1].strip()
                logger.info(f"line: {idx}\noutput_json: {output_json}")
                current_entry["output"] = json.loads(output_json)

        # ファイルの終わりに達して、最後のエントリにoutputが含まれていれば出力データに追加
        if current_entry != {}:
            output_data.append(current_entry)

        # JSON Lines形式で出力ファイルに書き込む
        with open(output_file_path, "w", encoding="utf-8") as outfile:
            for entry in output_data:
                json_line = json.dumps(entry, ensure_ascii=False)
                outfile.write(json_line + "\n")

    logger.info(
        f"Writing {SUBCATEGORY_COMMENTS_JSONL_PATH} from {SUP_SUBCATEGORY_COMMENTS_TXT_PATH}..."
    )
    read_and_convert_to_jsonl(
        SUP_SUBCATEGORY_COMMENTS_TXT_PATH, SUBCATEGORY_COMMENTS_JSONL_PATH
    )
    logger.info(f"Done writing {SUBCATEGORY_COMMENTS_JSONL_PATH}")


def create_annotation_csv():
    all_comment_df = pd.read_csv(LLM_ANOTATION_CSV_ALL_PATH)

    supplementary_comments_df = sample_supplementary_comments(all_comment_df, 100)

    supplementary_comments_df.to_csv(SUBCATEGORY_ANNOTATION_CSV_PATH, index=False)


def statistics_subcategory():
    subcategory_data = []
    with open(SUBCATEGORY_COMMENTS_JSONL_PATH, encoding="utf-8") as file:
        lines = file.readlines()
        for line in lines:
            comment_data = json.loads(line)
            subcategory_data.append(comment_data)

    # サブカテゴリそれぞれの数をカウント
    subcategory_count = {}
    for comment_data in subcategory_data:
        for subcategory in comment_data["output"]:
            category = subcategory["category"]
            subcategory_count[category] = subcategory_count.get(category, 0) + 1

    subcategory_count_str = "\n".join(
        [f"{key}: {value}" for key, value in subcategory_count.items()]
    )
    logger.info(f"subcategory_count\n{subcategory_count_str}")

    # comment毎のサブカテゴリの数をカウント
    subcategory_length = {}
    for comment_data in subcategory_data:
        length = len(comment_data["output"])
        subcategory_length[length] = subcategory_length.get(length, 0) + 1

    subcategory_length_str = "\n".join(
        [f"{key}: {value}" for key, value in subcategory_length.items()]
    )
    logger.info(f"subcategory_length\n{subcategory_length_str}")


def create_annotation_csv_from_jsonl():
    all_comment_df = pd.read_csv(LLM_ANOTATION_CSV_ALL_PATH)
    anotation_data = []
    with open(SUBCATEGORY_COMMENTS_JSONL_PATH, encoding="utf-8") as file:
        lines = file.readlines()
        for line in lines:
            comment_data = json.loads(line)
            # カテゴリがない場合は0を入れる
            comment_data["subcategory"] = 0
            # 最後のサブカテゴリを取得
            for subcategory in comment_data["output"]:
                comment_data["subcategory"] = subcategory["category"]
            anotation_data.append(comment_data)
    annotation_idxs = [int(data["id"]) for data in anotation_data]
    annotation_df = all_comment_df[all_comment_df.index.isin(annotation_idxs)]

    # アノテーション済みのデータフレームを作成
    annotation_df.loc[annotation_idxs, subcategory_name] = [
        data["subcategory"] for data in anotation_data
    ]
    annotation_df.to_csv(SUBCATEGORY_ANNOTATION_CSV_PATH, index=False)


def create_llm_annotation_csv(subcategory_annotated_csv_path, file_name_prefix: str):
    annotation_df = pd.read_csv(subcategory_annotated_csv_path)
    annotation_df[subcategory_name] = pd.NA
    llm_target_csv_path = str(SUBCATEGORY_LLM_CSV_PATH).format(
        file_name_prefix=file_name_prefix,
        model_type=model_type,
    )

    assert not os.path.exists(llm_target_csv_path), f"{llm_target_csv_path}  exists. Use another file name."

    annotation_df.to_csv(
        llm_target_csv_path,
        index=False,
    )


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()

    parser.add_argument("type", type=str, help="type of function to run")
    parser.add_argument(
        "--prefix", type=str, help="file name prefix for llm_annotation_df", default=""
    )
    args = parser.parse_args()

    if args.type == "txt":
        run_write_supplementary_comments_txt()
    elif args.type == "jsonl":
        generate_subcategory_jsonlines()
    elif args.type == "statistics":
        statistics_subcategory()
    elif args.type == "jsonl2csv":
        create_annotation_csv_from_jsonl()
    elif args.type == "csv":
        create_annotation_csv()
    elif args.type == "llmcsv":
        create_llm_annotation_csv(SUBCATEGORY_ANNOTATION_CSV_PATH, args.prefix)
    else:
        raise ValueError(f"Invalid type: {args.type}")
