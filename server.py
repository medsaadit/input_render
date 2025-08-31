from flask import Flask, request, jsonify
import requests
import time
from datetime import datetime
import uuid

app = Flask(__name__)

# Global storage for received tokens
stored_tokens = []

# Storage for pool monitoring configurations
pool_monitors = {}  # {pool_address: {'callback_url': str, 'callback_id': str, 'webhook_id': str}}
stored_liquidity_events = []  # Storage for liquidity events

# Shyft API configuration
SHYFT_API_KEY = "YC65T1SP6NMXDI6X"
SHYFT_BASE_URL = "https://api.shyft.to/sol/v1"

def extract_addresses(data):
    """
    Extract pool address and token_mint_two address from transaction data.
    
    Args:
        data (dict): JSON data containing transaction information
        
    Returns:
        tuple: (pool_address, token_mint_two) or (None, None) if not found
    """
    try:
        # Check if data is a dictionary
        if not isinstance(data, dict):
            print("Error: Input data is not a dictionary")
            return None, None
        
        # Initialize variables
        pool_address = None
        token_mint_two = None
        
        # Check for actions list
        if 'actions' not in data or not isinstance(data['actions'], list):
            print("Error: 'actions' field missing or not a list")
            return None, None
        
        # Search for CREATE_POOL action
        for action in data['actions']:
            if action.get('type') == 'CREATE_POOL' and 'info' in action:
                info = action['info']
                
                # Extract pool address
                if 'liquidity_pool_address' in info:
                    pool_address = info['liquidity_pool_address']
                
                # Extract token_mint_two
                if 'token_mint_two' in info:
                    token_mint_two = info['token_mint_two']
                    if token_mint_two == "So11111111111111111111111111111111111111112":
                        token_mint_two = info['token_mint_one']
                
                # Once we find the CREATE_POOL action, we can break out of the loop
                break
        
        # Verify both values were found
        if pool_address is None:
            print("Warning: 'liquidity_pool_address' not found in CREATE_POOL action")
        
        if token_mint_two is None:
            print("Warning: 'token_mint_two' not found in CREATE_POOL action")
            
        return pool_address, token_mint_two
        
    except Exception as e:
        print(f"Error extracting addresses: {str(e)}")
        return None, None

def extract_liquidity_event(data):
    """
    Extract liquidity event information from transaction data.
    
    Args:
        data (dict): JSON data containing transaction information
        
    Returns:
        dict: Liquidity event information or None if not found
    """
    try:
        if not isinstance(data, dict) or 'actions' not in data:
            return None
        
        for action in data['actions']:
            action_type = action.get('type')
            
            # Check for liquidity-related actions
            if action_type in ['REMOVE_LIQUIDITY', 'SWAP']:
                info = action.get('info', {})
                
                # Extract relevant information based on action type
                event_data = {
                    'type': action_type,
                    'timestamp': time.time(),
                    'transaction_signature': data.get('signatures', [None])[0],
                    'pool_address': None,
                    'amount_in': None,
                    'amount_out': None,
                    'token_in': None,
                    'token_out': None,
                    'user_address': data.get('fee_payer'),
                    'raw_info': info
                }
                
                # Extract pool address from different possible fields
                if 'liquidity_pool_address' in info:
                    event_data['pool_address'] = info['liquidity_pool_address']
                elif 'pool' in info:
                    event_data['pool_address'] = info['pool']
                elif 'amm' in info:
                    event_data['pool_address'] = info['amm']
                
                # Extract amounts and tokens based on action type
                if action_type == 'SWAP':
                    event_data['amount_in'] = info.get('amount_in')
                    event_data['amount_out'] = info.get('amount_out')
                    event_data['token_in'] = info.get('token_in')
                    event_data['token_out'] = info.get('token_out')
                elif action_type in ['ADD_LIQUIDITY', 'REMOVE_LIQUIDITY']:
                    event_data['amount_in'] = info.get('token_a_amount') or info.get('amount_a')
                    event_data['amount_out'] = info.get('token_b_amount') or info.get('amount_b')
                    event_data['token_in'] = info.get('token_a') or info.get('token_a_mint')
                    event_data['token_out'] = info.get('token_b') or info.get('token_b_mint')
                
                return event_data
        
        return None
        
    except Exception as e:
        print(f"Error extracting liquidity event: {str(e)}")
        return None

