import json

import nltk
import pandas as pd
from loguru import logger

try:
    from sn_script.config import (
        Config,
        binary_category_name,
        category_name,
        half_number,
        subcategory_name,
    )
    from sn_script.csv_utils import stop_watch, write_csv
except ModuleNotFoundError:
    import sys

    sys.path.append(".")
    from src.sn_script.config import (
        Config,
        binary_category_name,
        category_name,
        half_number,
        subcategory_name,
    )
    from src.sn_script.csv_utils import stop_watch, write_csv

ALL_CSV_PATH = (
    Config.target_base_dir / f"500game_denoised_{half_number}_tokenized_224p_all.csv"
)

RAW_JSON_TEMPLATE = f"{half_number}_224p.json"
RAW_CSV_TEMPLATE = f"{half_number}_224p.csv"
DENOISED_TEXT_TEMPLATE = f"denoised_{half_number}_224p.txt"
DENISED_JSONLINE_TEPMLATE = f"denoised_{half_number}_224p.jsonl"
DENISED_TOKENIZED_TEPMLATE = f"denoised_{half_number}_tokenized_224p.txt"
DENISED_TOKENIZED_JSONLINE_TEPMLATE = f"denoised_{half_number}_tokenized_224p.jsonl"
DENISED_TOKENIZED_CSV_TEPMLATE = f"denoised_{half_number}_tokenized_224p.csv"


@stop_watch
def convert_json_to_csv():
    """whisperが生成したjsonファイルをCSVに変換する"""
    for target in Config.targets:
        # target: str = target.rstrip("/").split("/")[-1]
        json_path = Config.base_dir / target / RAW_JSON_TEMPLATE
        csv_path = Config.base_dir / target / RAW_CSV_TEMPLATE
        with open(json_path) as f:
            json_data = json.load(f)
        write_csv(json_data, csv_path)


@stop_watch
def denoise_sentenses():
    """whisperが生成したjsonに含まれるセグメントのうち，ノイズとなるセグメントを除去する"""

    def preprocess_data(sentenses_data: list[dict[str, str]]):
        result = []
        for sts in sentenses_data:
            sts["text"] = sts["text"].replace("\n", "").strip()
            result.append(sts)
        return result

    def is_noise(sentense, prev_sentense):
        result = sentense == prev_sentense
        return result

    def remove_noise(sentenses_data: list[dict[str, str]]):
        result = []
        prev_sentense = ""
        for sts in sentenses_data:
            if is_noise(sts["text"], prev_sentense):
                continue
            result.append(sts)
            prev_sentense = sts["text"]
        return result

    def dump_denoised_data(
        sentenses_data: list[dict[str, str]],
        denoised_txt_path: str,
        denoised_jsonl_path: str,
    ):
        texts = [sts["text"] for sts in sentenses_data]
        with open(denoised_txt_path, "w") as f:
            f.write(" ".join(texts))
        for sts in sentenses_data:
            with open(denoised_jsonl_path, "a") as f:
                json.dump(sts, f)
                f.write("\n")

    for target in Config.targets:
        # target: str = target.rstrip("/").split("/")[-1]
        json_txt_path = Config.base_dir / target / RAW_JSON_TEMPLATE
        denoised_txt_path = Config.base_dir / target / DENOISED_TEXT_TEMPLATE
        denoised_jsonl_path = Config.base_dir / target / DENISED_JSONLINE_TEPMLATE
        raw_data = json.load(open(json_txt_path))["segments"]
        preprocessed_data = preprocess_data(raw_data)
        denoised_data = remove_noise(preprocessed_data)
        logger.info(f"before: {len(preprocessed_data)}, after: {len(denoised_data)}")
        dump_denoised_data(denoised_data, denoised_txt_path, denoised_jsonl_path)


@stop_watch
def tokenize_sentense():
    """試合単位で結合されたコメント集合を文単位にtokenizeする"""
    for target in Config.targets:
        # target: str = target.rstrip("/").split("/")[-1]
        denoised_txt_path = Config.base_dir / target / DENOISED_TEXT_TEMPLATE
        tokenized_txt_path = Config.base_dir / target / DENISED_TOKENIZED_TEPMLATE
        with open(denoised_txt_path) as f:
            text = f.read()
        with open(tokenized_txt_path, "w") as f:
            f.write("\n".join(nltk.sent_tokenize(text)))


