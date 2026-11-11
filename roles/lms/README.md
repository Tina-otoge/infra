# LMS ignore rules

The `lms` role manages the `.lmsignore` file at a music library root. Configure
`lms_music_mount` as the required filesystem mount point, `lms_ignore_file` as
the host path to the file, and `lms_ignore_rules` as its complete contents.
The role fails if the required filesystem is not mounted.

LMS resolves symlinks before matching ignore rules. For files reached through
symlinks, use paths relative to the library root after resolving the target
inside the LMS container.

Run `server_install.yml` with `--tags lms` to apply the rules. LMS applies them
on its next library scan; changing the file does not start a scan.
