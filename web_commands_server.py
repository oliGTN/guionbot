import os

import aiohttp
from aiohttp import web

from connect_mysql import init_async_pool, close_async_pool
from web_commands import process_tbzone_order
import manage_mods
import go
import golog


HOST = "127.0.0.1"
PORT = 9000
TOKEN = os.environ.get("GUIONBOT_WEB_COMMANDS_TOKEN")


async def handle_tbzone_order(request):
    expected_token = request.app["token"]
    authorization = request.headers.get("Authorization", "")

    if not expected_token or authorization != "Bearer " + expected_token:
        return web.json_response(
            {"err_code": 401, "err_txt": "Unauthorized"},
            status=401
        )

    try:
        order_dict = await request.json()
        result = await process_tbzone_order(
            order_dict,
            request.app["http_session"]
        )
        return web.json_response(result)

    except Exception as error:
        # Do not expose internal exception details to the web client.
        golog.log("ERR", "Web command service error: " + str(error))
        return web.json_response(
            {"err_code": 500, "err_txt": "Internal server error"},
            status=500
        )


async def handle_sell_mods(request):
    expected_token = request.app["token"]
    authorization = request.headers.get("Authorization", "")

    if not expected_token or authorization != "Bearer " + expected_token:
        return web.json_response(
            {"err_code": 401, "err_txt": "Unauthorized"},
            status=401
        )

    try:
        payload = await request.json()
        ally_code = str(payload.get("allyCode", ""))
        mod_ids = payload.get("mod_ids")

        if not ally_code.isdigit() or not isinstance(mod_ids, list) or not mod_ids:
            return web.json_response(
                {"err_code": 400, "err_txt": "Invalid allyCode or mod selection"},
                status=400
            )
        if len(mod_ids) > 500 or any(
            not isinstance(mod_id, str)
            or not mod_id
            or len(mod_id) > 128
            or not all(ch.isalnum() or ch in "_-" for ch in mod_id)
            for mod_id in mod_ids
        ):
            return web.json_response(
                {"err_code": 400, "err_txt": "Invalid mod selection"},
                status=400
            )

        # Remove selected mods through the same RPC-backed function used by the bot.
        err_code, err_txt = await manage_mods.sell_mods(mod_ids, ally_code)
        if err_code != 0:
            golog.log(
                "WAR",
                "Sell mods failed for allyCode "
                + ally_code
                + " ("
                + str(len(mod_ids))
                + " selected mods): "
                + str(err_txt)
            )
            return web.json_response(
                {"err_code": int(err_code), "err_txt": str(err_txt)},
                status=400
            )

        golog.log(
            "INFO",
            "Sold "
            + str(len(mod_ids))
            + " selected mods for allyCode "
            + ally_code
        )
        return web.json_response(
            {"err_code": 0, "err_txt": "Successfully sold " + str(len(mod_ids)) + " mods."}
        )

    except Exception as error:
        golog.log("ERR", "Sell mods command error: " + str(error))
        return web.json_response(
            {"err_code": 500, "err_txt": "Internal server error"},
            status=500
        )


async def handle_deploy_tw_teams(request):
    expected_token = request.app["token"]
    authorization = request.headers.get("Authorization", "")
    if not expected_token or authorization != "Bearer " + expected_token:
        return web.json_response({"err_code": 401, "err_txt": "Unauthorized"}, status=401)

    try:
        payload = await request.json()
        guild_id = str(payload.get("guild_id", ""))
        ally_code = str(payload.get("allyCode", ""))
        teams = payload.get("teams")
        if not guild_id.isdigit() or not ally_code.isdigit():
            return web.json_response({"err_code": 400, "err_txt": "Invalid guild_id or allyCode"}, status=400)
        if not isinstance(teams, list) or not teams or len(teams) > 50:
            return web.json_response({"err_code": 400, "err_txt": "Select between 1 and 50 proposed teams"}, status=400)

        valid_zones = {"B1", "T1", "B2", "T2", "B3", "T3", "B4", "T4", "F1", "F2"}
        unit_dictionary = go.godata.get("unitsList_dict.json")
        validated_teams = []
        for team in teams:
            if not isinstance(team, dict):
                return web.json_response({"err_code": 400, "err_txt": "Invalid proposed team"}, status=400)
            zone = team.get("zone")
            units = team.get("units")
            if not isinstance(zone, str) or zone not in valid_zones:
                return web.json_response({"err_code": 400, "err_txt": "Invalid zone in proposed team"}, status=400)
            max_units = 8 if zone in {"F1", "F2"} else 5
            if not isinstance(units, list) or not 1 <= len(units) <= max_units:
                return web.json_response({"err_code": 400, "err_txt": "Invalid unit count in proposed team"}, status=400)
            if any(not isinstance(unit_id, str) or not unit_id or len(unit_id) > 64
                   or not all(ch.isalnum() or ch in "_-" for ch in unit_id)
                   for unit_id in units) or len(set(units)) != len(units):
                return web.json_response({"err_code": 400, "err_txt": "Invalid or duplicate unit in proposed team"}, status=400)
            if any(unit_id not in unit_dictionary for unit_id in units):
                return web.json_response({"err_code": 400, "err_txt": "A proposed team contains an unknown unit ID"}, status=400)
            # The web planner sends canonical SWGOH unit IDs. Resolve them to names
            # before calling deploy_def_tw(), which accepts character aliases.
            character_names = [unit_dictionary[unit_id]["name"] for unit_id in units]
            validated_teams.append((zone, character_names))

        completed = 0
        for zone, characters in validated_teams:
            err_code, err_txt = await go.deploy_def_tw(guild_id, ally_code, zone, characters)
            if err_code != 0:
                golog.log("WAR", "TW team deployment failed for allyCode " + ally_code + " in zone " + zone + ": " + str(err_txt))
                return web.json_response({
                    "err_code": int(err_code), "err_txt": str(err_txt),
                    "completed": completed, "failed_zone": zone
                }, status=400)
            completed += 1
            golog.log("INFO", "Deployed proposed TW team for allyCode " + ally_code + " in zone " + zone
                      + " (" + str(len(characters)) + " units)")

        return web.json_response({
            "err_code": 0,
            "err_txt": "Successfully deployed " + str(completed) + " proposed team(s).",
            "completed": completed
        })
    except Exception as error:
        golog.log("ERR", "Deploy TW teams command error: " + str(error))
        return web.json_response({"err_code": 500, "err_txt": "Internal server error"}, status=500)


async def on_startup(app):
    if not app["token"]:
        raise RuntimeError("GUIONBOT_WEB_COMMANDS_TOKEN is not configured")

    await init_async_pool()
    app["http_session"] = aiohttp.ClientSession()


def create_app():
    app = web.Application()
    app["token"] = TOKEN
    app.router.add_post("/TBzoneOrder", handle_tbzone_order)
    app.router.add_post("/SellMods", handle_sell_mods)
    app.router.add_post("/DeployTWTeams", handle_deploy_tw_teams)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


async def on_cleanup(app):
    session = app.get("http_session")
    if session is not None:
        await session.close()

    await close_async_pool()


if __name__ == "__main__":
    web.run_app(
        create_app(),
        host=HOST,
        port=PORT
    )
