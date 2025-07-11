#!/bin/bash
# From: https://medium.com/@danirod/receive-ssh-login-notifications-through-slack-or-discord-fe30a4da3574

if ! [ -f /etc/login-webhook.env ] ; then
    echo "Please create /etc/login-webhook.env with the WEBHOOK_URL variable."
    exit 0
fi
source /etc/login-webhook.env

# Let's capture only open_session and close_session events (login and logout).
case "$PAM_TYPE" in
     open_session)
         PAYLOAD=" { \"content\": \"$PAM_USER logged in to $HOSTNAME (remote host: $PAM_RHOST).\" }"
         ;;
     close_session)
         PAYLOAD=" { \"content\": \"$PAM_USER logged out from $HOSTNAME (remote host: $PAM_RHOST).\" }"
         ;;
esac

# Let's only perform a request if there is an actual payload to send.
if [ -n "$PAYLOAD" ] ; then
     curl -X POST -H 'Content-Type: application/json' -d "$PAYLOAD" "$WEBHOOK_URL"
fi
