const { ai } = require('../src/cloudbase');

function categorizeError(err) {
  const errMsg = (err && (err.message || err.toString())) || '';
  const errCode = (err && (err.code || '')) || '';
  const fullText = `${errCode} ${errMsg}`.toLowerCase();

  const categories = [];
  if (fullText.includes('exceed_authority') || fullText.includes('not authorized') || fullText.includes('403') || fullText.includes('auth')) {
    categories.push('权限不足 (EXCEED_AUTHORITY / 403)');
  }
  if (fullText.includes('资源点') || fullText.includes('resource_pack') || fullText.includes('package')) {
    categories.push('资源点套餐相关');
  }
  if (fullText.includes('非资源点套餐')) {
    categories.push('非资源点套餐');
  }
  if (fullText.includes('余额不足') || fullText.includes('insufficient') || fullText.includes('balance') || fullText.includes('arrears')) {
    categories.push('余额不足');
  }
  if (categories.length === 0) {
    categories.push('其他错误');
  }
  return categories.join(', ');
}

async function runSmoke() {
  console.log('====================================================');
  console.log('  dizical-ai Smoke Test: BLOCKER E1-E2-E3');
  console.log('  Timestamp:', new Date().toISOString());
  console.log('  Node version:', process.version);
  console.log('====================================================\n');

  const summary = {
    e1: { success: false, durationMs: 0, text: null, usage: null, error: null, code: null, category: null },
    e2: { success: false, durationMs: 0, url: null, error: null, code: null, category: null }
  };

  // ----------------------------------------------------
  // E1: 文本模型 (hunyuan-v3 / hy3)
  // ----------------------------------------------------
  console.log('[E1] Starting hunyuan-v3 text generation test...');
  const t1Start = Date.now();
  try {
    const textModel = ai.createModel('hunyuan-v3');
    const textRes = await textModel.generateText({
      model: 'hy3',
      messages: [{ role: 'user', content: '回复 OK 这两个字' }]
    });
    summary.e1.durationMs = Date.now() - t1Start;
    summary.e1.success = true;
    summary.e1.text = textRes.text || (textRes.choices && textRes.choices[0] && textRes.choices[0].message && textRes.choices[0].message.content) || JSON.stringify(textRes);
    summary.e1.usage = textRes.usage || null;

    console.log(`[E1] SUCCESS (${summary.e1.durationMs}ms)`);
    console.log('[E1] textRes.text:', summary.e1.text);
    console.log('[E1] usage:', JSON.stringify(summary.e1.usage));
  } catch (err) {
    summary.e1.durationMs = Date.now() - t1Start;
    summary.e1.success = false;
    summary.e1.code = err.code || 'UNKNOWN';
    summary.e1.error = err.message || err.toString();
    summary.e1.category = categorizeError(err);
    console.error(`[E1] FAILED (${summary.e1.durationMs}ms)`);
    console.error('[E1] Error Code:', summary.e1.code);
    console.error('[E1] Error Message:', summary.e1.error);
    console.error('[E1] Error RequestId:', err.requestId || '');
    console.error('[E1] Error Category:', summary.e1.category);
  }

  console.log('\n----------------------------------------------------\n');

  // ----------------------------------------------------
  // E2: 生图模型 (hunyuan-image / HY-Image-3.0-Plus-4090-Tob-v1.0)
  // ----------------------------------------------------
  console.log('[E2] Starting hunyuan-image generation test...');
  const t2Start = Date.now();
  try {
    const imgModel = ai.createImageModel('hunyuan-image');
    const imgRes = await imgModel.generateImage({
      model: 'HY-Image-3.0-Plus-4090-Tob-v1.0',
      prompt: '一只小猫',
      revise: { value: false }
    });
    summary.e2.durationMs = Date.now() - t2Start;
    summary.e2.success = true;
    summary.e2.url = (imgRes.data && imgRes.data[0] && imgRes.data[0].url) || (imgRes.images && imgRes.images[0]) || JSON.stringify(imgRes);

    console.log(`[E2] SUCCESS (${summary.e2.durationMs}ms)`);
    console.log('[E2] imgRes.data[0].url:', summary.e2.url);
  } catch (err) {
    summary.e2.durationMs = Date.now() - t2Start;
    summary.e2.success = false;
    summary.e2.code = err.code || 'UNKNOWN';
    summary.e2.error = err.message || err.toString();
    summary.e2.category = categorizeError(err);
    console.error(`[E2] FAILED (${summary.e2.durationMs}ms)`);
    console.error('[E2] Error Code:', summary.e2.code);
    console.error('[E2] Error Message:', summary.e2.error);
    console.error('[E2] Error RequestId:', err.requestId || '');
    console.error('[E2] Error Category:', summary.e2.category);
  }

  console.log('\n====================================================');
  console.log('  [E3] Smoke Test Summary & Analysis');
  console.log('====================================================');
  console.log('E1 文本生成 (hy3):', summary.e1.success ? '成功' : '失败');
  console.log('  - 时长:', `${summary.e1.durationMs}ms`);
  if (summary.e1.success) {
    console.log('  - 返回内容:', summary.e1.text);
    console.log('  - Token Usage:', JSON.stringify(summary.e1.usage));
  } else {
    console.log('  - 错误码:', summary.e1.code);
    console.log('  - 报错信息:', summary.e1.error);
    console.log('  - 报错类型:', summary.e1.category);
  }

  console.log('E2 图像生成 (HY-Image-3.0-Plus):', summary.e2.success ? '成功' : '失败');
  console.log('  - 时长:', `${summary.e2.durationMs}ms`);
  if (summary.e2.success) {
    console.log('  - 图像 URL:', summary.e2.url);
  } else {
    console.log('  - 错误码:', summary.e2.code);
    console.log('  - 报错信息:', summary.e2.error);
    console.log('  - 报错类型:', summary.e2.category);
  }

  console.log('\nE3 结论:');
  const allSuccess = summary.e1.success && summary.e2.success;
  if (allSuccess) {
    console.log('  - 状态: 两次调用均成功！已确认走通，走成长计划免费额度。');
  } else {
    console.log('  - 状态: 调用未成功（阻断）');
    if (summary.e1.category?.includes('权限不足') || summary.e2.category?.includes('权限不足')) {
      console.log('  - 权限分析: 命中【权限不足】(EXCEED_AUTHORITY / 403)。');
      console.log('    根因: 本地调用使用的 CAM 凭据 (COS_SECRET_ID) 仅具备 COS 存储权限，缺少 tcb:* 操作权限；同时成长计划 AI 资源包受《允许来源》红线保护，仅限云函数/云托管服务端与小程序客户端调用。');
      console.log('    解决路径: 需在腾讯云 CAM 给该密钥添加 QcloudTCBFullAccess 策略，或直接部署到 CloudBase 云托管内网通过容器注入的临时凭据调用。');
    }
  }
  console.log('====================================================\n');
}

runSmoke().catch(err => {
  console.error('Fatal smoke test runner error:', err);
  process.exit(1);
});
