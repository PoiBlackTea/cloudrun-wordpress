"""A Google Cloud Python Pulumi program"""

import pulumi
import pulumi_gcp as gcp

import json

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")
gcp_region = gcp_config.require("region")

# create custom vpc
wordpress_network = gcp.compute.Network("wordpress-vpc",
    auto_create_subnetworks=False,
    description="wordpress vpc",
    mtu=1460)


# create custom vpc subnet
wordpress_subnetwork = gcp.compute.Subnetwork("dataflow-demo-subnet1",
    ip_cidr_range="10.0.0.0/24",
    region=gcp_region,
    network=wordpress_network.id)



custom_test_network = gcp.compute.Network("customTestNetwork", auto_create_subnetworks=False)
custom_test_subnetwork = gcp.compute.Subnetwork("customTestSubnetwork",
    ip_cidr_range="10.2.0.0/28",
    region="us-central1",
    network=custom_test_network.id)

connector = gcp.vpcaccess.Connector("connector",
    subnet=gcp.vpcaccess.ConnectorSubnetArgs(
        name=custom_test_subnetwork.name,
    ),
    machine_type="e2-standard-4",
    min_instances=2,
    max_instances=3,
    region="us-central1")
default = gcp.cloudrunv2.Service("default",
    location="us-central1",
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        containers=[gcp.cloudrunv2.ServiceTemplateContainerArgs(
            image="us-docker.pkg.dev/cloudrun/container/hello",
        )],
        vpc_access=gcp.cloudrunv2.ServiceTemplateVpcAccessArgs(
            connector=connector.id,
            egress="ALL_TRAFFIC",
        ),
    ))




# create firewall allow ingress from load balancer health traffic
default_firewall = gcp.compute.Firewall("allow-cloud run",
    network=vpc_network.name,
    allows=[
        gcp.compute.FirewallAllowArgs(
            protocol="tcp",
            ports=[
                "22",
            ],
        ),
    ],
    priority=500,
    source_ranges=["Cloud Run service conect access ip"])


# create firewall allow dataflow mysql traffic
default_firewall = gcp.compute.Firewall("allow-from-dataflow-worker",
    network=vpc_network.name,
    allows=[
        gcp.compute.FirewallAllowArgs(
            protocol="tcp",
            ports=[
                "3306",
                "12345-12346"
            ],
        ),
    ],
    priority=500,
    source_ranges=["10.0.0.0/24"])


# cloudsql ip address
private_ip_address = gcp.compute.GlobalAddress("cloudsql-privateip",
    purpose="VPC_PEERING",
    address_type="INTERNAL",
    prefix_length=16,
    network=vpc_network.id)
# cloudsql private connector
private_vpc_connection = gcp.servicenetworking.Connection("privateVpcConnection",
    network=vpc_network.id,
    service="servicenetworking.googleapis.com",
    reserved_peering_ranges=[private_ip_address.name])

# create cloudsql 
instance = gcp.sql.DatabaseInstance("dataflow-soruce-database",
    region="us-central1",
    database_version="MYSQL_8_0",
    settings=gcp.sql.DatabaseInstanceSettingsArgs(
        tier="db-f1-micro",
        disk_autoresize=False,
        disk_size=10,
        disk_type="PD_HDD",
        availability_type="ZONAL",
        ip_configuration=gcp.sql.DatabaseInstanceSettingsIpConfigurationArgs(
            ipv4_enabled=False,
            private_network=vpc_network.id,
            enable_private_path_for_google_cloud_services=True,
        ),
        backup_configuration=gcp.sql.DatabaseInstanceSettingsBackupConfigurationArgs(
            binary_log_enabled=False,
            enabled=False,
            backup_retention_settings=gcp.sql.DatabaseInstanceSettingsBackupConfigurationBackupRetentionSettingsArgs(
                retained_backups=3,
            )
        )
    ),
    deletion_protection=False,
    opts=pulumi.ResourceOptions(
        depends_on=[private_vpc_connection])
        )

# create cloudsql user
dataflow_user = gcp.sql.User("dataflow",
    instance=instance.name,
    password=config.require_secret('dbPassword'),
    type="BUILT_IN")



# create bucket import sql file
bucket = gcp.storage.Bucket('dataflow-demo-bucket',
                            location="us-central1")
bucketObject = gcp.storage.BucketObject(
    'demo.sql',
    bucket=bucket.name,
    source=pulumi.FileAsset('demo.sql')
)

pulumi.export("Cloud Storage Object Path", pulumi.Output.all(bucket.url, bucketObject.output_name) \
    .apply(lambda args: f"{args[0]}/{args[1]}"))

pulumi.export("Cloud SQL Name", pulumi.Output.format(instance.name))
pulumi.export("Cloud SQL IP", pulumi.Output.format(instance.private_ip_address))
pulumi.export("Cloud SQL user", pulumi.Output.format(dataflow_user.id))

pulumi.export("VPC", pulumi.Output.format(vpc_network.self_link))
pulumi.export("Subnet", pulumi.Output.format(dataflow_subnet1.self_link))
