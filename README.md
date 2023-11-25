## Prerequisites

Ensure you have [Python 3](https://www.python.org/downloads/) and [the Pulumi CLI](https://www.pulumi.com/docs/get-started/install/).

We will be deploying to Google Cloud Platform (GCP), so you will need an account. If you don't have an account,
[sign up for free here](https://cloud.google.com/free/). In either case,
[follow the instructions here](https://www.pulumi.com/docs/intro/cloud-providers/gcp/setup/) to connect Pulumi to your GCP account.

This example assumes that you have GCP's `gcloud` CLI on your path. This is installed as part of the
[GCP SDK](https://cloud.google.com/sdk/).

Wordpress image base on bitnami [wordpress-nginx](https://hub.docker.com/r/bitnami/wordpress-nginx/)

## Running the Example

After cloning this repo, `cd` into it and run these commands. 

1. Create Artifact Registry and Docker image

    ```
    gcloud artifacts repositories create <REPOSITORY> \
        --repository-format=docker \
        --location=<LOCATION? \
        --description=>"DESCRIPTION"> \
        --immutable-tags \
        --async
    ```

    Setup instructions
    ```
    gcloud auth configure-docker \
        us-central1-docker.pkg.dev
    ```

    ```
    docker buildx build --cache-to type=inline --platform linux/amd64 --push -t us-central1-docker.pkg.dev/<your-gcp-project>/<REPOSITORY>/<image-name>:<tag> .
    ```

2. Create a new stack, which is an isolated deployment target for this example:

    ```bash
    $ pulumi stack init dev
    ```

3. Set the required configuration variables for this program:

    ```bash
    $ pulumi config set gcp:project <your-gcp-project>
    $ pulumi config set gcp:region <gcp-region>
    # Cloud Run image
    $ pulumi config set wordpress:image <artifact registry url>
    # Cloud SQL Disk
    $ pulumi config set wordpress:disk_size <disk size>
    # Cloud SQL instance type
    $ pulumi config set wordpress:tier <cloud sql instance tier>
    # Cloud SQL User for wordpress
    $ pulumi config set wordpress:user <user>
    # Cloud SQL Database for wordpress
    $ pulumi config set wordpress:db <db>
    # Cloud SQL password for wordpress
    $ pulumi config set --secret wordpress:dbPassword [your-database-password-here]
    ```

    cloud sql instance type ref: [instance type](https://cloud.google.com/sql/docs/mysql/instance-settings)

4. Deploy everything with the `pulumi up` command.

    ```bash
    $ pulumi up
    ```


Note: you must disable deletion protection before removing the resource (e.g., via pulumi destroy), or the instance cannot be deleted and the provider run will not complete successfully.
