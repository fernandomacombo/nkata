import assert from "node:assert/strict";
import test from "node:test";

import {
  createNkataIdStatusPoller,
  isPhoneReachableNkataIdOrigin,
  normalizeNkataIdAppOrigin,
} from "../src/services/nkataIdRuntime.js";

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
