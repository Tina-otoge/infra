set -euo pipefail
umask 077

mountpoint=/mnt/sakura
dedupe_folders=(
    "$mountpoint/public/Works/Games/Arcade"
    "$mountpoint/tina/Games/Arcade"
    "$mountpoint/tina/Downloads"
)
database_directory=/var/lib/sakura-dedupe
started=$SECONDS

log() {
    printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

cleanup() {
    status=$?
    trap - EXIT
    log "Maintenance finished: status=$status elapsed=$((SECONDS - started))s"
    exit "$status"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

exec 9>/run/lock/sakura-maintenance.lock
if ! flock -n 9; then
    log 'Another Sakura maintenance run is active; skipping.'
    exit 0
fi

if [[ "$(findmnt -n -M "$mountpoint" -o FSTYPE)" != xfs ]]; then
    log "Expected an XFS mount at $mountpoint; refusing to continue."
    exit 1
fi

for executable in duperemove ionice nice mkdir; do
    command -v "$executable" >/dev/null
done

mkdir -p -- "$database_directory"
if [[ "$(stat -c %d "$database_directory")" == "$(stat -c %d "$mountpoint")" ]]; then
    log 'The hash database must be outside Sakura.'
    exit 1
fi

log 'Starting Sakura maintenance; filesystem usage before:'
df -B1 "$mountpoint"

# Manual defrag (ensure sufficient free space first): sudo flock -n /run/lock/sakura-maintenance.lock ionice -c 3 nice -n 19 timeout --signal=TERM --kill-after=60s 2h xfs_fsr -v /mnt/sakura

log "Starting dedupe with persistent database $database_directory/hashes.db."
dedupe_started=$SECONDS
dedupe_status=0
ionice -c 3 nice -n 19 duperemove -dhr \
    --io-threads=1 --cpu-threads=1 \
    --hashfile="$database_directory/hashes.db" \
    "${dedupe_folders[@]}" || dedupe_status=$?
log "Dedupe ended with status=$dedupe_status after $((SECONDS - dedupe_started))s; filesystem usage after:"
df -B1 "$mountpoint"
exit "$dedupe_status"
