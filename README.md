# nios_get_zones_a_cname
This program connects to an Infoblox NIOS Grid and retrieves all zones, from all DNS views. It then retrieves the respective CNAME and A records from each zone and outputs them to a CSV file.

## Prerequisites
* Python 3.6+

## Usage
```
nios_get_zones_a_cname.py [-h] [-k] [-t] [-w VERSION] [-m MAX-RESULTS] [-u USER] [-o FILE] HOST
```
**Arguments**:
- Positional arguments
  - **HOST**
    - The hostname or IP address of the Grid Master/Grid Master Candidate

- Optional arguments
  - **-h, --help**
    -  Display the help messsage
  - **-k** 
    - Disable SSL verification
  - **-t** 
    - Truncate if results is greater than MAX-RESULTS (Default: False)
  - **-w VERSION**
    - WAPI version to use *(Default: 2.12.2)* 
  - **-m MAX-RESULTS**
    - Number of results per request *(Default: 100)*
  - **-u USER, --user USER**
    - The username for authentication *(Default: admin)*
  - **-o FILE**
    - CSV output filename (Default: zones.csv)

## Example
```
nios_get_zones_a_cname.py -k -w 2.12 -u aensminger -o example.csv mygrid.lab
Enter the password for user 'aensminger':
Using WAPI version: 2.12
Attempting to log in to mygrib.lab ... OK
Gathering all authoritative zones . OK
Gathering A and CNAME records for 6 zones ...
[1/6]  Zone: (10.33.122.0/24)
        - Requesting A records .......  OK
        - Requesting CNAME records ...  OK
[2/6]  Zone: (10.33.124.0/24)
        - Requesting A records .......  OK
        - Requesting CNAME records ...  OK
[3/6]  Zone: (10.33.178.0/24)
        - Requesting A records .......  OK
        - Requesting CNAME records ...  OK
[4/6]  Zone: (examplezone1.net)
        - Requesting A records .......  OK
        - Requesting CNAME records ...  OK
[5/6]  Zone: (examplezone2.com)
        - Requesting A records .......  OK
        - Requesting CNAME records ...  OK
[6/6]  Zone: (examplezone3.org)
        - Requesting A records .......  OK
        - Requesting CNAME records ...  OK
Logging out of mygrid.lab ... OK
Saving data to example.csv ... Done
Total execution time: 4.39 seconds
```
