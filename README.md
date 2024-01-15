# Tina Infra

Ansible playbooks to setup machines on my own hobby infra / home lab.

It is split into 2 playbooks, `server_install.yml` and `user_install.yml`, the
first one runs command as root, the other as the configured user.

The server playbook is responsible for OS-level setup, such as setting up the
hostname and installing packages.

The user playbook is responsible for installing "user apps", such as userland
systemd services and containers.

## Notes

### Testing the reverse-proxy when running in the VirtualBox molecule instance

- Add an entry with the domain you want to test to `/etc/hosts`

- Create an SSH tunnel to the port 80:

You will need the port of the VirtualBox NAT, you can find it in
`~/.cache/molecule/infra/default/inventory/ansible_inventory.yml` as
`ansible_port` (the path will differ if you named the repository differently)

```bash
host=laffey
ssh_port=2222
bind_to_port=80
bind_from_port=80
sudo ssh vagrant@localhost -p $port -i ~/.cache/molecule/infra/default/.vagrant/machines/$host/virtualbox/private_key -L $bind_port:127.0.0.1:$bind_from_port -N
```

root is needed to bind to a privileged port such as 80.

If the mechanisms you are testing do not need the client's host to use port 80
you can bind to another port instead, such as 8080, and will not need root.
