from typing import TYPE_CHECKING

from BaseClasses import ItemClassification

from .types import (
    ItemData,
    ItemType,
    KhimeraDAMGItem,
    StageIndex,
    stage_entrances,
    stage_id_to_name,
    stage_to_detonator_item_index,
)

if TYPE_CHECKING:
    from . import KhimeraDAMGWorld

ItemDict = dict[str, ItemData]

def make_item_id(item_type: ItemType, index: int) -> int:
    return (5000 + item_type.value) * 100000 + index

# ruff: disable[E501]
upgrades:ItemDict = {
    "Saucy Shot":       ItemData(make_item_id(ItemType.SKILLS, 1), ItemClassification.useful),
    "Mermaid Anchor":   ItemData(make_item_id(ItemType.SKILLS, 2), ItemClassification.useful),
    "Harpy Boost":      ItemData(make_item_id(ItemType.SKILLS, 3), ItemClassification.useful),
    "Treasure Box":     ItemData(make_item_id(ItemType.SKILLS, 4), ItemClassification.useful),
    "Demon Fire":       ItemData(make_item_id(ItemType.SKILLS, 5), ItemClassification.useful),
    "Sturdy Feet":      ItemData(make_item_id(ItemType.SKILLS, 6), ItemClassification.useful),
    "Giant's Wave":     ItemData(make_item_id(ItemType.SKILLS, 7), ItemClassification.useful),
    "Wicked Eye":       ItemData(make_item_id(ItemType.SKILLS, 8), ItemClassification.useful)
}

stage_unlocks:ItemDict = {
    stage_entrances[StageIndex.RAGAZZA_TOWN]:           ItemData(make_item_id(ItemType.STAGE_UNLOCK, 1), ItemClassification.progression),
    stage_entrances[StageIndex.CHELSHIAS_HOUSE]:        ItemData(make_item_id(ItemType.STAGE_UNLOCK, 2), ItemClassification.progression),
    stage_entrances[StageIndex.FAIRIES_DOMAIN]:         ItemData(make_item_id(ItemType.STAGE_UNLOCK, 3), ItemClassification.progression),
    stage_entrances[StageIndex.QUIZ]:                   ItemData(make_item_id(ItemType.STAGE_UNLOCK, 4), ItemClassification.progression),
    stage_entrances[StageIndex.RAGAZZA_PLAINS]:         ItemData(make_item_id(ItemType.STAGE_UNLOCK, 5), ItemClassification.progression),
    stage_entrances[StageIndex.MT_AFROKUPA]:            ItemData(make_item_id(ItemType.STAGE_UNLOCK, 6), ItemClassification.progression),
    stage_entrances[StageIndex.OIL_PLATFORM]:           ItemData(make_item_id(ItemType.STAGE_UNLOCK, 7), ItemClassification.progression),
    stage_entrances[StageIndex.SKY_FORTRESS]:           ItemData(make_item_id(ItemType.STAGE_UNLOCK, 8), ItemClassification.progression),
    stage_entrances[StageIndex.PUMPKIN_VALLEY]:         ItemData(make_item_id(ItemType.STAGE_UNLOCK, 9), ItemClassification.progression),
    stage_entrances[StageIndex.THE_BLACK_WIDOW]:        ItemData(make_item_id(ItemType.STAGE_UNLOCK, 10), ItemClassification.progression),
    stage_entrances[StageIndex.MECHANICAL_MAYHEM]:      ItemData(make_item_id(ItemType.STAGE_UNLOCK, 11), ItemClassification.progression),
    stage_entrances[StageIndex.THE_SPIDERS_WEB]:        ItemData(make_item_id(ItemType.STAGE_UNLOCK, 12), ItemClassification.progression),
    stage_entrances[StageIndex.ICY_PATH]:               ItemData(make_item_id(ItemType.STAGE_UNLOCK, 13), ItemClassification.progression),
    stage_entrances[StageIndex.BRINE_CAVE]:             ItemData(make_item_id(ItemType.STAGE_UNLOCK, 14), ItemClassification.progression),
    stage_entrances[StageIndex.TOWER_OF_POWER]:         ItemData(make_item_id(ItemType.STAGE_UNLOCK, 15), ItemClassification.progression),
    stage_entrances[StageIndex.WINDY_WAY]:              ItemData(make_item_id(ItemType.STAGE_UNLOCK, 16), ItemClassification.progression),
}

fairies:ItemDict = {
    "Fairy": ItemData(make_item_id(ItemType.FAIRY, 1), ItemClassification.filler)
}

