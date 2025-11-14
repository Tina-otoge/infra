class FilterModule:
    def filters(self):
        return {
            "domain_from_fqdn": lambda x: ".".join(x.split(".")[-2:]),
            "name_from_fqdn": lambda x: ".".join(x.split(".")[:-2]),
        }
