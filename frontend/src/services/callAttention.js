let audioContext = null;
let attentionActive = false;
let attentionTimer = null;
let unlockInstalled = false;
let unlocked = false;

function getAudioContext() {
  if (typeof window === "undefined") return null;
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return null;
  if (!audioContext) audioContext = new AudioContextClass();
  return audioContext;
}

async function unlockAudio() {
  const context = getAudioContext();
  if (!context) return false;
  try {
    if (context.state !== "running") await context.resume();
    unlocked = context.state === "running";
  } catch {
    unlocked = false;
  }
  return unlocked;
}

function playTone(context, frequency, offsetSeconds, durationSeconds) {
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  const startAt = context.currentTime + offsetSeconds;
  const endAt = startAt + durationSeconds;

  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(frequency, startAt);
  gain.gain.setValueAtTime(0.0001, startAt);
  gain.gain.exponentialRampToValueAtTime(0.045, startAt + 0.025);
  gain.gain.exponentialRampToValueAtTime(0.0001, endAt);

  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start(startAt);
  oscillator.stop(endAt + 0.02);
}

function ringOnce() {
  if (!attentionActive) return;

  const context = getAudioContext();
  if (context?.state === "running" && unlocked) {
    playTone(context, 659.25, 0, 0.32);
    playTone(context, 783.99, 0.38, 0.34);
  }

  try {
    navigator.vibrate?.([220, 110, 220]);
  } catch {
    // Vibração é opcional e não está disponível em todos os browsers.
  }
}

export function installCallAttentionUnlock() {
  if (typeof window === "undefined" || unlockInstalled) return () => {};
  unlockInstalled = true;

  const unlock = () => {
    unlockAudio().catch(() => {});
  };

  window.addEventListener("pointerdown", unlock, { passive: true });
  window.addEventListener("keydown", unlock);
  window.addEventListener("touchend", unlock, { passive: true });

  return () => {
    window.removeEventListener("pointerdown", unlock);
    window.removeEventListener("keydown", unlock);
    window.removeEventListener("touchend", unlock);
    unlockInstalled = false;
  };
}

export function startIncomingCallAttention() {
  if (attentionActive) return;
  attentionActive = true;
  unlockAudio().finally(() => ringOnce());
  attentionTimer = window.setInterval(ringOnce, 1900);
}

export function stopIncomingCallAttention() {
  attentionActive = false;
  if (attentionTimer) {
    window.clearInterval(attentionTimer);
    attentionTimer = null;
  }
  try {
    navigator.vibrate?.(0);
  } catch {
    // Sem suporte à vibração, não há nada para interromper.
  }
}
