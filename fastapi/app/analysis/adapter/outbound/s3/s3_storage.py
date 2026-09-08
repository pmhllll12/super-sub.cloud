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

    def create_download_url(self, storage_key: str) -> tuple[str, int]:
        """GET 용 사전 서명 URL. 재생·다운로드가 앱 서버를 지나지 않게 한다."""
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": storage_key},
            ExpiresIn=self._ttl,
        )
        return url, self._ttl

    def move_object(self, src_key: str, dst_key: str) -> None:
        """`CopyObject`(서버 쪽) 후 원본 삭제. 바이트가 앱 서버를 지나지 않는다."""
        if src_key == dst_key:
            return
        self._client.copy_object(
            Bucket=self._bucket,
            CopySource={"Bucket": self._bucket, "Key": src_key},
            Key=dst_key,
        )
        self._client.delete_object(Bucket=self._bucket, Key=src_key)

    def delete_object(self, storage_key: str) -> None:
        """객체 하나를 지운다. 없는 키에도 S3 는 오류를 안 낸다(멱등)."""
        self._client.delete_object(Bucket=self._bucket, Key=storage_key)

    def delete_prefix(self, prefix: str) -> None:
        """접두사 아래 전부 지운다. `list_objects_v2` 로 훑어 최대 1000개씩 배치."""
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if keys:
                self._client.delete_objects(
                    Bucket=self._bucket, Delete={"Objects": keys}
                )

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
