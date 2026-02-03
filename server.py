from http.server import BaseHTTPRequestHandler, HTTPServer
import json, uuid, os

rooms = {}          # room -> {owner, users}
waiting_queue = [] # match automático

class Handler(BaseHTTPRequestHandler):

    def send(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            with open("index.html", "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length))

        # MATCH AUTOMÁTICO
        if self.path == "/match":
            uid = str(uuid.uuid4())
            name = data.get("name","Anon")

            if waiting_queue:
                room = waiting_queue.pop(0)
                rooms[room]["users"][uid] = {"name":name,"queue":[]}
            else:
                room = uuid.uuid4().hex[:6]
                rooms[room] = {
                    "owner": uid,
                    "users": {uid:{"name":name,"queue":[]}}
                }
                waiting_queue.append(room)

            self.send({"uid":uid,"room":room})

        # SEÑALIZACIÓN (MULTIUSUARIO)
        elif self.path == "/signal":
            room = data["room"]
            uid = data["uid"]
            signal = data["signal"]

            for u in rooms[room]["users"]:
                if u != uid:
                    rooms[room]["users"][u]["queue"].append({
                        "from": uid,
                        "signal": signal
                    })
            self.send({"ok":True})

        elif self.path == "/poll":
            room = data["room"]
            uid = data["uid"]
            q = rooms[room]["users"][uid]["queue"]
            rooms[room]["users"][uid]["queue"] = []
            self.send(q)

        # MODERACIÓN
        elif self.path == "/kick":
            room = data["room"]
            target = data["target"]
            uid = data["uid"]

            if rooms[room]["owner"] == uid and target in rooms[room]["users"]:
                del rooms[room]["users"][target]
                self.send({"kicked":True})
            else:
                self.send({"error":"No autorizado"},403)

        else:
            self.send({"error":"Ruta inválida"},404)

if __name__ == "__main__":
    port = int(os.environ.get("PORT",8000))
    HTTPServer(("0.0.0.0",port),Handler).serve_forever()



