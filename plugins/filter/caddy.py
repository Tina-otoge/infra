import subprocess


def caddy_password(plaintext):
    result = subprocess.run(
        [
            "podman",
            "run",
            "--rm",
            "caddy/caddy",
            "caddy",
            "hash-password",
            "-plaintext",
            plaintext,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


class FilterModule:
    def filters(self):
        return {
            "caddy_password": caddy_password,
        }
