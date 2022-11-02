# Tool to create list of ip networks to work with bird
This tool is designed to create list of networks to be distributed with [bird](https://bird.network.cz/) ver 1.x.

Reasoning behind this tool — i need to access a lot of services in Russia, but while i'm not in country - a lot of services blocks access to them. Using this tool and data from network registers (RIPE, ARIN, AfriNIC, APNIC, LACNIC) i'm able to distribute most of Russia's public IP ranges to be routed trough VPN connetion with use of my home router and some cheapo VPS server in Russia.

Tool uses standart library in python3, so all you need is Python3 and Bird installed.

## Usage

 1. Create configuration file named `config.json` and fill it based on `config.json.example`
 2. Install bird and configure `bird.conf` based on `bird.conf.example`
 3. Install some VPN software on VPN and configure client on your router. For example you can see https://github.com/hwdsl2/setup-ipsec-vpn or https://github.com/angristan/wireguard-install 
 4. Configure BGP on your client based on your `bird.conf`
 My example on Mikrotik RouterOS 7:
````
/routing bgp connection
add as=64666 disabled=no input.filter=static_bgp .ignore-as-path-len=yes local.role=ibgp name=Russia remote.address=192.168.42.1/32 .as=\
    64666 router-id=192.168.42.10 routing-table=main templates=default
/routing filter rule
add chain=static_bgp disabled=no rule="set gw-interface l2tp_russia; set distance 15; accept"
````
 5. Create cron job for recreating tabled of remote networks:
````
0 6 15 * * python3 /root/bgp/createtable.py && /usr/sbin/birdc configure
````