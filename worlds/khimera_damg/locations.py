from .types import LocData, LocType, StageIndex, loc_type_to_name, stage_id_to_name

LocTuple = tuple[str, LocData]
LocList = list[LocTuple]


# Name is generated following the convention described in "Item and Location Conventions.md".
# It is available at the docs folder in the apworld github repository
def _make_name(stage: StageIndex, loc_type:LocType | str, identifier: str|None = None) -> str:
    name = ""
    if stage != StageIndex.GENERAL:
        name = f"{name}{stage_id_to_name[stage]}: "
    if isinstance(loc_type, str):
        name = f"{name}{loc_type}"
    else:
        name = f"{name}{loc_type_to_name[loc_type]}"
    if identifier is not None:
        name = f"{name} - {identifier}"
    return name

def _make_data(stage: StageIndex, loc_type:LocType, identifier: int) -> LocData:
    if identifier == 0:
        raise ValueError("Location ID identifier segment cannot be 0.")
    id = stage.value * 10000000 + loc_type.value * 100000 + identifier
    return LocData(id, stage)

def _make_loc(
        stage: StageIndex,
        loc_type:LocType,
        identifier: int,
        description: str|None = None,
        type_description: str|None = None
) -> LocTuple:
    name = _make_name(stage, loc_type if type_description is None else type_description, description)
    data = _make_data(stage, loc_type, identifier)
    return (name, data)

clear:LocList = [
    _make_loc(StageIndex.RAGAZZA_PLAINS, LocType.STAGE_CLEAR, 1),
    _make_loc(StageIndex.MT_AFROKUPA, LocType.STAGE_CLEAR, 1),
    _make_loc(StageIndex.OIL_PLATFORM, LocType.STAGE_CLEAR, 1),
    _make_loc(StageIndex.SKY_FORTRESS, LocType.STAGE_CLEAR, 1),
    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.STAGE_CLEAR, 1),
    _make_loc(StageIndex.THE_BLACK_WIDOW, LocType.STAGE_CLEAR, 1),
    _make_loc(StageIndex.MECHANICAL_MAYHEM, LocType.STAGE_CLEAR, 1),
    _make_loc(StageIndex.THE_SPIDERS_WEB, LocType.STAGE_CLEAR, 1),

    _make_loc(StageIndex.ICY_PATH, LocType.STAGE_CLEAR, 1),
    _make_loc(StageIndex.BRINE_CAVE, LocType.STAGE_CLEAR, 1),
    _make_loc(StageIndex.TOWER_OF_POWER, LocType.STAGE_CLEAR, 1),
    _make_loc(StageIndex.WINDY_WAY, LocType.STAGE_CLEAR, 1),
]

upgrades:LocList = [
    _make_loc(StageIndex.MT_AFROKUPA, LocType.STAGE_CLEAR, 2, "Saucy Shot Upgrade"),
    _make_loc(StageIndex.OIL_PLATFORM, LocType.STAGE_CLEAR, 2, "Mermaid Anchor Upgrade"),
    _make_loc(StageIndex.SKY_FORTRESS, LocType.STAGE_CLEAR, 2, "Harpy Boost Upgrade"),
    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.STAGE_CLEAR, 2, "Treasure Box Upgrade"),

    _make_loc(StageIndex.ICY_PATH, LocType.STAGE_CLEAR, 2, "Demon Fire Upgrade"),
    _make_loc(StageIndex.BRINE_CAVE, LocType.STAGE_CLEAR, 2, "Sturdy Feet Upgrade"),
    _make_loc(StageIndex.TOWER_OF_POWER, LocType.STAGE_CLEAR, 2, "Giant's Wave Upgrade"),
    _make_loc(StageIndex.WINDY_WAY, LocType.STAGE_CLEAR, 2, "Wicked Eye Upgrade"),
]

fairies:LocList = [
    _make_loc(StageIndex.RAGAZZA_TOWN, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.RAGAZZA_TOWN, LocType.FAIRY, 2, "2"),

    _make_loc(StageIndex.RAGAZZA_PLAINS, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.RAGAZZA_PLAINS, LocType.FAIRY, 2, "2"),

    _make_loc(StageIndex.MT_AFROKUPA, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.MT_AFROKUPA, LocType.FAIRY, 2, "2"),
    _make_loc(StageIndex.MT_AFROKUPA, LocType.FAIRY, 3, "3"),

    _make_loc(StageIndex.OIL_PLATFORM, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.OIL_PLATFORM, LocType.FAIRY, 2, "2"),
    _make_loc(StageIndex.OIL_PLATFORM, LocType.FAIRY, 3, "3"),

    _make_loc(StageIndex.SKY_FORTRESS, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.SKY_FORTRESS, LocType.FAIRY, 2, "2"),
    _make_loc(StageIndex.SKY_FORTRESS, LocType.FAIRY, 3, "3"),

    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.FAIRY, 2, "2"),
    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.FAIRY, 3, "3"),

    _make_loc(StageIndex.THE_BLACK_WIDOW, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.THE_BLACK_WIDOW, LocType.FAIRY, 2, "2"),
    _make_loc(StageIndex.THE_BLACK_WIDOW, LocType.FAIRY, 3, "3"),

    _make_loc(StageIndex.MECHANICAL_MAYHEM, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.MECHANICAL_MAYHEM, LocType.FAIRY, 2, "2"),

    _make_loc(StageIndex.ICY_PATH, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.BRINE_CAVE, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.TOWER_OF_POWER, LocType.FAIRY, 1, "1"),
    _make_loc(StageIndex.WINDY_WAY, LocType.FAIRY, 1, "1"),
]

