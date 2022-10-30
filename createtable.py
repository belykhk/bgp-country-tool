#!/usr/bin/env python3

"""
Author - Kostya Belykh k@belykh.su
Language - Python 3.8+
This script is designed to parse data from country network addresses and 
generate configuration file for bind to distribute as BGP table
"""

from optparse import OptionParser
import logging
import time
import os
import json
import sys
import requests
import ipaddress


start       = time.time()
logger      = logging.getLogger()

def parseCommandOptions():

    # Parsing input parameters
    p = OptionParser(add_help_option=False,
                     usage = '%prog [options]'
    )
    p.add_option('-h', '--help',
                 action = 'store_true',
                 dest = 'help',
                 help = 'Show this message and exit'
    )
    p.add_option('-l', '--logging',
                 dest = 'enablelogging',
                 help = 'Enable logging to STDOUT',
                 action='store_true'
    )

    (options, args) = p.parse_args()

    if options.help:
        p.print_help()
        exit()

    ## Setup logging
    if options.enablelogging:
        loglevel = 'INFO'
        logFormatStr = '%(asctime)s - %(levelname)-8s - %(message)s'
        logger.setLevel(loglevel)
        chandler = logging.StreamHandler()
        formatter = logging.Formatter(logFormatStr)
        chandler.setFormatter(formatter)
        logger.addHandler(chandler)

    main()

def main():
    logging.info('************************************************************')
    logging.info('Script started')

    logging.info('Importing configuration file')
    try: 
        with open(os.path.join(sys.path[0],'config.json'), 
                  encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        sys.exit('Configuration file not found, exiting')

    logging.info('Current configuration:')
    sources = config['Sources']
    logging.info('  Sources: {}'.format(sources))
    EnableIPv4 = bool(config['EnableIPv4'])
    logging.info('  Enable IPv4: {}'.format(EnableIPv4))
    EnableIPv6 = bool(config['EnableIPv6'])
    logging.info('  Enable IPv6: {}'.format(EnableIPv6))
    OutputFile = config['OutputFile']
    logging.info('  Output file: {}'.format(OutputFile))

    report = list()

    for s in sources:
        logging.info('Retreiwing data from {}'.format(s))
        r = requests.get(s)
        if r.status_code != 200:
            logging.error('Can\'t download page {}: {}'.format(
                s,
                r.reason
            ))
            break
        logging.info(' Saving data from source')
        for line in r.text.splitlines():
            if '#' in line:
                # Ommiting line with comments, for example:
                # "# Generated 2022-10-29 12:02:05.804401"
                pass
            else:
                if type(ipaddress.ip_network(line, strict=False)) is ipaddress.IPv4Network and not EnableIPv4:
                    break
                elif type(ipaddress.ip_network(line, strict=False)) is ipaddress.IPv6Network and not EnableIPv6:
                    break
                else:
                    network = str(ipaddress.ip_network(line, strict=False))
                    if network not in report:
                        report.append(network)
    logging.info('Report generation complete')

    logging.info('Saving report to {}'.format(OutputFile))
    with open(OutputFile, 'w') as file:
        for line in report:
            file.write('route {} reject;\n'.format(line))
        file.close

    logging.info('Script finished. Runtime: {} seconds.'.format(
        str(round(time.time() - start, 3))
        )
    )

if __name__ == '__main__':
    parseCommandOptions()