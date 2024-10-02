import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

import whisper
from faster_whisper import WhisperModel
from loguru import logger
from tap import Tap
from tqdm import tqdm

try:
    from sn_script.config import Config, half_number
except ModuleNotFoundError:
    import sys

    sys.path.append(".")
    from src.sn_script.config import Config, half_number


SttModels = Literal["whisper-large-v2", "conformer", "reason", "faster-whisper"]

def get_stt_model(model_name: SttModels):
    if model_name == "whisper-large-v2":
        return whisper.load_model("large")
    elif model_name == "faster-whisper":
        return WhisperModel(
            "large-v3",
            device="cuda",
        )
    elif model_name == "conformer":
        raise NotImplementedError("Conformer model is not implemented yet")
    elif model_name == "reason":
        raise NotImplementedError("Reason model is not implemented yet")
    else:
        raise ValueError(f"Unknown model name: {model_name}")

# コマンドライン引数を設定
class Speech2TextArguments(Tap):
    target_game: str = "all"
    suffix: str = ""
    model: SttModels = "whisper-large-v2"


def main(args: Speech2TextArguments):
    target_games = []
    if args.target_game == "all":
        target_games = Config.targets
    else:
        target_games = [args.target_game]

    model = get_stt_model(args.model)

    for target in tqdm(target_games):
        target_dir_path = Config.base_dir / target

        if not os.path.exists(target_dir_path):
            logger.info(f"Video not found: {target_dir_path}")
            continue

        run_transcribe(model, target_dir_path, args=args)


def run_transcribe(model, game_dir: Path, args: Speech2TextArguments):
    video_path = game_dir / f"{half_number}_224p.mkv"
    output_text_path = game_dir / f"{half_number}_224p{args.suffix}.txt"
    output_json_path = game_dir / f"{half_number}_224p{args.suffix}.json"


    if args.model == "faster-whisper":
        segments, info = model.transcribe(
            str(video_path),
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        # iteratorからlistに変換
        segments = list(segments)

        with open(output_text_path, "w") as f:
            text = " ".join([segment.text for segment in segments])
            f.writelines(text)
        with open(output_json_path, "w") as f:
            transcription_output = {
                "segments": [
                    segment._asdict()
                    for segment in segments
                ],
                "info": info._asdict(),
            }
            json.dump(transcription_output, f, indent=2, ensure_ascii=False)

    elif args.model == "whisper-large-v2":
        assert model.is_multilingual
        result = model.transcribe(
            str(video_path),
            verbose=True
        )
        with open(output_text_path, "w") as f:
            f.writelines(result["text"])
        with open(output_json_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    else:
        raise NotImplementedError(f"Model {args.model} is not implemented yet")


def asr_comformer():
    from espnet2.bin.asr_inference import Speech2Text
    import soundfile

    model = Speech2Text.from_pretrained(
        "espnet/YushiUeda_iemocap_sentiment_asr_train_asr_conformer"
    )

    speech, rate = soundfile.read("speech.wav")
    text, *_ = model(speech)[0]


def transcribe_reason():
    import reazonspeech as rs
    from espnet2.bin.asr_inference import Speech2Text

    target: str = "2014-11-04 - 20-00 Zenit Petersburg 1 - 2 Bayer Leverkusen"
    video_path = Config.base_dir / target / f"{half_number}_224p.oga"

    model = Speech2Text.from_pretrained(
        "espnet/kamo-naoyuki-mini_an4_asr_train_raw_bpe_valid.acc.best"
    )

    cap = rs.transcribe(str(video_path), model)

    # cap is generator
    while True:
        try:
            print(next(cap))
        except StopIteration:
            break


if __name__ == "__main__":
    time_str = datetime.now().strftime("%Y%m%d-%H%M%S")

    args = Speech2TextArguments().parse_args()

    logger.add(
        f"logs/llm_anotator_{time_str}.log",
    )
    main(args)
