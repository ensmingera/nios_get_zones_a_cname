#!/usr/bin/env python3
import argparse
import getpass
import requests
import json
import time
import sys
import os

class MaxResultsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values < 1:
            raise argparse.ArgumentError(
                self, "number of results must be a positive integer"
            )
        setattr(namespace, self.dest, values)


parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=(
        "This program connects to an Infoblox NIOS Grid and retrieves all"
        " zones, from all DNS views.\n"
        "It then retrieves the respective CNAME and A records from each zone"
        " and outputs them to a CSV file."
    ),
    epilog=(
        "Examples:\n"
        f"{sys.argv[0]} -k -w 2.10 -m 500 -u aensminger -o example.csv"
        " mygrid.lab\n"
        f"{sys.argv[0]} -w 2.12 -m 1000 -u foouser -o example2.csv"
        " 192.168.1.133"
    )
)
parser.add_argument(
    "-k", action="store_true", dest="ssl_no_verify",
    help="Disable SSL verification"
)
parser.add_argument(
    "-w", type=str, default="2.12.2", dest="wapi_ver", metavar="VERSION",
    help="WAPI version to use (Default: 2.12.2)"
)
parser.add_argument(
    "-m", type=int, default=1000, metavar="MAX-RESULTS", dest="max_results",
    action=MaxResultsAction,
    help="Number of results per request (Default: 1000)"
)
parser.add_argument(
    "-u", "--user", type=str, default="admin",
    help="The username for authentication (Default: admin)"
)
parser.add_argument(
    "host", type=str, metavar="HOST",
    help="The hostname or IP address of the Grid Master/Grid Master Candidate"
)
parser.add_argument(
    "-o", default="zones.csv", dest="output", metavar="FILE",
    help="CSV output filename (Default: zones.csv)"
)

ind_chars = "|/-\\"

args = parser.parse_args()

if args.ssl_no_verify == True:
    requests.packages.urllib3.disable_warnings()
    SECURITY_SSL_VERIFY = False
else:
    SECURITY_SSL_VERIFY = True

GM_HOST = args.host
GM_USER = args.user
MAX_RESULTS = args.max_results

output_file = os.path.basename(args.output)
if not output_file.endswith(".csv"):
    output_file += ".csv"

GM_USER_PASSWD = getpass.getpass(f"Enter the password for user '{GM_USER}': ",
                                 stream=None)

session = requests.session()

WAPI_VER = args.wapi_ver.lstrip("v")
print(f"Using WAPI version: {WAPI_VER}")

base_url = f"https://{GM_HOST}/wapi/v{WAPI_VER}/"

start_time = time.time()

# Login to the Grid
print(
    f"Attempting to log in to {GM_HOST} as {GM_USER} ... ", end="", flush=True
)
session = requests.get(
    base_url + "grid",
    verify=SECURITY_SSL_VERIFY,
    auth=(GM_USER, GM_USER_PASSWD)
)

if session.status_code == 200:
    print("OK")
else:
    print("FAIL")
    print(f"Couldn't log in. Code: {session.status_code}")
    sys.exit(1)

# Request zone_auth
i_ind = 0 # Progress indicator index
status_text = "Gathering all authoritative zones ..."
print(f"\r{status_text} ", end="", flush=True)
req_params = ("?_paging=1"
              f"&_max_results={MAX_RESULTS}"
              "&_return_as_object=1"
              "&_return_fields=network_view,view,dns_fqdn,parent")
rdata = requests.get(base_url + "zone_auth" + req_params,
                     verify=SECURITY_SSL_VERIFY,
                     cookies=session.cookies,
                     timeout=(30,60))
data = json.loads(rdata.text)
results = data['result']

while "next_page_id" in data:
    # Start a progress indicator
    print(f"\r{status_text} " + ind_chars[i_ind % len(ind_chars)],
            end="", flush=True)
    i_ind = (i_ind + 1) % len(ind_chars)
    next_page_id = data['next_page_id']
    req_params = "?_page_id=" + next_page_id
    rdata = requests.get(base_url + "zone_auth" + req_params,
                        verify=SECURITY_SSL_VERIFY,
                        cookies=session.cookies,
                        timeout=(30,60))
    data = json.loads(rdata.text)
    results = results + data['result']

# We've received all data now, as there is no next_page_id
print(f"\r{status_text}\tOK", flush=True)

uzones = {}
for entry in results:
    if entry['parent'] != '' and entry['parent'] not in uzones:
        ditem = (
            {
                entry['parent']: {
                    'network_view':entry['network_view'],
                    'view':entry['view'],
                    'records':[]
                }
            }
        )
    if entry['parent'] == '' and entry['dns_fqdn'] not in uzones:
        ditem = (
            {
                entry['dns_fqdn']: {
                    'network_view':entry['network_view'],
                    'view':entry['view'],
                    'records':[]
                }
            }
        )
    uzones.update(ditem)

# Sort zones alphabetically
zkeys = list(uzones.keys())
zkeys.sort(key=str.lower)
zones = {i: uzones[i] for i in zkeys}

