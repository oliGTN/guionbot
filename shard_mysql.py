import goutils

from connect_mysql import (
    get_line,
    simple_execute,
    get_value_async,
    get_table_async,
    text_query,
)


async def get_shard_from_player(txt_allyCode, shard_type):
    # test if the shard already exists
    query = "SELECT "+shard_type+"Shard_id, name, guildName " \
          + "FROM players " \
          + "WHERE allyCode='"+txt_allyCode+"'"
    goutils.log2("DBG", query)
    existingShard, name, guildName = get_line(query)
    if existingShard == None:
        # If the player has no shard, create one and allocate it to him or her
        query = "INSERT INTO shards(type) "\
               +"VALUES('"+shard_type+"')"
        goutils.log2("DBG", query)
        simple_execute(query)

        query = "SELECT MAX(id) FROM shards"
        goutils.log2("DBG", query)
        new_shard = await get_value_async(query)

        query = "UPDATE players "\
               +"SET "+shard_type+"Shard_id="+str(new_shard)+" " \
               +"WHERE allyCode="+txt_allyCode
        goutils.log2("DBG", query)
        simple_execute(query)

        return new_shard, name, guildName
    else:
        return existingShard, name, guildName


async def get_shard_list(shard_id, shard_type, txt_mode):
    query = "SELECT allyCode, name, guildName, arena_"+shard_type+"_rank, " \
          + "time('01-01-01 19:00:00' - interval poUTCOffsetMinutes minute) as 'PO_utc' " \
          + "FROM players " \
          + "WHERE "+shard_type+"Shard_id="+str(shard_id)+" "\
          + "ORDER BY arena_"+shard_type+"_rank, name"
    goutils.log2("DBG", query)
    if txt_mode:
        return text_query(query)
    else:
        return await get_table_async(query)


async def add_player_to_shard(txt_allyCode, target_shard, shard_type, force_merge):
    player_existing_shard, name, guildName = await get_shard_from_player(txt_allyCode, shard_type)

    if player_existing_shard == target_shard:
        #Already in the good shard
        return 0, "Joueur "+txt_allyCode+" ("+name+" @ "+guildName+") déjà dans le shard", None
    else:
        #player already in another shard
        player_shard_size = len(await get_shard_list(player_existing_shard, shard_type, False))
        if player_shard_size == 1:
            #The player is alone in its own shard
            # set the shard for this player
            query = "UPDATE players "\
                   +"SET "+shard_type+"Shard_id="+str(target_shard)+" " \
                   +"WHERE allyCode="+txt_allyCode
            goutils.log2("DBG", query)
            simple_execute(query)

            # delete the previous shard of the player
            query = "DELETE FROM shards " \
                   +"WHERE id="+str(player_existing_shard)
            goutils.log2("DBG", query)
            simple_execute(query)

            return 0, "Joueur "+txt_allyCode+" ("+name+" @ "+guildName+") ajouté au shard", None

        target_shard_size = len(await get_shard_list(target_shard, shard_type, False))
        if target_shard_size == 1 or force_merge:
            #If the requesting player (me) is alone in its shard
            # replace the target shard by the shard of the player
            query = "UPDATE players "\
                   +"SET "+shard_type+"Shard_id="+str(player_existing_shard)+" " \
                   +"WHERE "+shard_type+"Shard_id="+str(target_shard)
            goutils.log2("DBG", query)
            simple_execute(query)

            # delete the target shard
            query = "DELETE FROM shards " \
                   +"WHERE id="+str(target_shard)
            goutils.log2("DBG", query)
            simple_execute(query)

            return 0, "Joueur "+txt_allyCode+" ("+name+" @ "+guildName+") ajouté au shard", None

        #target shard and shard from player are both filled with several players
        # need to merge them with confirmation from player
        return 1, "", [target_shard, player_existing_shard]
