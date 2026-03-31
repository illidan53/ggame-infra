"""S3 resources — artifact bucket for CI/CD deployments"""

import pulumi
from pulumi_aws import s3

bucket = s3.BucketV2("ggame-artifacts",
    bucket="ggame-artifacts",
    tags={"Name": "ggame-artifacts"},
)

s3.BucketVersioningV2("ggame-artifacts-versioning",
    bucket=bucket.id,
    versioning_configuration={"status": "Enabled"},
)

s3.BucketLifecycleConfigurationV2("ggame-artifacts-lifecycle",
    bucket=bucket.id,
    rules=[{
        "id": "expire-old-artifacts",
        "status": "Enabled",
        "expiration": {"days": 30},
        "noncurrent_version_expiration": {"noncurrent_days": 7},
    }],
)

pulumi.export("artifacts_bucket_name", bucket.id)
pulumi.export("artifacts_bucket_arn", bucket.arn)
