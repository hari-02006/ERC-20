from flask import Flask, render_template, request
import requests
from web3 import Web3
from datetime import datetime, timezone

app = Flask(__name__)

# Initialize Web3 (Alchemy API URL)
ALCHEMY_API_URL = 'https://eth-mainnet.g.alchemy.com/v2/mpqtqAbC9VgsXnCIusc11YMIQDuVFEOI'
w3 = Web3(Web3.HTTPProvider(ALCHEMY_API_URL))

# ERC-20 ABI (Minimal)
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
]

# CoinGecko API to fetch extended market data
def get_extended_market_data(contract_address):
    url = f"https://api.coingecko.com/api/v3/coins/ethereum/contract/{contract_address}"
    response = requests.get(url)
    data = response.json()

    if 'market_data' in data:
        return {
            'market_price': data['market_data']['current_price'].get('usd'),
            'market_cap': data['market_data']['market_cap'].get('usd'),
            'volume_24h': data['market_data']['total_volume'].get('usd'),
            'price_change_24h': data['market_data'].get('price_change_percentage_24h'),
            'rank': data.get('market_cap_rank'),
            'ath': data['market_data']['ath'].get('usd'),
            'atl': data['market_data']['atl'].get('usd'),
            'circulating_supply': data['market_data'].get('circulating_supply'),
            'total_supply': data['market_data'].get('total_supply'),
        }
    else:
        return {}


# Function to fetch token information
def get_token_info(contract_address):
    try:
        contract = w3.eth.contract(address=contract_address, abi=ERC20_ABI)
        name = contract.functions.name().call()
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        total_supply = contract.functions.totalSupply().call() / (10 ** decimals)
        
        return name, symbol, decimals, total_supply
    except Exception as e:
        return None, None, None, None

# Function to fetch token creation date
def get_token_creation_date(contract_address):
    try:
        url = f"https://api.etherscan.io/api"
        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': contract_address,
            'page': 1,
            'offset': 1,
            'sort': 'asc',
            'apikey': 'BG82363TXYYNZ4PSF2ZCDQSQS44CBVVIBJ'
        }
        response = requests.get(url, params=params)
        data = response.json()
        transactions = data.get('result', [])
        if transactions:
            creation_tx = transactions[0]
            timestamp = int(creation_tx.get('timeStamp'))
            creation_date = datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            return creation_date
        else:
            return None
    except Exception as e:
        return None

# Function to fetch transfer count
def get_transfer_count(contract_address):
    try:
        transfers_url = "https://api.etherscan.io/api"
        transfers_params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': contract_address,
            'startblock': 0,
            'endblock': 99999999,
            'page': 1,
            'offset': 100,
            'sort': 'asc',
            'apikey': 'BG82363TXYYNZ4PSF2ZCDQSQS44CBVVIBJ'
        }
        transfers_response = requests.get(transfers_url, params=transfers_params)
        transfers_data = transfers_response.json()
        total_transfers = transfers_data.get('result', [])
        return len(total_transfers)
    except Exception as e:
        return 0

# Function to fetch current gas price
def get_current_gas_price():
    try:
        gas_price_wei = w3.eth.gas_price
        gas_price_gwei = w3.from_wei(gas_price_wei, 'gwei')
        return gas_price_gwei
    except Exception as e:
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    token_info = None
    if request.method == 'POST':
        token_address = request.form.get('address').strip()
        if w3.is_address(token_address):
            token_address = w3.to_checksum_address(token_address)

            # Get token information
            name, symbol, decimals, total_supply = get_token_info(token_address)

            # Get extended market data
            market_data = get_extended_market_data(token_address)
            creation_date = get_token_creation_date(token_address)
            transfer_count = get_transfer_count(token_address)
            gas_price = get_current_gas_price()

            # Prepare data to be passed to the template
            token_info = {
                'name': name,
                'symbol': symbol,
                'decimals': decimals,
                'total_supply': total_supply,
                'market_price': market_data.get('market_price'),
                'market_cap': market_data.get('market_cap'),
                'volume_24h': market_data.get('volume_24h'),
                'price_change_24h': market_data.get('price_change_24h'),
                'rank': market_data.get('rank'),
                'ath': market_data.get('ath'),
                'atl': market_data.get('atl'),
                'circulating_supply': market_data.get('circulating_supply'),
                'cg_total_supply': market_data.get('total_supply'),
                'creation_date': creation_date,
                'transfer_count': transfer_count,
                'gas_price': gas_price
            }
        else:
            token_info = {'error': 'Invalid Ethereum address.'}
    return render_template('index.html', token_info=token_info)

if __name__ == '__main__':
    app.run(debug=True)
