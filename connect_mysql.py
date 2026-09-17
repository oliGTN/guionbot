import os
import config
import sys
from urllib.parse import uses_netloc, urlparse
from mysql.connector import MySQLConnection, Error, connect as mysql_connect
from mysql.connector.aio import connect as mysql_async_connect
import datetime
import time
from wcwidth import wcswidth
import asyncio
from decimal import Decimal
from hashlib import md5
from json import dumps as json_dumps

def wc_ljust(text, length):
    return text + ' ' * max(0, length - wcswidth(text))

import goutils
import data

mysql_db = None


from contextvars import ContextVar

# ---------------------------------------------------------------------------
# Legacy synchronous connection
# ---------------------------------------------------------------------------
mysql_db = None

# ---------------------------------------------------------------------------
# Async connection pool
# ---------------------------------------------------------------------------
# Keep this modest. Your Discord loop can have more tasks than this, but only
# ASYNC_MYSQL_POOL_SIZE DB operations can hold a MySQL connection at once.
ASYNC_MYSQL_POOL_SIZE = 5

_async_pool = None
_async_pool_init_lock = asyncio.Lock()
_async_current_connection = ContextVar("mysql_async_current_connection", default=None)
_async_connection_tokens = {}


async def init_async_pool(pool_size=ASYNC_MYSQL_POOL_SIZE):
    """Create the async MySQL connection pool.

    Safe to call more than once. Prefer calling this once during bot startup.
    """
    global _async_pool

    if _async_pool is not None:
        return

    async with _async_pool_init_lock:
        if _async_pool is not None:
            return

        uses_netloc.append("mysql")
        url = urlparse(config.MYSQL_DATABASE_URL)

        connection_kwargs = {
            "host": url.hostname,
            "database": url.path[1:],
            "user": url.username,
            "password": url.password,
            # mysql.connector.aio currently requires the pure-Python
            # implementation.
            "use_pure": True,
            "ssl_disabled": True,
        }

        # urlparse() gives None when the URL has no explicit port.
        if url.port is not None:
            connection_kwargs["port"] = url.port

        goutils.log2(
            "INFO",
            f"Creating async MySQL pool with {pool_size} connections"
        )

        connections = await asyncio.gather(
            *(mysql_async_connect(**connection_kwargs) for _ in range(pool_size))
        )

        # Queue stores currently available connections.
        pool = asyncio.Queue(maxsize=pool_size)
        for connection in connections:
            await pool.put(connection)

        _async_pool = pool


async def adb_connect():
    """Acquire an async MySQL connection.

    If the current coroutine already owns a connection (for example
    update_player() calling get_value_async()), the same connection is reused.
    This preserves transaction visibility and avoids accidentally using a
    second connection inside an active transaction.
    """
    current = _async_current_connection.get()
    if current is not None:
        return current

    if _async_pool is None:
        await init_async_pool()

    connection = await _async_pool.get()
    token = _async_current_connection.set(connection)

    # Keep the ContextVar token separately. Some connector objects do not
    # allow arbitrary attributes.
    _async_connection_tokens[id(connection)] = token
    return connection


async def release_async_connection(connection):
    """Return a connection acquired by adb_connect() to the pool."""
    if connection is None or _async_pool is None:
        return

    token = _async_connection_tokens.pop(id(connection), None)

    try:
        # Roll back anything accidentally left open.
        try:
            if getattr(connection, "in_transaction", False):
                await connection.rollback()
        except Exception:
            pass

        await _async_pool.put(connection)
    except Exception as error:
        # If the connection cannot be returned, close it and create a
        # replacement so the pool does not permanently lose a slot.
        goutils.log2("ERR", "Error returning MySQL connection to pool: " + str(error))
        try:
            await connection.close()
        except Exception:
            pass

        try:
            url = urlparse(config.MYSQL_DATABASE_URL)
            kwargs = {
                "host": url.hostname,
                "database": url.path[1:],
                "user": url.username,
                "password": url.password,
                "use_pure": True,
                "ssl_disabled": True,
            }
            if url.port is not None:
                kwargs["port"] = url.port
            replacement = await mysql_async_connect(**kwargs)
            await _async_pool.put(replacement)
        except Exception as replacement_error:
            goutils.log2(
                "ERR",
                "Unable to replace MySQL connection: " + str(replacement_error)
            )

    if token is not None:
        try:
            _async_current_connection.reset(token)
        except Exception:
            pass


