"""Security Group resources"""

import pulumi
from pulumi_aws import ec2

from vpc import vpc

config = pulumi.Config()
my_ip = config.require("my_ip")

sg = ec2.SecurityGroup("ggame-security-group",
    vpc_id=vpc.id,
    description="Security group for ggame EC2",
    tags={"Name": "ggame-security-group"},
)

# Allow SSH (22) from my IP
ec2.SecurityGroupRule("ggame-sg-ssh",
    type="ingress",
    security_group_id=sg.id,
    protocol="tcp",
    from_port=22,
    to_port=22,
    cidr_blocks=[f"{my_ip}/32"],
    description="SSH from my IP",
)

# Allow HTTP (80) from internet
ec2.SecurityGroupRule("ggame-sg-http",
    type="ingress",
    security_group_id=sg.id,
    protocol="tcp",
    from_port=80,
    to_port=80,
    cidr_blocks=["0.0.0.0/0"],
    description="HTTP from internet",
)

# Allow HTTPS (443) from internet
ec2.SecurityGroupRule("ggame-sg-https",
    type="ingress",
    security_group_id=sg.id,
    protocol="tcp",
    from_port=443,
    to_port=443,
    cidr_blocks=["0.0.0.0/0"],
    description="HTTPS from internet",
)

# Allow all outbound
ec2.SecurityGroupRule("ggame-sg-egress",
    type="egress",
    security_group_id=sg.id,
    protocol="-1",
    from_port=0,
    to_port=0,
    cidr_blocks=["0.0.0.0/0"],
    description="Allow all outbound",
)

pulumi.export("sg_id", sg.id)
