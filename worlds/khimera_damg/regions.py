from typing import TYPE_CHECKING

from BaseClasses import Region

from .locations import books, clear, detonators, fairies, gourmet_gal, upgrades
from .types import (
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
    region.add_locations({name: data.id for name, data in clear if data.stage == stage}, KhimeraDAMGLocation)
    region.add_locations({name: data.id for name, data in upgrades if data.stage == stage}, KhimeraDAMGLocation)

    if world.options.shuffle_books:
        region.add_locations({name: data.id for name, data in books if data.stage == stage}, KhimeraDAMGLocation)

    if world.options.shuffle_fairies:
        region.add_locations({name: data.id for name, data in fairies if data.stage == stage}, KhimeraDAMGLocation)

    if world.options.shuffle_detonators:
        region.add_locations({name: data.id for name, data in detonators if data.stage == stage}, KhimeraDAMGLocation)

    if world.options.shuffle_gourmet_gal:
        region.add_locations({name: data.id for name, data in gourmet_gal if data.stage == stage}, KhimeraDAMGLocation)

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

    if stage_lock is None:
        func = None
    elif stage_lock in extra_stages:
        if is_shuffle_detonators:
            func = lambda state: state.has(stage_entrances[stage_lock], world.player) \
                             and state.has(stage_to_detonator_item_index[stage_lock], world.player) # noqa: E731
        else:
            # Instead of locking behind detonator item, extra stages will have to be locked
            # behind their parent stages instead.
            parent_stage = extra_to_stage_index[stage_lock]
            func = lambda state: state.has(stage_entrances[stage_lock], world.player) \
                             and state.has(stage_entrances[parent_stage], world.player) # noqa: E731
    else:
        func = lambda state: state.has(stage_entrances[stage_lock], world.player) # noqa: E731

    connected_region.connect(new_region, entrance_name, rule=func)

    return new_region
