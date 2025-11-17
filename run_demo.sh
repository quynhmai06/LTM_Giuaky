## run_demo.sh
```bash
#!/usr/bin/env bash
set -e
python server/server.py &
SERVER_PID=$!
sleep 1
gnome-terminal -- bash -c "python client/client.py; exec bash" 2>/dev/null || python client/client.py &
gnome-terminal -- bash -c "python client/client.py; exec bash" 2>/dev/null || python client/client.py &
wait $SERVER_PID
