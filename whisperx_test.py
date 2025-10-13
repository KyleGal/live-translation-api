import whisperx
import gc
from whisperx.diarize import DiarizationPipeline
import os
import torch

# WhisperX uses faster-whisper which doesn't support MPS, so use CPU
device = "cpu"
audio_file = "recording_20251012_202912.wav"
batch_size = 4 # Reduced for CPU
compute_type = "int8" # Use int8 for CPU (faster than float32)

# 1. Transcribe with original whisper (batched)
model = whisperx.load_model("large-v2", device, compute_type=compute_type)

# save model to local path (optional)
# model_dir = "/path/"
# model = whisperx.load_model("large-v2", device, compute_type=compute_type, download_root=model_dir)

audio = whisperx.load_audio(audio_file)
result = model.transcribe(audio, batch_size=batch_size)
print(result["segments"]) # before alignment

# delete model if low on GPU resources
# import gc; import torch; gc.collect(); torch.cuda.empty_cache(); del model

# 2. Align whisper output
model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

print(result["segments"]) # after alignment

# delete model if low on GPU resources
# import gc; import torch; gc.collect(); torch.cuda.empty_cache(); del model_a

# 3. Assign speaker labels
from dotenv import load_dotenv
load_dotenv()
HUGGINGFACE_ACCESS_TOKEN = os.getenv("HF_TOKEN")
diarize_model = DiarizationPipeline(use_auth_token=HUGGINGFACE_ACCESS_TOKEN, device=torch.device("cpu"))

# add min/max number of speakers if known
diarize_segments = diarize_model(audio)
# diarize_model(audio, min_speakers=min_speakers, max_speakers=max_speakers)

result = whisperx.assign_word_speakers(diarize_segments, result)
print(diarize_segments)
print(result["segments"]) # segments are now assigned speaker IDs