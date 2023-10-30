"""A Google Cloud Python Pulumi program"""

import pulumi
import pulumi_gcp as gcp


config = pulumi.Config()
gcp_config = pulumi.Config("gcp")
gcp_region = gcp_config.require("region")

cloudsql = pulumi.Config("workpress")
wordpress_image = cloudsql.require("image")
cloudsql_disk_size = cloudsql.require("disk_size")
cloudsql_instance_tier = cloudsql.require("tier")
cloudsql_user = cloudsql.require("user")
cloudsql_db = cloudsql.require("db")

# gce startup_script for wordpress nfs
startup_script = """#!/bin/bash
apt update -y 
apt upgrade -y
apt install nfs-kernel-server -y
mkdir -p /opt/nfs
curl https://downloads.bitnami.com/files/stacksmith/wordpress-6.3.2-1-linux-amd64-debian-11.tar.gz -O
tar -zxf wordpress-6.3.2-1-linux-amd64-debian-11.tar.gz -C /opt/nfs --strip-components=4 --no-same-owner --wildcards '*/files/wordpress/wp-content/*'
chown -R daemon:www-data /opt/nfs
chmod -R 666 /opt/nfs
echo '/opt/nfs 10.0.0.0/8(rw,sync,no_subtree_check,no_root_squash) > /etc/exports'
systemctl restart nfs-server 
systemctl enable nfs-server
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
bash add-google-cloud-ops-agent-repo.sh --also-install
apt autoremove -y"""



# create wordpress service account
service_account = gcp.serviceaccount.Account("serviceAccount",
    account_id="workpress-sa",
    display_name="workpress sa")


# create secret manager secret
secret = gcp.secretmanager.Secret("secret",
    secret_id="workpress-db_pass",
    replication=gcp.secretmanager.SecretReplicationArgs(
        auto=gcp.secretmanager.SecretReplicationAutoArgs(),
    ))
secret_version_data = gcp.secretmanager.SecretVersion("secret-version-data",
    secret=secret.name,
    secret_data=cloudsql.require_secret('dbPassword'))


# create custom vpc
wordpress_network = gcp.compute.Network("wordpress-vpc",
    auto_create_subnetworks=False,
    description="wordpress vpc",
    mtu=1460)


# create custom vpc subnet
wordpress_subnetwork = gcp.compute.Subnetwork("dataflow-demo-subnet1",
    ip_cidr_range="10.0.2.0/24",
    region=gcp_region,
    network=wordpress_network.id,
    private_ip_google_access=True)

# create vpc access connector
connector = gcp.vpcaccess.Connector("cloudrunsql",
    ip_cidr_range="10.8.0.0/28",
    network=wordpress_network.id,
    opts=pulumi.ResourceOptions(
        depends_on=[wordpress_subnetwork]))

# create vpc nat
addr = gcp.compute.Address("addr", region=gcp_region)
router = gcp.compute.Router("router",
    region=wordpress_subnetwork.region,
    network=wordpress_network.id
    )
nat = gcp.compute.RouterNat("nat",
    router=router.name,
    region=router.region,
    nat_ip_allocate_option="MANUAL_ONLY",
    nat_ips=[addr.self_link],
    source_subnetwork_ip_ranges_to_nat="ALL_SUBNETWORKS_ALL_IP_RANGES",
    log_config=gcp.compute.RouterNatLogConfigArgs(
        enable=True,
        filter="ERRORS_ONLY",
    ))

# cloudsql ip address
private_ip_address = gcp.compute.GlobalAddress("cloudsql-privateip",
    purpose="VPC_PEERING",
    address_type="INTERNAL",
    prefix_length=24,
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
    deletion_protection=False,
    opts=pulumi.ResourceOptions(
        depends_on=[private_vpc_connection])
        )

# create cloudsql user
workpress_user = gcp.sql.User(cloudsql_user,
    instance=workpress_cloudsql.name,
    password=cloudsql.require_secret('dbPassword'),
    type="BUILT_IN")

# create workpress database
database = gcp.sql.Database(resource_name=cloudsql_db, 
                            charset="utf8mb4",
                            instance=workpress_cloudsql.name)

# Create a static IP
address = gcp.compute.Address('address',
                              subnetwork=wordpress_subnetwork.id,
                              address_type="INTERNAL",
                              address="10.0.2.64",
                              region=gcp_region)

# create GCE for nfs
default_account = gcp.serviceaccount.Account("defaultAccount",
    account_id="nfs-sa",
    display_name="nfs")
