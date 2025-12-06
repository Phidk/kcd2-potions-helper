# KCD2 Potions Helper

A small Python helper that ingests Omricon's **Henry's Moste Potente Potions** guide and shows what you can brew with the ingredients you have on hand. It includes both a quick CLI readout and a Tkinter GUI with search, sorting, a brew planner, and a shopping list.

## Credits and attribution
- All potion recipes, instructions, and quantities come from Omricon's excellent guide: https://github.com/Omricon/Henrys-Moste-Potente-Potions
- The file `omricon_guide.md` in this repo is a verbatim copy of that README and is used as the data source. Please credit Omricon if you redistribute or update the guide content.
- Price data in `prices.json` is based on community Fextralife notes.

## What you get
- Parse every potion from Omricon's guide into structured data (ingredients, instructions, quantities, effects).
- CLI helper that tells you how many brews of each potion you can make with your current inventory and prints the relevant steps.
- Desktop GUI planner (Tkinter) with:
  - Inventory entry with filtering and auto-recompute.
  - Craftable tab showing max brews, optional prices, total value, and inline instructions.
  - Library tab for browsing all potions.
  - Brew plan and shopping list that total required ingredients and projected sale value.
  - Search/sort controls and a quick link back to Omricon's GitHub page.

## Requirements
- Python 3.10+ (Tkinter is bundled with most Python installs; install your OS package if it is missing).
- `omricon_guide.md` sitting next to the scripts (already included here; replace it with a fresh copy if Omricon updates the guide).
- Optional: `prices.json` for sale values per potion quality.

## Usage
### GUI planner
```bash
python kcd2_gui.py
```
1) Enter how many of each ingredient you have.  
2) Let auto-recompute tally craftable potions, or click **Recompute** manually.  
3) Select a potion to see its instructions; set a quantity and add it to the brew plan.  
4) Check the shopping list to see what to buy or what you can sell.

### CLI helper
```bash
python kcd2_potions_tool.py
```
- The script will list all known ingredients and prompt you to enter your stock as `Belladonna 12` or `Belladonna: 12` (one per line, blank line to finish).  
- It then prints every potion you can brew at least once, including ingredients, quantity/effect tables, optional prices, and all instruction variants from the guide.

## Key files
- `omricon_guide.md` - raw potion guide from Omricon, parsed by both tools.
- `kcd2_gui.py` - Tkinter GUI planner (inventory, craftable list, brew plan, shopping list, detail pane).
- `kcd2_potions_tool.py` - CLI inventory-to-craftable reporter.
- `prices.json` - optional price lookup by potion name and quality (`{"Henry's": 70, "Strong": 55, ...}` format). Delete or edit freely.

## Updating the guide
1) Download the latest README from Omricon's repo linked above.  
2) Save it as `omricon_guide.md` in this directory (overwriting the existing copy).  
3) Rerun either tool; no other changes needed.

## Notes
- This helper is community-made and not affiliated with Warhorse Studios.  
- If the tools report "guide not found", ensure `omricon_guide.md` exists beside the scripts.  
- Feel free to fork and adjust the UI, or wire the data into other planners-just keep attribution to Omricon for the recipe content.
