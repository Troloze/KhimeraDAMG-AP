# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Region graph and entrance logic: which unlocks open which stage, and the final-stage chain."""

from BaseClasses import CollectionState  # type: ignore

from ...types import StageIndex, stage_entrances, stage_id_to_name, stage_to_detonator_item_index
from ..bases import ALL_SHUFFLES, BOOKS_WITHOUT_FAIRIES, NO_SHUFFLES, KhimeraTestBase

MAIN_STAGE_UNLOCKS = [
    stage_entrances[StageIndex.SKY_FORTRESS],
    stage_entrances[StageIndex.MT_AFROKUPA],
    stage_entrances[StageIndex.PUMPKIN_VALLEY],
    stage_entrances[StageIndex.OIL_PLATFORM]
]

FAIRY_QUEEN_BOOK = "The Fairies Domain: Log Book - 2 (The Fairy Queen)"

DETONATORS_ONLY = {
    **NO_SHUFFLES,
    "shuffle_detonators": True
}


class RegionAccessMixin:
    """Helper for asking "which regions open with exactly these items?"."""

    def reach_region_with(self, item_names: list[str], region: str) -> bool:
        """Can ``region`` be reached from a fresh state holding only ``item_names``?

        A fresh ``CollectionState`` already holds the precollected starting unlocks, so only the
        items a player would have to find are listed at the call sites.
        """
        state = CollectionState(self.multiworld)
        for item in self.get_items_by_name(item_names):
            state.collect(item)
        return state.can_reach(region, "Region", self.player)


class TestRegionGraph(KhimeraTestBase):
    """The shape of the graph, independent of logic."""

    options = NO_SHUFFLES

    def test_origin_region_exists(self) -> None:
        self.assertEqual(self.world.origin_region_name, "Map")
        self.assertIsNotNone(
            self.multiworld.get_region("Map", self.player),
            "the origin region named by the world class does not exist"
        )

    def test_regions_match_the_stage_table(self) -> None:
        skipped = {StageIndex.OTHER, StageIndex.HARVEST_EVENT}
        expected = {"Map"} | {
            name for stage, name in stage_id_to_name.items() if stage not in skipped
        }
        present = {region.name for region in self.multiworld.get_regions(self.player)}
        self.assertEqual(
            present,
            expected,
            f"unexpected regions {sorted(present - expected)}, missing {sorted(expected - present)}"
        )

    def test_stage_regions_hang_off_the_map(self) -> None:
        cakeboy = stage_id_to_name[StageIndex.CAKEBOY]
        for region in self.multiworld.get_regions(self.player):
            if region.name in ("Map", cakeboy):
                continue
            parents = {entrance.parent_region.name for entrance in region.entrances}
            self.assertEqual(
                parents,
                {"Map"},
                f"region \"{region.name}\" is entered from {sorted(parents)}, expected the Map hub"
            )

    def test_cakeboy_hangs_off_chelshias_house(self) -> None:
        cakeboy = self.multiworld.get_region(stage_id_to_name[StageIndex.CAKEBOY], self.player)
        parents = {entrance.parent_region.name for entrance in cakeboy.entrances}
        self.assertEqual(
            parents,
            {stage_id_to_name[StageIndex.CHELSHIAS_HOUSE]},
            f"Cakeboy is entered from {sorted(parents)}"
        )


