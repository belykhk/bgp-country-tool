# Tool to create list of ip networks to work with bird
This tool is designed to create list of networks to be distributed with [bird](https://bird.network.cz/) ver 1.x.

Reasoning behind this tool — i need to access a lot of services in Russia, but while i'm not in country - a lot of services blocks access to them. Using this tool and data from network registers (RIPE, ARIN, AfriNIC, APNIC, LACNIC) i'm able to distribute most of Russia's public IP ranges to be routed trough VPN connetion with use of my home router and some cheapo VPS server in Russia.

Tool uses `netaadr` library for summarizing adjasent networks, so aside of Python3 and Bird installed you also need to run:
````
python3 -m pip install netaddr
````

## Usage

 1. Create configuration file named `config.json` and fill it based on `config.json.example`. For additional information about config see below.
 2. Install bird and configure `bird.conf` based on `bird.conf.example` (additional information about confuration parameters is below)
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

## Configuration file parameters

 1. `Sources` - list of sources to get data from. You probably want to use all of them.
 2. `Countries` - list of countries to get data for. Possbile values are listed in section `List of possible country codes` of this document. Example: `"Countries": ["RU", "UA", "BY", "KZ"]`
 3. `EnableIPv4` - enable or disable gathering IPv4 data. Possible values: `true` or `false`  
    3.1. `AppendIPv4` - list of additional IPv4 networks to append to list. Example: `"AppendIPv4": ["192.168.0.0/24", "192.168.1.0/24"]`  
    3.2. `OutputFileipv4` - path to file where to save IPv4 networks. Example: `"/etc/bird/list.txt"`  
 4. `EnableIPv6` - enable or disable gathering IPv6 data. Possible values: `true` or `false`  
    4.1. `AppendIPv6` - list of additional IPv6 networks to append to list. Example: `"AppendIPv6": ["2001:db8::/32", "2001:db8:1::/48"]`  
    4.2. `OutputFileipv6` - path to file where to save IPv6 networks. Example: `"/etc/bird/list6.txt"`  
 5. `SummarizeNetworks` - enable or disable summarizing adjasent networks (eg 10.0.0.0/24 + 10.0.1.0/24 = 10.0.0.0/23). Possible values: `true` or `false`
 6. `SummarizeOutput` - enable saving both IPv4 and IPv6 networks in one file. Possible values: `true` or `false`. 
 7. `SummarizeOutputFile` - path to file where to save summarized networks. Example: `"/etc/bird/listall.txt"`
 8. `OutputFormat` - format of line in output. Example: `"route {0} reject;"`, where `{0}` is replaced with network.

## List of possible country codes

Below is list of contry codes that can be used in `Countries` section of `config.json`:
```
"AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AP", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ", 
"BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS", "BT", "BW", "BY", "BZ", 
"CA", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN", "CO", "CR", "CU", "CV", "CW", "CY", "CZ", 
"DE", "DJ", "DK", "DM", "DO", "DZ", 
"EC", "EE", "EG", "ER", "ES", "ET", "EU", 
"FI", "FJ", "FK", "FM", "FO", "FR", 
"GA", "GB", "GD", "GE", "GF", "GG", "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR", "GT", "GU", "GW", "GY", 
"HK", "HN", "HR", "HT", "HU", 
"ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT", 
"JE", "JM", "JO", "JP", 
"KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY", "KZ", 
"LA", "LB", "LC", "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY", 
"MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK", "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", 
"NA", "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", 
"OM", 
"PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM", "PR", "PS", "PT", "PW", "PY", 
"QA", 
"RE", "RO", "RS", "RU", "RW", 
"SA", "SB", "SC", "SD", "SE", "SG", "SI", "SK", "SL", "SM", "SN", "SO", "SR", "SS", "ST", "SV", "SX", "SY", "SZ", 
"TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TT", "TV", "TW", "TZ", 
"UA", "UG", "US", "UY", "UZ", 
"VA", "VC", "VE", "VG", "VI", "VN", "VU", 
"WF", "WS", 
"YE", "YT", 
"ZA", "ZM", "ZW"
```