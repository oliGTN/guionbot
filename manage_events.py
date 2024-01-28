import connect_mysql
import goutils

def exists(type, id):
    query = "SELECT timestamp FROM events WHERE type='"+type+"' AND event_id='"+id+"'"
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_value(query)
    event_exists = (db_data!=None)
    return (event_exists)

def create_event(type, id):
    query = "INSERT INTO events(type, event_id) VALUES('"+type+"', '"+id+"')"
    goutils.log2("DBG", query)
    connect_mysql.simple_execute(query)
