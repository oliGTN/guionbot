import os
import re

import aiohttp
from aiohttp import web

from connect_mysql import init_async_pool, close_async_pool
import update_mysql
from web_commands import process_tbzone_order
import manage_mods
import go
import connect_rpc
import data as godata
import golog
from json import dumps as json_dumps


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


async def handle_tb_mapstats(request):
    expected_token = request.app["token"]
    authorization = request.headers.get("Authorization", "")
    if not expected_token or authorization != "Bearer " + expected_token:
        return web.json_response(
            {"err_code": 401, "err_txt": "Unauthorized"},
            status=401
        )

    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            return web.json_response(
                {"err_code": 400, "err_txt": "JSON body must be an object"},
                status=400
            )

        guild_id = payload.get("guild_id")
        if not isinstance(guild_id, str) or not guild_id.isdigit() or not 1 <= len(guild_id) <= 24:
            return web.json_response(
                {"err_code": 400, "err_txt": "Invalid guild_id"},
                status=400
            )

        # Fetch current TB mapstats through the existing RPC layer. Keep the
        # RPC mechanics and diagnostics behind this internal command endpoint.
        err_code, err_txt, mapstats = await connect_rpc.get_TBmapstats_data(
            guild_id, False
        )
        if err_code != 0:
            golog.log(
                "WAR",
                "Unable to retrieve TB mapstats for guild " + guild_id
                + "; internal_err_code=" + str(err_code)
                + "; internal_err_txt=" + str(err_txt)
            )
            return web.json_response(
                {"err_code": 502, "err_txt": "Unable to retrieve TB mapstats"},
                status=502
            )

        if not isinstance(mapstats, (dict, list)):
            golog.log("ERR", "TB mapstats RPC returned an unexpected data type for guild " + guild_id)
            return web.json_response(
                {"err_code": 502, "err_txt": "Invalid TB mapstats response"},
                status=502
            )

        return web.json_response({
            "success": True,
            "mapstats": mapstats
        })

    except Exception as error:
        golog.log("ERR", "TB mapstats command error: " + str(error))
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
        if not ally_code.isdigit():
            return web.json_response({"err_code": 400, "err_txt": "Invalid allyCode"}, status=400)
        if not isinstance(teams, list) or not teams or len(teams) > 50:
            return web.json_response({"err_code": 400, "err_txt": "Select between 1 and 50 proposed teams"}, status=400)

        valid_zones = {"B1", "T1", "B2", "T2", "B3", "T3", "B4", "T4", "F1", "F2"}
        validated_teams = []
        for team in teams:
            if not isinstance(team, dict):
                return web.json_response({"err_code": 400, "err_txt": "Invalid proposed team"}, status=400)
            zone_name = team.get("zone")
            unit_ids = team.get("units")
            datacron_id = team.get("datacronId") or ""
            if not isinstance(zone_name, str) or zone_name not in valid_zones:
                return web.json_response({"err_code": 400, "err_txt": "Invalid zone in proposed team"}, status=400)
            # SWGOH datacron IDs are 16-byte URL-safe Base64 values (22 chars, no padding).
            if not isinstance(datacron_id, str) or (datacron_id and
                    (len(datacron_id) != 22 or not all(ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for ch in datacron_id))):
                return web.json_response({"err_code": 400, "err_txt": "Invalid datacron ID in proposed team"}, status=400)
            if zone_name in {"F1", "F2"} and datacron_id:
                return web.json_response({"err_code": 400, "err_txt": "Datacrons cannot be deployed with fleet teams"}, status=400)
            zone_id = godata.dict_tw.get(zone_name)
            if not zone_id:
                return web.json_response({"err_code": 400, "err_txt": "Unknown TW zone: " + zone_name}, status=400)
            max_units = 8 if zone_name in {"F1", "F2"} else 5
            if not isinstance(unit_ids, list) or not 1 <= len(unit_ids) <= max_units:
                return web.json_response({"err_code": 400, "err_txt": "Invalid unit count in proposed team"}, status=400)
            if any(not isinstance(unit_id, str) or not unit_id or len(unit_id) > 64
                   or not all(ch.isalnum() or ch in "_-" for ch in unit_id)
                   for unit_id in unit_ids) or len(set(unit_ids)) != len(unit_ids):
                return web.json_response({"err_code": 400, "err_txt": "Invalid or duplicate unit ID in proposed team"}, status=400)
            validated_teams.append({
                "zone_id": zone_id,
                "requested_defIds": unit_ids,
                "datacron_id": datacron_id or None,
            })

        err_code, err_txt, completed, latestTWstatus = await connect_rpc.deploy_tw(
            guild_id, ally_code, validated_teams
        )
        if err_code != 0:
            return web.json_response({
                "err_code": int(err_code), "err_txt": str(err_txt),
                "completed": int(completed)
            }, status=400)

        #Update TW data in DB thanks to returned TW status
        tw = latestTWstatus['territoryWarStatus'][0]
        tw_id = tw['instanceId']
        opp_guild_name = tw["awayGuild"]["profile"]["name"]
        opp_guild_id = tw["awayGuild"]["profile"]["id"]
        score = sum([int(x['zoneStatus']['score']) \
                     for x in tw['homeGuild']['conflictStatus']])
        opp_score = sum([int(x['zoneStatus']['score']) \
                         for x in tw['awayGuild']['conflictStatus']])
        currentRound = tw["currentRound"]

        dict_guild = {'profile':{'id': guild_id}} | latestTWstatus

        ret = await connect_rpc.get_tw_status(guild_id, 0, dict_guild=dict_guild)

        homeGuild = ret['homeGuild']
        awayGuild = ret['awayGuild']

        await update_mysql.update_tw(guild_id, tw_id, opp_guild_id,
                                      opp_guild_name, score, opp_score,
                                      currentRound,
                                      homeGuild, awayGuild)


        return web.json_response({
            "err_code": 0,
            "err_txt": "Successfully deployed " + str(completed) + " proposed team(s).",
            "completed": int(completed)
        })
    except Exception as error:
        golog.log("ERR", "Deploy TW teams command error: " + str(error))
        return web.json_response({"err_code": 500, "err_txt": "Internal server error"}, status=500)


