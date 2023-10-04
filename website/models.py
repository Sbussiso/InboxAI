from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func


#users will eventually be able to create and store notes
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    notes = db.relationship('Note')


class Email(db.Model):
    id = db.Column(db.String(50), primary_key=True) #Gmail API ID
    sender = db.Column(db.String(100))
    receiver = db.Column(db.String(100))
    subject = db.Column(db.String(100))
    content = db.Column(db.Text)
    date = db.Column(db.DateTime)
    gpt_response = db.Column(db.Text)
    token_size = db.Column(db.Integer)

    #to display database contents 
    def to_dict(self):
            return {
                'id': self.id,
                'sender': self.sender,
                'receiver': self.receiver,
                'subject': self.subject,
                'content': self.content,
                'date': self.date.isoformat() if self.date else None,  # Convert date to string
                'gpt_response': self.gpt_response,
                'token_size': self.token_size
            }



#chatbot and user conversation history
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    role = db.Column(db.String(10))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }



class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    key = db.Column(db.String(64), nullable=False)
