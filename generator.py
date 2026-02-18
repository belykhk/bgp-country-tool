#!/usr/bin/env python3

"""
Author - Kostya Belykh k@belykh.su
Language - Python 3.8+
This script is designed to parse data from country network addresses and
generate configuration file for bind to distribute as BGP table. For additional
information please refer to README.md file.
"""

import json
import logging
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from ipaddress import ip_network

import requests
from dotenv import load_dotenv
from netaddr import cidr_merge

load_dotenv()

SOURCE_CONFIG = {
    "source": json.loads(os.getenv("SOURCESURLS")),
    "countries": json.loads(os.getenv("COUNTRIES")),
    "enable_ipv4": os.getenv("ENABLEIPV4") == "True",
    "append_ipv4": json.loads(os.getenv("APPENDIPV4")),
    "exclude_ipv4": json.loads(os.getenv("EXCLUDEIPV4")),
    "enable_ipv6": os.getenv("ENABLEIPV6") == "True",
    "append_ipv6": json.loads(os.getenv("APPENDIPV6")),
    "exclude_ipv6": json.loads(os.getenv("EXCLUDEIPV6")),
}

OUTPUT_CONFIG = {
    "output_format": os.getenv("OUTPUTFORMAT"),
    "output_file_ipv4": os.getenv("OUTPUTFILEIPV4"),
    "output_file_ipv6": os.getenv("OUTPUTFILEIPV6"),
}

start = time.time()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def netmaskcidr(num_hosts):
    # Return cidr notation of netmask based on number of hosts it contains
    required_bits = math.ceil(math.log2(int(num_hosts)))
    network_bits = 32 - required_bits
    return f"{network_bits}"


def updatesubnet(networks, subnets_to_remove, subnets_to_add):
    networks = cidr_merge(networks)
    returnnetworks = set()
    for network in networks:
        if subnets_to_remove:
            for subnet in subnets_to_remove:
                if ip_network(subnet, strict=False).overlaps(ip_network(network, strict=False)):
                    resultnets = list(
                        ip_network(network, strict=False).address_exclude(ip_network(subnet, strict=False))
                    )
                    for net in resultnets:
                        returnnetworks.add(str(net))
                else:
                    returnnetworks.add(network)
        else:
            returnnetworks.add(network)
    for subnet in subnets_to_add:
        returnnetworks.add(subnet)
    # Correct data in case some registrars have wrong info about network
    corrected_networks = set()
    for network in returnnetworks:
        n = ip_network(network, strict=False)
        corrected_networks.add(str(f"{n.network_address}/{n.prefixlen}"))
    return corrected_networks


def fetch_source_lines(source_name, source_address, retries=10, backoff_seconds=5):
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(source_address)
            response.raise_for_status()
            return response.text.splitlines()
        except requests.RequestException as e:
            if attempt == retries:
                logging.error(f"Unable to retrieve data from {source_name}: {e}")
                raise RuntimeError(f"Unable to retrieve data from {source_name}: {e}") from e

            logging.warning(
                f"Unable to retrieve data from {source_name}: {e}. "
                f"Retrying in {backoff_seconds} seconds ({attempt}/{retries})"
            )
            time.sleep(backoff_seconds)


def save_output(networks, output_file, output_format):
    with open(output_file, "w") as f:
        for network in networks:
            f.write(output_format.format(network) + "\n")
    logging.info(f"Output saved to {output_file}")


def main():
    logging.info("**************")
    logging.info("Script started")

    data = {}
    with ThreadPoolExecutor(max_workers=min(32, len(SOURCE_CONFIG["source"]) or 1)) as executor:
        futures = {}
        for s in SOURCE_CONFIG["source"]:
            logging.info(f'Retreiwing data from {s["Name"]}')
            future = executor.submit(fetch_source_lines, s["Name"], s["Address"])
            futures[future] = s["Name"]

        for future in as_completed(futures):
            source_name = futures[future]
            try:
                data[source_name] = future.result()
            except RuntimeError as e:
                sys.exit(str(e))

    reportipv4 = set()
    reportipv6 = set()
    for s in SOURCE_CONFIG["source"]:
        logging.info(f'Processing data from {s["Name"]}')
        for line in data[s["Name"]]:
            try:
                l = line.split("|")
                if l[1] in SOURCE_CONFIG["countries"]:
                    if l[2] == "ipv4" and bool(SOURCE_CONFIG["enable_ipv4"]) == True:
                        reportipv4.add(str(f"{l[3]}/{netmaskcidr(l[4])}"))
                    if l[2] == "ipv6" and bool(SOURCE_CONFIG["enable_ipv6"]) == True:
                        reportipv6.add(str(f"{l[3]}/{l[4]}"))
            except IndexError:
                # Sometimes lines do not have separators
                pass
    if bool(SOURCE_CONFIG["enable_ipv4"]) == True:
        reportipv4 = updatesubnet(reportipv4, SOURCE_CONFIG["exclude_ipv4"], SOURCE_CONFIG["append_ipv4"])
    if bool(SOURCE_CONFIG["enable_ipv6"]) == True:
        reportipv6 = updatesubnet(reportipv6, SOURCE_CONFIG["exclude_ipv6"], SOURCE_CONFIG["append_ipv6"])

    if bool(SOURCE_CONFIG["enable_ipv4"]) == True:
        logging.info(f"IPv4 networks: {len(reportipv4)}")
        save_output(reportipv4, OUTPUT_CONFIG["output_file_ipv4"], OUTPUT_CONFIG["output_format"])
    if bool(SOURCE_CONFIG["enable_ipv6"]) == True:
        logging.info(f"IPv6 networks: {len(reportipv6)}")
        save_output(reportipv6, OUTPUT_CONFIG["output_file_ipv6"], OUTPUT_CONFIG["output_format"])

    logging.info(f"Script finished. Runtime: {str(round(time.time() - start, 3))} seconds.")
    sys.exit(0)


if __name__ == "__main__":
    main()
