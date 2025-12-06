from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import json
import re
import unicodedata
from math import inf

GUIDE_FILENAME = "omricon_guide.md"


@dataclass
class Potion:
    id: Optional[int]
    name: str
    liquid: str
    ingredients: Dict[str, int]              # solid ingredients only
    instructions: Dict[str, List[str]]       # variant label -> step lines
    quantity_table: List[str]                # raw markdown lines
    effects_table: List[str]                 # raw markdown lines
    notes: List[str] = field(default_factory=list)


def normalize_name(name: str) -> str:
    """Simplify a potion name for matching (strip accents/punctuation, lower)."""
    normalized = unicodedata.normalize("NFKD", name)
    normalized = "".join(ch for ch in normalized if ch.isalnum() or ch.isspace())
    return " ".join(normalized.lower().split())


# -------------------------------
# Parsing Omricon's README.md
# -------------------------------

def split_into_potion_blocks(text: str) -> Dict[str, List[str]]:
    """
    Split the README.md into sections per potion.

    We treat each '## {Name}' (except Introduction/Table of Contents) as the
    start of a potion block and capture everything up to the next '## '.
    """
    lines = text.splitlines()
    potions: Dict[str, List[str]] = {}
    current_name: Optional[str] = None
    current_lines: List[str] = []

    for line in lines:
        if line.startswith("## "):
            title = line[3:].strip()
            if title in ("Introduction", "Table of Contents"):
                # Not a potion section
                continue
            # Close previous potion
            if current_name is not None:
                potions[current_name] = current_lines
            current_name = title
            current_lines = [line]
        else:
            if current_name is not None:
                current_lines.append(line)

    # Final potion
    if current_name is not None and current_lines:
        potions[current_name] = current_lines

    return potions


def parse_ingredients(block_lines: List[str]) -> tuple[str, Dict[str, int]]:
    """
    Parse the '### Ingredients' fenced code block into:
      - liquid: e.g. 'Spirits'
      - ingredients: dict of solid ingredient -> required count
    """
    liquid = ""
    ingredients: Dict[str, int] = {}

    try:
        idx = block_lines.index("### Ingredients")
    except ValueError:
        return liquid, ingredients

    # Find the triple-backtick block that follows
    i = idx + 1
    while i < len(block_lines) and block_lines[i].strip() != "```":
        i += 1
    if i >= len(block_lines):
        return liquid, ingredients

    # Inside code fence
    i += 1
    while i < len(block_lines) and block_lines[i].strip() != "```":
        line = block_lines[i].strip()
        if line.startswith("Liquid:"):
            liquid = line.split(":", 1)[1].strip()
        elif line.startswith("x"):
            # Format: x2 Belladonna
            m = re.match(r"x(\d+)\s+(.+)", line)
            if m:
                qty = int(m.group(1))
                name = m.group(2).strip()
                ingredients[name] = qty
        i += 1

    return liquid, ingredients


def parse_instructions(block_lines: List[str]) -> Dict[str, List[str]]:
    """
    Parse all '### Instructions [Variant]' subsections.

    Returns dict:
        variant_label -> list of raw step lines (with numbering preserved)
    """
    instructions: Dict[str, List[str]] = {}
    i = 0

    while i < len(block_lines):
        line = block_lines[i]
        if line.startswith("### Instructions"):
            header = line
            m = re.search(r"\[(.+?)\]", header)
            variant = m.group(1) if m else "Default"

            # Move into the body, skipping leading blank lines
            i += 1
            while i < len(block_lines) and not block_lines[i].strip():
                i += 1

            steps: List[str] = []
            while i < len(block_lines):
                l = block_lines[i]
                # Stop when we hit another section or the next potion
                if l.startswith("### ") and not l.startswith("### Instructions"):
                    break
                if l.startswith("## "):
                    break
                if l.strip().startswith("---"):
                    break
                steps.append(l)
                i += 1

            # Trim trailing blank lines
            while steps and not steps[-1].strip():
                steps.pop()

            instructions[variant] = steps
        else:
            i += 1

    return instructions


