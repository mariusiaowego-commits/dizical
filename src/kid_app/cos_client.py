"""COS 云存储上传客户端 (PR-F).

把 /uploads 上传的图片存到 CloudBase COS, 解决 CloudRun 容器重启丢图问题.
- 配置: COS_BUCKET / COS_REGION / COS_SECRET_ID / COS_SECRET_KEY (EnvParams 或环境变量)
- 无完整配置时 is_available=False, 调用方回落本地磁盘 (开发环境)
- 上传失败 raise (fail loud), 不静默降级
"""
import os
from typing import Optional

try:
    from qcloud_cos import CosConfig, CosS3Client
except ImportError:  # 依赖未装 (如纯测试环境) 时降级
    CosConfig = None
    CosS3Client = None


class CosUploader:
    """封装 COS 上传. 配置来自环境变量."""

    def __init__(self) -> None:
        self.bucket = os.getenv("COS_BUCKET", "").strip()
        self.region = os.getenv("COS_REGION", "ap-shanghai").strip()
        self.secret_id = os.getenv("COS_SECRET_ID", "").strip()
        self.secret_key = os.getenv("COS_SECRET_KEY", "").strip()
        self._client: Optional[object] = None

    @property
    def is_available(self) -> bool:
        """有完整配置且 SDK 可导入才可用."""
        return bool(self.bucket and self.secret_id and self.secret_key and CosS3Client is not None)

    @property
    def _cos_client(self):
        if self._client is None:
            if not self.is_available:
                raise RuntimeError("COS 配置不完整, 无法创建客户端")
            config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
            )
            self._client = CosS3Client(config)  # type: ignore[call-arg]
        return self._client

    def upload(self, filename: str, content: bytes, content_type: str = "image/jpeg") -> str:
        """上传到 COS, 返回公开 URL.

        Args:
            filename: 对象键 (uuid4 随机名, 防枚举)
            content: 文件字节
            content_type: Content-Type

        Returns:
            公开可访问的 COS URL

        Raises:
            RuntimeError: 上传失败 (fail loud, 调用方转 500)
        """
        if not self.is_available:
            raise RuntimeError("COS 未配置, 无法上传")
        try:
            resp = self._cos_client.put_object(  # type: ignore[union-attr]
                Bucket=self.bucket,
                Key=filename,
                Body=content,
                ContentType=content_type,
            )
            etag = resp.get("ETag", "")
            if not etag:
                raise RuntimeError("COS 上传响应异常 (无 ETag)")
        except Exception as e:
            # 透传, 但包装成明确错误信息
            raise RuntimeError(f"COS 上传失败: {e}") from e

        # 公开读 URL — 用 CDN 域名 (tcb.qcloud.la), 已验证 200; COS 直连域名对公开读桶 403
        return f"https://{self.bucket}.tcb.qcloud.la/{filename}"

    def upload_stream(self, filename: str, file_obj, content_type: str = "video/mp4") -> str:
        """流式上传 (用于视频, 不读 bytes 防 OOM).

        Args:
            filename: 对象键 (uuid4 随机名, 前缀如 videos/)
            file_obj: 文件对象/流 (如 file.file 或 io.BytesIO)
            content_type: Content-Type

        Returns:
            公开可访问的 COS URL

        Raises:
            RuntimeError: 上传失败 (fail loud, 调用方转 500)
        """
        if not self.is_available:
            raise RuntimeError("COS 未配置, 无法上传")
        try:
            resp = self._cos_client.put_object(  # type: ignore[union-attr]
                Bucket=self.bucket,
                Key=filename,
                Body=file_obj,
                ContentType=content_type,
            )
            etag = resp.get("ETag", "")
            if not etag:
                raise RuntimeError("COS 上传响应异常 (无 ETag)")
        except Exception as e:
            raise RuntimeError(f"COS 上传失败: {e}") from e

        return f"https://{self.bucket}.tcb.qcloud.la/{filename}"


# 模块级单例 (与 app.py 里其他单例风格一致)
cos_uploader = CosUploader()
