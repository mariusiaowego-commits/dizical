const fs = require('fs');
const express = require('express');
const { app: cloudbaseApp, ai } = require('./cloudbase');

const app = express();
const PORT = process.env.PORT || 8080;

// 防止任何 secret 回显的兜底
function redact(obj) {
  if (typeof obj !== 'object' || obj === null) return obj;
  if (Array.isArray(obj)) return obj.map(redact);
  const out = {};
  for (const [k, v] of Object.entries(obj)) {
    if (/(key|secret|token|password|akid|skid)/i.test(k)) {
      out[k] = '<REDACTED>';
    } else {
      out[k] = redact(v);
    }
  }
  return out;
}

app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    uptime: process.uptime(),
    version: '0.1.0',
  });
});

app.get('/diag', async (req, res) => {
  let metadataOk = false;
  let metadataMsg = null;
  try {
    const { getTmpSecret } = require('@cloudbase/node-sdk/dist/utils/metadata-secret');
    const s = await getTmpSecret();
    metadataOk = !!(s && s.id);
  } catch (e) {
    metadataMsg = e.message;
  }

  let hasToken = false;
  try {
    const { loadWxCloudbaseAccesstoken } = require('@cloudbase/node-sdk/dist/utils/wxCloudToken');
    const token = loadWxCloudbaseAccesstoken();
    hasToken = !!token;
  } catch (e) {}

  res.json({
    status: 'ok',
    uptime: process.uptime(),
    cbr_env_id: process.env.CBR_ENV_ID || null,
    has_secret_id: !!(process.env.TENCENTCLOUD_SECRETID || process.env.TCB_SECRETID || process.env.COS_SECRET_ID),
    metadata_ok: metadataOk,
    metadata_error: metadataMsg,
    has_token_file: fs.existsSync('/.tencentcloudbase/wx/cloudbase_access_token'),
    has_token: hasToken,
  });
});

app.get('/smoke', async (req, res) => {
  const result = { text: null, image: null, errors: [] };
  const aiClient = ai || cloudbaseApp.ai();

  try {
    const t0 = Date.now();
    const tr = await aiClient.createModel('hunyuan-v3').generateText({
      model: 'hy3',
      messages: [{ role: 'user', content: '回复 OK 这两个字' }],
    });
    result.text = {
      ok: !!(tr && tr.text),
      text: tr ? tr.text : null,
      usage: tr && tr.usage ? redact(tr.usage) : null,
      duration_ms: Date.now() - t0,
    };
  } catch (e) {
    result.errors.push({ kind: 'text', message: e.message, code: e.code || 'ERR_TEXT' });
  }

  try {
    const i0 = Date.now();
    const ir = await aiClient.createImageModel('hunyuan-image').generateImage({
      model: 'HY-Image-3.0-Plus-4090-Tob-v1.0',
      prompt: '一只小猫',
      revise: { value: false },
    });
    const imgUrl = (ir && ir.data && ir.data[0] && ir.data[0].url) || null;
    result.image = {
      ok: !!imgUrl,
      url: imgUrl,
      duration_ms: Date.now() - i0,
    };
  } catch (e) {
    result.errors.push({ kind: 'image', message: e.message, code: e.code || 'ERR_IMAGE' });
  }

  res.json(result);
});

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`dizical-ai listening on :${PORT}`);
});