/**
 * pcm-capture-processor
 *
 * AudioWorkletProcessor for the Gemini Live voice coach (Phase 2).
 * Runs on the audio render thread and:
 *   - receives mono Float32 mic frames at the AudioContext sample rate,
 *   - downsamples to 16 kHz with linear interpolation,
 *   - converts Float32 [-1,1] -> 16-bit little-endian PCM,
 *   - computes a per-frame RMS level for local VAD / barge-in,
 *   - posts { pcm: ArrayBuffer, rms: number } to the main thread (buffer transferred).
 *
 * Gemini Live requires 16-bit PCM, 16 kHz, mono, little-endian on input.
 */
const TARGET_SAMPLE_RATE = 16000;

class PCMCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // `sampleRate` is a global available inside the worklet scope (e.g. 48000).
    this._ratio = sampleRate / TARGET_SAMPLE_RATE;
    // Fractional read position within the current input block; carries across blocks.
    this._pos = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) {
      return true;
    }
    const channel = input[0];
    if (!channel || channel.length === 0) {
      return true;
    }

    const n = channel.length;

    // Per-frame RMS on the raw input (cheap local VAD signal).
    let sumSq = 0;
    for (let i = 0; i < n; i++) {
      sumSq += channel[i] * channel[i];
    }
    const rms = Math.sqrt(sumSq / n);

    // Downsample to 16 kHz via linear interpolation.
    const out = [];
    while (this._pos < n) {
      const idx = Math.floor(this._pos);
      const frac = this._pos - idx;
      const s0 = channel[idx];
      const s1 = idx + 1 < n ? channel[idx + 1] : channel[n - 1];
      out.push(s0 + (s1 - s0) * frac);
      this._pos += this._ratio;
    }
    this._pos -= n;

    // Float32 [-1,1] -> Int16 little-endian PCM.
    const pcm = new Int16Array(out.length);
    for (let i = 0; i < out.length; i++) {
      let s = out[i];
      if (s > 1) s = 1;
      else if (s < -1) s = -1;
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }

    this.port.postMessage({ pcm: pcm.buffer, rms }, [pcm.buffer]);
    return true;
  }
}

registerProcessor('pcm-capture-processor', PCMCaptureProcessor);
