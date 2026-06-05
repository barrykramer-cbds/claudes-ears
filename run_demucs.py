import os
import torch
import torchaudio
import soundfile as sf
import numpy as np
import sys

# Patch torchaudio.save to use soundfile instead of broken torchcodec
original_save = torchaudio.save
def patched_save(filepath, src, sample_rate, **kwargs):
    wav = src.cpu().numpy()
    if wav.shape[0] <= 2:  # channels first -> channels last
        wav = wav.T
    sf.write(str(filepath).replace('.mp3', '.wav').replace('.m4a', '.wav'), wav, sample_rate)
    print(f"    Saved: {filepath}")
torchaudio.save = patched_save

# Run demucs. Output root is configurable; default is ./stems next to the repo.
out_root = os.environ.get('CLAUDES_EARS_STEMS_ROOT', 'stems')

from demucs.separate import main
sys.argv = ['demucs', '-n', 'htdemucs', '-o', out_root] + sys.argv[1:]
main()
