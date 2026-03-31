"""EC2 resources"""

import pulumi
from pulumi_aws import ec2, iam

from vpc import public_subnet
from security_group import sg
from s3 import bucket as artifacts_bucket

# Amazon Linux 2023 AMI lookup
ami = ec2.get_ami(
    most_recent=True,
    owners=["amazon"],
    filters=[
        {"name": "name", "values": ["al2023-ami-2023.*-x86_64"]},
        {"name": "state", "values": ["available"]},
    ],
)

# IAM role for EC2 to pull artifacts from S3
ec2_role = iam.Role("ggame-ec2-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Effect": "Allow"
        }]
    }""",
    tags={"Name": "ggame-ec2-role"},
)

# Policy: allow read from artifacts bucket
s3_policy = iam.RolePolicy("ggame-ec2-s3-policy",
    role=ec2_role.id,
    policy=artifacts_bucket.arn.apply(lambda arn: f"""{{
        "Version": "2012-10-17",
        "Statement": [{{
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": ["{arn}", "{arn}/*"]
        }}]
    }}"""),
)

instance_profile = iam.InstanceProfile("ggame-ec2-profile",
    role=ec2_role.name,
)

user_data_script = artifacts_bucket.id.apply(lambda bucket_name: f"""#!/bin/bash
set -e

# Install nginx
dnf install -y nginx

# Create web directory for DarkPath game
mkdir -p /var/www/darkpath
chown ec2-user:ec2-user /var/www/darkpath

# Configure nginx to serve the game
cat > /etc/nginx/conf.d/darkpath.conf << 'CONF'
server {{
    listen 80;
    server_name _;
    root /var/www/darkpath;
    index index.html;

    # Required MIME type for WebAssembly
    types {{
        application/wasm wasm;
    }}

    # Gzip for faster loading
    gzip on;
    gzip_types application/javascript application/wasm application/octet-stream;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
CONF

# Move default nginx listener off port 80 to avoid conflict
sed -i 's/listen       80/listen       8080/' /etc/nginx/nginx.conf

# Start and enable nginx
systemctl enable nginx
systemctl start nginx

# Create deploy script that syncs latest artifact from S3
cat > /usr/local/bin/deploy-darkpath.sh << 'DEPLOY'
#!/bin/bash
BUCKET="{bucket_name}"
LATEST=$(aws s3 ls "s3://$BUCKET/web/" --recursive | sort | tail -1 | awk '{{print $4}}')
if [ -z "$LATEST" ]; then
    echo "No artifacts found in s3://$BUCKET/web/"
    exit 0
fi
MARKER="/var/www/darkpath/.deployed_artifact"
if [ -f "$MARKER" ] && [ "$(cat $MARKER)" = "$LATEST" ]; then
    exit 0  # Already deployed
fi
echo "Deploying $LATEST..."
aws s3 cp "s3://$BUCKET/$LATEST" /tmp/darkpath-web.zip
rm -rf /var/www/darkpath/*
unzip -o /tmp/darkpath-web.zip -d /var/www/darkpath/
rm /tmp/darkpath-web.zip
echo "$LATEST" > "$MARKER"
echo "Deployed $LATEST at $(date)"
DEPLOY
chmod +x /usr/local/bin/deploy-darkpath.sh

# Run every minute via cron
echo "* * * * * ec2-user /usr/local/bin/deploy-darkpath.sh >> /var/log/darkpath-deploy.log 2>&1" > /etc/cron.d/darkpath-deploy
chmod 644 /etc/cron.d/darkpath-deploy
""")  # end of .apply()

instance = ec2.Instance("ggame-ec2",
    instance_type="t3.medium",  # 2 vCPU, 4 GB RAM
    ami=ami.id,
    subnet_id=public_subnet.id,
    vpc_security_group_ids=[sg.id],
    associate_public_ip_address=False,
    key_name="slzhao-personal-mac",
    iam_instance_profile=instance_profile.name,
    user_data=user_data_script,
    tags={"Name": "ggame-ec2"},
)

eip = ec2.Eip("ggame-eip",
    instance=instance.id,
    domain="vpc",
    tags={"Name": "ggame-eip"},
)

pulumi.export("instance_id", instance.id)
pulumi.export("instance_public_ip", eip.public_ip)
