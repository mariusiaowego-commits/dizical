const fs = require('fs');
const path = require('path');
const os = require('os');
const tcb = require('@cloudbase/node-sdk');

// 全局异常防护，防止未捕获异常或拒绝引发 Node 进程退出
process.on('uncaughtException', (err) => {
  // eslint-disable-next-line no-console
  console.error('[UNCAUGHT_EXCEPTION]', (err && err.stack) || err);
});
process.on('unhandledRejection', (reason) => {
  // eslint-disable-next-line no-console
  console.error('[UNHANDLED_REJECTION]', (reason && reason.stack) || reason);
});

// 兼容 SDK bug 1：当 OpenAPI 返回 4xx/5xx 错误且 body 已被解析为对象时，
// 保证 AIRequestAdapter 能正确提取 error.code / error.message
try {
  const openapicommonrequester = require('@cloudbase/node-sdk/dist/utils/tcbopenapicommonrequester');
  if (openapicommonrequester && typeof openapicommonrequester.request === 'function') {
    const origRequest = openapicommonrequester.request;
    openapicommonrequester.request = async function(args) {
      const res = await origRequest.apply(this, arguments);
      if (res && res.statusCode >= 400 && res.body && typeof res.body === 'object' && !Buffer.isBuffer(res.body)) {
        res.body = JSON.stringify(res.body);
      }
      return res;
    };
  }
} catch (e) {
  // 忽略补丁失败
}

// 修复 SDK bug 2: openapicommonrequester.prepareCredentials 缺失 await/return 导致未捕获 Promise 拒绝与 Node 崩溃，
// 同时补充对云托管容器内元数据服务（TCB_QcsRole）及访问令牌的自动获取
try {
  const tcbapirequester = require('@cloudbase/node-sdk/dist/utils/tcbapirequester');
  const openapi = require('@cloudbase/node-sdk/dist/utils/tcbopenapicommonrequester');
  if (openapi && openapi.TcbOpenApiHttpCommonRequester) {
    openapi.TcbOpenApiHttpCommonRequester.prototype.prepareCredentials = async function() {
      if (!this.config.secretId || !this.config.secretKey) {
        // 尝试从元数据服务获取 IAM 临时凭据 (TCB_QcsRole / CBR_ROLE)
        try {
          const { getTmpSecret } = require('@cloudbase/node-sdk/dist/utils/metadata-secret');
          const tmp = await getTmpSecret();
          if (tmp && tmp.id && tmp.key) {
            this.config.secretId = tmp.id;
            this.config.secretKey = tmp.key;
            this.config.sessionToken = tmp.token;
            return;
          }
        } catch (e) {}

        // 尝试从 CBR 访问令牌文件获取
        try {
          const { loadWxCloudbaseAccesstoken } = require('@cloudbase/node-sdk/dist/utils/wxCloudToken');
          const token = loadWxCloudbaseAccesstoken();
          if (token) {
            this.config.accessKey = token;
            return;
          }
        } catch (e) {}
      }
      return tcbapirequester.prepareCredentials.bind(this)();
    };
  }
} catch (e) {
  // 忽略补丁失败
}

// 本地开发环境：若环境变量中无腾讯云凭据，尝试从 ~/.dizical/.env 读取备用凭据
if (!process.env.TENCENTCLOUD_SECRETID && !process.env.TCB_SECRETID) {
  try {
    const envFile = path.join(os.homedir(), '.dizical', '.env');
    if (fs.existsSync(envFile)) {
      const content = fs.readFileSync(envFile, 'utf-8');
      content.split('\n').forEach(line => {
        const match = line.match(/^export\s+([^=]+)=(.*)$/);
        if (match) {
          const key = match[1].trim();
          const val = match[2].trim().replace(/^['"]|['"]$/g, '');
          if (!process.env[key]) {
            process.env[key] = val;
          }
        }
      });
      if (process.env.COS_SECRET_ID && !process.env.TENCENTCLOUD_SECRETID) {
        process.env.TENCENTCLOUD_SECRETID = process.env.COS_SECRET_ID;
      }
      if (process.env.COS_SECRET_KEY && !process.env.TENCENTCLOUD_SECRETKEY) {
        process.env.TENCENTCLOUD_SECRETKEY = process.env.COS_SECRET_KEY;
      }
    }
  } catch (err) {
    // 忽略文件读取错误（云托管容器内置凭据）
  }
}

// 单例模式初始化 CloudBase
let appInstance = null;
let aiInstance = null;

function getApp() {
  if (!appInstance) {
    appInstance = tcb.init({
      env: process.env.CLOUDBASE_ENV_ID || 'cloud1-d4gfwyvsk1435e2e4',
      timeout: 60000
    });
  }
  return appInstance;
}

function getAi() {
  if (!aiInstance) {
    aiInstance = getApp().ai();
  }
  return aiInstance;
}

const app = getApp();
const ai = getAi();

module.exports = {
  app,
  ai,
  getApp,
  getAi
};
