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

# Policy: S3 read (artifacts) + Route53 (certbot DNS validation)
ec2_policy = iam.RolePolicy("ggame-ec2-policy",
    role=ec2_role.id,
    policy=artifacts_bucket.arn.apply(lambda arn: f"""{{
        "Version": "2012-10-17",
        "Statement": [
            {{
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": ["{arn}", "{arn}/*"]
            }},
            {{
                "Effect": "Allow",
                "Action": ["route53:ListHostedZones", "route53:GetChange"],
                "Resource": "*"
            }},
            {{
                "Effect": "Allow",
                "Action": "route53:ChangeResourceRecordSets",
                "Resource": "arn:aws:route53:::hostedzone/Z05670062ZTWRSY6PDM7V"
            }}
        ]
    }}"""),
)

instance_profile = iam.InstanceProfile("ggame-ec2-profile",
    role=ec2_role.name,
)

user_data_script = artifacts_bucket.id.apply(lambda bucket_name: f"""#!/bin/bash
set -e

# Install nginx and cron
dnf install -y nginx cronie
systemctl enable crond
systemctl start crond

# Create web directories
mkdir -p /var/www/darkpath
mkdir -p /var/www/nphunter
chown ec2-user:ec2-user /var/www/darkpath /var/www/nphunter

# Create nphunter.net home page
cat > /var/www/nphunter/index.html << 'HOMEPAGE'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>nphunter.net</title>
    <style>
        body {{ background: #0a0a0f; color: #e0e0e0; font-family: monospace; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
        .container {{ text-align: center; max-width: 600px; padding: 2rem; }}
        h1 {{ color: #cc3333; font-size: 2.5rem; letter-spacing: 0.3rem; }}
        p {{ color: #888; line-height: 1.8; }}
        a {{ color: #cc3333; text-decoration: none; border: 1px solid #cc3333; padding: 0.5rem 1.5rem; display: inline-block; margin-top: 1rem; }}
        a:hover {{ background: #cc3333; color: #0a0a0f; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>nphunter.net</h1>
        <p>Welcome. This is a personal project hub.</p>
        <a href="https://ggame.nphunter.net">Play DarkPath</a>
    </div>
</body>
</html>
HOMEPAGE

# Configure nginx to serve the game
cat > /etc/nginx/conf.d/darkpath.conf << 'CONF'
server {{
    listen 80;
    server_name ggame.nphunter.net;
    root /var/www/darkpath;
    index index.html;

    include /etc/nginx/mime.types;
    types {{
        application/wasm wasm;
    }}

    # Required headers for Godot web export (secure context)
    add_header Cross-Origin-Opener-Policy same-origin;
    add_header Cross-Origin-Embedder-Policy require-corp;

    gzip on;
    gzip_types text/html application/javascript application/wasm application/octet-stream;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
CONF

# Move default nginx listener off port 80 to avoid conflict (IPv4 + IPv6)
sed -i 's/listen       80/listen       8080/' /etc/nginx/nginx.conf
sed -i 's/listen       \[::\]:80/listen       [::]:8080/' /etc/nginx/nginx.conf

# Start and enable nginx
systemctl enable nginx
systemctl start nginx

# Install certbot with Route53 DNS plugin for HTTPS
dnf install -y certbot python3-certbot-nginx python3-certbot-dns-route53 || pip3 install certbot-dns-route53
certbot certonly --dns-route53 -d ggame.nphunter.net -d nphunter.net --non-interactive --agree-tos --email slzhao@outlook.com || true

# Configure HTTPS nginx blocks if cert was issued
if [ -f /etc/letsencrypt/live/ggame.nphunter.net/fullchain.pem ]; then
    cat > /etc/nginx/conf.d/darkpath-ssl.conf << 'SSLCONF'
server {{
    listen 443 ssl;
    server_name ggame.nphunter.net;
    root /var/www/darkpath;
    index index.html;

    ssl_certificate /etc/letsencrypt/live/ggame.nphunter.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ggame.nphunter.net/privkey.pem;

    include /etc/nginx/mime.types;
    types {{
        application/wasm wasm;
    }}

    add_header Cross-Origin-Opener-Policy same-origin;
    add_header Cross-Origin-Embedder-Policy require-corp;

    gzip on;
    gzip_types text/html application/javascript application/wasm application/octet-stream;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
SSLCONF

    cat > /etc/nginx/conf.d/nphunter-ssl.conf << 'ROOTSSL'
server {{
    listen 443 ssl;
    server_name nphunter.net;
    root /var/www/nphunter;
    index index.html;

    ssl_certificate /etc/letsencrypt/live/ggame.nphunter.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ggame.nphunter.net/privkey.pem;
}}

server {{
    listen 80;
    server_name nphunter.net;
    return 301 https://$host$request_uri;
}}
ROOTSSL

    nginx -t && systemctl reload nginx
fi

systemctl enable certbot-renew.timer
systemctl start certbot-renew.timer

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
