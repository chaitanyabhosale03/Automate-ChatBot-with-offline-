from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_socketio import SocketIO, emit
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import openai
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/virtual_bpo'
app.config['JWT_SECRET_KEY'] = 'your_secret_key'
app.config['MAIL_SERVER'] = 'smtp.example.com'  # Configure mail server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@example.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins='*')
mail = Mail(app)

# Define User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='customer')

# Define Ticket Model
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default='open')

# User Registration Route
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    hashed_password = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password=hashed_password, role=data.get('role', 'customer'))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'})

# User Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        token = create_access_token(identity={'id': user.id, 'role': user.role})
        return jsonify({'access_token': token})
    return jsonify({'message': 'Invalid credentials'}), 401

# Create Ticket Route
@app.route('/create_ticket', methods=['POST'])
@jwt_required()
def create_ticket():
    data = request.json
    current_user = get_jwt_identity()
    new_ticket = Ticket(user_id=current_user['id'], subject=data['subject'])
    db.session.add(new_ticket)
    db.session.commit()
    
    # Send email notification
    msg = Message("New Ticket Created", sender=app.config['MAIL_USERNAME'], recipients=['support@example.com'])
    msg.body = f"User {current_user['id']} created a new ticket: {data['subject']}"
    mail.send(msg)
    
    return jsonify({'message': 'Ticket created successfully'})

# Update Ticket Status (Admin/Agent only)
@app.route('/update_ticket/<int:ticket_id>', methods=['PUT'])
@jwt_required()
def update_ticket(ticket_id):
    data = request.json
    current_user = get_jwt_identity()
    
    if current_user['role'] not in ['admin', 'agent']:
        return jsonify({'message': 'Unauthorized'}), 403
    
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'message': 'Ticket not found'}), 404
    
    ticket.status = data['status']
    db.session.commit()
    
    # Send email notification
    msg = Message("Ticket Status Updated", sender=app.config['MAIL_USERNAME'], recipients=['customer@example.com'])
    msg.body = f"Your ticket has been updated to: {data['status']}"
    mail.send(msg)
    
    return jsonify({'message': 'Ticket updated successfully'})

# Chatbot Integration (OpenAI API)
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data['message']
    response = openai.ChatCompletion.create(
        model='gpt-4',
        messages=[{"role": "user", "content": user_message}]
    )
    return jsonify({'response': response['choices'][0]['message']['content']})

# WebSocket for Real-time Chat
@socketio.on('send_message')
def handle_message(data):
    emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    db.create_all()
    socketio.run(app, debug=True)
