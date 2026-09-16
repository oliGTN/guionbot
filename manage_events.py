import connect_mysql
import goutils

async def exists(type, guild_id, id):
    query = "SELECT timestamp FROM events WHERE type='"+type+"' AND guild_id='"+guild_id+"' AND event_id='"+id+"'"
    goutils.log2("DBG", query)
    db_data = await connect_mysql.get_value_async(query)
    event_exists = (db_data!=None)
    return (event_exists)

async def create_event(type, guild_id, id):
    query = "INSERT INTO events(type, guild_id, event_id) VALUES('"+type+"', '"+guild_id+"', '"+id+"')"
    goutils.log2("DBG", query)
    await connect_mysql.simple_execute_async(query)

    # By opportunity, delete old events (more than 6 months)
    query = "DELETE FROM events WHERE timestampdiff(DAY, timestamp, current_timestamp)>180"
    goutils.log2("DBG", query)
    await connect_mysql.simple_execute_async(query)
