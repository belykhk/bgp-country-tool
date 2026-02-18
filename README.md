# BGP Country Tool (BIRD route generator)

This project builds country-based IPv4/IPv6 prefix sets from delegated RIR files and writes them in BIRD static route format.

Supported registry sources:
- RIPE
- ARIN
- AfriNIC
- APNIC
- LACNIC

The repository includes:
- a Python generator container (`bgp-generator`)
- a BIRD container (`bird`)
- an `output/` mount shared by both

## What it does

1. Generates route files (`output_ipv4.txt` / `output_ipv6.txt`) from selected countries
2. Lets BIRD include those files and advertise them over BGP
3. Uses `bird-entrypoint.sh` to monitor config/output changes and reload BIRD

## Requirements

- Docker and Docker Compose
- Or Python 3.12+ for local generator-only runs
- A working BIRD config (`bird.conf`) mounted at `/mount/bird.conf`

Python dependencies (see `requirements.txt`):
- `netaddr`
- `python-dotenv`
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
- `COUNTRIES`: JSON array of country codes, e.g. `["RU"]` (full list below)
- `ENABLEIPV4`: `True` / `False`
- `APPENDIPV4`: JSON array of prefixes to force-add
- `EXCLUDEIPV4`: JSON array of prefixes to remove
- `OUTPUTFILEIPV4`: path inside container (default: `/mount/output_ipv4.txt`)
- `ENABLEIPV6`: `True` / `False`
- `APPENDIPV6`: JSON array of prefixes to force-add
- `EXCLUDEIPV6`: JSON array of prefixes to remove
- `OUTPUTFILEIPV6`: path inside container (default: `/mount/output_ipv6.txt`)
- `OUTPUTFORMAT`: output line template, e.g. `route {0} reject;`

## Files in `output/`

The compose setup mounts `./output` to `/mount` in both containers.

Expected files:
- `output/output_ipv4.txt` (generated when IPv4 enabled)
- `output/output_ipv6.txt` (generated when IPv6 enabled)
- `output/bird.conf` (you provide this, based on `bird.conf.example`)

Quick setup:

```powershell
Copy-Item bird.conf.example output/bird.conf
```

## Run with Docker Compose

Generate prefix files:

```bash
docker compose up --build bgp-generator
```

Start BIRD:

```bash
docker compose up --build bird
```

Run both services:

```bash
docker compose up --build
```

## Run generator locally (without Docker)

```bash
python -m pip install -r requirements.txt
python generator.py
```

## Troubleshooting

- If `bird` exits on startup, verify `output/bird.conf` exists and has valid syntax.
- Run `docker compose up bgp-generator` first to ensure output files exist.
- JSON values in `.env` must be valid JSON (double quotes and brackets).
- If BIRD is already installed on host and port `179` is in use, remove `179:179` mapping or stop host BIRD.

## List of possible country codes

Below is list of country codes that can be used in configuration:
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

## Example of RouterOS 7 client configuration to connect to Bird

```
/routing bgp instance
add as=65102 disabled=no name=bgp-ru
/routing bgp template
add as=65102 disabled=no hold-time=3m input.filter=static_bgp keepalive-time=1m name=ru routing-table=main
/routing bgp connection
add as=65102 connect=yes disabled=no hold-time=3m input.filter=static_bgp instance=bgp-ru keepalive-time=1m listen=no local.address=\
    10.250.10.2 .role=ibgp name="Russia" remote.address=10.250.10.1/32 routing-table=main templates=ru
/routing filter rule
add chain=static_bgp disabled=no rule="set gw 10.250.10.1; set distance 15; accept"
```
