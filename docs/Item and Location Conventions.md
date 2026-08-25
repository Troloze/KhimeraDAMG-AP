Structures and conventions designed around the [[Theoretical complete list of options]], under the assumption that it could grow.
# Items
## Item Naming Convention
The item names should be the simple whilst remaining descriptive.

There aren't nearly as many items compared to locations, so there will be no set naming structure.
## Item ID structure: 50AABBBBB
The constants serve to make the IDs easily discernible from 
the location IDs, for practicality. 
### AA - Type Identifier
- 00: Skills
- 01: Stage Entrance Unlocks
- 02: Fairy
- 03: Book
- 04: Candy
- 05: Detonator
- 06: Gourmet Gal
- 07: Costume
- 08: Filler (Traps)
- 09: Filler (harmless)
- 10: Trade Quest Progression

### BBBBB - Unique Identifier
Never is 00000.
A simple incremental identifier. Very likely to never go past 3 digits.
# Locations
## Location Naming Convention: REGION: TYPE - IDENTIFIER
If region is "Generic" the region prefix can be omitted.
If there is only one location of said type in the region, the identifier suffix can be omitted.
Follows the same structure as the IDs, as an example the second log book in Ragazza town should be named something like: `Ragazza Town: Book - Market Hidden Block`

Enemy location names will have the enemy name on the type depending on Enemysanity setting:
- "type" - `Enemy - Floof Pirate`
- "stage" - `Ragazza Plains: Enemy - Floof Pirate`
- "instance" - `Ragazza Plains: Floof Pirate - Start 2`
## Location ID structure: AABBCCCCC
### AA - Region Identifier
- 00: Generic/Misc
- 01 - 18: Stage specific
### BB - Type identifier
- 00: Generic/Misc
- 01: Stage Clear
- 02: Fairy
- 03: Book
- 04: Candy
- 05: Detonator
- 06: Gourmet Gal
- 07: Costume 
- 08: Checkpoint
- 09: Enemy 
- 10: Coin
- 11: Gem
- 12: Food
### CCCCC - Unique Identifier
Never is 00000.
On most cases will be a simple incremental identifier for the items specified by the region and type.

For enemy type it will be structured as:

DDEEE 

DD: Enemy type
EEE: Enemy Instance

On enemysanity "type" and "stage", EEE will be set to 0
otherwise instance will act as an incremental identifier.