async def handle_deploy_tb_platoons(request):
    expected_token = request.app["token"]
    authorization = request.headers.get("Authorization", "")
    if not expected_token or authorization != "Bearer " + expected_token:
        return web.json_response({"err_code": 401, "err_txt": "Unauthorized"}, status=401)

    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            return web.json_response({"err_code": 400, "err_txt": "JSON body must be an object"}, status=400)
        phase = payload.get("phase")
        ally_code = payload.get("ally_code")
        planets = payload.get("planets")

        if type(phase) is not int or phase not in range(1, 7):
            return web.json_response({"err_code": 400, "err_txt": "Invalid phase"}, status=400)
        if not isinstance(ally_code, str) or not ally_code.isdigit() or len(ally_code) != 9:
            return web.json_response({"err_code": 400, "err_txt": "Invalid ally_code"}, status=400)
        if not isinstance(planets, dict) or not planets or len(planets) > 50:
            return web.json_response({"err_code": 400, "err_txt": "Invalid or empty planets object"}, status=400)

        # Build groups in input order. Ordered dict semantics preserve the first
        # occurrence of each (zone_id, squad_id), as well as each unit's order.
        groups = {}
        total_units = 0
        for planet_name, planet in planets.items():
            if not isinstance(planet_name, str) or not isinstance(planet, dict):
                return web.json_response({"err_code": 400, "err_txt": "Invalid planet entry"}, status=400)

            zone_id_input = planet.get("zone_id")
            zone_match = re.fullmatch(r"P([0-9]{1,2})-C([0-9]{1,2})(-B)?", zone_id_input) if isinstance(zone_id_input, str) else None
            if not zone_match:
                return web.json_response({"err_code": 400, "err_txt": "Invalid zone_id for " + planet_name}, status=400)
            phase_number, conflict_number = map(int, zone_match.groups()[:2])
            if phase_number < 1 or phase_number > 99 or conflict_number < 1 or conflict_number > 99:
                return web.json_response({"err_code": 400, "err_txt": "zone_id is out of range for " + planet_name}, status=400)
            zone_suffix = "bonus_recon01" if zone_match.group(3) == "-B" else "recon01"
            zone_id = "tb3_mixed_phase{:02d}_conflict{:02d}_{}".format(phase_number, conflict_number, zone_suffix)

            platoons = planet.get("platoons")
            if not isinstance(platoons, dict):
                return web.json_response({"err_code": 400, "err_txt": "Missing platoons object for " + planet_name}, status=400)

            platoon_strategies = planet.get("platoon_strategies")
            if not isinstance(platoon_strategies, dict):
                return web.json_response({"err_code": 400, "err_txt": "Missing platoon_strategies object for " + planet_name}, status=400)

            for platoon_number, assignments in platoons.items():
                platoon_strategy = platoon_strategies.get(str(platoon_number))
                if platoon_strategy not in ("FULL", "PRELOAD"):
                    return web.json_response({"err_code": 400, "err_txt": "Missing or invalid strategy for platoon " + str(platoon_number) + "; expected FULL or PRELOAD"}, status=400)
                if not isinstance(assignments, list):
                    return web.json_response({"err_code": 400, "err_txt": "Invalid platoon assignment list"}, status=400)
                for assignment in assignments:
                    if not isinstance(assignment, dict):
                        return web.json_response({"err_code": 400, "err_txt": "Invalid platoon assignment"}, status=400)
                    squad_id = assignment.get("squad_id")
                    unit_id = assignment.get("unit_id")
                    if not isinstance(squad_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", squad_id):
                        return web.json_response({"err_code": 400, "err_txt": "Invalid squad_id"}, status=400)
                    if not isinstance(unit_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", unit_id):
                        return web.json_response({"err_code": 400, "err_txt": "Invalid unit_id"}, status=400)

                    key = (zone_id, squad_id)
                    if key not in groups:
                        groups[key] = {
                            "zone_id": zone_id,
                            "squad_id": squad_id,
                            "planet": planet_name,
                            "platoon_strategy": platoon_strategy,
                            "requested_defIds": [],
                        }
                    elif groups[key]["platoon_strategy"] != platoon_strategy:
                        return web.json_response({"err_code": 400, "err_txt": "Conflicting platoon_strategy for the same platoon"}, status=400)
                    if unit_id in groups[key]["requested_defIds"]:
                        return web.json_response({"err_code": 400, "err_txt": "Duplicate unit_id in the same platoon"}, status=400)
                    groups[key]["requested_defIds"].append(unit_id)
                    total_units += 1
                    if total_units > 1000:
                        return web.json_response({"err_code": 413, "err_txt": "Too many unit assignments"}, status=413)

        if not groups:
            return web.json_response({"err_code": 400, "err_txt": "No platoon assignments found"}, status=400)
        if len(groups) > 200:
            return web.json_response({"err_code": 413, "err_txt": "Too many platoon groups"}, status=413)

        results = []
        succeeded = 0
        partial_count = 0
        failed_count = 0
        rpc_http_statuses = []
        for group in groups.values():
            err_code, err_txt, result = await connect_rpc.platoon_tb(
                ally_code,
                group["zone_id"],
                group["squad_id"],
                group["requested_defIds"],
                preload=(group["platoon_strategy"] == "PRELOAD"),
                round=phase,
                disable_rpc_call=False,
            )

            # Expose only the requested public outcome lists. Internal RPC
            # categories and diagnostics remain hidden from the remote client.
            if err_code in (502, 504):
                status_name = "ERROR"
                rpc_http_statuses.append(int(err_code))
                deployed_def_ids = []
                already_deployed_def_ids = []
                not_deployed_def_ids = []
            elif err_code == 2:
                golog.log("ERR", "Deploy TB platoons phase mismatch")
                return web.json_response({
                        "err_code": 409, 
                        "err_txt": "TB phase mismatch",
                        "requested_phase": phase,
                        "current_phase": result["currentRound"],
                    }, 
                    status=409)
            else:
                result_data = result if isinstance(result, dict) else {}
                deployed_set = {
                    unit_id for unit_id in result_data.get("deployed_defIds", [])
                    if isinstance(unit_id, str)
                } if isinstance(result_data.get("deployed_defIds", []), list) else set()
                already_deployed_set = {
                    unit_id for unit_id in result_data.get("alreadyDeployed_defIds", [])
                    if isinstance(unit_id, str)
                } if isinstance(result_data.get("alreadyDeployed_defIds", []), list) else set()
                not_deployed_set = {
                    unit_id for unit_id in result_data.get("playerUsed_defIds", [])
                    if isinstance(unit_id, str)
                } if isinstance(result_data.get("playerUsed_defIds", []), list) else set()

                requested_def_ids = list(group["requested_defIds"])
                deployed_def_ids = [
                    unit_id for unit_id in requested_def_ids if unit_id in deployed_set
                ]
                already_deployed_def_ids = [
                    unit_id for unit_id in requested_def_ids
                    if unit_id in already_deployed_set
                ]
                not_deployed_def_ids = [
                    unit_id for unit_id in requested_def_ids if unit_id in not_deployed_set
                ]

                confirmed_set = deployed_set | already_deployed_set
                if all(unit_id in confirmed_set for unit_id in requested_def_ids):
                    status_name = "SUCCESS"
                    succeeded += 1
                elif deployed_def_ids or already_deployed_def_ids:
                    status_name = "PARTIAL"
                    partial_count += 1
                else:
                    status_name = "FAILED"
                    failed_count += 1

            if status_name == "ERROR":
                failed_count += 1

            item = {
                "planet": group["planet"],
                "zone_id": group["zone_id"],
                "squad_id": group["squad_id"],
                "platoon_strategy": group["platoon_strategy"],
                "requested_defIds": list(group["requested_defIds"]),
                "status": status_name,
                "deployed_defIds": deployed_def_ids,
                "alreadyDeployed_defIds": already_deployed_def_ids,
                "notDeployed_defIds": not_deployed_def_ids,
            }
            results.append(item)

            if status_name != "SUCCESS":
                golog.log(
                    "WAR",
                    "TB platoon deployment outcome for allyCode " + ally_code
                    + ", zone " + group["zone_id"]
                    + ", platoon " + group["squad_id"]
                    + ": status=" + status_name
                    + ", deployed=" + str(deployed_def_ids)
                    + ", notDeployed=" + str(not_deployed_def_ids)
                    + ", internal_err_code=" + str(err_code)
                    + ", internal_err_txt=" + str(err_txt or "")
                )

        all_succeeded = succeeded == len(results)
        response = {
            "success": all_succeeded,
            "ally_code": ally_code,
            "completed": succeeded,
            "partial": partial_count,
            "failed": failed_count,
            "total": len(results),
            "results": results,
        }
        if rpc_http_statuses:
            # Prefer the gateway timeout status if any backend call timed out.
            http_status = 504 if 504 in rpc_http_statuses else 502
        else:
            http_status = 200 if all_succeeded else 207
        return web.json_response(response, status=http_status)

    except Exception as error:
        golog.log("ERR", "Deploy TB platoons command error: " + str(error))
        return web.json_response({"err_code": 500, "err_txt": "Internal server error"}, status=500)


async def on_startup(app):
    if not app["token"]:
        raise RuntimeError("GUIONBOT_WEB_COMMANDS_TOKEN is not configured")

    await init_async_pool()
    app["http_session"] = aiohttp.ClientSession()


def create_app():
    app = web.Application()
    app["token"] = TOKEN
    app.router.add_post("/TBmapstats", handle_tb_mapstats)
    app.router.add_post("/TBzoneOrder", handle_tbzone_order)
    app.router.add_post("/SellMods", handle_sell_mods)
    app.router.add_post("/DeployTWTeams", handle_deploy_tw_teams)
    app.router.add_post("/DeployTBPlatoons", handle_deploy_tb_platoons)
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
