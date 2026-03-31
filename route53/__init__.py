"""Route53 resources"""

import pulumi
from pulumi_aws import route53

from ec2 import eip

zone = route53.Zone("main-zone",
    comment="HostedZone created by Route53 Registrar",
    name="nphunter.net",
    opts=pulumi.ResourceOptions(protect=True))

ggame_record = route53.Record("ggame-record",
    zone_id=zone.zone_id,
    name="ggame.nphunter.net",
    type="A",
    ttl=300,
    records=[eip.public_ip])

pulumi.export("zone_id", zone.zone_id)
pulumi.export("ggame_domain", ggame_record.fqdn)
