from flask import Flask, render_template, request, session, redirect, jsonify
from werkzeug.utils import secure_filename
from flask_mysqldb import MySQL
from flask_session import Session
from better_profanity import profanity
from uuid import uuid4
import helpers.dbfunc as dbf
from helpers.filters import nl2br, text_filters
from PIL import Image
import random
import hashlib
import datetime
import time
import html
import os

UPLOAD_FOLDER = os.getcwd() + '/pfps'
UPLOAD_FOLDER = UPLOAD_FOLDER.replace(os.sep, '/')
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.secret_key = "sevenSeasBroughtTogetherForIceCream"
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'superbarreldb'
app.config['MYSQL_CHARSET'] = 'utf8mb4'
app.config['MYSQL_COLLATION'] = 'utf8mb4_unicode_ci'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql = MySQL(app)

app.jinja_env.filters['nl2br'] = nl2br
app.jinja_env.filters['text_filters'] = text_filters

# https://github.com/snguyenthanh/better_profanity/blob/master/better_profanity/profanity_wordlist.txt
custom_curse_words = [
   'shit',
   'fuck'
]
profanity.load_censor_words(custom_curse_words)

@app.errorhandler(404)
def not_found(e):
   title = "404"
   return render_template('404.html', title=title, error="We couldn't find that page.")

@app.errorhandler(500)
def server_error(e):
   title = "Server error"
   return render_template('error.html', title=title, error=e)

# 403 here (CHECK AGAIN IF WORKS)
@app.errorhandler(403)
def forbidden(e):
   title = "403 Forbidden"
   return render_template('error.html', title=title, error="That page is hidden from the public.")

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
   cursor.execute('''SELECT profiles.username, profiles.is_verified, profiles.is_mod, profiles.ppic, posts.id, title, timestamp FROM profiles, posts WHERE profiles.id = user_id AND type=1 ORDER BY timestamp DESC LIMIT 10''')
   mysql.connection.commit()
   data = cursor.fetchall()
   cursor.close()
   return render_template('forum.html', data=data, get_post_time=get_post_time, limit_char=limit_char)

@app.route('/forum/universities')
def universities():
   msg = ""
   if not session.get("token"):
      msg = "Log in to connect with students from your university."
   return render_template('universities.html', msg=msg)

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
   cursor.execute('''INSERT INTO posts (posts.user_id, posts.type, posts.title, posts.descr, posts.timestamp) SELECT %s, %s, %s, %s, %s WHERE NOT EXISTS (SELECT * FROM posts where posts.title=%s AND posts.user_id=%s AND posts.type=%s);''', 
   (session['id'], 1, title, content, int(time.time()), title, session['id'], 1))
   mysql.connection.commit()
   # if post with the same title already exists
   if cursor.rowcount == 0:
      return render_template('create.html', msg="Post with the same title already exists. Please try another title for your post.")
   cursor.close()
   return redirect('/forum')

@app.route('/forum/latest')
def latest():
   cursor = mysql.connection.cursor()
   cursor.execute('''SELECT profiles.username, profiles.is_verified, profiles.is_mod, profiles.ppic, posts.id, title, descr, timestamp FROM profiles, posts WHERE profiles.id=user_id AND type=1 ORDER BY timestamp DESC LIMIT 10''')
   mysql.connection.commit()
   data = cursor.fetchall()
   cursor.close()
   return render_template('latest.html', data=data, get_post_time=get_post_time, limit_char=limit_char)

