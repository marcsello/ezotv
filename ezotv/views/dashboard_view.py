#!/usr/bin/env python3
from flask import request, abort, render_template, current_app, redirect, url_for, flash
from flask_classful import FlaskView, route

from flask_login import login_required, current_user, logout_user
import sqlalchemy.exc

from flask_dance.contrib.discord import discord
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError, TokenExpiredError
import requests.exceptions

from utils import RSA512SALTED_hash
from model import db, NameStatus, NameChange
from schemas import MinecraftFormSchema

from marshmallow import ValidationError
from discordbot_tools import discord_bot


class DashboardView(FlaskView):

    route_prefix = "/dashboard/"
    route_base = '/'

    minecraft_form_schema = MinecraftFormSchema(many=False)

    def loginfo(self):
        if current_user.is_authenticated:
            return redirect(url_for("DashboardView:index"))
        return render_template('loginfo.html')

    @route("/logout", methods=['POST'])  # POST to prevent redirect attack.... altrough not very good solution
    @login_required
    def logout(self):
        logout_user()
        # TODO: revoke token???? Lehet ez nem kell
        return redirect(url_for("DashboardView:loginfo"))

    @login_required  # redirects to loginfo
    def index(self):

        try:
            r = discord.get("/api/users/@me")
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError):
            flash("Nem sikerült kommunikálni a Discord szervereivel", "danger")
            logout_user()
            return redirect(url_for("DashboardView:loginfo"))
        except (InvalidGrantError, TokenExpiredError):
            # flash("Kérlek jelentkezz be újra!", "warning")  # Mert a flask dance egy büdös buzi, és szarul van implementálva benne a refresh token magic
            logout_user()
            return redirect(url_for("DashboardView:loginfo"))

        user_extra = {
            "discord_tag": "{}#{}".format(r.json()['username'], r.json()['discriminator'])
        }

        return render_template('dashboard.html', user_extra=user_extra)

    @login_required
    def post(self):  # Using the Post-Redirect-Get pattern

        form_raw_data = dict(request.form)

        # check validity
        try:
            form_data = self.minecraft_form_schema.dump(  # mer' ez így jó
                self.minecraft_form_schema.load(form_raw_data)
            )
        except ValidationError as e:
            flash("Hiba a bevitt adatokban!", "danger")  # Akinek nincs HTML5 kompatibilis böngészője, az ott bassza meg
            return redirect(url_for("DashboardView:index"))

        # Check for name change
        if form_data['minecraft_name'] != current_user.minecraft_name:

            NameChange.query.filter(db.and_(NameChange.user == current_user, NameChange.active == True)).delete()  # Invalidate all previous requests
            change_object = NameChange(old_name=current_user.minecraft_name, user=current_user, active=True)

            current_user.minecraft_name = form_data['minecraft_name']
            current_user.name_status = NameStatus.CHANGED

            db.session.add(change_object)

        # Hash password for AuthMe RSA512SALTED format
        password_hashed, password_salt = RSA512SALTED_hash(form_data['password'])

        current_user.password = password_hashed
        current_user.salt = password_salt

        del form_data

        # Commit changes
        current_user.in_sync = False
        db.session.add(current_user)
        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError as e:
            flash("Ilyen névvel már létezik regisztráció!", "danger")
            return redirect(url_for("DashboardView:index"))

        flash("Adatok elmentve!", "info")

        if current_user.name_status == NameStatus.CHANGED:
            discord_bot.instance.post_log(f"New administraion event!\nName {current_user.minecraft_name} is waiting for approval.")

        return redirect(url_for("DashboardView:index"))
