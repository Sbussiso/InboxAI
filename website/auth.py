from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User, ApiKey
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user
from lang import check_api_key

auth = Blueprint('auth', __name__)

#login
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            #if password and hash match
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    
    return render_template("login.html", user=current_user)


#logout
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))




#sign up
@auth.route('/sign-up', methods=['GET', 'POST'])

def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        api_key = request.form.get('apiKey') # Retrieve the API key from the form

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists')
        elif len(email) < 4:
            flash("email must be greater than 4 characters", category='error')
        elif len(first_name) < 2:
            flash("First name must be greater than 1 character", category='error')
        elif password1 != password2:
            flash("Passwords do not match", category='error')
        elif len(password1) < 7:
            flash("Password must be at least 7 characters", category='error')  
        # Check if the API key is valid
        elif check_api_key(api_key) == False:
            flash("Invalid API key", category='error')
        

        else:
            #add user
            new_user = User(email=email, first_name=first_name, password=generate_password_hash(password1, method='sha256'))
            db.session.add(new_user)
            db.session.commit()

            #add user's API key
            new_api_key = ApiKey(user_id=new_user.id, key=api_key)
            db.session.add(new_api_key)
            db.session.commit()


            login_user(new_user, remember=True)
            flash("Account created!", category="success")
            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)

