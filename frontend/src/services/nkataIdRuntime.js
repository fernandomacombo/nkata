const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

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