# Harvest event books will be stored separately when implemented.
books:LocList = [
    _make_loc(StageIndex.RAGAZZA_TOWN, LocType.BOOK, 1, "1 (Scuttlebit)"),
    _make_loc(StageIndex.RAGAZZA_TOWN, LocType.BOOK, 2, "2 (Nyazione)"),

    _make_loc(StageIndex.CHELSHIAS_HOUSE, LocType.BOOK, 1, "1 (Muffey)"),

    _make_loc(StageIndex.FAIRIES_DOMAIN, LocType.BOOK, 1, "1 (Gourmet Gal)"),
    _make_loc(StageIndex.FAIRIES_DOMAIN, LocType.BOOK, 2, "2 (The Fairy Queen)"),

    _make_loc(StageIndex.QUIZ, LocType.BOOK, 1, "1 (Mouthface)"),

    _make_loc(StageIndex.RAGAZZA_PLAINS, LocType.BOOK, 1, "1 (Serpantina)"),
    _make_loc(StageIndex.RAGAZZA_PLAINS, LocType.BOOK, 2, "2 (Floof Pirate)"),
    _make_loc(StageIndex.RAGAZZA_PLAINS, LocType.BOOK, 3, "3 (Chelshia)"),

    _make_loc(StageIndex.MT_AFROKUPA, LocType.BOOK, 1, "1 (Pirate Explorer)"),
    _make_loc(StageIndex.MT_AFROKUPA, LocType.BOOK, 2, "2 (Misboro)"),
    _make_loc(StageIndex.MT_AFROKUPA, LocType.BOOK, 3, "3 (Little Oni)"),
    _make_loc(StageIndex.MT_AFROKUPA, LocType.BOOK, 4, "4 (Anchovy)"),

    _make_loc(StageIndex.OIL_PLATFORM, LocType.BOOK, 1, "1 (Pacifica Oceania)"),
    _make_loc(StageIndex.OIL_PLATFORM, LocType.BOOK, 2, "2 (Pirate Swordsman)"),
    _make_loc(StageIndex.OIL_PLATFORM, LocType.BOOK, 3, "3 (Floof Bomber)"),
    _make_loc(StageIndex.OIL_PLATFORM, LocType.BOOK, 4, "4 (Tamole)"),

    _make_loc(StageIndex.SKY_FORTRESS, LocType.BOOK, 1, "1 (Floof Aviator)"),
    _make_loc(StageIndex.SKY_FORTRESS, LocType.BOOK, 2, "2 (The Professor)"),
    _make_loc(StageIndex.SKY_FORTRESS, LocType.BOOK, 3, "3 (Pirate Cannoneer)"),
    _make_loc(StageIndex.SKY_FORTRESS, LocType.BOOK, 4, "4 (Amelia)"),

    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.BOOK, 1, "1 (Zambot)"),
    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.BOOK, 2, "2 (Seedle)"),
    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.BOOK, 3, "3 (Mimi the Mimic)"),
    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.BOOK, 4, "4 (Bernadette)"),

    _make_loc(StageIndex.THE_BLACK_WIDOW, LocType.BOOK, 1, "1 (Pirate Samurai)"),
    _make_loc(StageIndex.THE_BLACK_WIDOW, LocType.BOOK, 2, "2 (Weekday Witches)"),

    _make_loc(StageIndex.MECHANICAL_MAYHEM, LocType.BOOK, 1, "1 (DJ Doroko)"),

    _make_loc(StageIndex.THE_SPIDERS_WEB, LocType.BOOK, 1, "1 (The Pirate Captain)"),

    _make_loc(StageIndex.ICY_PATH, LocType.BOOK, 1, "1 (Skallo)"),
    _make_loc(StageIndex.ICY_PATH, LocType.BOOK, 2, "2 (Chibeara)"),

    _make_loc(StageIndex.BRINE_CAVE, LocType.BOOK, 1, "1 (Squidge)"),
    _make_loc(StageIndex.BRINE_CAVE, LocType.BOOK, 2, "2 (Pirate Demolitions)"),

    _make_loc(StageIndex.TOWER_OF_POWER, LocType.BOOK, 1, "1 (Spaîctre Die)"),
    _make_loc(StageIndex.TOWER_OF_POWER, LocType.BOOK, 2, "2 (Estylia)"),

    _make_loc(StageIndex.WINDY_WAY, LocType.BOOK, 1, "1 (Kiran)"),
    _make_loc(StageIndex.WINDY_WAY, LocType.BOOK, 2, "2 (Pirate Marksman)"),

    _make_loc(StageIndex.CAKEBOY, LocType.BOOK, 1, "1 (Cakeboy)"),
]

detonators:LocList = [
    _make_loc(StageIndex.MT_AFROKUPA, LocType.DETONATOR, 1),
    _make_loc(StageIndex.OIL_PLATFORM, LocType.DETONATOR, 1),
    _make_loc(StageIndex.SKY_FORTRESS, LocType.DETONATOR, 1),
    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.DETONATOR, 1),
]

gourmet_gal:LocList = [
    _make_loc(StageIndex.MT_AFROKUPA, LocType.GOURMET_GAL, 1),
    _make_loc(StageIndex.OIL_PLATFORM, LocType.GOURMET_GAL, 1),
    _make_loc(StageIndex.SKY_FORTRESS, LocType.GOURMET_GAL, 1),
    _make_loc(StageIndex.PUMPKIN_VALLEY, LocType.GOURMET_GAL, 1),
]

def _make_loc_table(locs: LocList):
    return dict(locs)

loc_table:dict[str, LocData] = _make_loc_table(
    clear
    + upgrades
    + fairies
    + books
    + detonators
    + gourmet_gal
)
