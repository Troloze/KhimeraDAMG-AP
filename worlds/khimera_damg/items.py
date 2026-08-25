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
    "Fairy": ItemData(make_item_id(ItemType.FAIRY, 1), ItemClassification.progression_skip_balancing)
}

# Harvest event log books will be placed in a separate category when implemented, but are all books regardless.
books:ItemDict = {
    "Log Book: Chelshia":               ItemData(make_item_id(ItemType.BOOK, 1), ItemClassification.progression_skip_balancing),
    "Log Book: The Professor":          ItemData(make_item_id(ItemType.BOOK, 2), ItemClassification.progression_skip_balancing),
    "Log Book: Bernadette":             ItemData(make_item_id(ItemType.BOOK, 3), ItemClassification.progression_skip_balancing),
    "Log Book: Floof Pirate":           ItemData(make_item_id(ItemType.BOOK, 4), ItemClassification.progression_skip_balancing),
    "Log Book: Floof Aviator":          ItemData(make_item_id(ItemType.BOOK, 5), ItemClassification.progression_skip_balancing),
    "Log Book: Floof Bomber":           ItemData(make_item_id(ItemType.BOOK, 6), ItemClassification.progression_skip_balancing),
    "Log Book: Pirate Swordsman":       ItemData(make_item_id(ItemType.BOOK, 7), ItemClassification.progression_skip_balancing),
    "Log Book: Pirate Marksman":        ItemData(make_item_id(ItemType.BOOK, 8), ItemClassification.progression_skip_balancing),
    "Log Book: Pirate Cannoneer":       ItemData(make_item_id(ItemType.BOOK, 9), ItemClassification.progression_skip_balancing),
    "Log Book: Pirate Demolitions":     ItemData(make_item_id(ItemType.BOOK, 10), ItemClassification.progression_skip_balancing),
    "Log Book: Pirate Explorer":        ItemData(make_item_id(ItemType.BOOK, 11), ItemClassification.progression_skip_balancing),
    "Log Book: Pirate Samurai":         ItemData(make_item_id(ItemType.BOOK, 12), ItemClassification.progression_skip_balancing),
    "Log Book: Scuttlebit":             ItemData(make_item_id(ItemType.BOOK, 13), ItemClassification.progression_skip_balancing),
    "Log Book: Zambot":                 ItemData(make_item_id(ItemType.BOOK, 14), ItemClassification.progression_skip_balancing),
    "Log Book: Seedle":                 ItemData(make_item_id(ItemType.BOOK, 15), ItemClassification.progression_skip_balancing),
    "Log Book: Misboro":                ItemData(make_item_id(ItemType.BOOK, 16), ItemClassification.progression_skip_balancing),
    "Log Book: Skallo":                 ItemData(make_item_id(ItemType.BOOK, 17), ItemClassification.progression_skip_balancing),
    "Log Book: Kiran":                  ItemData(make_item_id(ItemType.BOOK, 18), ItemClassification.progression_skip_balancing),
    "Log Book: Little Oni":             ItemData(make_item_id(ItemType.BOOK, 19), ItemClassification.progression_skip_balancing),
    "Log Book: Squidge":                ItemData(make_item_id(ItemType.BOOK, 20), ItemClassification.progression_skip_balancing),
    "Log Book: Tamole":                 ItemData(make_item_id(ItemType.BOOK, 21), ItemClassification.progression_skip_balancing),
    "Log Book: Spaîctre Die":           ItemData(make_item_id(ItemType.BOOK, 22), ItemClassification.progression_skip_balancing),
    "Log Book: Weekday Witches":        ItemData(make_item_id(ItemType.BOOK, 23), ItemClassification.progression_skip_balancing),
    "Log Book: Chibeara":               ItemData(make_item_id(ItemType.BOOK, 24), ItemClassification.progression_skip_balancing),
    "Log Book: Serpantina":             ItemData(make_item_id(ItemType.BOOK, 25), ItemClassification.progression_skip_balancing),
    "Log Book: Amelia":                 ItemData(make_item_id(ItemType.BOOK, 26), ItemClassification.progression_skip_balancing),
    "Log Book: Anchovy":                ItemData(make_item_id(ItemType.BOOK, 27), ItemClassification.progression_skip_balancing),
    "Log Book: Mimi the Mimic":         ItemData(make_item_id(ItemType.BOOK, 28), ItemClassification.progression_skip_balancing),
    "Log Book: Pacifica Oceania":       ItemData(make_item_id(ItemType.BOOK, 29), ItemClassification.progression_skip_balancing),
    "Log Book: DJ Dokoro":              ItemData(make_item_id(ItemType.BOOK, 30), ItemClassification.progression_skip_balancing),
    "Log Book: The Pirate Captain":     ItemData(make_item_id(ItemType.BOOK, 31), ItemClassification.progression_skip_balancing),
    "Log Book: The Fairy Queen":        ItemData(make_item_id(ItemType.BOOK, 32), ItemClassification.progression_skip_balancing),
    "Log Book: Gourmet Gal":            ItemData(make_item_id(ItemType.BOOK, 33), ItemClassification.progression_skip_balancing),
    "Log Book: Mouthface":              ItemData(make_item_id(ItemType.BOOK, 34), ItemClassification.progression_skip_balancing),
    "Log Book: Nyazione":               ItemData(make_item_id(ItemType.BOOK, 35), ItemClassification.progression_skip_balancing),
    "Log Book: Muffey":                 ItemData(make_item_id(ItemType.BOOK, 36), ItemClassification.progression_skip_balancing),
    "Log Book: Estylia":                ItemData(make_item_id(ItemType.BOOK, 37), ItemClassification.progression_skip_balancing),
    "Log Book: Cakeboy":                ItemData(make_item_id(ItemType.BOOK, 38), ItemClassification.progression_skip_balancing)
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
    "Nothing": ItemData(make_item_id(ItemType.FILLER, 1), ItemClassification.filler)
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

def get_filler(world: "KhimeraDAMGWorld") -> str:
    return list(filler).pop(world.random.randrange(0, len(filler)))

def create_item(world: "KhimeraDAMGWorld", name) -> KhimeraDAMGItem:
    data = item_table[name]
    return KhimeraDAMGItem(name, data.type, data.id, world.player)

def create_items(world: "KhimeraDAMGWorld") -> None:
    # Entrance Items
    for stage in stage_id_to_name:
        if stage in [StageIndex.GENERAL, StageIndex.HARVEST_EVENT, StageIndex.CAKEBOY]:
            continue
        entrance_item = world.create_item(stage_entrances[stage])
        if stage in world.starting_locations:
            # Place in starting inventory, not pool
            world.push_precollected(entrance_item)
        else:
            world.multiworld.itempool.append(entrance_item)

    # Upgrade
    for entry in upgrades:
        upgrade_item = world.create_item(entry)
        world.multiworld.itempool.append(upgrade_item)

    if world.options.shuffle_fairies:
        for _i in range(item_frequencies["Fairy"]):
            fairy = world.create_item("Fairy")
            world.multiworld.itempool.append(fairy)

    if world.options.shuffle_books:
        for entry in books:
            book = world.create_item(entry)
            world.multiworld.itempool.append(book)

    if world.options.shuffle_detonators:
        for entry in detonators:
            detonator = world.create_item(entry)
            world.multiworld.itempool.append(detonator)

    if world.options.shuffle_gourmet_gal:
        for entry in gourmet_upgrades:
            gourmet_upgrade = world.create_item(entry)
            world.multiworld.itempool.append(gourmet_upgrade)
