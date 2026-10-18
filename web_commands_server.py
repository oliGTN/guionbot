import os

import aiohttp
from aiohttp import web

from connect_mysql import init_async_pool, close_async_pool
from web_commands import process_tbzone_order
import manage_mods
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
