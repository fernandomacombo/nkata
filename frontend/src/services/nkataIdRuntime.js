const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

export function fitNkataIdCaptureDimensions(width, height, maxSide = 1280) {
  const sourceWidth = Math.max(1, Number(width) || 1);
  const sourceHeight = Math.max(1, Number(height) || 1);
  const limit = Math.max(1, Number(maxSide) || 1280);
  const scale = Math.min(1, limit / Math.max(sourceWidth, sourceHeight));

  return {
    width: Math.max(1, Math.round(sourceWidth * scale)),
    height: Math.max(1, Math.round(sourceHeight * scale)),
  };
}

export function advanceNkataIdDetectionStability(
  previous,
  result,
  captureType,
  requiredReadings = 2,
) {
  const sameCapture = previous?.captureType === captureType;
  const count = result?.ready ? (sameCapture ? Number(previous?.count || 0) : 0) + 1 : 0;
  return {
    captureType,
    count,
    shouldCapture: count >= Math.max(1, Number(requiredReadings) || 2),
  };
}

export function nkataIdCameraConstraints(facingMode) {
  const isDocument = facingMode === "environment";
  return {
    video: {
      facingMode: { ideal: facingMode },
      width: { ideal: isDocument ? 1920 : 1280 },
      height: { ideal: isDocument ? 1080 : 720 },
    },
    audio: false,
  };
}

export async function optimizeNkataIdCameraTrack(track) {
  if (!track?.applyConstraints || !track?.getCapabilities) return false;
  const capabilities = track.getCapabilities() || {};
  const focusModes = Array.isArray(capabilities.focusMode)
    ? capabilities.focusMode
    : [];
  if (!focusModes.includes("continuous")) return false;

  try {
    await track.applyConstraints({ advanced: [{ focusMode: "continuous" }] });
    return true;
  } catch {
    // Nem todos os WebKit que anunciam a capacidade conseguem aplicá-la.
    return false;
  }
}

export function normalizeNkataIdAppOrigin(configuredOrigin, browserOrigin) {
  const candidate = String(configuredOrigin || browserOrigin || "").trim();
  if (!candidate) return "";

  try {
    const parsed = new URL(candidate);
    return parsed.origin;
  } catch {
    return "";
  }
}

export function isPhoneReachableNkataIdOrigin(origin) {
  try {
    const parsed = new URL(origin);
    return parsed.protocol === "https:" && !LOOPBACK_HOSTS.has(parsed.hostname.toLowerCase());
  } catch {
    return false;
  }
}

export function createNkataIdStatusPoller({
  load,
  onStatus,
  onError,
  intervalMs = 5000,
  rateLimitBackoffMs = 60000,
  retryMs = 15000,
  schedule = (callback, delay) => window.setTimeout(callback, delay),
  cancel = (timerId) => window.clearTimeout(timerId),
  createController = () => new AbortController(),
}) {
  let stopped = false;
  let running = false;
  let timerId = null;
  let controller = null;

  const queue = (delay) => {
    if (stopped) return;
    timerId = schedule(tick, delay);
  };

  const tick = async () => {
    if (stopped || running) return;
    running = true;
    controller = createController();
    let nextDelay = null;

    try {
      const result = await load({ signal: controller.signal });
      if (stopped) return;
      onStatus?.(result);
      if (!result?.can_submit && !result?.expired) {
        nextDelay = intervalMs;
      }
    } catch (error) {
      if (stopped || error?.name === "AbortError") return;
      onError?.(error);
      nextDelay = Number(error?.status) === 429 ? rateLimitBackoffMs : retryMs;
    } finally {
      running = false;
      controller = null;
      if (nextDelay !== null && !stopped) queue(nextDelay);
    }
  };

  // A resposta de criação já contém o primeiro estado. Aguardar antes da
  // primeira consulta evita uma chamada duplicada e também torna o efeito
  // seguro no modo estrito do React.
  queue(intervalMs);

  return () => {
    stopped = true;
    if (timerId !== null) cancel(timerId);
    controller?.abort?.();
  };
}
