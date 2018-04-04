from models import Base, User
from flask import Flask, jsonify, request, url_for, abort, g
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

# Provide basic httpauth for flask
# have to define more in @auth.verify_password
# and have to include @auth.login_required at the endpoint
from flask.ext.httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

engine = create_engine('sql:///users.db')

Base.metadata.bind = engine
DBSession = sessionmake(bind=engine)
session = DBSession()
app = Flask(__name__)

# Return true if both username and password is correct
@auth.verify_password
def verify_password(username, password):
    user = session.query(User).filter_by(username = username).first()
    if not user or not user.verify_password(password):
        return False
    g.user = user
    return True

@app.route('/users', methods=['POST'])
def new_user():
    username = request.json.get('username')
    password = request.json.get('password')
    if username is None or password is None:
        abort(400) # missing arguments
    if session.query(User).filter_by(username = username).first() is not None:
        print "existing user" # existing user
        user = session.query(User).filter_by(username = username).first()
        return jsonify({ 'message': 'user already exist' }), 200, {'Location': url_for('get_user', id = user.id, _external = True)}

    user = User(username = username)
    user.hash_password(password)
    session.add(user)
    session.commit()
    return jsonify({ 'username': user.username }), 201, {'Location': url_for('get_user', id = user.id, _external = True)}

@app.route('/api/users/<int:id>')
def get_user(id):
    user = session.query(User).filter_by(id = id).one()
    if not user:
        abort(400)
    return jsonify({'username': user.username})

@app.route('/api/resource')
@auth.login_required
def get_resource():
    return jsonify({ 'data': 'Hello, %s!' % g.user.username })

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=12345)
