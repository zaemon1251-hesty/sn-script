#!/bin/bash

python src/sn_script/v3/v3_to_gsr.py \
    --SoccerNet_path "/raid_elmo/home/lr/moriy/SoccerNet" \
    --output_base_path "/raid_elmo/home/lr/moriy/SoccerNetGS/v3-720p" \
    --resol720p

# 計算機サーバーのローカルにコピー
rsync -avz --inplace /raid_elmo/home/lr/moriy/SoccerNetGS/v3-720p/ /local/moriy/SoccerNetGS/v3-720p/
# rm -rf /raid_elmo/home/lr/moriy/SoccerNetGS/v3-720p/train/SNGS-012/