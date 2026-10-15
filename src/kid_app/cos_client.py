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


def sdk_version() -> str:
    """qcloud_cos (pip 名 cos-python-sdk-v5) 的实测导入状态 + 版本.

    P0 (sprint-26101302, 2026-10-13): 解释器漂移会让这个包静默 MISSING,
    is_available 随之 False → 图静默回落 static。服务启动时把它打进日志(见 app.py [cos-selfcheck])。
    """
    if CosS3Client is None:
        return "MISSING (cos-python-sdk-v5 未装在该解释器里)"
    try:
        import importlib.metadata as _md
        return _md.version("cos-python-sdk-v5")
    except Exception:  # noqa: BLE001 (元数据读不到不影响可用性)
        return "unknown(installed)"


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

    def object_url(self, filename: str) -> str:
        """公开读 URL — 用 CDN 域名 (tcb.qcloud.la), 已验证 200; COS 直连域名对公开读桶 403.

        注意 (P0 sprint-26101302): 这是**公开 CDN** 域, 可能按 CDN 规则缓存 ——
        可变对象(草稿 JSON) 不能用它读, 走 SDK get_object (self.download) 才拿到最新字节。
        """
        return f"https://{self.bucket}.tcb.qcloud.la/{filename}"

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
        return self.object_url(filename)

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

        return self.object_url(filename)

    def exists(self, filename: str) -> bool:
        """对象是否存在 (head_object). 404 → False; 其它异常抛 (fail loud, 不把网络故障当"不存在")."""
        if not self.is_available:
            raise RuntimeError("COS 未配置, 无法 head_object")
        try:
            self._cos_client.head_object(Bucket=self.bucket, Key=filename)  # type: ignore[union-attr]
            return True
        except Exception as e:  # noqa: BLE001
            if self._is_not_found(e):
                return False
            raise RuntimeError(f"COS head_object 失败: {e}") from e

    def download(self, filename: str) -> bytes:
        """读对象字节 (get_object, 走 SDK 不走公开 CDN —— CDN 可能缓存旧版本).

        Raises:
            FileNotFoundError: 对象不存在 (key 写错 / 被清)
            RuntimeError: 其它失败 (凭据 / 网络)
        """
        if not self.is_available:
            raise RuntimeError("COS 未配置, 无法下载")
        try:
            resp = self._cos_client.get_object(  # type: ignore[union-attr]
                Bucket=self.bucket, Key=filename,
            )
        except Exception as e:  # noqa: BLE001
            if self._is_not_found(e):
                raise FileNotFoundError(f"COS 对象不存在: {filename}") from e
            raise RuntimeError(f"COS get_object 失败: {e}") from e

        body = resp.get("Body")
        if body is None:
            raise RuntimeError(f"COS get_object 响应无 Body: {filename}")
        if hasattr(body, "get_raw_stream"):
            return body.get_raw_stream().read()
        if hasattr(body, "read"):
            return body.read()
        return bytes(body)  # type: ignore[arg-type]

    @staticmethod
    def _is_not_found(e: Exception) -> bool:
        """判定 404 —— CosServiceError.get_status_code()==404, 退化时看错误字符串."""
        getter = getattr(e, "get_status_code", None)
        if callable(getter):
            try:
                if getter() == 404:
                    return True
            except Exception:  # noqa: BLE001
                pass
        return "404" in str(e) or "NoSuchKey" in str(e) or "NoSuchResource" in str(e)

    def list_keys(self, prefix: str, max_keys: int = 200) -> list[str]:
        """列对象 key (分页聚合). 读草稿列表用 —— 失败抛 (不许静默当成"空").

        Raises:
            RuntimeError: 未配置 / 网络或凭据错误
        """
        if not self.is_available:
            raise RuntimeError("COS 未配置, 无法 list_objects")
        keys: list[str] = []
        marker = ""
        try:
            while True:
                kw = {"Bucket": self.bucket, "Prefix": prefix, "MaxKeys": min(1000, max_keys)}
                if marker:
                    kw["Marker"] = marker
                resp = self._cos_client.list_objects(**kw)  # type: ignore[union-attr]
                contents = resp.get("Contents") or []
                keys.extend(c["Key"] for c in contents)
                if len(contents) < kw["MaxKeys"] or len(keys) >= max_keys:
                    break
                marker = contents[-1]["Key"]
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"COS list_objects 失败: {e}") from e
        return keys[:max_keys]

    def delete_object(self, filename: str) -> bool:
        """删对象 (idempotent). 存在并删成功返 True; 本来不存在返 False; 其它失败抛."""
        if not self.is_available:
            raise RuntimeError("COS 未配置, 无法 delete_object")
        try:
            self._cos_client.delete_object(Bucket=self.bucket, Key=filename)  # type: ignore[union-attr]
        except Exception as e:  # noqa: BLE001
            if self._is_not_found(e):
                return False
            raise RuntimeError(f"COS delete_object 失败: {e}") from e
        return True


# 模块级单例 (与 app.py 里其他单例风格一致)
cos_uploader = CosUploader()
