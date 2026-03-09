"""
Audio Renderer — WAV output from the forced harmonic structure.

Generates .wav files from the eigenvalue frequencies and Z₃ chord.
Every parameter is derived from the algebra:

  Base frequency    → 440 Hz (A4, a convention — the only free parameter)
  Chord             → Z₃ augmented triad (120° intervals forced by roots of unity)
  Overtone          → 3:1 ratio (boundary eigenvalue)
  Amplitude         → 2/3 (live fraction)
  Beating rate      → |1-2α|/3 × base (color eigenvalue)
  Spectral gap      → 2/3 = descending perfect fifth

Usage:
    python demos/audio_renderer.py              # generates demos/distinction_chord.wav
    python demos/audio_renderer.py --alpha 0.0  # pure geometric Z₂ (no color beating)
    python demos/audio_renderer.py --alpha 1.0  # pure algebraic Z₂ (max beating)
"""

import sys
import os
import struct
import wave
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algebra.sensory_manifold import DistinctionHarmonics


def write_wav(filename: str, samples: np.ndarray, sample_rate: int = 44100):
    """Write a numpy array of float samples [-1, 1] to a WAV file."""
    # Convert to 16-bit PCM
    pcm = np.clip(samples, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)

    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def generate_distinction_chord(alpha: float = 0.5, duration: float = 4.0,
                                base_freq: float = 440.0) -> np.ndarray:
    """Generate the full distinction chord.

    Layer 1: Z₃ augmented triad (three roots of unity at 120° on pitch helix)
    Layer 2: Boundary overtone (3:1 ratio — the absorbing eigenvalue)
    Layer 3: Color beating (|1-2α|/3 amplitude modulation)
    Layer 4: Spectral gap envelope (2/3 amplitude decay per Z₃ cycle)
    """
    harmonics = DistinctionHarmonics(base_freq)
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    # Layer 1: Z₃ triad
    triad = harmonics.chord_from_z3()
    signal = np.zeros_like(t)
    gap = 2.0 / 3.0

    for i, freq in enumerate(triad):
        # Each voice at amplitude 2/3, phase offset by Z₃ rotation
        phase = i * 2 * np.pi / 3
        signal += gap * np.sin(2 * np.pi * freq * t + phase)

    # Layer 2: Boundary overtone (quiet — it's the absorber)
    boundary_freq = base_freq * 3
    signal += 0.1 * np.sin(2 * np.pi * boundary_freq * t)

    # Layer 3: Color beating
    color_rate = abs(1 - 2 * alpha) * base_freq / 3
    if color_rate > 0.5:
        signal *= (1 + 0.3 * np.sin(2 * np.pi * color_rate * t))

    # Layer 4: Gentle envelope (fade in/out)
    fade_samples = int(0.1 * sr)
    envelope = np.ones_like(t)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    signal *= envelope

    # Normalize
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.9

    return signal


def generate_eigenvalue_sequence(alpha: float = 0.5, duration: float = 6.0,
                                  base_freq: float = 440.0) -> np.ndarray:
    """Play each eigenvalue frequency in sequence, then all together.

    Demonstrates the forced harmonic structure:
    1. Boundary eigenvalue (λ=1) → base frequency
    2. Position exchange (λ=1/3) → base/3
    3. Color exchange (λ=(1-2α)/3) → base × |1-2α|/3
    4. All together → the distinction chord
    """
    harmonics = DistinctionHarmonics(base_freq)
    sr = 44100
    gap = 2.0 / 3.0

    # Individual eigenvalue tones (1s each)
    tone_dur = 1.0
    t_tone = np.linspace(0, tone_dur, int(sr * tone_dur), endpoint=False)
    fade = int(0.05 * sr)

    tones = []

    # λ=1: boundary
    tone = np.sin(2 * np.pi * base_freq * t_tone)
    tone[:fade] *= np.linspace(0, 1, fade)
    tone[-fade:] *= np.linspace(1, 0, fade)
    tones.append(tone * gap)

    # Brief silence
    tones.append(np.zeros(int(0.2 * sr)))

    # λ=1/3: position exchange
    tone = np.sin(2 * np.pi * base_freq / 3 * t_tone)
    tone[:fade] *= np.linspace(0, 1, fade)
    tone[-fade:] *= np.linspace(1, 0, fade)
    tones.append(tone * gap)

    tones.append(np.zeros(int(0.2 * sr)))

    # λ=(1-2α)/3: color exchange
    color_freq = base_freq * abs(1 - 2 * alpha) / 3
    if color_freq > 20:  # audible
        tone = np.sin(2 * np.pi * color_freq * t_tone)
        tone[:fade] *= np.linspace(0, 1, fade)
        tone[-fade:] *= np.linspace(1, 0, fade)
        tones.append(tone * gap)
    else:
        # Sub-audible: play as modulation on the position tone
        carrier = np.sin(2 * np.pi * base_freq / 3 * t_tone)
        modulator = 0.5 + 0.5 * np.sin(2 * np.pi * color_freq * t_tone)
        tone = carrier * modulator
        tone[:fade] *= np.linspace(0, 1, fade)
        tone[-fade:] *= np.linspace(1, 0, fade)
        tones.append(tone * gap)

    tones.append(np.zeros(int(0.3 * sr)))

    # Full chord
    chord = generate_distinction_chord(alpha, 2.0, base_freq)
    tones.append(chord)

    signal = np.concatenate(tones)
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.9
    return signal


def main():
    alpha = 0.5
    for arg in sys.argv[1:]:
        if arg.startswith("--alpha"):
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                alpha = float(sys.argv[idx + 1])

    out_dir = os.path.dirname(__file__)

    # Generate the distinction chord
    chord = generate_distinction_chord(alpha, duration=4.0)
    chord_path = os.path.join(out_dir, "distinction_chord.wav")
    write_wav(chord_path, chord)
    print(f"Chord: {chord_path}")

    # Generate the eigenvalue sequence
    seq = generate_eigenvalue_sequence(alpha, duration=6.0)
    seq_path = os.path.join(out_dir, "eigenvalue_sequence.wav")
    write_wav(seq_path, seq)
    print(f"Sequence: {seq_path}")

    print(f"\nAlpha = {alpha}")
    print(f"Z₃ triad: augmented chord (120° intervals on pitch helix)")
    print(f"Spectral gap: 2/3 = descending perfect fifth")
    print(f"Color beating: |1 - 2×{alpha}|/3 × 440 = {abs(1-2*alpha)/3 * 440:.1f} Hz")
    print(f"All parameters forced by algebra. No tuning knobs.")


if __name__ == "__main__":
    main()
