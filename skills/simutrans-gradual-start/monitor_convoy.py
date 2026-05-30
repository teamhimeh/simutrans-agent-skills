#!/usr/bin/env python3
"""
Simutrans 段階的出庫モニター
Usage: python3 monitor_convoy.py <depot_x> <depot_y> <line_name> [schedule_index=0] [threshold=2] [batch=2] [interval=2]
"""
import socket, json, time, sys

HOST = "::1"
PORT = 13354

def usage():
    print("Usage: monitor_convoy.py <depot_x> <depot_y> <line_name> [schedule_index=0] [threshold=2] [batch=2] [interval=2]")
    sys.exit(1)

args = sys.argv[1:]
if len(args) < 3:
    usage()

depot_x     = int(args[0])
depot_y     = int(args[1])
line_name   = args[2]
sched_idx   = int(args[3]) if len(args) > 3 else 0
threshold   = int(args[4]) if len(args) > 4 else 2
batch       = int(args[5]) if len(args) > 5 else 2
interval    = float(args[6]) if len(args) > 6 else 2.0

CHECK_CODE_TEMPLATE = """\
local pl = player_x(0)
local lines = pl.get_line_list()
local target_line = null
foreach(ln in lines) {{
    if(ln.get_name() == "{line_name}") {{ target_line = ln; break }}
}}
if(target_line == null) return "ERROR: no line: {line_name}"

local waiting = 0
foreach(cnv in target_line.get_convoy_list()) {{
    if(cnv.get_schedule().current == {sched_idx} && !cnv.is_in_depot()) {{
        waiting++
    }}
}}

if(waiting > {threshold}) {{
    return "SKIP:" + waiting
}}

local depot_tile = tile_x({depot_x}, {depot_y}, 0)
local depot = depot_tile.get_depot()
if(depot == null) return "ERROR: no depot at ({depot_x},{depot_y})"

local started = 0
local names = ""
foreach(cnv in depot.get_convoy_list()) {{
    if(started >= {batch}) break
    depot.start_convoy(pl, cnv)
    names += cnv.get_name() + " "
    started++
}}
if(started == 0) return "EMPTY:" + waiting
return "STARTED:" + waiting + ":" + started + ":" + names
"""

CHECK_CODE = CHECK_CODE_TEMPLATE.format(
    line_name=line_name,
    sched_idx=sched_idx,
    threshold=threshold,
    depot_x=depot_x,
    depot_y=depot_y,
    batch=batch,
)

_req_id = 0

def next_id():
    global _req_id
    _req_id += 1
    return _req_id

def send_recv(sock, method, params):
    req = {"jsonrpc": "2.0", "id": next_id(), "method": method, "params": params}
    sock.sendall((json.dumps(req, ensure_ascii=False) + "\n").encode("utf-8"))
    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("disconnected")
        buf += chunk
    return json.loads(buf.split(b"\n")[0])

def notify(sock, method, params):
    req = {"jsonrpc": "2.0", "method": method, "params": params}
    sock.sendall((json.dumps(req, ensure_ascii=False) + "\n").encode("utf-8"))

def run_squirrel(sock, code):
    resp = send_recv(sock, "tools/call", {"name": "run_squirrel", "arguments": {"code": code, "player_nr": 0}})
    if "error" in resp:
        return None, str(resp["error"])
    text = resp["result"]["content"][0]["text"]
    inner = json.loads(text)
    if "error" in inner:
        return None, inner["error"]
    return inner["result"], None

def connect():
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((HOST, PORT, 0, 0))
    send_recv(sock, "initialize", {
        "protocolVersion": "2024-11-05",
        "clientInfo": {"name": "monitor_convoy", "version": "1.0"},
        "capabilities": {}
    })
    notify(sock, "notifications/initialized", {})
    return sock

def main():
    print(
        f"監視開始: {line_name} / sched_idx={sched_idx} / "
        f"閾値≤{threshold} → {batch}台出庫 / {interval}秒ごと",
        flush=True
    )
    while True:
        try:
            sock = connect()
            while True:
                result, err = run_squirrel(sock, CHECK_CODE)
                ts = time.strftime("%H:%M:%S")
                if err:
                    print(f"[{ts}] ERROR: {err}", flush=True)
                    if "no line:" in str(err):
                        print(f"[{ts}] 路線が見つからないため終了", flush=True)
                        sys.exit(1)
                elif result.startswith("SKIP:"):
                    count = result.split(":")[1]
                    print(f"[{ts}] 待機 {count}台 → 出庫不要", flush=True)
                elif result.startswith("STARTED:"):
                    parts = result.split(":", 3)
                    print(f"[{ts}] 待機 {parts[1]}台 ≤{threshold} → {parts[2]}台出庫: {parts[3]}", flush=True)
                elif result.startswith("EMPTY:"):
                    print(f"[{ts}] 待機 {result.split(':')[1]}台 ≤{threshold} だがデポ空 → 終了", flush=True)
                    sys.exit(0)
                elif result.startswith("ERROR: no line:"):
                    print(f"[{ts}] {result} → 終了", flush=True)
                    sys.exit(1)
                else:
                    print(f"[{ts}] {result}", flush=True)
                time.sleep(interval)
        except Exception as e:
            print(f"接続エラー: {e} — 5秒後に再接続", flush=True)
            try: sock.close()
            except: pass
            time.sleep(5)

if __name__ == "__main__":
    main()
