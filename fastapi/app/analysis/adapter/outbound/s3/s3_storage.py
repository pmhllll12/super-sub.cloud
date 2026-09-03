"""`StoragePort` 의 S3 구현.

원본은 **앱 서버를 지나지 않는다**(PER-002). 클라이언트가 사전 서명 URL 로 S3 에
직접 PUT 하고, 서버는 키와 크기만 안다.

🔴 **자격증명을 코드에서 만들지 않는다.** boto3 가 기본 체인(EC2 인스턴스 역할 →
환경변수 → `~/.aws`)에서 찾는다. EC2 에서 돌 때는 역할을 붙이는 것이 맞고,
로컬에서만 `.env` 의 `AWS_ACCESS_KEY_ID` 를 쓴다 — 장기 키를 서버 파일에 두지
않기 위해서다(`.env.example` 의 AWS 절).
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from app.analysis.application.ports.output.storage_port import StoragePort


class S3Storage(StoragePort):
    def __init__(self, bucket: str, region: str, url_ttl_seconds: int) -> None:
        self._bucket = bucket
        self._ttl = url_ttl_seconds
        self._client = boto3.client("s3", region_name=region or None)

    def create_upload_url(self, storage_key: str, content_type: str) -> tuple[str, int]:
        """PUT 용 사전 서명 URL.

        `ContentType` 을 서명에 넣으므로 **클라이언트가 같은 값을 헤더로 보내야**
        한다. 안 보내면 S3 가 서명 불일치로 거절한다 — 계약 문서에 적어 두었다.
        """
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

    def size_of(self, storage_key: str) -> int | None:
        try:
            head = self._client.head_object(Bucket=self._bucket, Key=storage_key)
        except ClientError as exc:
            # 없는 키는 404, 권한이 없으면 403 이다. **403 을 "없다"로 읽지
            # 않는다** — 버킷 정책이 잘못됐는데 "안 올렸다"고 답하면 원인을
            # 엉뚱한 데서 찾게 된다.
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return None
            raise
        return head["ContentLength"]