async def close_async_pool():
    """Close all async MySQL connections.

    Call this once when the bot shuts down.
    """
    global _async_pool

    if _async_pool is None:
        return

    while not _async_pool.empty():
        connection = await _async_pool.get()
        try:
            await connection.close()
        except Exception:
            pass

    _async_pool = None


async def simple_execute_async(query, params=None):
    """Execute one INSERT/UPDATE/DELETE/DDL statement asynchronously."""
    connection = None
    cursor = None
    owns_connection = _async_current_connection.get() is None
    row_count = 0

    try:
        connection = await adb_connect()

        cursor = await connection.cursor()
        await cursor.execute(query, params)
        row_count = cursor.rowcount
        await connection.commit()

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        raise

    finally:
        if cursor is not None:
            try:
                await cursor.close()
            except Exception:
                pass

        if owns_connection and connection is not None:
            await release_async_connection(connection)

    return row_count

async def executemany_async(query, params_list):
    """Execute one INSERT/UPDATE/DELETE statement for many rows asynchronously."""
    connection = None
    cursor = None
    owns_connection = _async_current_connection.get() is None
    row_count = 0

    try:
        connection = await adb_connect()

        cursor = await connection.cursor()
        await cursor.executemany(query, params_list)
        row_count = cursor.rowcount
        await connection.commit()

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        raise

    finally:
        if cursor is not None:
            try:
                await cursor.close()
            except Exception:
                pass

        if owns_connection and connection is not None:
            await release_async_connection(connection)

    return row_count


async def _execute_read_async(query, params=None):
    """Internal read helper returning all rows."""
    connection = None
    cursor = None
    owns_connection = False

    try:
        current = _async_current_connection.get()
        if current is None:
            connection = await adb_connect()
            owns_connection = True
        else:
            connection = current

        cursor = await connection.cursor(buffered=True)
        await cursor.execute(query, params)
        return await cursor.fetchall()

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        raise

    finally:
        if cursor is not None:
            try:
                await cursor.close()
            except Exception:
                pass

        if owns_connection and connection is not None:
            await release_async_connection(connection)


async def get_value_async(query, params=None):
    rows = await _execute_read_async(query, params)
    if not rows:
        return None
    return rows[0][0]


async def get_column_async(query, params=None):
    rows = await _execute_read_async(query, params)
    return [row[0] for row in rows]


async def get_line_async(query, params=None):
    rows = await _execute_read_async(query, params)
    return rows[0] if rows else None


async def get_table_async(query, params=None):
    rows = await _execute_read_async(query, params)
    return rows if rows else None


async def text_query_async(query, params=None):
    """Async replacement for text_query().

    Connector/Python 9.2+ no longer uses execute(..., multi=True). For the
    normal single-statement SELECTs used by this bot, one result set is enough.
    """
    rows = []
    cursor = None
    connection = None
    owns_connection = False

    try:
        current = _async_current_connection.get()
        if current is None:
            connection = await adb_connect()
            owns_connection = True
        else:
            connection = current

        cursor = await connection.cursor(buffered=True)
        await cursor.execute(query, params)

        if cursor.with_rows:
            fetch_results = await cursor.fetchall()

            if fetch_results:
                widths = []
                columns = []
                tavnit = "|"
                separator = "+"

                for index, cd in enumerate(cursor.description):
                    max_col_length = max(
                        wcswidth(str(row[index])) for row in fetch_results
                    )
                    widths.append(max(max_col_length, wcswidth(cd[0])))
                    columns.append(cd[0])

                for width in widths:
                    tavnit += " %-" + "%s.%ss |" % (width, width)
                    separator += "-" * width + "--+"

                rows.append(separator)
                rows.append(tavnit % tuple(columns))
                rows.append(separator)

                for fetch in fetch_results:
                    row = "|"
                    for index, value in enumerate(fetch):
                        row += " " + wc_ljust(str(value), widths[index]) + " |"
                    rows.append(row)

                rows.append(separator)

        return rows

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        return [error]

    finally:
        if cursor is not None:
            try:
                await cursor.close()
            except Exception:
                pass

        if owns_connection and connection is not None:
            await release_async_connection(connection)


