import unittest

from facebook.facebook_specs_parser import (
    parse_ram,
    parse_pc_specs,
)


class RamParserV2Tests(unittest.TestCase):

    def test_supported_formats(self):

        examples = {
            "RAM 16GB": 16,
            "RAM: 32 GB": 32,
            "16GB RAM": 16,
            "RAM DDR4 32GB": 32,
            "Pamięć RAM: 16 GB": 16,
            "Pamięć operacyjna: 32 GB": 32,
            "DDR5 32GB": 32,
            "32 GB DDR5": 32,
            "RAM 2x8GB": 16,
            "RAM: 2 x 16 GB": 32,
            "2x8GB RAM": 16,
            "2 x 16GB DDR4": 32,
            "DDR4 2x8 GB": 16,
            "2×16GB": 32,
            "RTX 4080 16GB; RAM 32 GB": 32,
            "RTX 5070 Ti 16GB, Ryzen 7 5800X, 32GB RAM": 32,
        }

        for text, expected in examples.items():
            with self.subTest(text=text):
                self.assertEqual(
                    parse_ram(text),
                    expected,
                )

    def test_do_not_confuse_vram(self):

        examples = (
            "RTX 4080 SUPER 16GB",
            "RTX 4080 16GB DDR5",
            "RTX 3090 24GB GDDR6X",
            "VRAM 16 GB",
            "Radeon RX 7800XT 16GB",
            "16GB VRAM, GPU RTX 4060",
            "RTX 4080 SUPER 16GB | bez SSD",
            "Komputer gamingowy 16GB",
            "SSD 512GB, HDD 1TB",
            "",
        )

        for text in examples:
            with self.subTest(text=text):
                self.assertIsNone(parse_ram(text))

    def test_pc_parser(self):

        specs = parse_pc_specs(
            "RTX 4080 SUPER 16GB Ryzen 7 7800X3D",
            "DDR5 2x16GB; SSD 1TB",
        )

        self.assertEqual(specs["ram"], 32)
        self.assertEqual(
            specs["cpu"],
            "Ryzen 7 7800X3D",
        )
        self.assertEqual(
            specs["gpu"],
            "RTX 4080 SUPER",
        )


if __name__ == "__main__":
    unittest.main()