nfs_instance = gcp.compute.Instance("nfs-server-instance",
    machine_type="e2-medium",
    zone=f"{gcp_region}-a",
    tags=[
        "nfs"
    ],
    boot_disk=gcp.compute.InstanceBootDiskArgs(
        initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(
            image="ubuntu-os-cloud/ubuntu-2204-lts",
            size=50
        ),
    ),
    network_interfaces=[gcp.compute.InstanceNetworkInterfaceArgs(
        network=wordpress_network.id,
        subnetwork=wordpress_subnetwork.id,
        network_ip=address.address, # nfs private ip
        access_configs=[gcp.compute.InstanceNetworkInterfaceAccessConfigArgs(
        )],
    )],
    metadata_startup_script=startup_script,
    service_account=gcp.compute.InstanceServiceAccountArgs(
        email=default_account.email,
        scopes=["cloud-platform"],
    ),
    opts=pulumi.ResourceOptions(depends_on=[nat]),
    )


# create cloud run service
workpress_cloudrun = gcp.cloudrunv2.Service("workpress",
    location=gcp_region,
    ingress="INGRESS_TRAFFIC_ALL",
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        containers=[gcp.cloudrunv2.ServiceTemplateContainerArgs(
            image=wordpress_image,
            envs=[
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="WORDPRESS_DATABASE_HOST",
                        value=workpress_cloudsql.private_ip_address,
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="WORDPRESS_DATABASE_NAME",
                        value=database.name,
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="WORDPRESS_DATABASE_USER",
                        value=workpress_user.name,
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="WORDPRESS_ENABLE_REVERSE_PROXY",
                        value="yes",
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="WORDPRESS_PLUGINS",
                        value="wp-stateless",
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                    name="WORDPRESS_DATABASE_PASSWORD",
                    value_source=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceArgs(
                        secret_key_ref=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceSecretKeyRefArgs(
                            secret=secret.secret_id,
                            version="1",
                        ),
                    ),
                ),
            ],
            resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                cpu_idle=False,
                limits={'cpu':'2', 'memory':'2Gi'}
            ),
        )],
        volumes=[
            gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                name="cloudsql",
                cloud_sql_instance=gcp.cloudrunv2.ServiceTemplateVolumeCloudSqlInstanceArgs(
                instances=[workpress_cloudsql.connection_name],
                ),
            )
        ],
        vpc_access=gcp.cloudrunv2.ServiceTemplateVpcAccessArgs(
            connector=connector.id,
            egress="ALL_TRAFFIC",
        ),
        scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
                max_instance_count=10,
                min_instance_count=1
            ),
        execution_environment="EXECUTION_ENVIRONMENT_GEN2",
        service_account=service_account.email,
        timeout="3600s",
        session_affinity=True,
    ),
    traffics=[gcp.cloudrunv2.ServiceTrafficArgs(
        type="TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST",
        percent=100,
    )],
    opts=pulumi.ResourceOptions(depends_on=[secret_version_data, database, nfs_instance])
    )

# Grant the 'roles/run.invoker' role to 'allUsers' for the newly created service
service_iam_member = gcp.cloudrunv2.ServiceIamMember("service-iam-member", 
    name=workpress_cloudrun.name,
    role="roles/run.invoker",
    member="allUsers"
)

project = gcp.organizations.get_project()
secret_access = gcp.secretmanager.SecretIamMember("secret-access",
    secret_id=secret.id,
    role="roles/secretmanager.secretAccessor",
    member=pulumi.Output.concat("serviceAccount:", service_account.email),
    opts=pulumi.ResourceOptions(depends_on=[secret]))




# create bucket
bucket = gcp.storage.Bucket('workpress-bucket',
                            location=gcp_region)

member = gcp.storage.BucketIAMMember("member",
    bucket=bucket.id,
    role="roles/storage.admin",
    member=pulumi.Output.concat("serviceAccount:", service_account.email))

# create firewall allow ingress iap traffic
default_firewall = gcp.compute.Firewall("allow-from-iap",
    network=wordpress_network.name,
    allows=[
        gcp.compute.FirewallAllowArgs(
            protocol="tcp",
            ports=[
                "22",
            ],
        ),
    ],
    priority=500,
    source_ranges=["35.235.240.0/20"])

cloudrun_firewall = gcp.compute.Firewall("allow-from-cloudrun",
    network=wordpress_network.name,
    allows=[
        gcp.compute.FirewallAllowArgs(
            protocol="tcp",
            ports=[
                "3306",
                "111",
                "2049"
            ],
        ),
    ],
    priority=500,
    source_ranges=["10.8.0.0/28"])


pulumi.export("cloud_sql_instance_name", pulumi.Output.format(workpress_cloudsql.name))
pulumi.export("Cloud SQL IP", pulumi.Output.format(workpress_cloudsql.private_ip_address))

pulumi.export("VPC", pulumi.Output.format(wordpress_network.self_link))
pulumi.export("Subnet", pulumi.Output.format(wordpress_subnetwork.self_link))

pulumi.export("cloud run url", pulumi.Output.format(workpress_cloudrun.uri))