def parse_section(block_lines: List[str], section_title: str) -> List[str]:
    """
    Generic parser for sections like '### Quantity', '### Effects', '### Notes'.
    Grabs everything until the next '###', '##', or '---' divider.
    """
    try:
        idx = block_lines.index(section_title)
    except ValueError:
        return []

    lines: List[str] = []
    i = idx + 1
    while i < len(block_lines):
        l = block_lines[i]
        if l.startswith("### ") or l.startswith("## "):
            break
        if l.strip().startswith('---'):
            break
        lines.append(l)
        i += 1

    while lines and not lines[-1].strip():
        lines.pop()

    return lines


def parse_potion_block(name: str, block_lines: List[str]) -> Potion:
    """
    Turn a single potion block into a Potion object.
    """
    pot_id: Optional[int] = None
    for line in block_lines:
        m = re.search(r"\*No\.\s*(\d+)\*", line)
        if m:
            pot_id = int(m.group(1))
            break

    liquid, ingredients = parse_ingredients(block_lines)
    instructions = parse_instructions(block_lines)
    quantity = parse_section(block_lines, "### Quantity")
    effects = parse_section(block_lines, "### Effects")
    notes = parse_section(block_lines, "### Notes")

    return Potion(
        id=pot_id,
        name=name,
        liquid=liquid,
        ingredients=ingredients,
        instructions=instructions,
        quantity_table=quantity,
        effects_table=effects,
        notes=notes,
    )


def parse_readme_to_potions(readme_path: Path) -> Dict[str, Potion]:
    """
    High-level: read README.md and return a dict name -> Potion.
    """
    text = readme_path.read_text(encoding="utf-8")
    blocks = split_into_potion_blocks(text)
    potions = {name: parse_potion_block(name, lines) for name, lines in blocks.items()}
    return potions


# -------------------------------
# Inventory and availability
# -------------------------------

def compute_max_brews(potions: Dict[str, Potion],
                      inventory: Dict[str, int]) -> Dict[str, int]:
    """
    For each potion, compute how many full brews you can make given inventory.

    Liquids are ignored (assumed unlimited). For each potion, we take:
        min( floor(inventory[ingredient] / required_per_brew) ).

    Returns dict:
        potion_name -> max_brews (integer >= 1)
    """
    craftable: Dict[str, int] = {}

    for name, p in potions.items():
        if not p.ingredients:
            continue

        max_brews = inf
        for ing, req in p.ingredients.items():
            avail = inventory.get(ing, 0)
            possible = avail // req
            if possible < max_brews:
                max_brews = possible

        if max_brews > 0 and max_brews != inf:
            craftable[name] = int(max_brews)

    return craftable


# -------------------------------
# Pricing support
# -------------------------------

def load_prices(path: Path) -> Dict[str, Dict[str, float]]:
    """
    Load prices from prices.json, if it exists.

    Expected JSON structure:
    {
      "Aesop": {
        "Weak": 10,
        "Standard": 20,
        "Strong": 30,
        "Henry's": 40
      },
      "Aqua Vitalis": {
        "Weak": 5,
        ...
      }
    }

    Potion names are normalized (case-insensitive, punctuation/accents stripped),
    so ASCII keys like "Bowman's Brew" will match the guide's name.
    """
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    prices: Dict[str, Dict[str, float]] = {}
    for pot_name, qualities in data.items():
        inner: Dict[str, float] = {}
        if not isinstance(qualities, dict):
            continue
        for q_name, val in qualities.items():
            try:
                inner[q_name] = float(val)
            except (TypeError, ValueError):
                continue
        prices[normalize_name(pot_name)] = inner

    return prices


# -------------------------------
# CLI / I/O helpers
# -------------------------------

