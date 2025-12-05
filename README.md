# Tina Infra

Ansible playbooks to setup machines on my own hobby infra / home lab.

It is split into 2 playbooks, `server_install.yml` and `user_install.yml`, the
first one runs commands as root, the other runs only rootless commands as the
configured user.

The server playbook is responsible for OS-level setup, such as setting up the
hostname and installing packages.

The user playbook is responsible for installing "user apps", such as userland
systemd services, apps, and containers.

## Requirements

- Python, only tested with 3.10+

## Running

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run server setup on all machines
# -K to pass sudo password, as I do not use passwordless sudo
ansible-playbook server_install.yml -K

# Run server setup on only one machine
ansible-playbook -l laffey server_install.yml -K

# Run user setup
ansible-playbook user_install.yml

# Run only a specific tag / task
ansible-playbook user_install.yml -t containers
```

## Testing

### Requirements

- vagrant, only tested with v2.4.1 on WSL2 with VirtualBox on Windows

### Running the playbook in a VM

```bash
molecule converge
```

## Notes

### Easy SSH port-tunneling when testing in a VM

1. Go to where molecule has generated the Vagrantfile, should be
   `~/.cache/molecule/tina-infra/default`

2. Run `vagrant ssh laffey -- -NL 8080:localhost:80` where *laffey* is the host
   you want to connect to, *8080* is the port you want to bind to on your host,
   and *80* is the port you want to bind to in the VM.

## License

MIT.
