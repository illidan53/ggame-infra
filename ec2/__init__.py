"""EC2 resources"""

import pulumi
from pulumi_aws import ec2

from vpc import public_subnet
from security_group import sg

# Amazon Linux 2023 AMI lookup
ami = ec2.get_ami(
    most_recent=True,
    owners=["amazon"],
    filters=[
        {"name": "name", "values": ["al2023-ami-2023.*-x86_64"]},
        {"name": "state", "values": ["available"]},
    ],
)

user_data_script = """#!/bin/bash
set -e

# Install nginx
dnf install -y nginx

# Create web directory for DarkPath game
mkdir -p /var/www/darkpath
chown ec2-user:ec2-user /var/www/darkpath

# Configure nginx to serve the game
cat > /etc/nginx/conf.d/darkpath.conf << 'CONF'
server {
    listen 80;
    server_name _;
    root /var/www/darkpath;
    index index.html;

    # Required MIME type for WebAssembly
    types {
        application/wasm wasm;
    }

    # Gzip for faster loading
    gzip on;
    gzip_types application/javascript application/wasm application/octet-stream;

    location / {
        try_files $uri $uri/ =404;
    }
}
CONF

# Move default nginx listener off port 80 to avoid conflict
sed -i 's/listen       80/listen       8080/' /etc/nginx/nginx.conf

# Start and enable nginx
systemctl enable nginx
systemctl start nginx
"""

instance = ec2.Instance("ggame-ec2",
    instance_type="t3.medium",  # 2 vCPU, 4 GB RAM
    ami=ami.id,
    subnet_id=public_subnet.id,
    vpc_security_group_ids=[sg.id],
    associate_public_ip_address=False,
    key_name="slzhao-personal-mac",
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
