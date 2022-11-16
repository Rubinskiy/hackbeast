from flask import Flask, render_template, request, session, redirect
from flask_mysqldb import MySQL
from flask_session import Session
from better_profanity import profanity
from uuid import uuid4
import helpers.dbfunc as dbf
import hashlib
import datetime
import time

app = Flask(__name__)
app.secret_key = "myBbyIsASuperCutePumpkinPie"
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'superbarreldb'
mysql = MySQL(app)

# https://github.com/snguyenthanh/better_profanity/blob/master/better_profanity/profanity_wordlist.txt
custom_curse_words = [
   'areole', 
   'arian',
   'aryan',
   'asanchez',
   ''
]
profanity.load_censor_words(custom_curse_words)

@app.errorhandler(404)
def not_found(e):
   title = "404"
   return render_template('404.html', title=title, error=e)

@app.route('/')
def home():
   msg = ""
   if not session.get("token"):
      msg = "Not logged in."
   return render_template('index.html', msg=msg)

# -----------------FORUM-----------------#
@app.route('/forum')
def forum():
   cursor = mysql.connection.cursor()
   cursor.execute('''SELECT profiles.username, profiles.is_verified, profiles.is_mod, profiles.ppic, post_id, title, timestamp FROM profiles, posts WHERE profiles.id = user_id AND type=1 ORDER BY timestamp DESC LIMIT 6''')
   mysql.connection.commit()
   data = cursor.fetchall()
   return render_template('forum.html', data=data, get_post_time=get_post_time, limit_char=limit_char)
   cursor.close()

@app.route('/forum/create')
def create():
   msg = ""
   if not session.get("token"):
      return redirect('/login')
   return render_template('create.html')
@app.route('/post-content', methods=['POST'])
def create_post():
   if not session.get("token"):
      return redirect('/login')
   title = profanity.censor(request.form['title'])
   content = profanity.censor(request.form['content'])
   cursor = mysql.connection.cursor()
   cursor.execute('''INSERT INTO posts (user_id, type, title, descr, timestamp) VALUES (%s, %s, %s, %s, %s)''', 
   (session['id'], 1, title, content, int(time.time())))
   mysql.connection.commit()
   cursor.close()
   return redirect('/forum')

@app.route('/forum/latest')
def latest():
   cursor = mysql.connection.cursor()
   cursor.execute('''SELECT profiles.username, profiles.is_verified, profiles.is_mod, profiles.ppic, post_id, title, descr, timestamp FROM profiles, posts WHERE profiles.id=user_id AND type=1 ORDER BY timestamp DESC LIMIT 10''')
   mysql.connection.commit()
   data = cursor.fetchall()
   return render_template('latest.html', data=data, get_post_time=get_post_time, limit_char=limit_char)
   cursor.close()

@app.route('/forum/<id>/<page>')
def forum_page(id=None, page=None):
   if page == None or id == None:
      return redirect('/forum')
   else:
      cursor = mysql.connection.cursor()
      cursor.execute('''SELECT profiles.username, profiles.is_verified, profiles.is_mod, profiles.ppic, post_id, title, descr, timestamp FROM profiles, posts WHERE profiles.id=user_id AND post_id=%s AND REPLACE(posts.title, ' ', '-')=%s;''', 
      ([int(id), str(page)]))
      mysql.connection.commit()
      data = cursor.fetchone()
      if data == None:
         return redirect('/404')
      return render_template('post.html', data=data, get_post_time=get_post_time)
      cursor.close()
   return page

#-----------------AUTH-----------------#
@app.route('/login')
def login():
   if not session.get("token"):
      return render_template('login.html')
   return redirect("/")
@app.route('/register')
def register():
   if not session.get("token"):
      return render_template('register.html')
   return redirect("/")
@app.route('/logout')
def logout():
   session.clear()
   return redirect(request.referrer)

@app.route('/authlog', methods = ['POST'])
def authlog():
   if request.method == 'POST':
      unem = request.form['unem']
      pwd = request.form['pwd']
      pwd = hashlib.sha256(pwd.encode('utf-8')).hexdigest()
      cursor = mysql.connection.cursor()
      cursor.execute('''SELECT id, username, is_banned, is_verified, is_mod FROM profiles WHERE email=%s AND pwd=%s or username=%s AND pwd=%s''',
      ([unem], [pwd], [unem], [pwd]))
      mysql.connection.commit()
      success = cursor.fetchone()
      if success:
         if success[2] == 1:
            return render_template('login.html', msg="<strong>Your account has been banned indefinitely</strong>.<span style=\"display:block;\"></span>Please <a href=\"#\" class=\"one\">contact us</a> for more information.")
         session['token'] = uuid4()
         session['id'] = success[0]
         session['uname'] = success[1]
         session['verified'] = success[3]
         session['mod'] = success[4]
         return redirect('/')
      else:
         return render_template('login.html', msg="Invalid Email/Username or Password.")
      cursor.close()
   return render_template("login.html")

@app.route('/authreg', methods = ['POST'])
def authreg():
   cursor = mysql.connection.cursor()
   if request.method == 'POST':
      if dbf.check_user_exists(cursor=cursor, username=request.form['uname']):
         return "User already exists"
      elif dbf.check_email_exists(cursor=cursor, email=request.form['email']):
         return "Email already exists"
      else:
         name = request.form['name']
         username = request.form['uname']
         email = request.form['email']
         pwd = request.form['pwd']
         pwd = hashlib.sha256(pwd.encode('utf-8')).hexdigest()
         ip_address = request.remote_addr
         cursor.execute(''' INSERT INTO profiles (name, username, email, pwd, ip_address, last_ip) VALUES(%s, %s, %s, %s, %s, %s)''', 
         (name, username, email, pwd, ip_address, ip_address))
         try:
            mysql.connection.commit()
         except mysql.IntegrityError:
            return render_template("error.html", error="Uh oh, something went wrong in our system.")
         finally:
            cursor.close()
            return render_template("login.html", msg="Account created successfully! Please login to continue.", type="success")



'''def post_request():
    headers = {"X-API-Key" : api_key, "Content-Type" : "application/json"}
    data = {"item" : {"name" : "test", "age" : 20}}
    response = requests.post(api_route, data=data, headers=headers)'''

# -----------------FUNCTIONS-----------------#
def limit_char(text, limit=50, ext="..."):
   if len(text) > limit:
      return text[:limit] + ext
   return text

def get_post_time(postTimestamp):
   time1 = datetime.datetime.fromtimestamp(postTimestamp)
   time2 = datetime.datetime.fromtimestamp(int(time.time()))
   timeDiff = time2 - time1

   sec = int(timeDiff.total_seconds())
   min = int(timeDiff.total_seconds() / 60)
   hr = int(timeDiff.total_seconds() / 3600)
   day = int(timeDiff.total_seconds() / 86400)
   mon = int(timeDiff.total_seconds() / 2592000)
   yr = int(timeDiff.total_seconds() / 31536000)

   if yr > 0:
      return f"{yr}yr ago"
   elif mon > 0:
      return f"{mon}mon ago"
   elif day > 0:
      return f"{day}d ago"
   elif hr > 0:
      return f"{hr}h ago"
   elif min > 0:
      return f"{min}m ago"
   elif sec > 0:
      return f"{sec}s ago"
   else:
      return "Just now"

if __name__ == '__main__':
   app.run(port=8000, debug=True)