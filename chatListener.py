from cocorum import RumbleAPI
import time

# API_URL should be the endpoint for the Rumble livestream API (this may require a key or token if not just public streams)
API_URL = "https://rumble.com/-livestream-api/get-data?key=0uSPgyv65njK1n38mMiZuNFVdX6wlQ6XBVaNpD6AcdKGQJgoKTo8bT2_byDUp5M_ByIJ16vUMsiavq1XCBq4Pw"
api = RumbleAPI(API_URL, refresh_rate=2)
songQueue = []


def commandRun(user, cmd, message):


    if cmd == "!songrequest" or cmd == "!sr":
        print("\nAdding to queue:\n%s - %s\n" % (user, message))
        songQueue.append(f"{user} - {message}")







if __name__ == '__main__':

    print("Connected to Chat.....\n")
    start_time = time.time()

    while True:
        livestream = api.latest_livestream
        try:
            for message in livestream.chat.new_messages:
                messageString = str(message)
                if round(time.time(), 1) > round(start_time, 1):  # Messy way of ensuring none of the messages already in chat are read
                    timestamp_str = time.strftime("(%H:%M)", time.localtime(time.time()))
                    print(f"{timestamp_str} {message.username}: {messageString}")

                    if str(message):
                        if str(message)[0] == "!":
                            command = ((messageString.split(' ', 1)[0]).lower()).replace("\r", "")
                            cmdarguments = messageString.replace(command or "\r" or "\n", "")[1:]

                            commandRun(message.username, command, cmdarguments)
        except:
            pass

        time.sleep(1)