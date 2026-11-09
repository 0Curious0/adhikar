// Resamples the AudioContext's native input rate down to Prisma's required 16kHz mono, and emits
// exactly-1024-byte (512-sample) int16 PCM frames — Prisma's VAD is sensitive to send timing with
// no internal buffering, so framing has to happen here rather than being left to the caller.
// Lives in public/ (not src/) because AudioWorklet modules are loaded via a plain URL, not
// bundled — Vite's `?worker` import handling is specific to Web Workers, not AudioWorklets.
class PCMDownsampler extends AudioWorkletProcessor {
  static FRAME_SAMPLES = 512

  constructor(options) {
    super()
    const { inputSampleRate, outputSampleRate } = options.processorOptions
    this.ratio = inputSampleRate / outputSampleRate
    this.inputPos = 0
    this.pending = []
  }

  process(inputs) {
    const channel = inputs[0]?.[0]
    if (!channel || channel.length === 0) return true

    let pos = this.inputPos
    while (pos < channel.length) {
      const i0 = Math.floor(pos)
      const i1 = Math.min(i0 + 1, channel.length - 1)
      const frac = pos - i0
      const sample = channel[i0] * (1 - frac) + channel[i1] * frac
      const clamped = Math.max(-1, Math.min(1, sample))
      this.pending.push(Math.round(clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff))
      pos += this.ratio
    }
    this.inputPos = pos - channel.length

    while (this.pending.length >= PCMDownsampler.FRAME_SAMPLES) {
      const frame = this.pending.splice(0, PCMDownsampler.FRAME_SAMPLES)
      const int16 = new Int16Array(frame)
      this.port.postMessage(int16.buffer, [int16.buffer])
    }

    return true
  }
}

registerProcessor('pcm-downsampler', PCMDownsampler)