class TestStageUnlocks(RegionAccessMixin, KhimeraTestBase):
    """Each stage needs its own unlock; the extra stages also need the stage they branch off."""

    options = NO_SHUFFLES

    def test_main_stages_need_their_unlock(self) -> None:
        for stage in (
            StageIndex.SKY_FORTRESS,
            StageIndex.MT_AFROKUPA,
            StageIndex.PUMPKIN_VALLEY,
            StageIndex.OIL_PLATFORM
        ):
            name = stage_id_to_name[stage]
            with self.subTest(stage=name):
                self.assertFalse(
                    self.reach_region_with([], name),
                    f"\"{name}\" is reachable without \"{stage_entrances[stage]}\""
                )
                self.assertTrue(
                    self.reach_region_with([stage_entrances[stage]], name),
                    f"\"{name}\" is not reachable with \"{stage_entrances[stage]}\""
                )

    def test_extra_stages_need_their_base_stage(self) -> None:
        # Without the detonator shuffle, an extra stage is gated behind the unlock of the stage it
        # branches off, because that is where the vanilla detonator lives.
        for stage, base in (
            (StageIndex.TOWER_OF_POWER, StageIndex.SKY_FORTRESS),
            (StageIndex.ICY_PATH, StageIndex.MT_AFROKUPA),
            (StageIndex.WINDY_WAY, StageIndex.PUMPKIN_VALLEY),
            (StageIndex.BRINE_CAVE, StageIndex.OIL_PLATFORM)
        ):
            name = stage_id_to_name[stage]
            own = stage_entrances[stage]
            base_unlock = stage_entrances[base]
            with self.subTest(stage=name):
                self.assertFalse(
                    self.reach_region_with([own], name),
                    f"\"{name}\" is reachable with only \"{own}\"; \"{base_unlock}\" should also be required"
                )
                self.assertFalse(
                    self.reach_region_with([base_unlock], name),
                    f"\"{name}\" is reachable with only \"{base_unlock}\"; \"{own}\" should also be required"
                )
                self.assertTrue(
                    self.reach_region_with([own, base_unlock], name),
                    f"\"{name}\" is not reachable with both \"{own}\" and \"{base_unlock}\""
                )

    def test_final_stage_chain(self) -> None:
        black_widow = stage_id_to_name[StageIndex.THE_BLACK_WIDOW]
        mechanical = stage_id_to_name[StageIndex.MECHANICAL_MAYHEM]
        spiders_web = stage_id_to_name[StageIndex.THE_SPIDERS_WEB]
        widow_unlock = stage_entrances[StageIndex.THE_BLACK_WIDOW]
        mechanical_unlock = stage_entrances[StageIndex.MECHANICAL_MAYHEM]
        web_unlock = stage_entrances[StageIndex.THE_SPIDERS_WEB]

        self.assertFalse(
            self.reach_region_with([widow_unlock], black_widow),
            f"\"{black_widow}\" is reachable without the four main stage unlocks"
        )
        self.assertTrue(
            self.reach_region_with([widow_unlock, *MAIN_STAGE_UNLOCKS], black_widow),
            f"\"{black_widow}\" is not reachable with its unlock and the four main stage unlocks"
        )
        self.assertFalse(
            self.reach_region_with([mechanical_unlock, *MAIN_STAGE_UNLOCKS], mechanical),
            f"\"{mechanical}\" is reachable without \"{widow_unlock}\""
        )
        self.assertTrue(
            self.reach_region_with([mechanical_unlock, widow_unlock, *MAIN_STAGE_UNLOCKS], mechanical),
            f"\"{mechanical}\" is not reachable with the full chain up to it"
        )
        self.assertFalse(
            self.reach_region_with([web_unlock, widow_unlock, *MAIN_STAGE_UNLOCKS], spiders_web),
            f"\"{spiders_web}\" is reachable without \"{mechanical_unlock}\""
        )
        self.assertTrue(
            self.reach_region_with(
                [web_unlock, mechanical_unlock, widow_unlock, *MAIN_STAGE_UNLOCKS],
                spiders_web
            ),
            f"\"{spiders_web}\" is not reachable with the full chain up to it"
        )

    def test_quiz_needs_the_four_main_stages(self) -> None:
        # The quiz room's own unlock is a starting item, so the main stage unlocks are the gate.
        quiz = stage_id_to_name[StageIndex.QUIZ]
        self.assertFalse(
            self.reach_region_with([], quiz),
            f"\"{quiz}\" is reachable without the four main stage unlocks"
        )
        self.assertTrue(
            self.reach_region_with(MAIN_STAGE_UNLOCKS, quiz),
            f"\"{quiz}\" is not reachable with the four main stage unlocks"
        )


class TestDetonatorGating(RegionAccessMixin, KhimeraTestBase):
    """With detonators shuffled, the extra stages move behind the detonator items."""

    options = DETONATORS_ONLY

    def test_extra_stages_need_their_detonator(self) -> None:
        for stage in (
            StageIndex.TOWER_OF_POWER,
            StageIndex.ICY_PATH,
            StageIndex.WINDY_WAY,
            StageIndex.BRINE_CAVE
        ):
            name = stage_id_to_name[stage]
            own = stage_entrances[stage]
            detonator = stage_to_detonator_item_index[stage]
            with self.subTest(stage=name):
                self.assertFalse(
                    self.reach_region_with([own], name),
                    f"\"{name}\" is reachable with only \"{own}\"; \"{detonator}\" should also be required"
                )
                self.assertTrue(
                    self.reach_region_with([own, detonator], name),
                    f"\"{name}\" is not reachable with \"{own}\" and \"{detonator}\""
                )


class TestFairyQueenBookWithFairyItems(RegionAccessMixin, KhimeraTestBase):
    """The Fairy Queen book needs twelve fairies, counted as items when they are shuffled."""

    options = ALL_SHUFFLES

    def test_twelve_fairies_are_required(self) -> None:
        fairies = self.get_items_by_name("Fairy")
        self.assertGreaterEqual(len(fairies), 12, f"only {len(fairies)} fairies exist in the pool")

        state = CollectionState(self.multiworld)
        for item in fairies[:11]:
            state.collect(item)
        self.assertFalse(
            state.can_reach(FAIRY_QUEEN_BOOK, "Location", self.player),
            f"\"{FAIRY_QUEEN_BOOK}\" is reachable with 11 fairies"
        )
        state.collect(fairies[11])
        self.assertTrue(
            state.can_reach(FAIRY_QUEEN_BOOK, "Location", self.player),
            f"\"{FAIRY_QUEEN_BOOK}\" is not reachable with 12 fairies"
        )


class TestFairyQueenBookWithFairyEvents(KhimeraTestBase):
    """With fairies unshuffled the same rule counts the fairy events instead."""

    options = BOOKS_WITHOUT_FAIRIES

    def test_the_book_needs_the_fairy_events(self) -> None:
        self.assertFalse(
            CollectionState(self.multiworld).can_reach(FAIRY_QUEEN_BOOK, "Location", self.player),
            f"\"{FAIRY_QUEEN_BOOK}\" is reachable from an empty state, so the fairy count is not gating it"
        )
        self.assertTrue(
            self.multiworld.get_all_state().can_reach(FAIRY_QUEEN_BOOK, "Location", self.player),
            f"\"{FAIRY_QUEEN_BOOK}\" is unreachable even with everything collected; the fairy events "
            "are not being counted"
        )
