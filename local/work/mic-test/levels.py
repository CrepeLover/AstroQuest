# Loudness of a 16-bit WAV in 100 ms windows, measured the way the emulator does (RMS of all
# samples, dBFS), against Astro Bot's blow thresholds (-21 dB = half strength, -9 dB = full).
import sys
import wave

import numpy as np

w = wave.open(sys.argv[1], 'rb')
rate, ch = w.getframerate(), w.getnchannels()
data = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64) / 32768.0
data = data[: len(data) // ch * ch].reshape(-1, ch)
win = rate // 10
n = len(data) // win
db = []
for i in range(n):
    seg = data[i * win:(i + 1) * win]
    rms = np.sqrt(np.mean(seg * seg))
    db.append(20 * np.log10(rms) if rms > 0 else -120.0)
db = np.array(db)
print(f'{len(data) / rate:.1f} s, {ch} channels, {rate} Hz')
print(f'exact-zero windows: {(db <= -119).sum()} of {n}; median {np.median(db):.0f} dB; '
      f'loudest {db.max():.1f} dB')
print(f'windows >= -21 dB (half-strength blow): {(db >= -21).sum()}, >= -9 dB (full): {(db >= -9).sum()}')
# Events: runs of windows louder than -40 dB.
print('\nsounds (runs louder than -40 dB):')
i = 0
while i < n:
    if db[i] > -40:
        j = i
        while j < n and db[j] > -40:
            j += 1
        seg = db[i:j]
        print(f'  {i / 10:6.1f}-{j / 10:6.1f} s  peak {seg.max():6.1f} dB  mean {seg.mean():6.1f} dB')
        i = j
    else:
        i += 1
# Spectrum of the loudest second: breath noise is broadband, speech has harmonics.
k = int(db.argmax())
seg = data[max(0, k - 5) * win:(k + 5) * win].mean(axis=1)
if len(seg):
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), 1 / rate)
    bands = [(0, 300), (300, 1000), (1000, 3000), (3000, 8000), (8000, 24000)]
    total = (spec ** 2).sum() or 1
    print('\nenergy by band around the loudest moment: ' + ', '.join(
        f'{a}-{b} Hz {100 * (spec[(freqs >= a) & (freqs < b)] ** 2).sum() / total:.0f}%' for a, b in bands))
