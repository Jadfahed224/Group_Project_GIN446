"""Database models: user accounts and their favorite Pokémon (proposal, section 9)."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
 id = db.Column(db.Integer, primary_key=True)
 email = db.Column(db.String(120), unique=True, nullable=False)
 password_hash = db.Column(db.String(255), nullable=False) 
 created_at = db.Column(db.DateTime, server_default=db.func.now()) 
 favorites = db.relationship("Favorite", backref="user",cascade="all, delete-orphan")


class Favorite(db.Model):
 id = db.Column(db.Integer, primary_key=True)
 user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
 pokemon_id = db.Column(db.Integer, nullable=False) 
 pokemon_name = db.Column(db.String(100), nullable=False) 
 sprite_url = db.Column(db.String(500)) 
 saved_at = db.Column(db.DateTime, server_default=db.func.now())
 __table_args__ = (db.UniqueConstraint("user_id", "pokemon_id",name="uniq_user_pokemon"),)
