terraform {
  required_providers {
    freebox = {
      source = "registry.terraform.io/NikolaLohinski/freebox"
    }
  }

  backend "s3" {
    bucket = "terraform"
    key    = "tina/freebox.tfstate"
    region = "laffey-ii"

    endpoints = {
      s3 = "https://s3.tina.moe"
    }

    use_path_style              = true
    use_lockfile                = true
    skip_credentials_validation = true
    skip_region_validation      = true
  }
}


variable "FREEBOX_TOKEN" {
  sensitive = true
}

provider "freebox" {
  endpoint    = "http://mafreebox.freebox.fr"
  api_version = "v16"
  app_id      = "terraform-provider-freebox"
  token       = var.FREEBOX_TOKEN
}

resource "freebox_vpn_server" "wireguard" {
  vpn_id      = "wireguard"
  enabled     = true
  enable_ipv4 = true
  port        = 46880
}

import {
  to = freebox_vpn_server.wireguard
  id = "wireguard"
}