# Harvest event log books will be placed in a separate category when implemented, but are all books regardless.
books:ItemDict = {
    "Log Book: Chelshia":               ItemData(make_item_id(ItemType.BOOK, 1), ItemClassification.filler),
    "Log Book: The Professor":          ItemData(make_item_id(ItemType.BOOK, 2), ItemClassification.filler),
    "Log Book: Bernadette":             ItemData(make_item_id(ItemType.BOOK, 3), ItemClassification.filler),
    "Log Book: Floof Pirate":           ItemData(make_item_id(ItemType.BOOK, 4), ItemClassification.filler),
    "Log Book: Floof Aviator":          ItemData(make_item_id(ItemType.BOOK, 5), ItemClassification.filler),
    "Log Book: Floof Bomber":           ItemData(make_item_id(ItemType.BOOK, 6), ItemClassification.filler),
    "Log Book: Pirate Swordsman":       ItemData(make_item_id(ItemType.BOOK, 7), ItemClassification.filler),
    "Log Book: Pirate Marksman":        ItemData(make_item_id(ItemType.BOOK, 8), ItemClassification.filler),
    "Log Book: Pirate Cannoneer":       ItemData(make_item_id(ItemType.BOOK, 9), ItemClassification.filler),
    "Log Book: Pirate Demolitions":     ItemData(make_item_id(ItemType.BOOK, 10), ItemClassification.filler),
    "Log Book: Pirate Explorer":        ItemData(make_item_id(ItemType.BOOK, 11), ItemClassification.filler),
    "Log Book: Pirate Samurai":         ItemData(make_item_id(ItemType.BOOK, 12), ItemClassification.filler),
    "Log Book: Scuttlebit":             ItemData(make_item_id(ItemType.BOOK, 13), ItemClassification.filler),
    "Log Book: Zambot":                 ItemData(make_item_id(ItemType.BOOK, 14), ItemClassification.filler),
    "Log Book: Seedle":                 ItemData(make_item_id(ItemType.BOOK, 15), ItemClassification.filler),
    "Log Book: Misboro":                ItemData(make_item_id(ItemType.BOOK, 16), ItemClassification.filler),
    "Log Book: Skallo":                 ItemData(make_item_id(ItemType.BOOK, 17), ItemClassification.filler),
    "Log Book: Kiran":                  ItemData(make_item_id(ItemType.BOOK, 18), ItemClassification.filler),
    "Log Book: Little Oni":             ItemData(make_item_id(ItemType.BOOK, 19), ItemClassification.filler),
    "Log Book: Squidge":                ItemData(make_item_id(ItemType.BOOK, 20), ItemClassification.filler),
    "Log Book: Tamole":                 ItemData(make_item_id(ItemType.BOOK, 21), ItemClassification.filler),
    "Log Book: Spaîctre Die":           ItemData(make_item_id(ItemType.BOOK, 22), ItemClassification.filler),
    "Log Book: Weekday Witches":        ItemData(make_item_id(ItemType.BOOK, 23), ItemClassification.filler),
    "Log Book: Chibeara":               ItemData(make_item_id(ItemType.BOOK, 24), ItemClassification.filler),
    "Log Book: Serpantina":             ItemData(make_item_id(ItemType.BOOK, 25), ItemClassification.filler),
    "Log Book: Amelia":                 ItemData(make_item_id(ItemType.BOOK, 26), ItemClassification.filler),
    "Log Book: Anchovy":                ItemData(make_item_id(ItemType.BOOK, 27), ItemClassification.filler),
    "Log Book: Mimi the Mimic":         ItemData(make_item_id(ItemType.BOOK, 28), ItemClassification.filler),
    "Log Book: Pacifica Oceania":       ItemData(make_item_id(ItemType.BOOK, 29), ItemClassification.filler),
    "Log Book: DJ Dokoro":              ItemData(make_item_id(ItemType.BOOK, 30), ItemClassification.filler),
    "Log Book: The Pirate Captain":     ItemData(make_item_id(ItemType.BOOK, 31), ItemClassification.filler),
    "Log Book: The Fairy Queen":        ItemData(make_item_id(ItemType.BOOK, 32), ItemClassification.filler),
    "Log Book: Gourmet Gal":            ItemData(make_item_id(ItemType.BOOK, 33), ItemClassification.filler),
    "Log Book: Mouthface":              ItemData(make_item_id(ItemType.BOOK, 34), ItemClassification.filler),
    "Log Book: Nyazione":               ItemData(make_item_id(ItemType.BOOK, 35), ItemClassification.filler),
    "Log Book: Muffey":                 ItemData(make_item_id(ItemType.BOOK, 36), ItemClassification.filler),
    "Log Book: Estylia":                ItemData(make_item_id(ItemType.BOOK, 37), ItemClassification.filler),
    "Log Book: Cakeboy":                ItemData(make_item_id(ItemType.BOOK, 38), ItemClassification.filler)
}

detonators:ItemDict = {
    stage_to_detonator_item_index[StageIndex.ICY_PATH]:         ItemData(make_item_id(ItemType.DETONATOR, 1), ItemClassification.progression),
    stage_to_detonator_item_index[StageIndex.BRINE_CAVE]:       ItemData(make_item_id(ItemType.DETONATOR, 2), ItemClassification.progression),
    stage_to_detonator_item_index[StageIndex.TOWER_OF_POWER]:   ItemData(make_item_id(ItemType.DETONATOR, 3), ItemClassification.progression),
    stage_to_detonator_item_index[StageIndex.WINDY_WAY]:        ItemData(make_item_id(ItemType.DETONATOR, 4), ItemClassification.progression)
}

