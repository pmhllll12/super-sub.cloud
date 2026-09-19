"""`PhotoStoragePort` 의 S3 구현.

사진은 **앱 서버를 지나지 않는다**(PER-002). 브라우저가 사전 서명 URL 로 S3 에
직접 PUT 하고, 서버는 키만 안다. `analysis` 의 `S3Storage` 와 같은 짜임이고,
컨텍스트 경계 때문에 코드를 공유하지 않는다(포트 머리말 참고).

🔴 **자격증명을 코드에서 만들지 않는다.** boto3 가 기본 체인(EC2 인스턴스 역할 →
환경변수 → `~/.aws`)에서 찾는다 — 영상 쪽과 같은 판단이다.

⚠️ **버킷은 영상과 같은 것을 쓴다.** 접두사(`cards/photos/`)로 갈리고, 버킷을
따로 두면 CORS·권한·배포 설정이 하나 더 늘어난다.
"""

from __future__ import annotations

import boto3

from app.card.application.ports.output.photo_storage_port import PhotoStoragePort


class CardPhotoS3Storage(PhotoStoragePort):
    def __init__(self, bucket: str, region: str, url_ttl_seconds: int) -> None:
        self._bucket = bucket
        self._ttl = url_ttl_seconds
        self._client = boto3.client("s3", region_name=region or None)

    def create_upload_url(self, storage_key: str, content_type: str) -> tuple[str, int]:
        url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket,
                "Key": storage_key,
                "ContentType": content_type,
            },
            ExpiresIn=self._ttl,
        )
        return url, self._ttl

    def create_download_url(self, storage_key: str) -> tuple[str, int]:
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": storage_key},
            ExpiresIn=self._ttl,
        )
        return url, self._ttl

    def delete_object(self, storage_key: str) -> None:
        """S3 의 `DeleteObject` 는 **없는 키에도 성공**이라 따로 안 가린다."""
        self._client.delete_object(Bucket=self._bucket, Key=storage_key)
