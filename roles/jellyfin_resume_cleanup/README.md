# Jellyfin resume cleanup

This role installs a daily systemd timer on asashio. It uses the Jellyfin HTTP
API to find episodes with a non-zero resume position and resets only positions
whose last-played time is older than `jellyfin_resume_cleanup_days`. It leaves
watched status, play count, favorites, other user data, and media files alone.
All users and paginated episode results are read before any updates are sent.

Create an API key in the Jellyfin dashboard (**Administration → API Keys**) and
put it in the ignored `group_vars/all/secrets.yml` as `jellyfin_api_key`. The
role fails before installing anything if the key is undefined or empty. It
stores the key in a root-only file for the system service.

Defaults are 30 days, a daily schedule, the loopback Jellyfin URL derived from
`loopback_ip` and `ports.jellyfin`, and dry-run disabled. Set
`jellyfin_resume_cleanup_dry_run: true` to report candidates without changing
resume positions. The Python script uses only the standard library.