gourmet_upgrades:ItemDict = {
    "Gourmet Chicken":  ItemData(make_item_id(ItemType.GOURMET_GAL, 1), ItemClassification.useful),
    "Gourmet Pizza":    ItemData(make_item_id(ItemType.GOURMET_GAL, 2), ItemClassification.useful),
    "Gourmet Burger":   ItemData(make_item_id(ItemType.GOURMET_GAL, 3), ItemClassification.useful),
    "Gourmet Calamari": ItemData(make_item_id(ItemType.GOURMET_GAL, 4), ItemClassification.useful)
}

filler:ItemDict = {
    "Coin": ItemData(make_item_id(ItemType.FILLER, 1), ItemClassification.filler),
    "Small Gem": ItemData(make_item_id(ItemType.FILLER, 2), ItemClassification.filler),
    "Gem": ItemData(make_item_id(ItemType.FILLER, 3), ItemClassification.filler),
    "Large Gem": ItemData(make_item_id(ItemType.FILLER, 4), ItemClassification.filler),
    "Food": ItemData(make_item_id(ItemType.FILLER, 5), ItemClassification.filler),
}

filler_weights:dict[str, int] = {
    "Coin": 30,
    "Small Gem": 20,
    "Gem": 10,
    "Large Gem": 5,
    "Food": 5
}

# Ensure parity between filler and filler_weights, checked at apworld loading so it is caught early on testing.
def validate_filler() -> None:
    if not filler.keys() == filler_weights.keys():
        raise ValueError("filler and filler_weights have different keys.")
validate_filler()

filler_item_names:list[str] = list(filler_weights.keys())
filler_item_weights:list[int] = list(filler_weights.values())

# Not currently added to item table; the first alpha release won't have traps.
traps:ItemDict = {
    "Cannonball Trap": ItemData(make_item_id(ItemType.TRAPS, 1), ItemClassification.trap),
    "Floof Aviator Swarm Trap": ItemData(make_item_id(ItemType.TRAPS, 2), ItemClassification.trap),
    "Kiran Drive-By Trap": ItemData(make_item_id(ItemType.TRAPS, 3), ItemClassification.trap),
    "Box Trap": ItemData(make_item_id(ItemType.TRAPS, 4), ItemClassification.trap),
    "Random Enemy Trap": ItemData(make_item_id(ItemType.TRAPS, 5), ItemClassification.trap),
}

item_frequencies = {
    "Fairy": 25
}

item_groups = {
    "Log Books": set(books),
    "Detonators": set(detonators),
    "Gourmet Upgrades": set(gourmet_upgrades)
}

item_table = {
    **upgrades,
    **stage_unlocks,
    **fairies,
    **books,
    **detonators,
    **gourmet_upgrades,
    **filler
}

# ruff: enable[E501]

def update_item_classification(world: "KhimeraDAMGWorld") -> None:
    if world.options.shuffle_books:
        world.progression_overrides["Harpy Boost"] = ItemClassification.progression
        if world.options.shuffle_fairies:
            world.progression_overrides["Fairy"] = ItemClassification.progression_deprioritized_skip_balancing

def get_filler(world: "KhimeraDAMGWorld") -> str:
    # No trap logic yet
    return world.random.choices(filler_item_names, weights=filler_item_weights)[0]

def create_item(world: "KhimeraDAMGWorld", name) -> KhimeraDAMGItem:
    data = item_table[name]
    classification = data.type
    if name in world.progression_overrides:
        classification = world.progression_overrides[name]
    return KhimeraDAMGItem(name, classification, data.id, world.player)

def create_items(world: "KhimeraDAMGWorld") -> None:
    itempool: list[KhimeraDAMGItem] = []
    unfilled: int = len(world.multiworld.get_unfilled_locations(world.player))
    # Entrance Items
    for stage in stage_id_to_name:
        if stage in [StageIndex.GENERAL, StageIndex.HARVEST_EVENT, StageIndex.CAKEBOY]:
            continue
        entrance_item = world.create_item(stage_entrances[stage])
        if stage in world.starting_locations:
            # Place in starting inventory, not pool
            world.push_precollected(entrance_item)
        else:
            itempool.append(entrance_item)

    # Upgrade
    for entry in upgrades:
        upgrade_item = world.create_item(entry)
        itempool.append(upgrade_item)

    if world.options.shuffle_fairies:
        for _ in range(item_frequencies["Fairy"]):
            fairy = world.create_item("Fairy")
            itempool.append(fairy)

    if world.options.shuffle_books:
        for entry in books:
            book = world.create_item(entry)
            itempool.append(book)

    if world.options.shuffle_detonators:
        for entry in detonators:
            detonator = world.create_item(entry)
            itempool.append(detonator)

    if world.options.shuffle_gourmet_gal:
        for entry in gourmet_upgrades:
            gourmet_upgrade = world.create_item(entry)
            itempool.append(gourmet_upgrade)

    itempool_count = len(itempool)
    world.multiworld.itempool += itempool
    filler_count = unfilled - itempool_count
    if filler_count > 0:
        for _ in range(filler_count):
            world.multiworld.itempool.append(world.create_filler())

