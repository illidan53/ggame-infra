"""Route53 resources"""

import pulumi
from pulumi_aws import route53

zone = route53.Zone("main-zone",
    comment="HostedZone created by Route53 Registrar",
    name="nphunter.net",
    opts=pulumi.ResourceOptions(protect=True))

pulumi.export("zone_id", zone.zone_id)
