"""A Google Cloud Python Pulumi program"""

import pulumi
import pulumi_gcp as gcp

import json

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")
gcp_region = gcp_config.require("region")
wordpress_image = gcp_config.require("image")
cloudsql = gcp_config.require("cloudsql")
cloudsql_disk_size = cloudsql.require("disk_size")
cloudsql_instance_tier = cloudsql.require("tier")
cloudsql_user = cloudsql.require("user")

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

# create vpc access connector
connector = gcp.vpcaccess.Connector("cloudrun-connector",
    subnet=gcp.vpcaccess.ConnectorSubnetArgs(
        name=wordpress_subnetwork.name,
    ),
    region=gcp_region)

workpress_cloudrun = gcp.cloudrunv2.Service("workpress",
    location=gcp_region,
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        containers=[gcp.cloudrunv2.ServiceTemplateContainerArgs(
            image=wordpress_image,
            envs=[],
            resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                cpu_idle=False,
                limits=['2', '2']
            ),
            scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
                max_instance_count=10,
                min_instance_count=1
            )
        )],
        vpc_access=gcp.cloudrunv2.ServiceTemplateVpcAccessArgs(
            connector=connector.id,
            egress="PRIVATE_RANGES_ONLY",
        ),
        session_affinity=True
    ))


# cloudsql ip address
private_ip_address = gcp.compute.GlobalAddress("cloudsql-privateip",
    purpose="VPC_PEERING",
    address_type="INTERNAL",
    prefix_length=28,
    network=wordpress_network.id)
# cloudsql private connector
private_vpc_connection = gcp.servicenetworking.Connection("privateVpcConnection",
    network=wordpress_network.id,
    service="servicenetworking.googleapis.com",
    reserved_peering_ranges=[private_ip_address.name])

# create cloudsql 
workpress_cloudsql = gcp.sql.DatabaseInstance("wordpress-database",
    region=gcp_region,
    database_version="MYSQL_8_0",
    settings=gcp.sql.DatabaseInstanceSettingsArgs(
        tier=cloudsql_instance_tier,
        disk_autoresize=False,
        disk_size=cloudsql_disk_size,
        disk_type="PD_SSD",
        availability_type="ZONAL",
        ip_configuration=gcp.sql.DatabaseInstanceSettingsIpConfigurationArgs(
            ipv4_enabled=False,
            private_network=wordpress_network.id,
            enable_private_path_for_google_cloud_services=True,
        ),
        backup_configuration=gcp.sql.DatabaseInstanceSettingsBackupConfigurationArgs(
            binary_log_enabled=True,
            enabled=True,
            backup_retention_settings=gcp.sql.DatabaseInstanceSettingsBackupConfigurationBackupRetentionSettingsArgs(
                retained_backups=7,
            )
        )
    ),
    deletion_protection=True,
    opts=pulumi.ResourceOptions(
        depends_on=[private_vpc_connection])
        )

# create cloudsql user
dataflow_user = gcp.sql.User(cloudsql_user,
    instance=workpress_cloudsql.name,
    password=config.require_secret('dbPassword'),
    type="BUILT_IN")



# create firewall allow ingress from load balancer health traffic
default_firewall = gcp.compute.Firewall("allow-cloud run",
    network=vpc_network.name,
    allows=[
        gcp.compute.FirewallAllowArgs(
            protocol="tcp",
            ports=[
                "111,2049",
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





# create bucket
bucket = gcp.storage.Bucket('dataflow-demo-bucket',
                            location="us-central1")

pulumi.export("Cloud Storage Object Path", pulumi.Output.all(bucket.url, bucketObject.output_name) \
    .apply(lambda args: f"{args[0]}/{args[1]}"))

pulumi.export("Cloud SQL Name", pulumi.Output.format(instance.name))
pulumi.export("Cloud SQL IP", pulumi.Output.format(instance.private_ip_address))
pulumi.export("Cloud SQL user", pulumi.Output.format(dataflow_user.id))

pulumi.export("VPC", pulumi.Output.format(vpc_network.self_link))
pulumi.export("Subnet", pulumi.Output.format(dataflow_subnet1.self_link))
