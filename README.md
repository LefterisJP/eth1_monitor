# eth1_monitor
Simple script to monitor an eth1 node and stop it if it falls out of sync

## Usage

`python main.py --eth1-rpc-endpoint http://localhost:XXXX --sleep-time 10 --max-oracle-failures 10 --max-block-difference 25`

where for:
 - `--eth1-rpc-endpoint`: you give the eth1 rpc endpoint you need to monitor
 - `--sleep-time`: the time in seconds to sleep between checks
 - `--max-oracle-failures`: The maximum number of times reaching the oracle (etherscan) can fail before we bail
 - `--max-block-difference`: The maximum block difference that will be tolerated. Anything above it the eth1 node will be stopped
 
 
 ## Possible way to automate
 
 A nice way to automate this would be via a systemd service. An example service file is below
 
 ```
[Unit]
Description=Simple script to monitor an eth1 node and stop it if it falls out of sync
Requires=network.target
After=turbogeth-rpc-daemon.service

[Service]
ExecStart=python /home/lefteris/w/eth1_monitor/main.py --eth1-rpc-endpoint http://localhost:XXX --sleep-time 20 --max-oracle-failures \
10 --max-block-difference 25
Type=simple
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

 ```
