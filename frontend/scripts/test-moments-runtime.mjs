import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = (await readFile(new URL('../src/services/momentsApi.js', import.meta.url), 'utf8')).replace('import { API_BASE_URL } from "./api.js";', 'const API_BASE_URL = "";');
const api = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
test('Moment request sends caption and persisted appearance; returns server moment', async () => {
  const oldFetch = globalThis.fetch;
  const oldDocument = globalThis.document;
  globalThis.document = { cookie: 'csrftoken=test' };
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/momentos/');
    assert.equal(options.body.get('caption'), 'DIA_TRANQUILO');
    assert.equal(options.body.get('theme'), 'sand');
    assert.equal(options.body.get('font'), 'italic');
    return new Response(JSON.stringify({ id: 1, text: 'Um dia tranquilo por aqui.', theme: 'sand', font: 'italic' }), { status: 201, headers: { 'content-type': 'application/json' } });
  };
  try {
    const moment = await api.createMoment({ caption: 'DIA_TRANQUILO', theme: 'sand', font: 'italic' });
    assert.equal(moment.id, 1);
    assert.equal(moment.text, 'Um dia tranquilo por aqui.');
  } finally { globalThis.fetch = oldFetch; globalThis.document = oldDocument; }
});
