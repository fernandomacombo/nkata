import assert from "node:assert/strict";
import test from "node:test";

import {
  advanceNkataIdDetectionStability,
  createNkataIdStatusPoller,
  fitNkataIdCaptureDimensions,
  isPhoneReachableNkataIdOrigin,
  nkataIdCameraConstraints,
  normalizeNkataIdAppOrigin,
  optimizeNkataIdCameraTrack,
} from "../src/services/nkataIdRuntime.js";

test("captura apenas depois de duas deteções estáveis consecutivas", () => {
  let state = advanceNkataIdDetectionStability(
    null,
    { ready: true },
    "selfie_ao_vivo",
  );
  assert.equal(state.count, 1);
  assert.equal(state.shouldCapture, false);

  state = advanceNkataIdDetectionStability(
    state,
    { ready: true },
    "selfie_ao_vivo",
  );
  assert.equal(state.count, 2);
  assert.equal(state.shouldCapture, true);

  state = advanceNkataIdDetectionStability(
    state,
    { ready: false },
    "selfie_ao_vivo",
  );
  assert.equal(state.count, 0);
  assert.equal(state.shouldCapture, false);
});

test("limita a captura a 1280 px sem deformar a imagem", () => {
  assert.deepEqual(fitNkataIdCaptureDimensions(3024, 4032), {
    width: 960,
    height: 1280,
  });
  assert.deepEqual(fitNkataIdCaptureDimensions(1280, 720), {
    width: 1280,
    height: 720,
  });
  assert.deepEqual(fitNkataIdCaptureDimensions(640, 480), {
    width: 640,
    height: 480,
  });
});

test("pede maior resolução para o BI e mantém a câmara frontal leve", () => {
  assert.deepEqual(nkataIdCameraConstraints("environment"), {
    video: {
      facingMode: { ideal: "environment" },
      width: { ideal: 1920 },
      height: { ideal: 1080 },
    },
    audio: false,
  });
  assert.equal(nkataIdCameraConstraints("user").video.width.ideal, 1280);
});

test("ativa focagem contínua apenas quando a câmara a suporta", async () => {
  let applied = null;
  const supported = await optimizeNkataIdCameraTrack({
    getCapabilities: () => ({ focusMode: ["manual", "continuous"] }),
    applyConstraints: async (constraints) => { applied = constraints; },
  });
  assert.equal(supported, true);
  assert.deepEqual(applied, { advanced: [{ focusMode: "continuous" }] });

  const unsupported = await optimizeNkataIdCameraTrack({
    getCapabilities: () => ({}),
    applyConstraints: async () => assert.fail("não deve aplicar constraints"),
  });
  assert.equal(unsupported, false);
});

function manualScheduler() {
  const jobs = [];
  return {
    jobs,
    schedule(callback, delay) {
      const job = { callback, delay, cancelled: false };
      jobs.push(job);
      return job;
    },
    cancel(job) {
      if (job) job.cancelled = true;
    },
    next() {
      return jobs.find((job) => !job.cancelled);
    },
    remove(job) {
      const index = jobs.indexOf(job);
      if (index >= 0) jobs.splice(index, 1);
    },
  };
}

test("usa a origem pública configurada e rejeita localhost para o telefone", () => {
  const origin = normalizeNkataIdAppOrigin(
    "https://192.168.0.101:5173/qualquer-rota",
    "http://localhost:5173",
  );
  assert.equal(origin, "https://192.168.0.101:5173");
  assert.equal(isPhoneReachableNkataIdOrigin(origin), true);
  assert.equal(isPhoneReachableNkataIdOrigin("http://localhost:5173"), false);
  assert.equal(isPhoneReachableNkataIdOrigin("http://127.0.0.1:5173"), false);
  assert.equal(isPhoneReachableNkataIdOrigin("http://192.168.0.101:5173"), false);
});

test("mantém exatamente uma consulta agendada por sessão", async () => {
  const scheduler = manualScheduler();
  let calls = 0;
  const updates = [];
  const stop = createNkataIdStatusPoller({
    load: async () => {
      calls += 1;
      return { token: "sessao", can_submit: false, expired: false };
    },
    onStatus: (result) => updates.push(result),
    schedule: scheduler.schedule,
    cancel: scheduler.cancel,
  });

  assert.equal(scheduler.jobs.filter((job) => !job.cancelled).length, 1);
  const first = scheduler.next();
  scheduler.remove(first);
  await first.callback();
  assert.equal(calls, 1);
  assert.equal(updates.length, 1);
  assert.equal(scheduler.jobs.filter((job) => !job.cancelled).length, 1);

  stop();
  assert.equal(scheduler.jobs.filter((job) => !job.cancelled).length, 0);
});

test("para de consultar quando as capturas terminam", async () => {
  const scheduler = manualScheduler();
  const stop = createNkataIdStatusPoller({
    load: async () => ({ can_submit: true, expired: false }),
    schedule: scheduler.schedule,
    cancel: scheduler.cancel,
  });

  const first = scheduler.next();
  scheduler.remove(first);
  await first.callback();
  assert.equal(scheduler.jobs.filter((job) => !job.cancelled).length, 0);
  stop();
});

test("aplica espera maior depois de um limite 429", async () => {
  const scheduler = manualScheduler();
  const stop = createNkataIdStatusPoller({
    load: async () => {
      const error = new Error("Muitos pedidos");
      error.status = 429;
      throw error;
    },
    schedule: scheduler.schedule,
    cancel: scheduler.cancel,
    rateLimitBackoffMs: 60000,
  });

  const first = scheduler.next();
  scheduler.remove(first);
  await first.callback();
  assert.equal(scheduler.next().delay, 60000);
  stop();
});
