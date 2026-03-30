"""VPC resources"""

import pulumi
from pulumi_aws import ec2

# VPC
vpc = ec2.Vpc("nphunter-game-vpc",
    cidr_block="172.16.0.0/26",
    enable_dns_support=True,
    enable_dns_hostnames=True,
    tags={"Name": "nphunter-game-vpc"},
)

# Internet Gateway
igw = ec2.InternetGateway("nphunter-game-igw",
    vpc_id=vpc.id,
    tags={"Name": "nphunter-game-igw"},
)

# Public Subnet (single AZ)
public_subnet = ec2.Subnet("nphunter-game-public-subnet",
    vpc_id=vpc.id,
    cidr_block="172.16.0.0/26",
    availability_zone="us-east-1a",
    map_public_ip_on_launch=True,
    tags={"Name": "nphunter-game-public-subnet"},
)

# Route Table
public_rt = ec2.RouteTable("nphunter-game-public-rt",
    vpc_id=vpc.id,
    routes=[{
        "cidr_block": "0.0.0.0/0",
        "gateway_id": igw.id,
    }],
    tags={"Name": "nphunter-game-public-rt"},
)

# Associate Route Table with Subnet
rt_assoc = ec2.RouteTableAssociation("nphunter-game-public-rt-assoc",
    subnet_id=public_subnet.id,
    route_table_id=public_rt.id,
)

pulumi.export("vpc_id", vpc.id)
pulumi.export("public_subnet_id", public_subnet.id)
