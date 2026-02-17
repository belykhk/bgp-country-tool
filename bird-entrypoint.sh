#!/bin/sh
set -e

BIRD_CONF="/mount/bird.conf"
POLL_INTERVAL=30

# --- Helper: get md5 of a file, empty string if missing ---
file_hash() {
    md5sum "$1" 2>/dev/null | cut -d' ' -f1
}

# --- Helper: reload or restart BIRD ---
reload_bird() {
    if ! kill -0 "$BIRD_PID" 2>/dev/null; then
        echo "$(date): BIRD process died, restarting..."
        bird -c "$BIRD_CONF" -d &
        BIRD_PID=$!
        sleep 2
        return
    fi

    if bird -c "$BIRD_CONF" -p 2>/dev/null; then
        birdc configure \
            && echo "$(date): BIRD reloaded successfully" \
            || echo "$(date): BIRD reload failed"
    else
        echo "$(date): Config syntax error — skipping reload"
        bird -c "$BIRD_CONF" -p
    fi
}

# --- Start BIRD ---
bird -c "$BIRD_CONF" -d &
BIRD_PID=$!
echo "$(date): BIRD started with PID $BIRD_PID"
sleep 2

# --- Initial hashes ---
HASH_CONF=$(file_hash "$BIRD_CONF")
HASH_IPV4=$(file_hash "/mount/output_ipv4.txt")
HASH_IPV6=$(file_hash "/mount/output_ipv6.txt")

echo "$(date): Polling every ${POLL_INTERVAL}s..."
echo "$(date): bird.conf        = ${HASH_CONF:-(missing)}"
echo "$(date): output_ipv4.txt  = ${HASH_IPV4:-(missing)}"
echo "$(date): output_ipv6.txt  = ${HASH_IPV6:-(missing)}"

# --- Poll loop ---
while true; do
    sleep "$POLL_INTERVAL"

    NEW_HASH_CONF=$(file_hash "$BIRD_CONF")
    NEW_HASH_IPV4=$(file_hash "/mount/output_ipv4.txt")
    NEW_HASH_IPV6=$(file_hash "/mount/output_ipv6.txt")

    CHANGED=0

    if [ "$NEW_HASH_CONF" != "$HASH_CONF" ]; then
        echo "$(date): bird.conf changed"
        HASH_CONF="$NEW_HASH_CONF"
        CHANGED=1
    fi

    if [ "$NEW_HASH_IPV4" != "$HASH_IPV4" ]; then
        echo "$(date): output_ipv4.txt changed"
        HASH_IPV4="$NEW_HASH_IPV4"
        CHANGED=1
    fi

    if [ "$NEW_HASH_IPV6" != "$HASH_IPV6" ]; then
        echo "$(date): output_ipv6.txt changed"
        HASH_IPV6="$NEW_HASH_IPV6"
        CHANGED=1
    fi

    if [ "$CHANGED" = "1" ]; then
        reload_bird
    fi
done
