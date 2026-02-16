#!/usr/bin/env python3

"""
Author - Kostya Belykh k@belykh.su
Language - Python 3.8+
This script is designed to parse data from country network addresses and
generate configuration file for bind to distribute as BGP table. For additional
information please refer to README.md file.
"""

import atexit
import json
import logging
import math
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from ipaddress import ip_network

import requests
import routeros_api
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

ROUTEROS_CONFIG = {
    "routeros_host": os.getenv("ROUTEROSHOST"),
    "routeros_user": os.getenv("ROUTEROSUSER"),
    "routeros_password": os.getenv("ROUTEROSPASSWORD"),
    "routeros_address_list": os.getenv("ROUTEROSADDRESSLIST"),
    "routeros_api_use_ssl": os.getenv("ROUTEROSAPIUSESSL") == "True",
    "routeros_workers": int(os.getenv("ROUTEROSWORKERS", 8)),
}

start = time.time()
logger = logging.getLogger()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

_thread_local = threading.local()
_worker_connections = []
_worker_connections_lock = threading.Lock()


def create_routeros_connection():
    return routeros_api.RouterOsApiPool(
        ROUTEROS_CONFIG["routeros_host"],
        username=ROUTEROS_CONFIG["routeros_user"],
        password=ROUTEROS_CONFIG["routeros_password"],
        plaintext_login=True,
        use_ssl=ROUTEROS_CONFIG["routeros_api_use_ssl"],
    )


def get_thread_api():
    if not hasattr(_thread_local, "connection"):
        connection = create_routeros_connection()
        _thread_local.connection = connection
        _thread_local.api = connection.get_api()
        with _worker_connections_lock:
            _worker_connections.append(connection)
    return _thread_local.api


def close_worker_connections():
    with _worker_connections_lock:
        connections = list(_worker_connections)
        _worker_connections.clear()

    for connection in connections:
        try:
            connection.disconnect()
        except Exception:
            pass


def deleteaddresslist(id):
    # Function to delete address list item by id
    try:
        api = get_thread_api()
        api.get_resource("/ip/firewall/address-list").remove(id=id)
        return True
    except Exception as e:
        logging.error(f"Unable to delete address list item with id {id}: {e}")
        raise RuntimeError(f"Unable to delete address list item with id {id}: {e}") from e


def addaddresslist(address, list_name):
    # Function to add address list item
    try:
        api = get_thread_api()
        api.get_resource("/ip/firewall/address-list").add(address=address, list=list_name)
        return True
    except Exception as e:
        logging.error(f"Unable to add address list item with address {address}: {e}")
        raise RuntimeError(f"Unable to add address list item with address {address}: {e}") from e


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


def fetch_source_lines(source_name, source_address, retries=3, backoff_seconds=5):
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


def main():
    logging.info("**************")
    logging.info("Script started")

    data = {}
    for s in SOURCE_CONFIG["source"]:
        logging.info(f'Retreiwing data from {s["Name"]}')
        try:
            data[s["Name"]] = fetch_source_lines(s["Name"], s["Address"])
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
    if bool(SOURCE_CONFIG["enable_ipv6"]) == True:
        logging.info(f"IPv6 networks: {len(reportipv6)}")

    try:
        connection = create_routeros_connection()
        api = connection.get_api()
        atexit.register(connection.disconnect)
        atexit.register(close_worker_connections)
        logging.info(f"Connected to RouterOS at {ROUTEROS_CONFIG['routeros_host']}")
    except Exception as e:
        logging.error(f"Unable to connect to RouterOS: {e}")
        sys.exit(f"Unable to connect to RouterOS: {e}")

    try:
        address_list = api.get_resource("/ip/firewall/address-list")
        current_list = address_list.get(list=ROUTEROS_CONFIG["routeros_address_list"])

        # Delete old address list
        if len(current_list) > 0:
            logging.info(
                f"Deleting old address list {ROUTEROS_CONFIG['routeros_address_list']} "
                f"in RouterOS: {len(current_list)} items"
            )
            with ThreadPoolExecutor(max_workers=ROUTEROS_CONFIG["routeros_workers"]) as executor:
                futures = [executor.submit(deleteaddresslist, item["id"]) for item in current_list]

        # Create new address list
        if bool(SOURCE_CONFIG["enable_ipv4"]) == True:
            logging.info(
                f"Adding {len(reportipv4)} IPv4 networks to address list {ROUTEROS_CONFIG['routeros_address_list']}"
            )
            with ThreadPoolExecutor(max_workers=ROUTEROS_CONFIG["routeros_workers"]) as executor:
                futures = [
                    executor.submit(addaddresslist, address, ROUTEROS_CONFIG["routeros_address_list"])
                    for address in reportipv4
                ]
        if bool(SOURCE_CONFIG["enable_ipv6"]) == True:
            logging.info(
                f"Adding {len(reportipv6)} IPv6 networks to address list {ROUTEROS_CONFIG['routeros_address_list']}"
            )
            with ThreadPoolExecutor(max_workers=ROUTEROS_CONFIG["routeros_workers"]) as executor:
                futures = [
                    executor.submit(addaddresslist, address, ROUTEROS_CONFIG["routeros_address_list"])
                    for address in reportipv6
                ]

    except Exception as e:
        logging.error(f"Unable to retrieve address list from RouterOS: {e}")
        sys.exit(f"Unable to retrieve address list from RouterOS: {e}")

    logging.info(f"Script finished. Runtime: {str(round(time.time() - start, 3))} seconds.")
    sys.exit(0)


if __name__ == "__main__":
    main()