@app.route('/forum/<id>/<page>')
def forum_page(id=None, page=None):
   try:
      if page == None or id == None:
         return redirect('/404')
      else:
         if not session.get("id"):
            session_id = 0
         else:
            session_id = session['id']

         cursor = mysql.connection.cursor()
         cursor.execute(
         '''
            SELECT profiles.username, profiles.is_verified, profiles.is_mod, profiles.ppic, posts.id, title, descr, timestamp FROM profiles, posts WHERE profiles.id=posts.user_id AND posts.id=%s AND REPLACE(posts.title, ' ', '-')=%s
            UNION ALL SELECT COUNT(*), NULL, NULL, NULL, NULL, NULL, NULL, NULL FROM posts WHERE posts.type=2 AND posts.post_id=%s
            UNION ALL SELECT COUNT(*), NULL, NULL, NULL, NULL, NULL, NULL, NULL FROM posts WHERE posts.type=2 AND posts.post_id=%s AND posts.user_id=%s
            UNION ALL SELECT COUNT(*), NULL, NULL, NULL, NULL, NULL, NULL, NULL FROM posts WHERE posts.type=3 AND posts.post_id=%s;
         ''', 
         ([int(id), str(page), int(id), int(id), session_id, int(id)]))
         mysql.connection.commit()
         data = cursor.fetchall()
         if data == None:
            return redirect('/404')
         cursor.execute('''SELECT profiles.username, profiles.is_verified, profiles.is_mod, profiles.ppic, posts.id, posts.descr, posts.timestamp FROM profiles, posts WHERE profiles.id=posts.user_id AND posts.type=3 AND posts.post_id=%s ORDER BY posts.timestamp DESC LIMIT 6;''',
         ([int(id)]))
         
         comments = cursor.fetchall()
         cursor.close()
         return render_template('post.html', data=data, comments=comments, get_post_time=get_post_time)
   except Exception as e:
      return render_template('error.html', title="Error.", error=e)

@app.route('/profile/<username>')
def profile(username=None):
   if username == None:
      return redirect('/404')
   else:
      cursor = mysql.connection.cursor()
      cursor.execute('''SELECT id, username, ppic, is_verified, is_mod, bio, reg_date, instagram, twitter, github, linkedin, is_banned FROM profiles WHERE username=%s;''', ([username]))
      mysql.connection.commit()
      data = cursor.fetchone()
      if data == None:
         return redirect('/404')
      else:
         cursor.execute('''SELECT COUNT(*) FROM posts WHERE posts.user_id=%s AND posts.type=1''', ([data[0]]))
         mysql.connection.commit()
         stats = cursor.fetchall()
         cursor.close()
         return render_template('profile.html', data=data, stats=stats, get_post_time=get_post_time)