def create_shyft_callback(pool_address, callback_url):
    """
    Create a Shyft callback for monitoring a specific pool address.
    
    Args:
        pool_address (str): The pool address to monitor
        callback_url (str): The webhook URL to send events to
        
    Returns:
        dict: Response from Shyft API or None if failed
    """
    try:
        url = f"{SHYFT_BASE_URL}/callback/create"
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': SHYFT_API_KEY
        }
        
        # Use the deployed URL for internal processing
        internal_callback_url = f"https://input-render.onrender.com/liquidity_callback"
        
        payload = {
            "network": "mainnet-beta",
            "addresses": [pool_address],
            "callback_url": internal_callback_url,
            "type": "CALLBACK",
            "enable_raw": True,
            "enable_events": True
        }
        
        print(f"Creating Shyft callback for pool {pool_address}")
        print(f"Payload: {payload}")
        
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Shyft API response status: {response.status_code}")
        print(f"Shyft API response: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data
        else:
            print(f"Failed to create Shyft callback: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error creating Shyft callback: {str(e)}")
        return None

def delete_shyft_callback(callback_id):
    """
    Delete a Shyft callback.
    
    Args:
        callback_id (str): The callback ID to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        url = f"{SHYFT_BASE_URL}/callback/remove"
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': SHYFT_API_KEY
        }
        
        payload = {
            "callback_id": callback_id
        }
        
        response = requests.delete(url, json=payload, headers=headers)
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error deleting Shyft callback: {str(e)}")
        return False

def forward_liquidity_event(pool_address, event_data):
    """
    Forward liquidity event to the registered webhook URL.
    
    Args:
        pool_address (str): The pool address
        event_data (dict): The event data to forward
    """
    if pool_address not in pool_monitors:
        return
    
    callback_url = pool_monitors[pool_address]['callback_url']
    
    try:
        response = requests.post(
            callback_url,
            json=event_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Forwarded event to {callback_url}: {response.status_code}")
        
    except Exception as e:
        print(f"Error forwarding event to {callback_url}: {str(e)}")

@app.route('/', methods=['POST', 'GET'])  # Add GET for testing
def handle_callback():
    print("=== Callback Hit ===")
    print("Method:", request.method)
    print("Headers:", dict(request.headers))
    print("Raw Body:", request.data)
    try:
        data = request.get_json(force=True, silent=True)
        pool_address, mint_address = extract_addresses(data)
        
        # Store the new token info if valid
        if pool_address and mint_address:
            # Use current timestamp instead of relying on the data
            current_time = time.time()
            token_info = {
                'timestamp': current_time,  # Store as Unix timestamp directly
                'pool_address': pool_address,
                'mint_address': mint_address,
                'received_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')  # For human-readable reference
            }
            
            # Add to the tokens list
            stored_tokens.append(token_info)
            print(f"New token stored: {token_info}")
            print(f"Total tokens waiting to be fetched: {len(stored_tokens)}")
        
    except Exception as e:
        print("JSON parsing failed:", str(e))
        data = None
    
    return jsonify({'status': 'received'}), 200

@app.route('/liquidity_callback', methods=['POST'])
def handle_liquidity_callback():
    """Handle liquidity events from Shyft and forward to registered webhooks"""
    print("=== Liquidity Callback Hit ===")
    print("Method:", request.method)
    print("Headers:", dict(request.headers))
    
    try:
        data = request.get_json(force=True, silent=True)
        
        if not data:
            print("No JSON data received")
            return jsonify({'status': 'no_data'}), 400
        
        # Extract liquidity event information
        event_data = extract_liquidity_event(data)
        
        if event_data and event_data.get('pool_address'):
            pool_address = event_data['pool_address']
            
            # Store the event for potential retrieval
            event_data['received_at'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            stored_liquidity_events.append(event_data)
            
            print(f"Liquidity event detected for pool {pool_address}: {event_data['type']}")
            
            # Forward to registered webhook if pool is being monitored
            if pool_address in pool_monitors:
                forward_liquidity_event(pool_address, event_data)
            else:
                print(f"No monitor registered for pool {pool_address}")
        else:
            print("No relevant liquidity event found in callback data")
    
    except Exception as e:
        print(f"Error processing liquidity callback: {str(e)}")
    
    return jsonify({'status': 'received'}), 200

@app.route('/monitor_pool', methods=['POST'])
def monitor_pool():
    """
    Register a pool for liquidity monitoring
    
    Expected JSON payload:
    {
        "pool_address": "string",
        "callback_url": "string",
        "test_mode": false  // optional - skips Shyft API call for testing
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        pool_address = data.get('pool_address')
        callback_url = data.get('callback_url')
        test_mode = data.get('test_mode', False)
        
        if not pool_address or not callback_url:
            return jsonify({'error': 'pool_address and callback_url are required'}), 400
        
        # Check if pool is already being monitored
        if pool_address in pool_monitors:
            return jsonify({'error': 'Pool is already being monitored'}), 409
        
        # Generate unique callback ID for this monitor
        callback_id = str(uuid.uuid4())
        webhook_id = None
        
        # Create Shyft callback only if not in test mode
        if not test_mode:
            shyft_response = create_shyft_callback(pool_address, callback_url)
            
            if not shyft_response:
                return jsonify({'error': 'Failed to create Shyft callback'}), 500
            
            webhook_id = shyft_response.get('webhook_id')
        else:
            print(f"Test mode: Skipping Shyft API call for pool {pool_address}")
        
        # Store the monitor configuration
        pool_monitors[pool_address] = {
            'callback_url': callback_url,
            'callback_id': callback_id,
            'webhook_id': webhook_id,
            'test_mode': test_mode,
            'created_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }
        
        print(f"Started monitoring pool {pool_address} with callback URL {callback_url} (test_mode: {test_mode})")
        
        return jsonify({
            'status': 'success',
            'message': 'Pool monitoring started' + (' (test mode)' if test_mode else ''),
            'callback_id': callback_id,
            'pool_address': pool_address
        }), 201
        
    except Exception as e:
        print(f"Error in monitor_pool: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/stop_monitoring/<pool_address>', methods=['DELETE'])
def stop_monitoring(pool_address):
    """Stop monitoring a specific pool"""
    try:
        if pool_address not in pool_monitors:
            return jsonify({'error': 'Pool not being monitored'}), 404
        
        monitor_config = pool_monitors[pool_address]
        
        # Delete Shyft callback if webhook_id exists
        if monitor_config.get('webhook_id'):
            delete_success = delete_shyft_callback(monitor_config['webhook_id'])
            if not delete_success:
                print(f"Warning: Failed to delete Shyft callback for pool {pool_address}")
        
        # Remove from local storage
        del pool_monitors[pool_address]
        
        print(f"Stopped monitoring pool {pool_address}")
        
        return jsonify({
            'status': 'success',
            'message': 'Pool monitoring stopped',
            'pool_address': pool_address
        }), 200
        
    except Exception as e:
        print(f"Error in stop_monitoring: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/monitored_pools', methods=['GET'])
def get_monitored_pools():
    """Get list of all monitored pools"""
    try:
        pools = []
        for pool_address, config in pool_monitors.items():
            pools.append({
                'pool_address': pool_address,
                'callback_url': config['callback_url'],
                'callback_id': config['callback_id'],
                'created_at': config['created_at']
            })
        
        return jsonify({
            'status': 'success',
            'count': len(pools),
            'pools': pools
        }), 200
        
    except Exception as e:
        print(f"Error in get_monitored_pools: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/liquidity_events', methods=['GET'])
def get_liquidity_events():
    """Get recent liquidity events (last 5 minutes)"""
    try:
        current_time = time.time()
        recent_events = []
        
        # Filter events from the last 5 minutes
        for event in stored_liquidity_events:
            event_time = event['timestamp']
            age = current_time - event_time
            
            if age <= 300:  # 5 minutes = 300 seconds
                recent_events.append(event)
        
        return jsonify({
            'status': 'success',
            'count': len(recent_events),
            'events': recent_events
        }), 200
        
    except Exception as e:
        print(f"Error in get_liquidity_events: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/get_crypto_tokens', methods=['GET'])
def get_crypto_tokens():
    """Return all newly received tokens and clear the storage"""
    global stored_tokens
    
    # Get current tokens
    all_tokens = stored_tokens.copy()
    print(f"Total tokens in storage: {len(all_tokens)}")

    current_time = time.time()  # Get current Unix timestamp
    print(f"Current time: {current_time}")

    # Filter out tokens older than 20 seconds
    recent_tokens = []
    for token in all_tokens:
        token_time = token['timestamp']  # Now directly stored as Unix timestamp
        age = current_time - token_time
        print(f"Token timestamp: {token_time}, age: {age} seconds")
        
        if age <= 20:
            recent_tokens.append(token)
        else:
            print(f"Filtering out token older than 20 seconds: {token}")

    token_count = len(recent_tokens)
    print(f"Returning {token_count} tokens that are less than 20 seconds old")

    # Clear the tokens list for new ones
    stored_tokens = []
    print("Storage cleared.")
    
    # Return all tokens that were in storage
    return jsonify({
        'status': 'success',
        'count': token_count,
        'tokens': recent_tokens
    })

if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=5000, debug=True)
    app.run(debug=True)