#!/usr/bin/env python3
from .db import db
from sqlalchemy.sql import func


class Player(db.Model):

    # Identification
    id = db.Column(db.Integer, primary_key=True, auto_increment=True)
    name = db.Column(db.String(50), unique=False, nullable=False)

    # Important data
    minecraft_name = db.Column(db.String(16), unique=True, nullable=False)

    password = db.Column(db.String(255), unique=False, nullable=False)
    salt = db.Column(db.String(50), unique=False, nullable=False)

    email = db.Column(db.String(500), unique=False, nullable=False)
    discord_id = db.Column(db.String(32), unique=True, nullable=False)

    # administrative
    registered = db.Column(db.TIMESTAMP, nullable=False, server_default=func.now())