def print_potion_detail(p: Potion,
                        max_brews: int,
                        prices: Dict[str, Dict[str, float]]) -> None:
    """
    Pretty-print a potion summary + instructions + quantity/effects/prices.
    """
    print("=" * 80)
    print(f"{p.name} (No. {p.id if p.id is not None else '?'})")
    print(f"Liquid: {p.liquid}")
    print("Ingredients per brew:")
    for ing, qty in p.ingredients.items():
        print(f"  - {qty} x {ing}")

    print(f"\nMax brews with current inventory (ignoring perks & liquids): {max_brews}")

    print("\nQuantity per brew (from README):")
    if p.quantity_table:
        for line in p.quantity_table:
            print("  " + line)
    else:
        print("  (no quantity table in README)")

    print("\nEffects by quality (from README):")
    if p.effects_table:
        for line in p.effects_table:
            print("  " + line)
    else:
        print("  (no effects table in README)")

    price_info = prices.get(normalize_name(p.name), {})
    print("\nPrices per bottle (from Fextralife Potions page, if provided):")
    if price_info:
        for q in ["Weak", "Standard", "Strong", "Henry's"]:
            if q in price_info:
                print(f"  {q}: {price_info[q]}")
    else:
        print("  (no prices configured yet for this potion)")

    print("\nInstructions:")
    for variant, steps in p.instructions.items():
        print(f"  [{variant}]")
        for s in steps:
            print("   " + s)
        print()

    if p.notes:
        print("Notes:")
        for line in p.notes:
            print("  " + line)
        print()


def prompt_inventory(ingredients: List[str]) -> Dict[str, int]:
    """
    Interactive prompt to capture your current ingredient stock.

    You can paste any of:
      - Belladonna 10
      - Belladonna: 10
      - St. John's Wort 7
    """
    print("Known ingredients (excluding liquids):")
    for ing in ingredients:
        print(f"  - {ing}")

    print("\nEnter your inventory, one ingredient per line as:")
    print("    <name> <count>")
    print("    <name>: <count>")
    print("Press Enter on an empty line when you are finished.\n")

    inventory: Dict[str, int] = {}

    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break

        if not line:
            break

        name = None
        qty_str = None

        if ":" in line:
            left, right = line.split(":", 1)
            name = left.strip()
            qty_str = right.strip()
        else:
            parts = line.split()
            if len(parts) >= 2 and parts[-1].isdigit():
                qty_str = parts[-1]
                name = " ".join(parts[:-1])

        if name is None or qty_str is None:
            print("  Could not parse line. Please use '<name> <count>' or '<name>: <count>'.")
            continue

        try:
            qty = int(qty_str)
        except ValueError:
            print("  Quantity must be an integer.")
            continue

        inventory[name] = qty

    return inventory


# -------------------------------
# Main entry point
# -------------------------------

def main() -> None:
    guide_path = Path(GUIDE_FILENAME)
    if not guide_path.exists():
        print(f"ERROR: {GUIDE_FILENAME} not found in current directory.")
        print("Download Omricon's Henry's Moste Potente Potions README and save it as that filename next to this script.")
        return

    potions = parse_readme_to_potions(guide_path)

    all_ingredients = sorted(
        {ing for p in potions.values() for ing in p.ingredients.keys()}
    )

    inventory = prompt_inventory(all_ingredients)
    if not inventory:
        print("No inventory entered; nothing to do.")
        return

    craftable = compute_max_brews(potions, inventory)
    if not craftable:
        print("With this inventory you can't brew any potion from Henry's Moste Potente Potions.")
        return

    prices = load_prices(Path("prices.json"))

    print("\nYou can brew the following potions at least once (assuming unlimited liquids):\n")
    for name in sorted(craftable.keys()):
        p = potions[name]
        max_brews = craftable[name]
        print_potion_detail(p, max_brews, prices)


if __name__ == "__main__":
    main()
