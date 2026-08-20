let audioContext: AudioContext | null = null;

const context = (): AudioContext | null => {
  if (audioContext !== null) return audioContext;
  if (typeof window === 'undefined') return null;
  const AudioContextConstructor = window.AudioContext;
  if (AudioContextConstructor === undefined) return null;
  audioContext = new AudioContextConstructor();
  return audioContext;
};

/**
 * Browsers only permit notification audio after a user gesture. AppShell
 * calls this from pointer/keyboard interaction so later background queue
 * updates are allowed to make a sound.
 */
export const unlockReviewAlertSound = (): void => {
  const current = context();
  if (current?.state === 'suspended') void current.resume();
};

/** A short, neutral two-note chime for a new review item. */
export const playReviewAlertSound = (): void => {
  const current = context();
  if (current === null || current.state !== 'running') return;

  const now = current.currentTime;
  const playTone = (frequency: number, start: number): void => {
    const oscillator = current.createOscillator();
    const gain = current.createGain();
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(frequency, start);
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.12, start + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.16);
    oscillator.connect(gain);
    gain.connect(current.destination);
    oscillator.start(start);
    oscillator.stop(start + 0.17);
  };

  playTone(660, now);
  playTone(880, now + 0.13);
};
