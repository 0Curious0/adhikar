// Prisma's REST STT endpoint (`POST /stt/v3`) only accepts mp3/flac/aac/m4a/wav/ogg — notably
// not webm, which is what MediaRecorder actually produces by default on Chrome/Edge (the
// majority browser). There's no single MediaRecorder mimeType that's both cross-browser-
// supported and Prisma-accepted, so instead of fighting codec selection at record time, decode
// whatever the browser recorded back to raw PCM (the same engine that can play the clip back can
// also decode it) and rewrap that PCM in a plain WAV header — no codec library needed either way,
// since WAV is just a header in front of raw samples.
export async function blobToWav(blob: Blob): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer()
  const audioContext = new AudioContext()
  try {
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
    const samples = downmixToMono(audioBuffer)
    const pcm16 = floatTo16BitPCM(samples)
    const header = buildWavHeader({
      dataLength: pcm16.byteLength,
      numChannels: 1,
      sampleRate: audioBuffer.sampleRate,
    })
    return new Blob([header, pcm16], { type: 'audio/wav' })
  } finally {
    await audioContext.close()
  }
}

function downmixToMono(audioBuffer: AudioBuffer): Float32Array {
  if (audioBuffer.numberOfChannels === 1) return audioBuffer.getChannelData(0)

  // Spoken-voice input only — a simple channel average is plenty, no need for a proper mixdown.
  const length = audioBuffer.length
  const mixed = new Float32Array(length)
  for (let channel = 0; channel < audioBuffer.numberOfChannels; channel++) {
    const data = audioBuffer.getChannelData(channel)
    for (let i = 0; i < length; i++) mixed[i] += data[i] / audioBuffer.numberOfChannels
  }
  return mixed
}

function floatTo16BitPCM(samples: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(samples.length * 2)
  const view = new DataView(buffer)
  for (let i = 0; i < samples.length; i++) {
    const clamped = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
  }
  return buffer
}

function buildWavHeader(params: { dataLength: number; numChannels: number; sampleRate: number }): ArrayBuffer {
  const { dataLength, numChannels, sampleRate } = params
  const bytesPerSample = 2
  const blockAlign = numChannels * bytesPerSample
  const byteRate = sampleRate * blockAlign

  const buffer = new ArrayBuffer(44)
  const view = new DataView(buffer)
  const writeString = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i))
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + dataLength, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, byteRate, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, 16, true) // bits per sample
  writeString(36, 'data')
  view.setUint32(40, dataLength, true)

  return buffer
}
