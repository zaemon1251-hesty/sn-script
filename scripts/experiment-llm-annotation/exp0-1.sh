#!/bin/bash

# 再現実験
# ラベルは 5:2 の比率

suffix=20241016-exp0-1

# llmアノテーション用のデータcsvを準備
src="database/llm_annotation/gpt-3.5-turbo-1106_42_1_llm_annotation-20231217.csv"
dst="database/llm_ready/llm_annotation-$suffix.csv"
uv run python src/sn_script/csv_utils.py \
    denoised_to_llm_ready \
    --input_csv $src \
    --output_csv $dst

# llmアノテーション実行
llm_log_jsonl="database/log_jsonline/llm_annotation-$suffix.jsonl"
touch $llm_log_jsonl

src=$dst
dst="database/llm_annotation/llm_annotation-$suffix.csv"
all_csv="database/denoised/denoised_1_tokenized_224p_all.csv"
prompt_yaml="resources/classify_comment.yaml"
uv run python src/sn_script/llm_anotator.py \
    --llm_ready_path $src \
    --llm_annotation_path $dst \
    --llm_log_jsonl_path $llm_log_jsonl \
    --all_csv_path $all_csv \
    --prompt_yaml_path $prompt_yaml \
    --model_type "gpt-3.5-turbo-1106"

# 評価
human_csv="database/annotations/42_1_moriy_annotation_preprocessed.csv"
llm_csv=$dst
uv run python src/sn_script/evaluate_llm_annotation.py \
    --target binary \
    --human_csv $human_csv \
    --llm_csv $llm_csv

# 結果
# 'accuracy': {'accuracy': 0.95}, 'precision': {'precision': 0.8181818181818182}, 'recall': {'recall': 0.75}, 'f1': {'f1': 0.7826086956521738}}, 'subcategory': None}
# 'accuracy': {'accuracy': 0.93}, 'precision': {'precision': 0.6666666666666666}, 'recall': {'recall': 0.8333333333333334}, 'f1': {'f1': 0.7407407407407408}},
# 'accuracy': {'accuracy': 0.94}, 'precision': {'precision': 0.7142857142857143}, 'recall': {'recall': 0.8333333333333334}, 'f1': {'f1': 0.7692307692307692}
# temperatureを固定しても、ちょくちょく変わる..?