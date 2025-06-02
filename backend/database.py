import pyodbc

def get_connection():
    return pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=localhost;'
        'DATABASE=powerbi;'
        'Trusted_Connection=yes;'
    )