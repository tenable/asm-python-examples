# Bit Discovery Python scripts

These scripts demonstrate how you can integrate your work with the Bit Discovery API.

To run these scripts, you have to have [Python 3.6+](https://www.python.org/downloads/) installed on your computer and
your Bit Discovery API keys for an inventory. (You can get this on
your [Bit Discovery profile page](https://dev.bitdiscovery.com/user/profile).) The best way is to save your API key to a
variable and reuse it for every script.

```shell
APIKEY=eyJh...hUFs
python pdf-report.py $APIKEY
```

If you need more information about the options of any script, just see the help message:

```shell
python pdf-report.py --help
```

## PDF Report

The `pdf-report.py` script exports the assets from one or all of your inventories (`--multiple` flag), and creates a PDF
file analysis based on the inventory data.

### Usage

Install the dependencies:

```shell
pip install argparse datetime fpdf2 matplotlib pypdf2 requests
```

Create a pdf report by passing the inventory api key:

```shell
python3 pdf-report.py $APIKEY
```

If you want to create a pdf report for every inventory you own, you can pass the `--multiple` flag:

```shell
python3 pdf-report.py $APIKEY --multiple
```

## Auto add assets

The `auto-add-assets.py` script can search your cloud provider, AWS, Google Cloud or Azure (using their respective
command-line tools), and add your running instances to the provided inventory.

### Usage

For this script you need to have and be signed in to the command-line interfaces of your cloud provider of choice. For
AWS, install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html), for GCP Cloud
the [gcloud CLI](https://cloud.google.com/sdk/docs/install) and for
Azure [az](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli).

After that, install the Python dependencies:

```shell
pip install argparse datetime requests sh
```

Read your running EC2 instances and buckets from your AWS account:

```shell
python3 auto-add-assets.py amazon-ec2 $APIKEY
```

Similarly for Google Cloud and Azure:

```shell
# GCP
python3 auto-add-assets.py google-cloud $APIKEY
# Azure
python3 auto-add-assets.py azure $APIKEY
```

## Delete ip or source

The `delete-ip.py` script deletes one specific IP or source from your inventory.

### Usage

First, install the Python dependencies:

```shell
pip install argparse requests sh
```

Delete an IP or a source (with its id) from the given inventory:

```shell
python3 delete-ip.py ip 1.1.1.1 $APIKEY
python3 delete-ip.py source 13 $APIKEY
```

## Add IP by geography

The `add-by-geo.py` script adds country-specific IP sources to your inventory based on the IP2 location repository.

__Note: this may add a huge number of sources, it is not recommended to use this script__
__without first running without the --add-to-inventory parameter__

### Usage

First, register for an account with IP2Location LITE - http://lite.ip2location.com

Second, download the IP2location-lite database files (IPv6) CSV files and place in the `./ip2loc/` folder.

Third, install the dependencies:

```shell
pip install argparse requests sortedcontainers
```

Finally, update APIURL and obtain a single-inventory API key to use as argument to --apikey

Add to inventory all country-specific (-c = UA) IP ranges (-4, IPv4 only) as sources:

```shell
python3 add-by-geo.py -4 -f COUNTRY_CODE=UA --add-to-inventory --apikey=asdfasdf
```

It is an error to use `--add-to-inventory` without a valid, single-inventory API key.

Output, but do not add to inventory all ip ranges coorsponding to Los Angeles in country=US:

```shell
python3 add-by-geo.py -f COUNTRY_CODE=US -f CITY="Los Angeles"
```

Output, but do not add to inventory all IP ranges in any country, region, or city named "Dallas"
```shell
python3 add-by-geo.py -f ANY="Dallas"
```