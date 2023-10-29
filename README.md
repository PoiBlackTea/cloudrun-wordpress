$ export GOOGLE_PROJECT=YOURPROJECTID; export GOOGLE_REGION=asia-east1; export GOOGLE_ZONE=asia-east1-a;
$ export GOOGLE_CREDENTIALS=YOURGCPCREDENTIALS



``````
$ pulumi stack init testing
$ pulumi config set gcp:project <your-gcp-project>
$ pulumi config set gcp:region <gcp-region>
$ pulumi config set gcp:image <artifact registry url>
$ pulumi config set gcp:cloudsql:disk_size <disk size>
$ pulumi config set gcp:cloudsql:tier <cloud sql instance tier>
$ pulumi config set gcp:cloudsql:user <user>
$ pulumi config set gcp:cloudsql:db <db>
$ pulumi config set --secret dbPassword [your-database-password-here]
```
LB 和cdn設定


must set WORDPRESS_PLUGINS
gce must set delete_protection