from mysql import connector
from flask_mysqldb import MySQL



def connect_flask_mysql(flask_app:object, user:str, password:str, db_name:str, hostname:str='localhost', port=3306, *args, **kwargs) -> object:
    """Connect to mysql database using 'Flask-MySQLdb' library and return 'mysql' object (is same as connection object)"""
    flask_app.config['MYSQL_USER'] = user
    flask_app.config['MYSQL_PASSWORD'] = password
    flask_app.config['MYSQL_DB'] = db_name
    flask_app.config['MYSQL_HOST'] = hostname
    # flask_app.config['MYSQL_PORT'] = port
    # Other oprtions can be added later

    mysql = MySQL(flask_app)
    return mysql



def connect_mysql(user:str, password:str, db_name:str, hostname:str='localhost', port=3306, *args, **kwargs) -> object:
    """Connect to mysql database. returns a mysql connection object"""
    mysql = connector.connect(
        user=user,
        password=password,
        host=hostname,
        database=db_name,
        # port=port,
    )
    return mysql



def chunker(seq, size):
    """Read an iterable by chunk with arbitrary size"""
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))
