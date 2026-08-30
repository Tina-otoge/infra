#!/bin/bash

cd "$(dirname "$0")"

if [ -f ./bin/terraform-provider-freebox ]; then
    echo "terraform-provider-freebox already exists, skipping download"
else
    mkdir -p bin
    curl -L https://github.com/LAP-Arcade/terraform-provider-freebox/releases/download/wg/terraform-provider-freebox -o bin/terraform-provider-freebox
    chmod +x bin/terraform-provider-freebox
fi

set -a
source .env
set +a

if [ -n "$TF_CLI_CONFIG_FILE" ]; then
    echo TF_CLI_CONFIG_FILE already found in .env, skipping terraformrc setup
else
    echo TF_CLI_CONFIG_FILE="$PWD/terraformrc" >> .env
    echo Wrote TF_CLI_CONFIG_FILE to .env
fi

if [ -n "$TF_VAR_FREEBOX_TOKEN" ]; then
    echo TF_VAR_FREEBOX_TOKEN already found in .env, skipping authentication
else
    echo "TF_VAR_FREEBOX_TOKEN is not set, trying to authenticate..."
    echo
    ./bin/terraform-provider-freebox authorize
    echo
    echo Now save FREEBOX_TOKEN from the output to .env as TF_VAR_FREEBOX_TOKEN
    echo Press any key to continue after you have done that
    read -n 1 -s
fi