#-----------------AUTH-----------------#
@app.route('/login')
def login():
   if not session.get("token"):
      referrer = request.referrer
      return render_template('login.html', ref=referrer)
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
      cursor.execute('''SELECT id, username, is_banned, is_verified, is_mod, ppic FROM profiles WHERE email=%s AND pwd=%s or username=%s AND pwd=%s''',
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
         session['ppic'] = success[5]
         referrer = request.args.get('ref')
         if referrer == None:
            return redirect('/')
         elif "hackbeast.org" not in referrer:
            return redirect('/')
         else:
            return redirect(referrer)
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
         cursor.execute(''' INSERT INTO profiles (id, name, username, email, pwd, ip_address, last_ip) VALUES(%s, %s, %s, %s, %s, %s, %s)''', 
         (''.join((random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890') for i in range(8))), name, username, email, pwd, ip_address, ip_address))
         try:
            mysql.connection.commit()
         except mysql.IntegrityError:
            return render_template("error.html", error="Uh oh, something went wrong in our system.")
         finally:
            cursor.close()
            return render_template("login.html", msg="Account created! Please login to continue.", type="success")

# -----------------API-----------------#
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
@app.route('/api/v1/<post_id>/<post_type>/<action>', methods=['POST'])
def api_forum(post_id=None, post_type=None, action=None):
   response = ""
   # user must be logged in
   if not session.get("token") and action != "c-c":
      return "You must be logged in to perform this action."
   if post_id==None or post_type==None or action==None:
      return "Invalid request", 400
   # Like functionality
   cursor = mysql.connection.cursor()
   if action == "l":
      cursor.execute('''INSERT INTO posts (posts.post_id, posts.user_id, posts.type, timestamp) SELECT %s, %s, %s, %s WHERE NOT EXISTS (SELECT * FROM posts where posts.post_id=%s AND posts.user_id=%s AND posts.type=%s);''', 
      (post_id, session['id'], post_type, int(time.time()), post_id, session['id'], post_type))
   # Unlike functionality
   elif action == "u":
      cursor.execute('''DELETE FROM posts WHERE posts.post_id=%s AND posts.user_id=%s AND posts.type=%s;''', 
      (post_id, session['id'], post_type))
   # Comment functionality
   elif action == "c":
      post_content = profanity.censor(request.form['content'])
      cursor.execute('''INSERT INTO posts (posts.post_id, posts.user_id, posts.type, posts.descr, timestamp) VALUES(%s, %s, %s, %s, %s);''',
      (post_id, session['id'], post_type, post_content, int(time.time())))
   # Get comments
   elif action == "c-c":
      cursor.execute('''SELECT profiles.username, profiles.is_verified, profiles.is_mod, profiles.ppic, posts.id, posts.descr, posts.timestamp FROM profiles, posts WHERE profiles.id=posts.user_id AND posts.type=3 AND posts.post_id=%s ORDER BY posts.timestamp DESC LIMIT 6 OFFSET %s;''',
      ([post_id, int(request.form['last_id'])]))
      response = cursor.fetchall()
      response = [list(i) for i in response]
      for i in response:
         i[6] = get_post_time(i[6])
      response = [tuple(i) for i in response]
   # Delete post
   elif action == "d":
      cursor.execute('''DELETE FROM posts WHERE posts.id=%s AND posts.user_id=%s AND posts.type=%s;''', 
      (post_id, session['id'], post_type))
   # Profile picture
   elif action == "p":
      if 'file' not in request.files:
         return "No file part", 400
      file = request.files['file']
      if file.filename == '':
         return "No selected file", 400
      if file and allowed_file(file.filename):
         filename = secure_filename(str(uuid4()) + "." + file.filename.split(".")[1])
         file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
         cursor.execute('''UPDATE profiles SET ppic=%s WHERE id=%s;''', 
         ([app.config['UPLOAD_FOLDER'] + "/" + filename, post_id]))
         session['ppic'] = app.config['UPLOAD_FOLDER'] + "/" + filename

         # strip metadata
         img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
         data = list(img.getdata())
         img_without_exif = Image.new(img.mode, img.size)
         img_without_exif.putdata(data)
         img_without_exif.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
   # Edit profile
   elif action == "ed-p":
      username = request.form['lmao'].lower()
      bio = profanity.censor(request.form['what'])
      instagram = request.form['are']
      twitter = request.form['you']
      github = request.form['looking']
      linkedin = request.form['at']
      if 0 < len(username) <= 16:
         if dbf.check_user_exists(cursor=cursor, username=username) and session['uname'] != username:
            return "Username already taken"
         else:
            cursor.execute('''UPDATE profiles SET username=%s, bio=%s, instagram=%s, twitter=%s, github=%s, linkedin=%s WHERE id=%s;''',
            ([username, bio, instagram, twitter, github, linkedin, post_id]))
            session['uname'] = username
      else:
         return "Invalid username"
   # Reply to comments
   elif action == "r":
      post_content = profanity.censor(request.form['content'])
      cursor.execute('''INSERT INTO posts (posts.post_id, posts.user_id, posts.type, posts.descr, timestamp) VALUES(%s, %s, %s, %s, %s);''',
      (post_id, session['id'], post_type, post_content, int(time.time())))
   # Get replies
   elif action == "r-c":
      cursor.execute('''SELECT profiles.username, profiles.is_verified, profiles.is_mod, profiles.ppic, posts.id, posts.descr, posts.timestamp FROM profiles, posts WHERE profiles.id=posts.user_id AND posts.type=4 AND posts.post_id=%s ORDER BY posts.timestamp DESC LIMIT 6 OFFSET %s;''',
      ([post_id, int(request.form['last_id'])]))
      response = cursor.fetchall()
      response = [list(i) for i in response]
      for i in response:
         i[6] = get_post_time(i[6])
      response = [tuple(i) for i in response]
   cursor.close()

   try:
      mysql.connection.commit()
   except mysql.IntegrityError:
      return "Error", 500
   finally:
      cursor.close()
      if (action == "c-c"):
         return jsonify(response)
      elif (action == "r-c"):
         return jsonify(response)
      else:
         return "OK", 200

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