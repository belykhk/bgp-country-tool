# BGP Country Tool (RouterOS address-list generator)

This project builds country-based IPv4/IPv6 prefix lists from RIR delegated files and syncs them into a MikroTik RouterOS firewall address-list.

Data sources supported:
- RIPE
- ARIN
- AfriNIC
- APNIC
- LACNIC

Tools itself created with docker in mind, so it can be run on MikroTik itself via containers.

## What the script does

`generator.py`:
1. Downloads delegated stats files from `SOURCESURLS`
2. Filters records by selected `COUNTRIES`
3. Builds IPv4/IPv6 prefix sets
4. Applies `EXCLUDE*` / `APPEND*` overrides
5. Connects to RouterOS API
6. Replaces the target address-list contents with the generated set

Address-list operations are concurrent (`ThreadPoolExecutor`) and tuned by `ROUTEROSWORKERS`.

## Requirements

- Docker + Docker Compose **or** Python 3.12+
- RouterOS API access to your router

Python dependencies (see `requirements.txt`):
- `netaddr`
- `python-dotenv`
- `routeros-api`
- `requests`

## Configuration

Copy `.env.ref` to `.env` and edit values:

```bash
cp .env.ref .env
```

Windows PowerShell:

```powershell
Copy-Item .env.ref .env
```

### Environment variables

- `SOURCESURLS`: JSON array of source objects (`Name`, `Address`)
- `COUNTRIES`: JSON array of country codes, e.g. `["RU"]`. See below for all possible country codes.
- `ENABLEIPV4`: `True` / `False`
- `APPENDIPV4`: JSON array of prefixes to force-add
- `EXCLUDEIPV4`: JSON array of prefixes to remove
- `ENABLEIPV6`: `True` / `False`
- `APPENDIPV6`: JSON array of prefixes to force-add
- `EXCLUDEIPV6`: JSON array of prefixes to remove
- `ROUTEROSHOST`: RouterOS hostname/IP
- `ROUTEROSUSER`: RouterOS API user
- `ROUTEROSPASSWORD`: RouterOS API password
- `ROUTEROSADDRESSLIST`: destination address-list name
- `ROUTEROSAPIUSESSL`: `True` / `False` (TLS for API)
- `ROUTEROSWORKERS`: number of concurrent RouterOS workers (default `8`)

## Run with Docker Compose

Build and run:

```bash
docker compose up --build
```

Current `compose.yaml` passes these env vars into the container:
- `SOURCESURLS`, `COUNTRIES`
- `ENABLEIPV4`, `APPENDIPV4`, `EXCLUDEIPV4`
- `ENABLEIPV6`, `APPENDIPV6`, `EXCLUDEIPV6`
- `ROUTEROSHOST`, `ROUTEROSUSER`, `ROUTEROSPASSWORD`, `ROUTEROSADDRESSLIST`, `ROUTEROSAPIUSESSL`, `ROUTEROSWORKERS`

## Run locally (without Docker)

```bash
python -m pip install -r requirements.txt
python generator.py
```

## Notes

- JSON values in `.env` must be valid JSON (double quotes, brackets, etc.).
- Very high `ROUTEROSWORKERS` values can overload RouterOS API; start with `2-8`.
- The tool currently performs a full replace of the target address-list each run.
- For old version of tool, please see [this](https://github.com/belykhk/bgp-country-tool/tree/15980294da2543f05a2e4c94fc0abb893a2e6d57) commit

## List of possible country codes

Below is list of contry codes that can be used in configuration:
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
