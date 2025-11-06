from flask import Flask, jsonify, request
import requests
from flask_cors import CORS
import time
import os

app = Flask(__name__)
CORS(app)

def get_user_id_from_username(username):
    """Convert username to user ID"""
    try:
        url = f"https://users.roblox.com/v1/usernames/users"
        payload = {"usernames": [username]}
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data') and len(data['data']) > 0:
                return str(data['data'][0]['id'])
        return None
    except Exception as e:
        print(f"💥 Error getting user ID: {e}")
        return None

def get_gamepass_creator_info(gamepass_id):
    """Get creator info dari gamepass"""
    try:
        print(f"  🔍 Checking gamepass {gamepass_id}...")
        url = f"https://apis.roblox.com/game-passes/v1/game-passes/{gamepass_id}/product-info"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            creator_info = data.get('Creator') or data.get('creator') or {}
            creator_id = (creator_info.get('Id') or creator_info.get('id') or 
                         creator_info.get('CreatorTargetId') or creator_info.get('creatorTargetId'))
            creator_type = (creator_info.get('CreatorType') or creator_info.get('Type') or 
                           creator_info.get('creatorType') or creator_info.get('type'))
            
            if creator_id:
                print(f"  ✅ Creator: {creator_id} ({creator_type})")
                return str(creator_id), creator_type, data
        
        # Fallback method
        url2 = f"https://economy.roblox.com/v2/assets/{gamepass_id}/details"
        response2 = requests.get(url2, timeout=10)
        
        if response2.status_code == 200:
            data2 = response2.json()
            creator_info = data2.get('Creator') or data2.get('creator') or {}
            creator_id = (creator_info.get('Id') or creator_info.get('id'))
            creator_type = (creator_info.get('CreatorType') or creator_info.get('Type'))
            
            if creator_id:
                return str(creator_id), creator_type, data2
        
        print(f"  ❌ Could not find creator")
        return None, None, None
        
    except Exception as e:
        print(f"  💥 Error: {e}")
        return None, None, None

def get_created_gamepasses(user_id, count=100):
    """Get gamepasses yang dibuat oleh user"""
    try:
        url = f"https://apis.roblox.com/game-passes/v1/users/{user_id}/game-passes"
        params = {'count': count}
        
        print(f"📡 Fetching gamepasses for user {user_id}...")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return []
        
        data = response.json()
        all_gamepasses = data.get('gamePasses', [])
        print(f"📦 Found {len(all_gamepasses)} gamepasses")
        
        created_gamepasses = []
        
        for idx, gamepass in enumerate(all_gamepasses):
            gamepass_id = gamepass.get('gamePassId')
            gamepass_name = gamepass.get('name', 'Unknown')
            
            print(f"[{idx+1}/{len(all_gamepasses)}] {gamepass_name}")
            
            creator_id, creator_type, gamepass_details = get_gamepass_creator_info(gamepass_id)
            
            is_creator = (
                creator_type and 
                creator_type.lower() == 'user' and 
                str(creator_id) == str(user_id)
            )
            
            if is_creator:
                created_gamepass = {
                    'gamepass_id': gamepass_id,
                    'name': gamepass.get('name', 'Unknown'),
                    'description': gamepass.get('description', ''),
                    'icon_url': gamepass.get('displayIcon', {}).get('imageUri', ''),
                    'price': gamepass.get('price', 0),
                    'is_for_sale': gamepass.get('isForSale', False),
                    'product_id': gamepass_details.get('ProductId') if gamepass_details else None
                }
                created_gamepasses.append(created_gamepass)
                print(f"  ✅ ADDED")
            else:
                print(f"  ⏭️ SKIPPED")
            
            time.sleep(0.3)
        
        print(f"🎉 Total: {len(created_gamepasses)} created gamepasses\n")
        return created_gamepasses
        
    except Exception as e:
        print(f"💥 Error: {e}")
        return []

# ========== MAIN ENDPOINT FOR ROBLOX ==========
@app.route('/api/gamepasses', methods=['GET'])
def get_gamepasses():
    """
    Main endpoint untuk Roblox Studio
    Query params:
    - user_id: Roblox user ID (required)
    - username: Roblox username (optional, alternative to user_id)
    """
    user_id = request.args.get('user_id')
    username = request.args.get('username')
    
    # Convert username to user_id jika diperlukan
    if username and not user_id:
        user_id = get_user_id_from_username(username)
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
    
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'user_id or username is required'
        }), 400
    
    print(f"\n{'='*60}")
    print(f"🎯 REQUEST FOR USER: {user_id}")
    print(f"{'='*60}\n")
    
    gamepasses = get_created_gamepasses(user_id)
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'username': username,
        'gamepasses': gamepasses,
        'total': len(gamepasses),
        'timestamp': time.time()
    })

@app.route('/api/check-gamepass', methods=['GET'])
def check_single():
    """Debug endpoint"""
    user_id = request.args.get('user_id')
    gamepass_id = request.args.get('gamepass_id')
    
    if not user_id or not gamepass_id:
        return jsonify({'error': 'user_id and gamepass_id required'}), 400
    
    creator_id, creator_type, data = get_gamepass_creator_info(gamepass_id)
    
    return jsonify({
        'user_id': user_id,
        'gamepass_id': gamepass_id,
        'creator_id': creator_id,
        'creator_type': creator_type,
        'is_creator': str(creator_id) == str(user_id) and creator_type and creator_type.lower() == 'user',
        'data': data
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'OK', 'message': 'Server running'})

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Roblox Gamepass API',
        'endpoints': {
            '/api/gamepasses': 'Get user gamepasses (params: user_id or username)',
            '/api/check-gamepass': 'Check single gamepass (params: user_id, gamepass_id)',
            '/health': 'Health check'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)