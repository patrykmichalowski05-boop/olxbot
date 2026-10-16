import re


class GPUCategory:

    def extract_attributes(self, listing):
        text = " ".join((
            listing.title,
            listing.description,
        )).upper()

        model = re.search(
            r"\b(?:RTX|GTX|RX)\s*"
            r"(\d{3,4})\s*(TI|SUPER|XT|XTX)?\b",
            text,
        )

        suffix = text[model.end():] if model else ""

        vram = re.match(
            r"^\s*[-/(]?\s*"
            r"(4|6|8|10|12|16|20|24|32)\s*GB"
            r"(?!\s*(?:RAM|DDR))",
            suffix,
        )

        if not vram:
            vram = re.search(
                r"\b(4|6|8|10|12|16|20|24|32)"
                r"\s*GB\s*(?:VRAM|GDDR\d*)\b",
                text,
            )

        return {
            "gpu_model": (
                "".join(model.groups(default=""))
                if model else None
            ),
            "gpu_vram_gb": (
                int(vram.group(1))
                if vram else None
            ),
        }

    def validate_completeness(self, attributes):
        return [
            name
            for name in ("gpu_model", "gpu_vram_gb")
            if not attributes.get(name)
        ]

    def comparable_key(self, attributes):
        if self.validate_completeness(attributes):
            return None

        return (
            f"GPU:{attributes['gpu_model']}:"
            f"{attributes['gpu_vram_gb']}GB"
        )


class PCCategory:

    def extract_attributes(self, listing):
        # Docelowo wykorzystamy istniejacy parser PC.
        return {"raw_title": listing.title}

    def validate_completeness(self, attributes):
        return [
            name
            for name in ("cpu", "gpu", "ram_gb")
            if not attributes.get(name)
        ]

    def comparable_key(self, attributes):
        if self.validate_completeness(attributes):
            return None

        return "PC:{cpu}:{gpu}:{ram_gb}".format(
            **attributes
        )
