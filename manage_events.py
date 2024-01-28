import connect_mysql
import goutils

def exists(type, guild_id, id):
    query = "SELECT timestamp FROM events WHERE type='"+type+"' AND guild_id='"+guild_id+"' AND event_id='"+id+"'"
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_value(query)
    event_exists = (db_data!=None)
    return (event_exists)

def create_event(type, guild_id, id):
    query = "INSERT INTO events(type, guild_id, event_id) VALUES('"+type+"', '"+guild_id+"', '"+id+"')"
    goutils.log2("DBG", query)
    connect_mysql.simple_execute(query)
