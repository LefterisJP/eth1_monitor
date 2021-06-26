import argparse
import json
import logging
import sys
import time
from subprocess import call

import requests

log = logging.getLogger(__name__)


def configure_logging():
    root = log
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)


def stop_rpc_daemon():
    """This stops the local eth client. Customize for your needs"""
    call(['systemctl', 'stop', 'erigon-rpc-daemon'])


def _get_result(location: str, response: requests.Response) -> int:
    try:
        json_ret = json.loads(response.text)
    except json.JSONDecodeError:
        raise ValueError(f'{location} returned invalid JSON response: {response.text}')

    result = json_ret.get('result', None)
    if result is None:
        raise ValueError(
            f'Unexpected format of {location} response for request {response.url}. '
            f'Missing a result in response. Response was: {response.text}',
        )

    return int(result, 16)


def get_oracle_block_number() -> int:
    query_str = 'https://api.etherscan.io/api?module=proxy&action=eth_blockNumber'
    try:
        response = requests.get(query_str)
    except requests.exceptions.RequestException as e:
        msg = f'Etherscan query failed due to {str(e)}'
        raise ValueError(msg)

    if response.status_code != 200:
        raise ValueError(
            f'Etherscan API request {response.url} failed '
            f'with HTTP status code {response.status_code} and text '
            f'{response.text}',
        )

    return _get_result('etherscan', response)


def get_local_block_number(eth_rpc_endpoint: str) -> int:
    json_data = {'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'params': [], 'id': 1}
    try:
        response = requests.post(eth_rpc_endpoint, json=json_data)
    except requests.exceptions.RequestException as e:
        msg = f'Local node query failed due to {str(e)}'
        raise ValueError(msg)

    if response.status_code != 200:
        raise ValueError(
            f'Local node API request {response.url} failed '
            f'with HTTP status code {response.status_code} and text '
            f'{response.text}',
        )

    return _get_result('local node', response)


def main(args):
    subsequent_oracle_failures = 0
    while True:
        try:
            local_block_number = get_local_block_number(args.eth1_rpc_endpoint)
        except ValueError as e:
            log.critical(
                f'Failed to get block number from local rpc due to {str(e)}. '
                f'Stopping rpc daemon ...'
            )
            stop_rpc_daemon()
            break

        try:
            master_block_number = get_oracle_block_number()
        except ValueError as e:
            log.error(f'Failed to get block number from oracle due to {str(e)}')
            subsequent_oracle_failures += 1
            if subsequent_oracle_failures == args.max_oracle_failures:
                log.error(
                    f'Failed to get block number from oracle due to {str(e)} '
                    f'for 10 subsequent times. Stopping rpc daemon just to be safe ...'
                )
                stop_rpc_daemon()
                break
        else:
            subsequent_oracle_failures = 0  # reset counter

        diff = master_block_number - local_block_number
        if diff > args.max_block_difference:
            log.error(
                f'Local block number: {local_block_number}, Oracle block '
                f'number: {master_block_number}. Diff: {diff} > '
                f'{args.max_block_difference}. Stopping rpc daemon ...'
            )
            stop_rpc_daemon()
            break
        else:
            log.info(
                f'Local block number: {local_block_number}, Oracle block '
                f'number: {master_block_number}. Diff: {diff}. All good.'
            )

        time.sleep(args.sleep_time)


if __name__ == "__main__":
    configure_logging()
    parser = argparse.ArgumentParser(
        prog='Eth1 monitor',
        description=(
            'Script to monitor eth1 node sync status and kill it if not in sync '
            'so that the backup (remote) nodes can take over',
        )
    )
    parser.add_argument(
        '--eth1-rpc-endpoint',
        required=True,
        help='The local eth rpc endpoint to monitor',
        type=str,
    )
    parser.add_argument(
        '--sleep-time',
        help='The time in seconds to sleep between each run',
        type=int,
        default=10,
    )
    parser.add_argument(
        '--max-oracle-failures',
        help='The maximum number of times the oracle call can fail before we bail',
        type=int,
        default=10,
    )
    parser.add_argument(
        '--max-block-difference',
        help=(
            'The maximum blocks difference the local node can have from the oracle before we bail',
        ),
        type=int,
        default=25,
    )
    args = parser.parse_args()
    main(args)