def db_connect():
    global mysql_db
    #mysql_db = None
    if mysql_db == None or not mysql_db.is_connected():
        if mysql_db == None:
            goutils.log2("INFO", "First connection to mysql")
        else:
            goutils.log2("INFO", "Close connection to mysql")
            mysql_db.close()
            goutils.log2("INFO", "New connection to mysql")
            
        # Recover DB information from URL
        uses_netloc.append('mysql')
        try:
            url = urlparse(config.MYSQL_DATABASE_URL)
        except Exception:
            goutils.log2("ERR", 'Unexpected error in connect:', sys.exc_info())
            return
        
        # Connect to DB
        mysql_db = None
        try:
            goutils.log2("INFO", 'Connecting to MySQL database...')
            mysql_db = mysql_connect(host=url.hostname,
                                     database=url.path[1:],
                                     user=url.username,
                                     password=url.password)
            if mysql_db.is_connected():
                # print('Connected to MySQL database')
                pass
            else:
                goutils.log2("ERR", 'Connection failed')

        except Error as e:
            goutils.log2("ERR", 'Exception during connect: '+str(e))
            
    return mysql_db
        
########################################
def text_query(query):
    rows = []
    cursor = None

    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)
        
        cursor.execute(query)
        results = cursor.fetchall()
        if len(results) >0:
            widths = []
            columns = []
            tavnit = '|'
            separator = '+' 
        
            index = 0
            for cd in cursor.description:
                #print("results: "+str(results))
                max_col_length = max(list(map(lambda x: wcswidth(str(x[index])), results)))
                widths.append(max(max_col_length, wcswidth(cd[0])))
                columns.append(cd[0])
                index+=1

            for w in widths:
                tavnit += " %-"+"%s.%ss |" % (w,w)
                separator += '-'*w + '--+'

            rows.append(separator)
            rows.append(tavnit % tuple(columns))
            rows.append(separator)

            for result in results:
                index=0
                row = "|"
                for value in result:
                    row += " " + wc_ljust(str(value), widths[index]) + " |"
                    index+=1
                rows.append(row)

            rows.append(separator)
        
        mysql_db.commit()
    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        rows=[error]
        
    finally:
        if cursor != None:
            cursor.close()
    
    return rows
        
        
def simple_execute(query):
    cursor = None
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)
        #print("simple_callproc: "+proc_name+" "+str(args))
        ret=cursor.execute(query)
        
        mysql_db.commit()
    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()

def simple_callproc(proc_name, args):
    rows = []
    cursor = None
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)
        #print("simple_callproc: "+proc_name+" "+str(args))
        ret=cursor.callproc(proc_name, args)
        #print(ret)
        
        mysql_db.commit()
    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()

def get_value(query):
    cursor = None
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)
        
        cursor.execute(query)
        results = cursor.fetchall()

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()
    
    if len(results) > 0:
        return results[0][0]
    else:
        return None
        
def get_column(query):
    cursor = None
    try:
        mysql_db = db_connect()
        #print("DBG: mysql_db="+str(mysql_db))
        cursor = mysql_db.cursor(buffered=True)
        #print("DBG: cursor="+str(cursor))
        
        cursor.execute(query)
        results = cursor.fetchall()

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()
    return [x[0] for x in results]
    
def get_line(query):
    cursor = None
    #print("get_line("+query+")")
    try:
        mysql_db = db_connect()
        #print("DBG: mysql_db="+str(mysql_db))
        cursor = mysql_db.cursor(buffered=True)
        #print("DBG: cursor="+str(cursor))
        
        cursor.execute(query)
        results = cursor.fetchall()

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()
    
    if len(results) == 0:
        return None
    else:
        return results[0]
    
def get_table(query):
    cursor = None
    try:
        #print("DBG: get_table db_connect")
        mysql_db = db_connect()
        #print("DBG: get_table cursor")
        #print("DBG: mysql_db="+str(mysql_db))
        cursor = mysql_db.cursor(buffered=True)
        #print("DBG: cursor="+str(cursor))

        # print("DBG: get_table execute "+query)
        cursor.execute(query)
        results = cursor.fetchall()

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()

    #print("DBG: get_table return")
    if len(results) == 0:
        return None
    else:
        return results

async def insert_roster_evo(allyCode, defId, evo_txt):

    #adapt syntax ty MYSQL
    evo_txt = evo_txt.replace("'","''")

    if defId!=None:
        query = "INSERT INTO roster_evolutions(allyCode, defId, description) "\
               +"VALUES("+str(allyCode)+", '"+str(defId)+"', '"+evo_txt+"')"
    else:
        query = "INSERT INTO roster_evolutions(allyCode, description) "\
               +"VALUES("+str(allyCode)+", '"+evo_txt+"')"
    goutils.log2("DBG", query)
    await simple_execute_async(query)

