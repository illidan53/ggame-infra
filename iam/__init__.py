"""IAM resources — GitHub Actions OIDC roles for CI/CD"""

import pulumi
from pulumi_aws import iam

from s3 import bucket as artifacts_bucket

# Reference the existing GitHub OIDC provider
oidc_provider = iam.get_open_id_connect_provider(
    url="https://token.actions.githubusercontent.com",
)

# CI/CD role for ggame repo — can only write to the artifacts S3 bucket
ggame_deploy_role = iam.Role("ggame-deploy-role",
    name="github-actions-ggame-deploy",
    assume_role_policy=pulumi.Output.all(oidc_provider.arn).apply(lambda args: f"""{{
        "Version": "2012-10-17",
        "Statement": [{{
            "Effect": "Allow",
            "Principal": {{
                "Federated": "{args[0]}"
            }},
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {{
                "StringEquals": {{
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                }},
                "StringLike": {{
                    "token.actions.githubusercontent.com:sub": "repo:illidan53/ggame:*"
                }}
            }}
        }}]
    }}"""),
    tags={"Name": "github-actions-ggame-deploy"},
)

# Policy: only S3 write to artifacts bucket
iam.RolePolicy("ggame-deploy-s3-policy",
    role=ggame_deploy_role.id,
    policy=artifacts_bucket.arn.apply(lambda arn: f"""{{
        "Version": "2012-10-17",
        "Statement": [{{
            "Effect": "Allow",
            "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
            "Resource": ["{arn}", "{arn}/*"]
        }}]
    }}"""),
)

pulumi.export("ggame_deploy_role_arn", ggame_deploy_role.arn)
