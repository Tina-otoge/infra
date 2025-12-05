class FilterModule:
    def filters(self):
        return {
            "arch": lambda x: {
                "i386": "386",
                "x86_64": "amd64",
                "aarch64": "arm64",
                "armv7l": "armv7",
                "armv6l": "armv6",
            }.get(x, x),
        }