@stop_watch
def create_jsonline_tokenized_sentences():
    """tokenized済みのテキストが含まれるファイルを，発話時間情報を付与しつつ，jsonline形式に変換する"""

    def _run(
        tokenized_txt_path: str, denoised_jsonl_path: str, tokenized_jsonl_path: str
    ):
        """
        gameごとにtokenized済みのテキストをjsonline形式に変換する
        Input:
            tokenized_text_path: str
            denoised_jsonl_path: str
            tokenized_jsonl_path: str
        Output:
            None

        アルゴリズム:
            入力:
                sentence-splitterで分割されたテキストセグメント P = {(seg_j)}
                ノイズ除去済みのWhisper書き起こしセグメント S = {(t_i, s_i, e_i)}
            出力:
                sentence-splitterで分割されたテキストセグメント P_ = {(seg_j, s_j, e_j)}
            手順:
                P_ = []
                i = 1
                i_max = |P|
                for seg_j in P:
                    start_i = i
                    covering_text = t_i
                    while covering_text not contains seg_j:
                        i = i + 1
                        covering_text = covering_text + " " + t_i
                    P_.append((seg_j, s_start_i, e_i))
                return P_
        """
        result = []
        with open(tokenized_txt_path) as f:
            tokenized_texts = f.readlines()

        with open(denoised_jsonl_path) as f:
            denoised_data = [json.loads(line) for line in f.readlines()]
        tokenized_texts = [t.rstrip("\n") for t in tokenized_texts]

        current_segment_idx = 0
        end_segments_idx = len(denoised_data) - 1

        for tokenized_text in tokenized_texts:
            start_span_idx = current_segment_idx
            end_span_idx = current_segment_idx

            covering_text = denoised_data[start_span_idx]["text"]
            while end_span_idx <= end_segments_idx:
                if tokenized_text.strip() in covering_text:
                    break
                end_span_idx += 1
                covering_text += " " + denoised_data[end_span_idx]["text"]

            tokinized_data = {
                "text": tokenized_text,
                "start": denoised_data[start_span_idx]["start"],
                "end": denoised_data[end_span_idx]["end"],
            }
            result.append(tokinized_data)
            current_segment_idx = end_span_idx

        for tokenized_data in result:
            with open(tokenized_jsonl_path, "a") as f:
                json.dump(tokenized_data, f)
                f.write("\n")

    for target in Config.targets:
        # target: str = target.rstrip("/").split("/")[-1]
        tokenized_txt_path = Config.base_dir / target / DENISED_TOKENIZED_TEPMLATE
        denoised_jsonl_path = Config.base_dir / target / DENISED_JSONLINE_TEPMLATE
        tokenized_jsonl_path = (
            Config.base_dir / target / DENISED_TOKENIZED_JSONLINE_TEPMLATE
        )
        if not tokenized_txt_path.exists() or not denoised_jsonl_path.exists():
            logger.warning(
                f"tokenized_txt_path or denoised_jsonl_path is not exists: {tokenized_txt_path}, {denoised_jsonl_path}"
            )
            continue
        if tokenized_jsonl_path.exists():
            logger.info(
                f"tokenized_jsonl_path is already exists: {tokenized_jsonl_path}"
            )
            continue
        _run(tokenized_txt_path, denoised_jsonl_path, tokenized_jsonl_path)


@stop_watch
def round_down():
    """小数点を2桁に丸める"""
    for target in Config.targets:
        # target: str = target.rstrip("/").split("/")[-1]
        tokenized_jsonl_path = (
            Config.base_dir / target / DENISED_TOKENIZED_JSONLINE_TEPMLATE
        )
        if not tokenized_jsonl_path.exists():
            logger.warning(
                f"tokenized_jsonl_path is not exists: {tokenized_jsonl_path}"
            )
            continue
        data = [json.loads(line) for line in open(tokenized_jsonl_path)]
        for d in data:
            d["start"] = round(d["start"], 2)
            d["end"] = round(d["end"], 2)
        with open(tokenized_jsonl_path, "w") as f:
            for d in data:
                json.dump(d, f)
                f.write("\n")


@stop_watch
def create_csv_tokenized_sentenses():
    """sentence tokenizedしたjsonlファイルをcsvに変換する"""
    for target in Config.targets:
        # target: str = target.rstrip("/").split("/")[-1]
        tokenized_jsonl_path = (
            Config.base_dir / target / DENISED_TOKENIZED_JSONLINE_TEPMLATE
        )
        if not tokenized_jsonl_path.exists():
            logger.warning(
                f"tokenized_jsonl_path is not exists: {tokenized_jsonl_path}"
            )
            continue
        tokenized_csv_path = Config.base_dir / target / DENISED_TOKENIZED_CSV_TEPMLATE
        data = [json.loads(line) for line in open(tokenized_jsonl_path)]
        for i, d in enumerate(data, start=1):
            d["id"] = i
        write_csv(data, tokenized_csv_path)


@stop_watch
def create_tokonized_all_csv():
    """全試合のコメントをまとめたCSVを作成する"""
    df_list = []
    for target in Config.targets:
        # target: str = target.rstrip("/").split("/")[-1]
        csv_path = Config.base_dir / target / DENISED_TOKENIZED_CSV_TEPMLATE
        if not csv_path.exists():
            logger.warning(f"csv_path is not exists: {csv_path}")
            continue
        tmp_df = pd.read_csv(csv_path)
        tmp_df["game"] = target.replace("SoccerNet/", "")
        df_list.append(tmp_df)

    all_game_df = pd.concat(df_list)
    all_game_df = (
        all_game_df.reindex(
            columns=[
                "id",
                "game",
                "start",
                "end",
                "text",
                binary_category_name,
                category_name,
                subcategory_name,
                "備考",
            ]
        )
        .sort_values(by=["game", "start", "end"], ascending=[True, True, True])
        .reset_index(drop=True)
    )

    all_game_df["id"] = all_game_df.index
    all_game_df.to_csv(ALL_CSV_PATH, index=False, encoding="utf-8_sig")


def main():
    time_str = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    logger.add(
        f"logs/transcribe_processor_{half_number}_{time_str}.log",
    )
    logger.info(f"start transcribe processor {half_number} half.")

    convert_json_to_csv()
    denoise_sentenses()
    tokenize_sentense()
    create_jsonline_tokenized_sentences()
    round_down()
    create_csv_tokenized_sentenses()
    create_tokonized_all_csv()


if __name__ == "__main__":
    # nltk.download("punkt")
    main()