# Loop through zones, and request records
print(f"Gathering A and CNAME records for {len(zones)} zones")
# Get max spacing for output
max_spacing = (len(f"{len(zones)}") * 2) + 3
for i, zone in enumerate(zones, start=1):
    position = f"[{i}/{len(zones)}]"
    spacing = (max_spacing % len(position)) + 1
    print(f"{position}{' ' * spacing}Zone: ({zone})")
    # First request A records
    status_text = (
        f"{' ' * (len(position) + spacing)}- Requesting A records ......."
    )
    print(f"\r{status_text}\t", end="", flush=True)
    req_params = (
        f"?zone={zone}&view={zones[zone]['view']}"
        f"&_paging=1&_return_as_object=1&_max_results={MAX_RESULTS}"
        "&type=record:a&_return_fields=type,name,address"
    )
    rdata = requests.get(
        base_url + "allrecords" + req_params,
        verify=SECURITY_SSL_VERIFY,
        cookies=session.cookies,
        timeout=(30,60)
    )
    data = json.loads(rdata.text)
    if "Error" not in data:
        results = data['result']
        # Append records from first page
        for record in range(len(results)):
            zones[zone]['records'].append({
                    'type':results[record]['type'],
                    'name':results[record]['name'],
                    'address':results[record]['address']
                })
        # If there was more records to get, then we'll have a next_page_id
        i_ind = 0 # Reset progress indicator index
        while "next_page_id" in data:
            # Start a progress indicator
            print(f"\r{status_text}\t" + ind_chars[i_ind % len(ind_chars)],
                  end="", flush=True)
            i_ind = (i_ind + 1) % len(ind_chars)
            next_page_id = data['next_page_id']
            req_params = "?_page_id=" + next_page_id
            rdata = requests.get(base_url + "allrecords" + req_params,
                                verify=SECURITY_SSL_VERIFY,
                                cookies=session.cookies,
                                timeout=(30,60))
            data = json.loads(rdata.text)
            results = data['result']
            # Append records from this page
            for record in range(len(results)):
                zones[zone]['records'].append(
                    {
                        'type':results[record]['type'],
                        'name':results[record]['name'],
                        'address':results[record]['address']
                    }
                )
        # We've retrieved all A records
        print(f"\r{status_text}\tOK", flush=True)
    else:
        print(f"\r{status_text}\tFAIL (Reason: {data['text']})", flush=True)

    #Now request CNAME
    status_text = (
        f"{' ' * (len(position) + spacing)}- Requesting CNAME records ..."
    )
    print(f"\r{status_text}\t", end="", flush=True)
    #CNAME needs record, then use results[record]['record']['canonical']
    req_params = (
        f"?zone={zone}&view={zones[zone]['view']}"
        f"&_paging=1&_return_as_object=1&_max_results={MAX_RESULTS}"
        "&type=record:cname&_return_fields=type,name,record"
    )
    rdata = requests.get(
        base_url + "allrecords" + req_params,
        verify=SECURITY_SSL_VERIFY,
        cookies=session.cookies,
        timeout=(30,60)
    )
    data = json.loads(rdata.text)
    if "Error" not in data:
        results = data['result']
        # Append records from first page
        for record in range(len(results)):
            zones[zone]['records'].append(
                {
                    'type':results[record]['type'],
                    'name':results[record]['name'],
                    'canonical':results[record]['record']['canonical']
                }
            )
        # If there was more records to get, then we'll have a next_page_id
        i_ind = 0 # Reset progress indicator index
        while "next_page_id" in data:
            # Start a progress indicator
            print(f"\r{status_text}\t" + ind_chars[i_ind % len(ind_chars)],
                  end="", flush=True)
            i_ind = (i_ind + 1) % len(ind_chars)
            next_page_id = data['next_page_id']
            req_params = "?_page_id=" + next_page_id
            rdata = requests.get(base_url + "allrecords" + req_params,
                                verify=SECURITY_SSL_VERIFY,
                                cookies=session.cookies,
                                timeout=(30,60))
            data = json.loads(rdata.text)
            results = data['result']
            # Append CNAME records from this page
            for record in range(len(results)):
                zones[zone]['records'].append(
                    {
                        'type':results[record]['type'],
                        'name':results[record]['name'],
                        'canonical':results[record]['record']['canonical']
                    }
                )
        # We've retrieved all CNAME records
        print(f"\r{status_text}\tOK", flush=True)
    else:
        print(f"\r{status_text}\tFAIL (Reason: {data['text']})", flush=True)

# Logout of Grid
print(f"Logging out of {GM_HOST} ... ", end="", flush=True)
response_logout = requests.post(
    base_url + "logout",
    verify=SECURITY_SSL_VERIFY,
    cookies=session.cookies
)

if response_logout.status_code == 200:
    print("OK")
else:
    print("FAIL")
    print(f"Couldn't log out. Code: {response_logout.status_code}")

# Let's save the data
print(f"Saving data to {output_file} ... ", end="", flush=True)
with open(output_file, "w", encoding="utf-8") as f:
    f.write("Zone,Type,Name,Value")
    f.write("\n")
    for zone in zones:
        for record in zones[zone]['records']:
            line = f"{zone},{record['type']},{record['name']},"
            if "canonical" in record:
                line = line + record['canonical']
            else:
                line = line + record['address']
            f.write(line)
            f.write("\n")

print("Done")
print(f"Total execution time: {round(time.time() - start_time, 2)} seconds")
