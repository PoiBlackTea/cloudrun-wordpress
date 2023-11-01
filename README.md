## Prerequisites

Ensure you have [Python 3](https://www.python.org/downloads/) and [the Pulumi CLI](https://www.pulumi.com/docs/get-started/install/).

We will be deploying to Google Cloud Platform (GCP), so you will need an account. If you don't have an account,
[sign up for free here](https://cloud.google.com/free/). In either case,
[follow the instructions here](https://www.pulumi.com/docs/intro/cloud-providers/gcp/setup/) to connect Pulumi to your GCP account.

This example assumes that you have GCP's `gcloud` CLI on your path. This is installed as part of the
[GCP SDK](https://cloud.google.com/sdk/).

## Running the Example

After cloning this repo, `cd` into it and run these commands. 

1. Create a new stack, which is an isolated deployment target for this example:

    ```bash
    $ pulumi stack init dev
    ```

2. Set the required configuration variables for this program:

    ```bash
    $ pulumi config set gcp:project <your-gcp-project>
    $ pulumi config set gcp:region <gcp-region>
    # Cloud Run image
    $ pulumi config set workpress:image <artifact registry url>
    # Cloud SQL Disk
    $ pulumi config set workpress:disk_size <disk size>
    # Cloud SQL instance type
    $ pulumi config set workpress:tier <cloud sql instance tier>
    # Cloud SQL User for workpress
    $ pulumi config set workpress:user <user>
    $ pulumi config set workpress:db <db>
    $ pulumi config set --secret workpress:dbPassword [your-database-password-here]
    ```

    cloud sql instance type ref: [instance type](https://cloud.google.com/sql/docs/mysql/instance-settings)

3. Deploy everything with the `pulumi up` command.

    ```bash
    $ pulumi up
    ```