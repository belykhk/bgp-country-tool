#!/usr/bin/env python3

"""
Author - Kostya Belykh k@belykh.su
Language - Python 3.8+
This script is designed to parse data from country network addresses and 
generate configuration file for bind to distribute as BGP table. For additional
information please refer to README.md file.
"""

from optparse import OptionParser
from netaddr import cidr_merge
import logging
import time
import os
import json
import sys
import urllib.request
import ipaddress
import math

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
    p.add_option('-c', '--config',
                 dest = 'configfile',
                 help = 'Configuration file to use, default is ./config.json',
                 default = os.path.join(sys.path[0],'config.json')
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

    main(options.configfile)

def main(configfile):
    logging.info('************************************************************')
    logging.info('Script started')

    logging.info('Importing configuration file')
    try: 
        with open(configfile, encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        sys.exit('Configuration file not found, exiting')

    logging.info('Current configuration:')
    logging.info('  Sources:')
    for s in config['Sources']:
        logging.info('    Name: {}, Address: {}'.format(
            s['Name'], s['Address']
        ))
    logging.info('  Countries: {}'.format(config['Countries']))
    logging.info('  Enable IPv4: {}'.format(bool(config['EnableIPv4'])))
    if bool(config['EnableIPv4']) == True:
        logging.info('    IPv4 networks to be appended: {}'.format(
            config['AppendIPv4']
        ))
        logging.info('    Output file for IPv4 networks: {}'.format(
            config['OutputFileipv4']
        ))
    logging.info('  Enable IPv6: {}'.format(bool(config['EnableIPv6'])))
    if bool(config['EnableIPv6']) == True:
        logging.info('    IPv6 networks to be appended: {}'.format(
            config['AppendIPv6']
        ))
        logging.info('    Output file for ipv6 networks: {}'.format(
            config['OutputFileipv6']
        ))
    logging.info('  Summarize networks: {}'.format(
        bool(config['SummarizeNetworks'])
    ))
    logging.info('  Summarize output file: {}'.format(
        config['SummarizeOutput']
    ))
    if bool(config['SummarizeOutput']) == True:
        logging.info('    Output file for summarized networks: {}'.format(
            config['SummarizeOutputFile']
        ))
    logging.info('  Output format: {}'.format(config['OutputFormat']))

    logging.info('Retrieving data from sources')
    data = {}
    for s in config['Sources']:
        logging.info('  Retreiwing data from {}'.format(s['Name']))
        try:
            with urllib.request.urlopen(s['Address']) as f:
                data[s['Name']] = f.read().decode('utf-8').splitlines()
        except urllib.error.URLError as e:
            logging.error('  Unable to retrieve data from {}: {}'.format(
                s['Name'],
                e.reason
            ))
            sys.exit('Unable to retrieve data from {}: {}'.format(
                s['Name'],
                e.reason
            ))
    
    logging.info('Generating report')
    reportipv4 = []
    reportipv6 = []
    reportsum = []
    for s in config['Sources']:
        logging.info('  Processing data from {}'.format(s['Name']))
        for line in data[s['Name']]:
            try:
                l = line.split('|')
                if l[1] in config['Countries']:
                    if l[2] == 'ipv4' and bool(config['EnableIPv4']) == True:
                        network = str(
                            ipaddress.ip_network(
                                str('{}/{}'.format(
                                    l[3],
                                    str(int(32-math.log(int(l[4]),2)))
                                )), 
                                strict=False
                            )
                        )
                        if network not in reportipv4:
                            reportipv4.append(network)
                    if l[2] == 'ipv6' and bool(config['EnableIPv6']) == True:
                        network = str(
                            ipaddress.ip_network(
                                str('{}/{}'.format(
                                    l[3],
                                    l[4]
                                )), 
                                strict=False
                            )
                        )
                        if network not in reportipv6:
                            reportipv6.append(network)
                    if (
                        l[2] == 'ipv4' or
                        l[2] == 'ipv6'
                    ) and bool(config['SummarizeOutput']) == True:
                        if l[2] == 'ipv4':
                            netmask = str(int(32-math.log(int(l[4]),2)))
                        elif l[2] == 'ipv6':
                            netmask = l[4]
                        else:
                            pass
                        network = str(
                            ipaddress.ip_network(
                                str('{}/{}'.format(
                                    l[3],
                                    netmask
                                )), 
                                strict=False
                            )
                        )
                        if network not in reportsum:
                            reportsum.append(network)
            except IndexError:
                # Sometimes lines do not have separators 
                pass
    if bool(config['EnableIPv4']) == True:
        for network in config['AppendIPv4']:
            if network not in reportipv4:
                reportipv4.append(network)
    if bool(config['EnableIPv6']) == True:
        for network in config['AppendIPv6']:
            if network not in reportipv6:
                reportipv6.append(network)
    logging.info('  Report generation complete')
    if bool(config['EnableIPv4']) == True:
        logging.info('    IPv4 networks: {}'.format(len(reportipv4)))
    if bool(config['EnableIPv6']) == True:
        logging.info('    IPv6 networks: {}'.format(len(reportipv6)))
    if bool(config['SummarizeOutput']) == True:
        logging.info('    Sum of all networks: {}'.format(len(reportsum)))

    if bool(config['SummarizeNetworks']) == True:
        logging.info('Summarizing networks')
        if bool(config['EnableIPv4']) == True:
            reportipv4 = cidr_merge(reportipv4)
            logging.info('  IPv4 networks: {}'.format(len(reportipv4)))
        if bool(config['EnableIPv6']) == True:
            reportipv6 = cidr_merge(reportipv6)
            logging.info('  IPv6 networks: {}'.format(len(reportipv6)))
        if bool(config['SummarizeOutput']) == True:
            reportsum = cidr_merge(reportsum)
            logging.info('  Sum of all networks: {}'.format(len(reportsum)))
    
    logging.info('Saving report')
    if bool(config['EnableIPv4']) == True:
        logging.info('  Saving IPv4 report to {}'.format(
            config['OutputFileipv4']
        ))
        with open(config['OutputFileipv4'], 'w') as file:
            for line in reportipv4:
                file.write(config['OutputFormat'].format(str(line))+'\n')
            file.close
    if bool(config['EnableIPv6']) == True:
        logging.info('  Saving IPv6 report to {}'.format(
            config['OutputFileipv6']
        ))
        with open(config['OutputFileipv6'], 'w') as file:
            for line in reportipv6:
                file.write(config['OutputFormat'].format(str(line))+'\n')
            file.close
    if bool(config['SummarizeOutput']) == True:
        logging.info('  Saving summarized report to {}'.format(
            config['SummarizeOutputFile']
        ))
        with open(config['SummarizeOutputFile'], 'w') as file:
            for line in reportsum:
                file.write(config['OutputFormat'].format(str(line))+'\n')
            file.close

    logging.info('Script finished. Runtime: {} seconds.'.format(
        str(round(time.time() - start, 3))
        )
    )

if __name__ == '__main__':
    parseCommandOptions()