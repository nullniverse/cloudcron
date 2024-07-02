# Cooking
from google.cloud import storage
from subprocess import call
from datetime import datetime
import csv, os, re, subprocess

#############################################################
############## Load Environment variables   #################
#############################################################

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/var/secrets/google/YOUR-SA-CREDENTIALS.json'
notification_chat = os.environ['GCHAT_NOTIFICATION']
apiToken = os.environ['API_TOKEN']


################################################################################################
# Load the TSV files containing the Zone IDs and Resources to iterate during the TF generation #
################################################################################################

client = storage.Client()
bucket = client.get_bucket('cloudcron-bucket')
zoneids = bucket.blob('zoneids.tsv')
zoneids.download_to_filename('zoneids.tsv')
resources = bucket.blob('cf_resources.tsv')
resources.download_to_filename('cf_resources.tsv')
account_res = bucket.blob('account_resources.tsv')
account_res.download_to_filename('account_resources.tsv')

### Read files retrieved in current root (/app)

## File path to the TSV files
zoneid_path = 'zoneids.tsv'
resource_path = 'cf_resources.tsv'
account_path = 'account_resources.tsv'

## Zone IDs List
def read_tsv_to_dict(zoneid_path):
    with open(zoneid_path, mode='r', newline='') as zones:
        reader = csv.DictReader(zones, delimiter='\t')
        result_dict = {row['Domains']: row['Zone_ID'] for row in reader}
    return result_dict
## Resources Array
def resource_tsv_to_array(resource_path):
    with open(resource_path, mode='r', encoding="utf8") as resource_file:
        tsv_reader = csv.DictReader(resource_file, delimiter="\t")
        rarray = []
        for resource in tsv_reader:
            cf_resource = resource["Resource"]
            rarray.append(cf_resource)
        return rarray
## Account Array
def account_tsv_to_array(account_path):
    with open(account_path, mode='r', encoding="utf8") as account_file:
        tsv_reader = csv.DictReader(account_file, delimiter="\t")
        rarray = []
        for account in tsv_reader:
            cf_account = account["Account_only"]
            rarray.append(cf_account)
        return rarray
    
## Read the TSV file into a dictionary
zone_dict = read_tsv_to_dict(zoneid_path)

## Read the TSV file into an Array
resources_list = resource_tsv_to_array(resource_path)
account_resources = account_tsv_to_array(account_path)

############################################
# Pivot to retrieve and generate resources #
############################################

### Define retrieve functon invoked after folder structure generation
## Pattern for matching resource output
pattern = r'(no resources of type)'

## Func to Retrieve Configurations of Resources
def retrieveConfigs():
    for key, ids in zone_dict.items():
        global stats_ne
        global stats_success
        global stats_failed
        global apiToken

        val = ids.split(sep=',')

        # Add ZoneId
        print(f"\n\n\n[INFO] Using AccountId: {val[1]} ZoneID: {val[0]}, Domain: {key}")
        zoneId = val[0]
        accountId = val[1]

        # Generate zone path name
        current_zoneid_folder = current_path + '/' + key
        os.mkdir(current_zoneid_folder)

        # Iterate among resources and save outputs to their respective names, given their types
        for resource in resources_list:

            if resource in account_resources:
                print("\n[INFO] This is an ACCOUNT Resource Type: ",resource)
                command = ['cf-terraforming','generate','--resource-type',resource,'--account',accountId,'--token', apiToken,'--terraform-binary-path','/usr/local/bin/terraform']

            else:
                print("\n[INFO] This is a ZONE Resource Type: ",resource)
                command = ['cf-terraforming','generate','--resource-type',resource,'--zone',zoneId,'--token', apiToken,'--terraform-binary-path','/usr/local/bin/terraform']

            comm_out = subprocess.run(command, capture_output=True, text=True)
            comm_result = comm_out.stdout
            rematch = re.search(pattern, comm_result)
            if rematch:
                print("[WARNING] Resource does not exists... Proceeding to the next one")
                stats_ne = stats_ne + 1
            else:
                # Define resource file path
                tf_filename = current_zoneid_folder + '/' + resource + '.tf'
                
                # Check if output is empty
                if not comm_result:
                    print(f"[WARNING] \"{resource}\" resource not present for the current Zone ID")
                    stats_ne = stats_ne + 1
                else:
                    # Save the data to a TF file
                    out = open(tf_filename, "w+")
                    out.write(comm_result)
                    print(f"[INFO] Successfully resource generated and saved in {tf_filename}")
                    stats_success = stats_success + 1

            # Print any occurred error 
            if comm_out.stderr:
                print(f"[ERROR] {comm_out.stderr}")
                stats_failed = stats_failed + 1

### Get the current date
current_date = datetime.now()

### Extract year, month, and day
year = str(current_date.year)
month = str(current_date.month)
day = str(current_date.day)

### Statistics
stats_success = 0
stats_ne = 0
stats_failed = 0
total_domains = len(zone_dict)
total_resources = len(resources_list)

### Current date path construction and generation
current_path = '/app/cloudcron/generated/' + year + '/' + month + '/' + day

print(f"\n\n############### CLOUDCRON | Cloudflare Backup System initializing for the Year: {year}, Month: {month}, Day: {day} ###############\n\n")

curl_command = [
    "curl",
    "-XPOST",
    "-H", "Content-type: application/json",
    "-d", '{"text": "*CLOUDCRON | Cloudflare Backup System initializing... '  + str(current_date) + '*\n*Domains Scanned: ' + str(total_domains) + ' | Resources Verified for Backup: ' + str(total_resources) +'*"}',
    notification_chat
]
result = subprocess.run(curl_command, capture_output=True, text=True)


print("[INFO] System date:",datetime.now())

if os.path.exists('/app/cloudcron/generated/' + year + '/' + month + '/'):
    print("[INFO] Year/Month dir already exists! Generating folder for day " + day + "...")
    call(['tree', '/app/cloudcron/generated/'+year+'/'+month])
    try:
        os.mkdir(current_path)
        call(['tree',current_path])
        print("[INFO] Starting execution...")
        retrieveConfigs()
    except FileExistsError:
        print("[WARNING] Directory for today's backup already exists! Exiting...")

else:
    os.makedirs(current_path)
    print("[INFO] Dir structure generated!")
    call(['tree', '/app/cloudcron/generated/'+year+'/'+month])
    print("[INFO] Starting execution...")
    retrieveConfigs()

# Finish and notify
print("\n[INFO] Finishing execution...")
curl_command = [
    "curl",
    "-XPOST",
    "-H", "Content-type: application/json",
    "-d", '{"text": "*CLOUDCRON | Cloudflare Backup System Routine Finished*\n' + '*Total Domains Scanned: ' + str(total_domains) + ' | Resources Succeeded: ' + str(stats_success) + ' | Resources Not Found: ' + str(stats_ne) + ' | Failed: ' + str(stats_failed) + '*"}',
    notification_chat
]
result = subprocess.run(curl_command, capture_output=True, text=True)
last_bye = result.stdout
print("\n\n[INFO] Notification sent. Process finished.")
print("[NOTICE]\n\n",last_bye)