

class MicrophoneProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    this.bufferSize = 2048; 
    this.targetSampleRate = 16000;
    this.inputSampleRate = 0;
  }

  downsample(input, inputSampleRate, targetSampleRate) {
    if (inputSampleRate === targetSampleRate) {
      return input;
    }

    const ratio = inputSampleRate / targetSampleRate;
    const newLength = Math.round(input.length / ratio);
    const result = new Float32Array(newLength);

    let offset = 0;
    for (let i = 0; i < newLength; i++) {
      const nextOffset = Math.round((i + 1) * ratio);
      let sum = 0;
      let count = 0;

      for (let j = offset; j < nextOffset && j < input.length; j++) {
        sum += input[j];
        count++;
      }

      result[i] = count ? sum / count : 0;
      offset = nextOffset;
    }

    return result;
  }

  floatTo16BitPCM(float32Array) {
    const int16Array = new Int16Array(float32Array.length);

    for (let i = 0; i < float32Array.length; i++) {
      const sample = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }

    return int16Array;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];

    if (!input || !input[0]) {
      return true;
    }

    const inputData = input[0];

    if (this.inputSampleRate === 0) {
      this.inputSampleRate = sampleRate;
    }

    const downsampled = this.downsample(
      inputData,
      this.inputSampleRate,
      this.targetSampleRate,
    );

    for (let i = 0; i < downsampled.length; i++) {
      this.buffer.push(downsampled[i]);
    }

    while (this.buffer.length >= this.bufferSize) {
      const chunk = this.buffer.slice(0, this.bufferSize);
      this.buffer = this.buffer.slice(this.bufferSize);

      const pcm = this.floatTo16BitPCM(new Float32Array(chunk));

      this.port.postMessage(
        {
          type: "audio",
          data: pcm.buffer,
          sampleRate: this.targetSampleRate,
        },
        [pcm.buffer],
      );
    }

    return true;
  }
}

registerProcessor("microphone-processor", MicrophoneProcessor);
