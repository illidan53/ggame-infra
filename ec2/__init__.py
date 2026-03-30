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

instance = ec2.Instance("ggame-ec2",
    instance_type="t3.medium",  # 2 vCPU, 4 GB RAM
    ami=ami.id,
    subnet_id=public_subnet.id,
    vpc_security_group_ids=[sg.id],
    associate_public_ip_address=True,
    key_name="slzhao-personal-mac",
    tags={"Name": "ggame-ec2"},
)

pulumi.export("instance_id", instance.id)
pulumi.export("instance_public_ip", instance.public_ip)
