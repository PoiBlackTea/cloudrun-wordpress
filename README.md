$ export GOOGLE_PROJECT=YOURPROJECTID; export GOOGLE_REGION=asia-east1; export GOOGLE_ZONE=asia-east1-a;
$ export GOOGLE_CREDENTIALS=YOURGCPCREDENTIALS



``````
$ pulumi stack init testing
$ pulumi config set gcp:project <your-gcp-project>
$ pulumi config set gcp:region <gcp-region>
$ pulumi config set workpress:image <artifact registry url>
$ pulumi config set workpress:disk_size <disk size>
$ pulumi config set workpress:tier <cloud sql instance tier>
$ pulumi config set workpress:user <user>
$ pulumi config set workpress:db <db>
$ pulumi config set --secret workpress:dbPassword [your-database-password-here]
```
LB 和cdn設定

cloud sql instance type https://cloud.google.com/sql/docs/mysql/instance-settings


must set WORDPRESS_PLUGINS
gce must set delete_protection