def check_user_exists(cursor, username):
    cursor.execute('''SELECT * FROM profiles WHERE username = %s''', ([username]))
    if cursor.fetchone() is None:
        return False
    else:
        return True
def check_email_exists(cursor, email):
    cursor.execute('''SELECT * FROM profiles WHERE email = %s''', ([email]))
    if cursor.fetchone() is None:
        return False
    else:
        return True