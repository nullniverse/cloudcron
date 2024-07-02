# CloudCron
![lake and cloud reflection](cover.jpg)


> Kubernetes cronjob to make periodical Cloudflare backups in Terraform format

This project builds atop of [cf-terraforming](https://github.com/cloudflare/cf-terraforming), leveraging all it's features. 

## Overview

__What it contains:__

- [x] Backup artifacts generated recurrently in an automated manner
- [x] Automation Python script
- [x] Dockerfile for generating the Docker container
- [x] Helm Chart for deploying the cronjob in a Kubernetes cluster

__This project uses:__

* Terraform 1.8.5
* Golang 1.22.4
* Python3 (last version at the image build date)
* cf-terraforming -dev+79ac2e6f4d66 (last version at the image build date)


__This project allows notifications!__

Use the available hook to send messages to Google Chats channel or customize 
it for your preferred tool!

Customize the Gchats channel link in `values.yaml`.

__Generated files:__

The following structure are generated for the current resources:

```
.
└── 2024
    └── 7
        └── 3
            ├── DOMAIN1.COM
            ├── DOMAIN2.COM
            ├── DOMAIN3.COM
            └── ...
```
The resources are saved this way:

```
└── DOMAIN1.COM
    ├── cloudflare_access_group.tf
    ├── cloudflare_access_identity_provider.tf
    ├── cloudflare_access_mutual_tls_certificate.tf
    ├── cloudflare_access_rule.tf
    ├── cloudflare_account_member.tf
    ├── cloudflare_argo.tf
    ├── cloudflare_bot_management.tf
    ├── cloudflare_load_balancer_monitor.tf
    ├── cloudflare_load_balancer_pool.tf
    ├── cloudflare_record.tf
    ├── cloudflare_tiered_cache.tf
    ├── cloudflare_url_normalization_settings.tf
    ├── cloudflare_zone_settings_override.tf
    ├── cloudflare_zone.tf
    └── ...
```


## Artifacts

`dir structure`
```
├── cloudcron-script.py
├── config.tf
├── Dockerfile
├── generated
│   └── 2024 ...
├── k8s
│   └── Cloudcron-app
├── requirements.txt
└── ssh
    ├── id_ed25519
    └── id_ed25519.pub
```

`cloudcron`
 - **cloudcron-script.py** - Python code responsible for communicating with Cloudflare and Terraform tool
 - **config.tf** - Terraform Provider configuration for Cloudflare (do not modify)
 - **Dockerfile** - Dockerfile for generating the Docker container image
 - **generated/** - resource terraform files, generated in the backup
 - **k8s/** - Helm template for provisioning in Kubernetes
 - **requirements.txt** - Python requirements used at container build time
 - **ssh/** - credentials to connect to Github, used by the application


| Artifact | Type | Used in | 
| ------- | ---- | -------- |
| account_resources.tsv    | Passes the list of Terraform `resources` that are in the scope of *Account*     | config-mirroring.py |
| cf_resources.tsv | `Resources` that are processed in the query to generate configurations, of the type *Zone* and *Account*    |  config-mirroring.py    |
| zoneids.tsv |  List of Zone IDs and Account IDs that the scanner will inspect    |   config-mirroring.py        |
| ssh/id_ed25519 | SSH private key used by the account that is Admin of the Github repository    | Dockerfile  |
| ssh/id_ed25519.pub |  SSH public key used by the account that is Admin of the Github repository    |  Dockerfile  |
| `YOUR-SA-CREDENTIALS.json`    |  Service Account used by automation, to connect to Cloud Object Storage     |  config-mirroring.py    |
| API_TOKEN | Environment variable containing the Cloudflare API Token used | k8s/cloudcron-app/values.yaml | Helm Chart Values file |
| GCHAT_NOTIFICATION | Webhook used for notification in Google Chats Space | k8s/cloudcron-app/values.yaml | Helm Chart Values file |

## Configuring:
> [!IMPORTANT]
> We are aware that providing ssh credentials is not the most noble of things, but we are trading usefulness for security, considering you are aware of risks and running in a self-contained environment

### Project configuration

It will hardly be necessary to update the code, unless changes arise in the structure of the `cf-terraforming` project.

To configure the project on a new cluster, for example, you will need:

 - [ ] Make sure that the k8s cluster has access to the Google Artifact Registry (GAR, preferably use it) or any other registry of your chosen
 - [ ] Resource limits supported by values ​​passed in `values.yaml`
 - [ ] Release the Service Account used on the Nodes to allow access to Google Object Storage where the .tsv files are stored


### Generating a new Docker container image


#### Choosing a Github account and generating SSH credentials

It will be necessary to modify the files in the `/ssh` folder by inserting the keys of the account used. Also - if a new image is generated - it will be necessary to change the account email configured in `values.yaml {} cronjob > script`.

> [!IMPORTANT]
> Be careful not to commit the credentials passed at this stage!

After inserting the keys, modify their file attributes:
```
chmod 644 YOUR-PUBLIC-KEY.pub
chmod 0600 YOUR-PRIV-KEY #(EX: id_ed25519)
```
When generating the new image, they will be in this path:

```
/app # cat ~/.ssh/id_ed25519.pub
/app # cat ~/.ssh/id_ed25519
```
#### Generating a new image

To generate a new image, make sure there is not one already generated on your machine by `docker image ls -a`.

* To generate a new image, run in the project folder:
 - `docker build -t cloudcron . `

It is important to check if the artifacts were generated correctly, if you want to run the container locally, run:
`docker run -it cloudcron`
Now, we will generate a new tag for the container and upload it to our Registry. For that:

 - [ ] Enter your registry in gcloud settings (ex: `gcloud auth configure-docker us-east4-docker.pkg.dev`)
 - [ ] If installing in a new, recently created cluster, it will be necessary to configure access to the repository for the cluster's SA, to do this run:
 ```
 gcloud artifacts repositories add-iam-policy-binding REGISTRY-REPO-NAME/ \
    --location=REGISTRY-LOCATION \
    --member=serviceAccount:SA@NAME.iam.gserviceaccount.com \
    --role="roles/artifactregistry.reader"
```
Now, apply the new tag to your image. We use the registry initially configured in this example:

```
docker tag cloudcron us-docker.pkg.dev/PROJECTNAME/REPONAME/cloudcron:<NEW-VERSION>
docker push us-docker.pkg.dev/PROJECTNAME/REPONAME/cloudcron:<NEW-VERSION>
```

### Installing or upgrading installation on a K8s cluster

> _The `cloudcron` namespace was used, change it to the desired one._

Update the image value in your `values.yaml` to the new image tag (if you generated one);

```
cd k8s/cloudcron-app
helm template cloudcron-app ./. --values values.yaml
```
Validate whether the changed information is as desired; Then, apply the upgrade/installation:

```
helm <upgrade|install> cloudcron-app ./. --namespace cloudcron
```
If you have changed the Service Account or it is a new installation, you will need to add it as a secret in the cluster:

If you have changed it, run it first:

`kubectl delete secret/gcs-sa-key -n cloudcron`

Once this is done, apply the SA Key file generated in the cluster as secret:

```
kubectl create secret generic gcs-sa-key --from-file=SA-JSON-FILE.json=SA-JSON-FILE.json -n cloudcron
```


### Validating the project in Kubernetes

Preferably, upload a `zoneids.tsv` into your bucket with few entries - two are enough - so that the test doesn't take too long.

If you haven't changed any names in the Helm charts, run the command below to create a Job and run the flow:

`kubectl create job --from=cronjob/cloudcron-app-job cloudcron-jobtrial -n cloudcron`

> [!TIP]
> Logs can be monitored via: `kubectl logs -f container-name`
> In the current cluster/namespace. You could also try [Coroot](https://coroot.com/) for metrics and log collection.

Once successfully validated, a folder with the current date will have been created in the path `/generated`.

After that, perform a `git pull` in your local project, delete the generated artifacts and commit to main again, to ensure that there are no incomplete backups in the project!

## Supported Terraform Features 
> [!WARNING]
> [Updated List](https://github.com/cloudflare/cf-terraforming?tab=readme-ov-file#supported-resources) 
> Any resources not listed are currently not supported.

| Resource                                                                                                                                         | Resource Scope  | Generate Supported | Import Supported |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | --------------- | ------------------ | ---------------- |
| [cloudflare_access_application](https://www.terraform.io/docs/providers/cloudflare/r/access_application)                                         | Account         | ✅                 | ✅               |
| [cloudflare_access_group](https://www.terraform.io/docs/providers/cloudflare/r/access_group)                                                     | Account         | ✅                 | ✅               |
| [cloudflare_access_identity_provider](https://www.terraform.io/docs/providers/cloudflare/r/access_identity_provider)                             | Account         | ✅                 | ❌               |
| [cloudflare_access_mutual_tls_certificate](https://www.terraform.io/docs/providers/cloudflare/r/access_mutual_tls_certificate)                   | Account         | ✅                 | ❌               |
| [cloudflare_access_policy](https://www.terraform.io/docs/providers/cloudflare/r/access_policy)                                                   | Account         | ❌                 | ❌               |
| [cloudflare_access_rule](https://www.terraform.io/docs/providers/cloudflare/r/access_rule)                                                       | Account         | ✅                 | ✅               |
| [cloudflare_access_service_token](https://www.terraform.io/docs/providers/cloudflare/r/access_service_token)                                     | Account         | ✅                 | ❌               |
| [cloudflare_account_member](https://www.terraform.io/docs/providers/cloudflare/r/account_member)                                                 | Account         | ✅                 | ✅               |
| [cloudflare_api_shield](https://www.terraform.io/docs/providers/cloudflare/r/api_shield)                                                         | Zone            | ✅                 | ❌               |
| [cloudflare_api_token](https://www.terraform.io/docs/providers/cloudflare/r/api_token)                                                           | User            | ❌                 | ❌               |
| [cloudflare_argo](https://www.terraform.io/docs/providers/cloudflare/r/argo)                                                                     | Zone            | ✅                 | ✅               |
| [cloudflare_authenticated_origin_pulls](https://www.terraform.io/docs/providers/cloudflare/r/authenticated_origin_pulls)                         | Zone            | ❌                 | ❌               |
| [cloudflare_authenticated_origin_pulls_certificate](https://www.terraform.io/docs/providers/cloudflare/r/authenticated_origin_pulls_certificate) | Zone            | ❌                 | ❌               |
| [cloudflare_bot_management](https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs/resources/bot_management)                  | Zone            | ✅                 | ✅               |
| [cloudflare_byo_ip_prefix](https://www.terraform.io/docs/providers/cloudflare/r/byo_ip_prefix)                                                   | Account         | ✅                 | ✅               |
| [cloudflare_certificate_pack](https://www.terraform.io/docs/providers/cloudflare/r/certificate_pack)                                             | Zone            | ✅                 | ✅               |
| [cloudflare_custom_hostname](https://www.terraform.io/docs/providers/cloudflare/r/custom_hostname)                                               | Zone            | ✅                 | ✅               |
| [cloudflare_custom_hostname_fallback_origin](https://www.terraform.io/docs/providers/cloudflare/r/custom_hostname_fallback_origin)               | Account         | ✅                 | ❌               |
| [cloudflare_custom_pages](https://www.terraform.io/docs/providers/cloudflare/r/custom_pages)                                                     | Account or Zone | ✅                 | ✅               |
| [cloudflare_custom_ssl](https://www.terraform.io/docs/providers/cloudflare/r/custom_ssl)                                                         | Zone            | ✅                 | ✅               |
| [cloudflare_filter](https://www.terraform.io/docs/providers/cloudflare/r/filter)                                                                 | Zone            | ✅                 | ✅               |
| [cloudflare_firewall_rule](https://www.terraform.io/docs/providers/cloudflare/r/firewall_rule)                                                   | Zone            | ✅                 | ✅               |
| [cloudflare_healthcheck](https://www.terraform.io/docs/providers/cloudflare/r/healthcheck)                                                       | Zone            | ✅                 | ✅               |
| [cloudflare_ip_list](https://www.terraform.io/docs/providers/cloudflare/r/ip_list)                                                               | Account         | ❌                 | ✅               |
| [cloudflare_load_balancer](https://www.terraform.io/docs/providers/cloudflare/r/load_balancer)                                                   | Zone            | ✅                 | ✅               |
| [cloudflare_load_balancer_monitor](https://www.terraform.io/docs/providers/cloudflare/r/load_balancer_monitor)                                   | Account         | ✅                 | ✅               |
| [cloudflare_load_balancer_pool](https://www.terraform.io/docs/providers/cloudflare/r/load_balancer_pool)                                         | Account         | ✅                 | ✅               |
| [cloudflare_logpull_retention](https://www.terraform.io/docs/providers/cloudflare/r/logpull_retention)                                           | Zone            | ❌                 | ❌               |
| [cloudflare_logpush_job](https://www.terraform.io/docs/providers/cloudflare/r/logpush_job)                                                       | Zone            | ✅                 | ❌               |
| [cloudflare_logpush_ownership_challenge](https://www.terraform.io/docs/providers/cloudflare/r/logpush_ownership_challenge)                       | Zone            | ❌                 | ❌               |
| [cloudflare_magic_firewall_ruleset](https://www.terraform.io/docs/providers/cloudflare/r/magic_firewall_ruleset)                                 | Account         | ❌                 | ❌               |
| [cloudflare_origin_ca_certificate](https://www.terraform.io/docs/providers/cloudflare/r/origin_ca_certificate)                                   | Zone            | ✅                 | ✅               |
| [cloudflare_page_rule](https://www.terraform.io/docs/providers/cloudflare/r/page_rule)                                                           | Zone            | ✅                 | ✅               |
| [cloudflare_rate_limit](https://www.terraform.io/docs/providers/cloudflare/r/rate_limit)                                                         | Zone            | ✅                 | ✅               |
| [cloudflare_record](https://www.terraform.io/docs/providers/cloudflare/r/record)                                                                 | Zone            | ✅                 | ✅               |
| [cloudflare_ruleset](https://www.terraform.io/docs/providers/cloudflare/r/ruleset)                                                               | Account or Zone | ✅                 | ✅               |
| [cloudflare_spectrum_application](https://www.terraform.io/docs/providers/cloudflare/r/spectrum_application)                                     | Zone            | ✅                 | ✅               |
| [cloudflare_tiered_cache](https://www.terraform.io/docs/providers/cloudflare/r/tiered_cache)                                                     | Zone            | ✅                 | ❌               |
| [cloudflare_teams_list](https://www.terraform.io/docs/providers/cloudflare/r/teams_list)                                                         | Account         | ✅                 | ✅               |
| [cloudflare_teams_location](https://www.terraform.io/docs/providers/cloudflare/r/teams_location)                                                 | Account         | ✅                 | ✅               |
| [cloudflare_teams_proxy_endpoint](https://www.terraform.io/docs/providers/cloudflare/r/teams_proxy_endpoint)                                     | Account         | ✅                 | ✅               |
| [cloudflare_teams_rule](https://www.terraform.io/docs/providers/cloudflare/r/teams_rule)                                                         | Account         | ✅                 | ✅               |
| [cloudflare_tunnel](https://www.terraform.io/docs/providers/cloudflare/r/tunnel)                                                                 | Account         | ✅                 | ✅               |
| [cloudflare_turnstile_widget](https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs/resources/turnstile_widget)              | Account         | ✅                 | ✅               |
| [cloudflare_url_normalization_settings](https://www.terraform.io/docs/providers/cloudflare/r/url_normalization_settings)                         | Zone            | ✅                 | ❌               |
| [cloudflare_waf_group](https://www.terraform.io/docs/providers/cloudflare/r/waf_group)                                                           | Zone            | ❌                 | ❌               |
| [cloudflare_waf_override](https://www.terraform.io/docs/providers/cloudflare/r/waf_override)                                                     | Zone            | ✅                 | ✅               |
| [cloudflare_waf_package](https://www.terraform.io/docs/providers/cloudflare/r/waf_package)                                                       | Zone            | ✅                 | ❌               |
| [cloudflare_waf_rule](https://www.terraform.io/docs/providers/cloudflare/r/waf_rule)                                                             | Zone            | ❌                 | ❌               |
| [cloudflare_waiting_room](https://www.terraform.io/docs/providers/cloudflare/r/waiting_room)                                                     | Zone            | ✅                 | ✅               |
| [cloudflare_worker_cron_trigger](https://www.terraform.io/docs/providers/cloudflare/r/worker_cron_trigger)                                       | Account         | ❌                 | ❌               |
| [cloudflare_worker_route](https://www.terraform.io/docs/providers/cloudflare/r/worker_route)                                                     | Zone            | ✅                 | ✅               |
| [cloudflare_worker_script](https://www.terraform.io/docs/providers/cloudflare/r/worker_script)                                                   | Account         | ❌                 | ❌               |
| [cloudflare_workers_kv](https://www.terraform.io/docs/providers/cloudflare/r/workers_kv)                                                         | Account         | ❌                 | ❌               |
| [cloudflare_workers_kv_namespace](https://www.terraform.io/docs/providers/cloudflare/r/workers_kv_namespace)                                     | Account         | ✅                 | ✅               |
| [cloudflare_zone](https://www.terraform.io/docs/providers/cloudflare/r/zone)                                                                     | Account         | ✅                 | ✅               |
| [cloudflare_zone_dnssec](https://www.terraform.io/docs/providers/cloudflare/r/zone_dnssec)                                                       | Zone            | ❌                 | ❌               |
| [cloudflare_zone_lockdown](https://www.terraform.io/docs/providers/cloudflare/r/zone_lockdown)                                                   | Zone            | ✅                 | ✅               |
| [cloudflare_zone_settings_override](https://www.terraform.io/docs/providers/cloudflare/r/zone_settings_override)                                 | Zone            | ✅                 | ❌               |


## References

* https://developers.cloudflare.com/terraform/advanced-topics/import-cloudflare-resources/