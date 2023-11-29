from time import sleep
import mysql.connector

class mysqlPool:
    def __init__(self, user, password, dbName, host="127.0.0.1", logFile="mysqllogs", errorWriter=None):
        self.connections = []
        self.user = user
        self.host = host
        self.password = password
        self.dbName = dbName
        self.logFile = logFile
        self.errorWriter = errorWriter if errorWriter is not None else self.defaultErrorWriter


    def checkDatabaseStructure(self):
        pass


    def defaultErrorWriter(self, category:str, text:str, extras:str="", log:bool=True):
        string = f"[MYSQL POOL] [{category}]: {text} {extras}"
        print(string)
        if log:
            open(self.logFile, "a").write(string + "\n")


    def execute(self, syntax: str, commitRequired: bool, ignoreErrors: bool=True, dbRequired: bool=True)->None|list:
        destroyConnection = commitRequired
        while True:
            try:
                if not dbRequired:
                    connection = mysql.connector.connect(user=self.user, host=self.host, password=self.password)
                    destroyConnection = True
                elif self.connections:
                    connection = self.connections.pop()
                else:
                    connection = mysql.connector.connect(user=self.user, host=self.host, password=self.password, database=self.dbName)
                break
            except Exception as e:
                self.errorWriter("CONNECTION FAIL", repr(e))
                sleep(1)
        cursor = connection.cursor()
        data = None
        try:
            cursor.execute(syntax)
            if commitRequired:
                connection.commit()
            data = cursor.fetchall()
        except Exception as e:
            destroyConnection = True
            self.errorWriter("EXCEPTION", repr(e))
            if ignoreErrors:
                pass
            else:
                raise e
        if destroyConnection:
            connection.close()
        else:
            self.connections.append(connection)
        return data
