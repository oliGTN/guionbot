"""Run local data generation scripts while sharing parsed GameData."""

import runpy
import sys


def run_script(module_name, *args):
    """Execute a script as __main__, temporarily setting its command-line args."""
    previous_argv = sys.argv
    try:
        sys.argv = [module_name] + list(args)
        runpy.run_module(module_name, run_name="__main__")
    finally:
        sys.argv = previous_argv


def main():
    game_data_file = "../warstats/GameData.json"

    print("update units...")
    run_script("SCRIPTS.update_unitsList_json", game_data_file)

    print("update mods...")
    run_script("SCRIPTS.update_modList_json", game_data_file)

    print("update capabilities...")
    run_script("SCRIPTS.create_capa_list", game_data_file)

    print("update equipment...")
    run_script("SCRIPTS.create_eqpt_dict", game_data_file)

    print("update targeting rules...")
    run_script("SCRIPTS.create_targetrule_dict", game_data_file)

    print("update TB...")
    run_script("SCRIPTS.create_tb_data", game_data_file)

    print("update relic promotion table...")
    run_script("SCRIPTS.create_relic_promo_table", game_data_file)

    print("update crinolo data...")
    run_script("SCRIPTS.create_crinolo_gameData", game_data_file)


if __name__ == "__main__":
    main()
