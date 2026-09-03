from typing import TYPE_CHECKING

from BaseClasses import CollectionRule, Region

from .types import (
    KhimeraDAMGItem,
    KhimeraDAMGLocation,
    StageIndex,
    extra_to_stage_index,
    stage_entrances,
    stage_id_to_name,
    stage_to_detonator_item_index,
)

if TYPE_CHECKING:
    from . import KhimeraDAMGWorld

def create_regions(world: "KhimeraDAMGWorld"):
    world_map = create_region(world, "Map")
    regions:dict[str, Region] = {}
    region_stages:dict[str, StageIndex] = {}

    for stage, name in stage_id_to_name.items():
        if stage in [StageIndex.GENERAL, StageIndex.HARVEST_EVENT, StageIndex.CAKEBOY]:
            continue
        regions[name] = create_and_connect_region(world, name, f"{name} Entrance", world_map, stage)
        region_stages[name] = stage

    # Cakeboy
    regions[stage_id_to_name[StageIndex.CAKEBOY]] = create_and_connect_region(
        world,
        stage_id_to_name[StageIndex.CAKEBOY],
        "Cakeboy Entrance",
        regions[stage_id_to_name[StageIndex.CHELSHIAS_HOUSE]]
    )
    region_stages[stage_id_to_name[StageIndex.CAKEBOY]] = StageIndex.CAKEBOY
    for name, region in regions.items():
        assign_locations_to_region(world, region, region_stages[name])

def assign_locations_to_region(world: "KhimeraDAMGWorld", region: Region, stage: StageIndex) -> None:
    from .locations import books, clears, detonators, fairies, gourmet_gal, minibosses, upgrades
    locations = {}
    event_locations = {}
    locations |= {name: data.id for name, data in clears if data.stage == stage}
    locations |= {name: data.id for name, data in upgrades if data.stage == stage}
    locations |= {name: data.id for name, data in minibosses if data.stage == stage}

    if world.options.shuffle_books:
        locations |= {name: data.id for name, data in books if data.stage == stage}

    if world.options.shuffle_fairies:
        locations |= {name: data.id for name, data in fairies if data.stage == stage}
    else:
        if world.options.shuffle_books:
            event_locations |= {name: "Fairy" for name, data in fairies if data.stage == stage}

    if world.options.shuffle_detonators:
        locations |= {name: data.id for name, data in detonators if data.stage == stage}

    if world.options.shuffle_gourmet_gal:
        locations |= {name: data.id for name, data in gourmet_gal if data.stage == stage}

    region.add_locations(locations, KhimeraDAMGLocation)

    for location, item_name in event_locations.items():
        region.add_event(
            location,
            item_name,
            location_type=KhimeraDAMGLocation,
            item_type=KhimeraDAMGItem,
            show_in_spoiler=False
        )


def create_region(world: "KhimeraDAMGWorld", name:str) -> Region:
    reg:Region = Region(name, world.player, world.multiworld)
    world.multiworld.regions.append(reg)
    return reg

def create_and_connect_region(
    world: "KhimeraDAMGWorld",
    name:str,
    entrance_name:str,
    connected_region: Region,
    stage_lock: StageIndex|None = None
) -> Region:
    new_region:Region = create_region(world, name)
    is_shuffle_detonators = world.options.shuffle_detonators

    extra_stages = [StageIndex.ICY_PATH, StageIndex.BRINE_CAVE, StageIndex.TOWER_OF_POWER, StageIndex.WINDY_WAY]
    func: CollectionRule | None
    # ruff: disable[E731]
    if stage_lock is None:
        func = None
    elif stage_lock in extra_stages:
        item_lock = stage_entrances[extra_to_stage_index[stage_lock]]
        if is_shuffle_detonators:
            item_lock = stage_to_detonator_item_index[stage_lock]
        func = lambda state: state.has_all(
            [
                stage_entrances[stage_lock],
                item_lock
            ],
            world.player
        )
    elif stage_lock is StageIndex.THE_BLACK_WIDOW:
        func = lambda state: state.has_all(
            [
                stage_entrances[stage_lock],
                stage_entrances[StageIndex.MT_AFROKUPA],
                stage_entrances[StageIndex.OIL_PLATFORM],
                stage_entrances[StageIndex.SKY_FORTRESS],
                stage_entrances[StageIndex.PUMPKIN_VALLEY]
            ],
            world.player
        )
    elif stage_lock is StageIndex.QUIZ:
        func = lambda state: state.has_all(
            [
                stage_entrances[stage_lock],
                stage_entrances[StageIndex.MT_AFROKUPA],
                stage_entrances[StageIndex.OIL_PLATFORM],
                stage_entrances[StageIndex.SKY_FORTRESS],
                stage_entrances[StageIndex.PUMPKIN_VALLEY]
            ],
            world.player
        )
    elif stage_lock is StageIndex.MECHANICAL_MAYHEM:
        func = lambda state: state.has_all(
            [
                stage_entrances[stage_lock],
                stage_entrances[StageIndex.MT_AFROKUPA],
                stage_entrances[StageIndex.OIL_PLATFORM],
                stage_entrances[StageIndex.SKY_FORTRESS],
                stage_entrances[StageIndex.PUMPKIN_VALLEY],
                stage_entrances[StageIndex.THE_BLACK_WIDOW]
            ],
            world.player
        )
    elif stage_lock is StageIndex.THE_SPIDERS_WEB:
        func = lambda state: state.has_all(
            [
                stage_entrances[stage_lock],
                stage_entrances[StageIndex.MT_AFROKUPA],
                stage_entrances[StageIndex.OIL_PLATFORM],
                stage_entrances[StageIndex.SKY_FORTRESS],
                stage_entrances[StageIndex.PUMPKIN_VALLEY],
                stage_entrances[StageIndex.THE_BLACK_WIDOW],
                stage_entrances[StageIndex.MECHANICAL_MAYHEM]
            ],
            world.player
        )
    else:
        func = lambda state: state.has(stage_entrances[stage_lock], world.player)
    # ruff: enable[E731]
    connected_region.connect(new_region, entrance_name, rule=func)

    return new_region
