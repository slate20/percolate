"""App entry point, screen router, global tick loop."""

from __future__ import annotations

from typing import ClassVar

from textual.app import App
from textual.screen import Screen

from percolate.backdrop_compositor import load_farmhouse_data
from percolate.config import DEV_MODE, PACKAGE_DIR, UI_TICK_SECONDS
from percolate.models.bean import load_bean_registry, load_plant_stage_art
from percolate.models.farm import Farm, load_upgrades_data
from percolate.models.roast import (
    load_ingredient_registry,
    load_recipe_registry,
    load_roast_stage_art,
)
from percolate.screens.farm_screen import FarmScreen
from percolate.screens.help_modal import HelpModal
from percolate.screens.market_screen import MarketScreen
from percolate.screens.roast_screen import RoastScreen
from percolate.theme import PERCOLATE_LATTE, PERCOLATE_THEMES


class PercolateApp(App):
    TITLE = "Percolate"
    CSS_PATH = "percolate.tcss"
    # Textual resolves a relative CSS_PATH via inspect.getfile(type(self)).
    # _BASE_PATH is Textual's documented override for that — point it at
    # config.PACKAGE_DIR, which already knows how to find the real, on-disk
    # package directory whether running from source or a Nuitka build.
    _BASE_PATH = str(PACKAGE_DIR / "main.py")

    SCREENS: ClassVar[dict[str, type[Screen]]] = {
        "farm": FarmScreen,
        "roast": RoastScreen,
        "market": MarketScreen,
    }

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("f", "show_screen('farm')", "Farm"),
        ("r", "show_screen('roast')", "Roast"),
        ("m", "show_screen('market')", "Market"),
        ("h", "show_help", "Help"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        for theme in PERCOLATE_THEMES:
            self.register_theme(theme)
        self.theme = PERCOLATE_LATTE.name
        self.beans = load_bean_registry()
        self.plant_stages = load_plant_stage_art()
        self.farmhouse_data = load_farmhouse_data()
        self.ingredients = load_ingredient_registry()
        self.recipes = load_recipe_registry()
        self.roast_stages = load_roast_stage_art()
        self.upgrades_data = load_upgrades_data()
        self.farm: Farm = Farm.load_from_disk()

        if DEV_MODE:
            self.bind("right_square_bracket", "dev_skip_small", description="Dev: +15m")
            self.bind("left_square_bracket", "dev_skip_large", description="Dev: +6h")
            self.bind("g", "dev_add_gold", description="Dev: +1000g")

    def on_mount(self) -> None:
        self.push_screen("farm")
        self.update_subtitle()
        self.set_interval(UI_TICK_SECONDS, self.update_subtitle)

    def update_subtitle(self) -> None:
        self.sub_title = f"{self.farm.gold}g"

    def action_show_screen(self, name: str) -> None:
        self.switch_screen(name)

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())

    def action_quit(self) -> None:
        self.farm.save_to_disk()
        self.exit()

    # --- Dev tools (PERCOLATE_DEV=1 only) --------------------------------

    def _dev_refresh_screen(self) -> None:
        # Give immediate feedback rather than waiting for the next 5s tick.
        screen = self.screen
        if hasattr(screen, "refresh_plots"):
            screen.refresh_plots()
        if hasattr(screen, "refresh_batches"):
            screen.refresh_batches()

    def action_dev_skip_small(self) -> None:
        self.farm.debug_advance_time(15 * 60)
        self.farm.save_to_disk()
        self._dev_refresh_screen()
        self.notify("Dev: skipped 15 minutes")

    def action_dev_skip_large(self) -> None:
        self.farm.debug_advance_time(6 * 3600)
        self.farm.save_to_disk()
        self._dev_refresh_screen()
        self.notify("Dev: skipped 6 hours")

    def action_dev_add_gold(self) -> None:
        self.farm.gold += 1000
        self.farm.save_to_disk()
        self.update_subtitle()
        self.notify("Dev: +1000g")


def main() -> None:
    PercolateApp().run()


if __name__ == "__main__":
    main()
