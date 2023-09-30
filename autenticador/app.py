from flask import Flask, request, jsonify, make_response
import uuid # for public id
from  werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
# imports for PyJWT authentication
import jwt
from datetime import datetime, timedelta
from functools import wraps

# creates Flask object
app = Flask(__name__)

app.config['SECRET_KEY'] = 'your secret key'

def getUsers( user = None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    if user:
        q = f"SELECT * FROM users WHERE users.name = '{user}'"
        cursor.execute(q)
        rows = cursor.fetchall()

    else:
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def create_users_table():
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                password TEXT,
                public_id  TEXT
            );
        ''')
        conn.commit()
        conn.close()
        print(f"Created Sucessfully 'users' table")
    except Exception as e:
        print(f"Error encountered while creating the 'users' table: {str(e)}")
            
# decorator for verifying the JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # jwt is passed in the request header
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        # return 401 if token is not passed
        if not token:
            return jsonify({'message' : 'Token is missing !!'}), 401

        try:
            # decoding the payload to fetch the stored details
            print('token', token)
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            users = getUsers()
            print('users', users)
            current_user = list(filter(lambda x: x[3  ] == data['public_id'], users))
        except Exception as e:
            print(f'{e = }')
            return jsonify({
                'message' : f'Token is invalid !!'
            }), 401
        # returns the current logged in users context to the routes
        return  f(current_user, *args, **kwargs)
  
    return decorated
  
# User Database Route
# this route sends back list of users
@app.route('/user', methods =['GET'])
@token_required
def get_all_users(current_user):
    # querying the database
    # for all the entries in it
    users = getUsers()
    # converting the query objects
    # to list of jsons
    output = [{
            'public_id': user[3],
            'name' : user[1]
        } for user in users]
    # for user in users:
    #     # appending the user data json
    #     # to the response list
    #     output.append({
    #         'public_id': user[3],
    #         'name' : user[1]
    #     })
  
    return jsonify({'users': output})
  
# route for logging user in
@app.route('/login', methods =['POST'])
def login():
    auth = request.get_json()
    print(auth)
  
    if not auth or not auth.get('password'):
        # returns 401 if any email or / and password is missing
        return make_response(
            'Could not verify',
            401,
            {'WWW-Authenticate' : 'Basic realm ="Login required !!"'}
        )
    
    user =  getUsers(auth.get('name'))
  
    if not user:
        # returns 401 if user does not exist
        return make_response(
            'Could not verify',
            401,
            {'WWW-Authenticate' : 'Basic realm ="User does not exist !!"'}
        )
    
    user = user[0]
    
    print(user[2], auth.get('password'))

    if check_password_hash(user[2], auth.get('password')):
        # generates the JWT Token
        token = jwt.encode({
            'public_id': user[3],
            'exp' : datetime.utcnow() + timedelta(minutes = 30)
        }, app.config['SECRET_KEY'])
  
        return make_response(jsonify({'token' : token}), 201)
    # returns 403 if password is wrong
    return make_response(
        'Could not verify',
        403,
        {'WWW-Authenticate' : 'Basic realm ="Wrong Password !!"'}
    )
  
# signup route
@app.route('/signup', methods =['POST'])
def signup():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # gets name, email and password
    data = request.get_json()
    name = data.get('name')
    password = data.get('password')
    rows = getUsers()
    
    if not list(filter(lambda x: x[1]  == name, rows)):
        query = "INSERT INTO users (name, password, public_id) VALUES (?, ?, ?)"
        values = (name, generate_password_hash(password),  str(uuid.uuid4()))
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return make_response('Successfully registered.', 201)
    else:
        cursor.close()
        conn.close()
        return make_response('User already exists. Please Log in.', 202)
  
if __name__ == "__main__":
    # setting debug to True enables hot reload
    # and also provides a debugger shell
    # if you hit an error while running the server
    create_users_table()
    app.run(debug = True)