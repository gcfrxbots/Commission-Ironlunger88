from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import threading
import logging
import time
import json
import os

app = Flask(__name__)
CORS(app)

CONFIG_FILE = 'config.json'

# Disable Flask request logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

ChatListenerThread = None
ChatListenerModule = None
ProcessedMessages = set()

@app.route('/')
def Index():
    return render_template('index.html')

@app.route('/api/queue')
def GetQueue():
    try:
        if ChatListenerModule and hasattr(ChatListenerModule, 'songQueue'):
            return jsonify(ChatListenerModule.songQueue)
    except:
        pass
    return jsonify([])

@app.route('/api/clear', methods=['POST'])
def ClearQueue():
    try:
        if ChatListenerModule and hasattr(ChatListenerModule, 'songQueue'):
            ChatListenerModule.songQueue.clear()
            return jsonify({"status": "success"})
    except:
        pass
    return jsonify({"status": "error"})

@app.route('/api/next', methods=['POST'])
def NextSong():
    try:
        if ChatListenerModule and hasattr(ChatListenerModule, 'songQueue'):
            queue = ChatListenerModule.songQueue
            if len(queue) > 0:
                queue.pop(0)
                return jsonify({"status": "success"})
            return jsonify({"status": "empty"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "error"})

@app.route('/api/move', methods=['POST'])
def MoveItem():
    try:
        from flask import request
        data = request.get_json()
        index = data.get('index')
        direction = data.get('direction')
        
        if ChatListenerModule and hasattr(ChatListenerModule, 'songQueue'):
            queue = ChatListenerModule.songQueue
            
            if direction == 'up':
                if index > 0:
                    queue[index], queue[index - 1] = queue[index - 1], queue[index]
                    return jsonify({"status": "success"})
            elif direction == 'down':
                if index < len(queue) - 1:
                    queue[index], queue[index + 1] = queue[index + 1], queue[index]
                    return jsonify({"status": "success"})
            
            return jsonify({"status": "invalid"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "error"})

@app.route('/api/remove', methods=['POST'])
def RemoveItem():
    try:
        data = request.get_json()
        index = data.get('index')
        
        if ChatListenerModule and hasattr(ChatListenerModule, 'songQueue'):
            queue = ChatListenerModule.songQueue
            if 0 <= index < len(queue):
                queue.pop(index)
                return jsonify({"status": "success"})
            return jsonify({"status": "invalid"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "error"})

def LoadConfig():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    
    # Default config
    defaultConfig = {
        "themeColor": "#667eea",
        "backgroundColor": "#ffffff",
        "textColor": "#000000",
        "apiUrl": "https://rumble.com/-livestream-api/get-data?key=REDACTED"
    }
    SaveConfig(defaultConfig)
    return defaultConfig

def SaveConfig(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

@app.route('/api/config', methods=['GET'])
def GetConfig():
    try:
        config = LoadConfig()
        return jsonify(config)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/config', methods=['POST'])
def UpdateConfig():
    try:
        data = request.get_json()
        themeColor = data.get('themeColor')
        backgroundColor = data.get('backgroundColor')
        textColor = data.get('textColor')
        apiUrl = data.get('apiUrl')
        
        if not themeColor or not backgroundColor or not textColor:
            return jsonify({"status": "error", "message": "Missing required fields"})
        
        # Load existing config to preserve other settings
        existingConfig = LoadConfig()
        
        config = {
            "themeColor": themeColor,
            "backgroundColor": backgroundColor,
            "textColor": textColor
        }
        
        if apiUrl:
            config["apiUrl"] = apiUrl
        elif "apiUrl" in existingConfig:
            config["apiUrl"] = existingConfig["apiUrl"]
        
        if SaveConfig(config):
            return jsonify({"status": "success", "config": config})
        else:
            return jsonify({"status": "error", "message": "Failed to save config"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def StartFlask(port=5000):
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)

def RunChatListener():
    import chatListener
    from cocorum import RumbleAPI
    
    global ChatListenerModule
    global ProcessedMessages
    
    ChatListenerModule = chatListener
    
    config = LoadConfig()
    API_URL = config.get('apiUrl', "https://rumble.com/-livestream-api/get-data?key=0uSPgyv65njK1n38mMiZuNFVdX6wlQ6XBVaNpD6AcdKGQJgoKTo8bT2_byDUp5M_ByIJ16vUMsiavq1XCBq4Pw")
    api = RumbleAPI(API_URL, refresh_rate=2)
    
    print("Connected to Livestream!\n")
    startTime = time.time()
    
    while True:
        try:
            livestream = api.latest_livestream
            
            if livestream is None:
                print("Stream is offline - Rechecking in 10s")
                time.sleep(10)
                continue
            
            currentTime = time.time()
            
            for message in livestream.chat.new_messages:
                messageString = str(message)
                
                if not messageString:
                    continue
                
                # Create unique message identifier
                messageId = f"{message.username}:{messageString}:{getattr(message, 'id', None) or hash(messageString)}"
                
                # Ignore messages received within 1 second of startup
                if currentTime <= startTime + 1.0:
                    continue
                
                # Skip if message already processed
                if messageId in ProcessedMessages:
                    continue
                
                # Mark message as processed
                ProcessedMessages.add(messageId)
                
                timestampStr = time.strftime("(%H:%M)", time.localtime(currentTime))
                print(f"{timestampStr} {message.username}: {messageString}")
                
                if messageString[0] == "!":
                    splitResult = messageString.split(' ', 1)
                    command = (splitResult[0].lower()).replace("\r", "")
                    cmdArguments = splitResult[1] if len(splitResult) > 1 else ""
                    cmdArguments = cmdArguments.replace("\r", "").replace("\n", "")
                    
                    chatListener.commandRun(message.username, command, cmdArguments)
            
            time.sleep(1)
        except Exception:
            time.sleep(1)

if __name__ == '__main__':
    print("Rumble Song Request Queue")
    print("=" * 40)
    
    # Start chat listener in a separate thread
    ChatListenerThread = threading.Thread(target=RunChatListener, daemon=True)
    ChatListenerThread.start()
    
    print("Chat listener started in background thread")
    print("=" * 40)
    
    # Start Flask web server
    print(f"Web server starting at http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 40)
    
    try:
        StartFlask()
    except KeyboardInterrupt:
        print("\nStopping...")
