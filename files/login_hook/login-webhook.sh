#!/bin/bash
# From: https://medium.com/@danirod/receive-ssh-login-notifications-through-slack-or-discord-fe30a4da3574

if ! [ -f /etc/login-webhook.env ] ; then
    echo Please create /etc/login-webhook.env with the WEBHOOK_URL variable, and
    echo optional KNOWN_HOSTS variable.
    echo Example:
    echo WEBHOOK_URL=https://discord.com/api/webhooks/123456789012345678
    echo KNOWN_HOSTS=192.168.0.1:myhome,192.168.0.2:mywork
    exit 0
fi
source /etc/login-webhook.env

get_host() {
    IFS=',' read -ra HOST_PAIRS <<< "$KNOWN_HOSTS"

    for pair in "${HOST_PAIRS[@]}"; do
        IFS=':' read -r host_ip host_name <<< "$pair"
        if [[ "$host_ip" == "$1" ]]; then
            echo "$host_name"
            return
        fi
    done
    echo "Unknown Host"
}

# Let's capture only open_session and close_session events (login and logout).
case "$PAM_TYPE" in
    open_session)
        PAYLOAD=" { \"content\": \"$PAM_USER logged in to $HOSTNAME (remote host: $PAM_RHOST $(get_host "$PAM_RHOST")).\" }"
        ;;
    close_session)
        PAYLOAD=" { \"content\": \"$PAM_USER logged out from $HOSTNAME (remote host: $PAM_RHOST $(get_host "$PAM_RHOST")).\" }"
        ;;
esac

# Let's only perform a request if there is an actual payload to send.
if [ -n "$PAYLOAD" ] ; then
     curl -X POST -H 'Content-Type: application/json' -d "$PAYLOAD" "$WEBHOOK_URL"
fi
