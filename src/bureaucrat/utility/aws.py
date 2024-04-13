import os

from aioboto3 import Session
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bureaucrat import Bureaucrat


class AWSClient:

    def __init__(self, bot: "Bureaucrat") -> None:
        self.bot = bot
        self.bucket = os.getenv("AWS_BUCKET")

    async def s3_delete(self, *, bucket, prefix):
        if prefix == "" or bucket == "":
            return

        async with Session().resource("s3") as s3:
            bucket = await s3.Bucket(self.bucket)
            await bucket.objects.filter(Prefix=f"{bucket}/{prefix}/").delete()

    async def s3_create(self, *, bucket, key, file: Path):
        async with Session().client("s3") as s3:
            try:
                with file.open("rb") as file:
                    s3_key = "/".join([bucket, key])
                    await s3.upload_fileobj(file, self.bucket, s3_key)
            except Exception as e:
                self.bot.logger.error(e)

        return f"https://{self.bucket}.s3.amazonaws.com/{bucket}/{key}"

    def s3_url(self, *, bucket, key, stem):
        return f"https://{self.bucket}.s3.amazonaws.com/{bucket}/{key}/{stem}"
