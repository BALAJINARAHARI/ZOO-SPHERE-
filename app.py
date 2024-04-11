import os
from flask import Flask, render_template, request, redirect, session,send_file
 

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt
from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.orm.exc import NoResultFound
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask_mail import Mail, Message






app = Flask(__name__)
mail = Mail(app)
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@example.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
app.secret_key = 'secret_key'


class Events_fl(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), nullable=False)
  date = db.Column(db.Date, nullable=False)
  location = db.Column(db.String(100), nullable=False)
  capacity = db.Column(db.Integer, nullable=False)
  price = db.Column(db.Integer, nullable=False)
  tickets_sold = db.Column(db.Integer, default=0)

  def __init__(self, name, date, location, capacity,price):
      self.name = name
      self.date = date
      self.location = location
      self.capacity = capacity
      self.price = price

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    reset_token = db.Column(db.String(100))
  
    def __init__(self,email,password,name):
        self.name = name
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self,password):
        return bcrypt.checkpw(password.encode('utf-8'),self.password.encode('utf-8'))

with app.app_context():
    db.create_all()
    db.session.commit()






@app.route('/register', methods=['GET', 'POST'])
def register():
      if request.method == 'POST':
          name = request.form['name']
          email = request.form['email']
          password = request.form['password']

          existing_user = Users.query.filter_by(email=email).first()
          if existing_user:
              flash('An account with this email already exists. Please use a different email.', 'error')
              return redirect(url_for('register'))

          new_user = Users(name=name, email=email, password=password)
          db.session.add(new_user)
          db.session.commit()
          flash('Registration successful. You can now log in.', 'success')
          return redirect('/login')

      return render_template('register.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = Users.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['email'] = user.email
            return redirect('/home')
        else:
            return render_template('login.html',error='Invalid user')

    return render_template('login.html')



@app.route('/add_events', methods=['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = datetime.strptime(request.form['event_date'], '%Y-%m-%d').date()
        event_location = request.form['event_location']
        event_capacity = int(request.form[
            'event_capacity'])
        event_price = int(request.form['event_price'])

        try:
            new_event = Events_fl(name=event_name, date=event_date, location=event_location, capacity=event_capacity, price=event_price)
            db.session.add(new_event)
            db.session.commit()
            return redirect(url_for('manage_events'))  # Redirect to manage events after adding an event
        except Exception as e:
            return f"An error occurred: {str(e)}"
    else:
        return render_template('add_events.html')

@app.route('/manage_events',methods=['GET','POST'])
def manage_events():
    try:
      # Fetch all events from the database
      events = Events_fl.query.all()
      return render_template('manage_events.html', events=events)
    except Exception as e:
          return f"An error occurred: {str(e)}"



@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if request.method == 'POST':
        event = Events_fl.query.get(event_id)
        event.name = request.form['event_name']
        event.date = datetime.strptime(request.form['event_date'], '%Y-%m-%d').date()
        event.location = request.form['event_location']
        event.capacity = int(request.form['event_capacity'])
        event.price = int(request.form['event_price'])

        try:
            db.session.commit()
            return redirect(url_for('manage_events'))  # Redirect to manage events after editing
        except Exception as e:
            return f"An error occurred: {str(e)}"
    else:
        event = Events_fl.query.get(event_id)
        return render_template('edit_event.html', event=event)

@app.route('/delete_event/<int:event_id>', methods=['GET', 'POST'])
def delete_event(event_id):
    if request.method == 'POST':
        try:
            # Find the event to delete
            event = Events_fl.query.get(event_id)
            if event:
                # Delete the event from the database
                db.session.delete(event)
                db.session.commit()
                flash('Event deleted successfully', 'success')
            else:
                flash('Event not found', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

        return redirect(url_for('manage_events'))
    else:
        event = Events_fl.query.get(event_id)
        return render_template('delete_event.html', event=event)

@app.route('/logout')
def logout():
    session.pop('email',None)
    return redirect('/login')

@app.route("/")
def index():
  return render_template("index.html")
@app.route('/sell_tickets', methods=['POST'])
def sell_tickets():
    # Get form data
    customer_name = request.form['customer_name']
    event_id = request.form['event_id']
    num_tickets = int(request.form['num_tickets'])

    # Query the event from the database
    event = Events_fl.query.get(event_id)

    if event:
        # Check if enough tickets are available for sale
        if num_tickets <= event.capacity - event.tickets_sold:
            # Update tickets sold
            event.tickets_sold += num_tickets
            db.session.commit()

            # Generate PDF ticket
            pdf_file_path = generate_pdf_ticket(event, customer_name, num_tickets)

            # Send the PDF file to the client as an attachment
            return send_file(pdf_file_path, as_attachment=True, mimetype='application/pdf', download_name=f'ticket_{event.id}.pdf')
        else:
            flash('Not enough tickets available for sale!', 'error')
    else:
        flash('Event not found!', 'error')

    # Redirect to sales page in case of error
    return redirect(url_for('sales'))

@app.route("/sales")
def sales():
    events = Events_fl.query.all()
    return render_template("sales.html", events=events)
  
  
@app.route('/settings', methods=['GET', 'POST'])
def settings():
     

      if request.method == 'POST':
          new_password = request.form['password']

          if not new_password:
              flash('Please enter a new password.', 'error')
              return redirect(url_for('settings'))

          # Retrieve the user from the database
          user = Users.query.filter_by(email=session['email']).first()

          if user:
              # Update the user's password
              user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
              db.session.commit()
              flash('Password changed successfully!', 'success')
          else:
              flash('User not found.', 'error')

      return render_template('settings.html')




@app.route("/home")
def home():
  return render_template("home.html")
@app.route("/events")
def events():
  return render_template("events.html")
  
def generate_pdf_ticket(event, customer_name, num_tickets):
  # Specify the directory to save PDF tickets
  ticket_dir = os.path.join(os.getcwd(), 'tickets')

  # Create directory if it doesn't exist
  if not os.path.exists(ticket_dir):
      os.makedirs(ticket_dir)

  # Generate the file path
  pdf_file = os.path.join(ticket_dir, f'ticket_{event.id}.pdf')

  # Create a canvas to draw the PDF
  c = canvas.Canvas(pdf_file, pagesize=letter)
  c.drawString(100, 750, f'Event: {event.name}')
  c.drawString(100, 730, f'Location: {event.location}')
  c.drawString(100, 710, f'Customer Name: {customer_name}')
  c.drawString(100, 690, f'Number of Tickets: {num_tickets}')
  c.drawString(100, 670, f'Total Cost: ${event.price * num_tickets}')

  # Add other ticket details as needed
  c.save()

  print(f'PDF saved at: {pdf_file}')  # Debug statement

  # Return the file path
  return pdf_file
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate a unique password reset token (you can use UUID or any other method)
            token = generate_reset_token()
            user.reset_token = token
            db.session.commit()
            # Send reset password email with token
            send_reset_email(user)
            flash('An email with instructions for resetting your password has been sent.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email address not found.', 'error')
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['POST'])
def reset_password():
    token = request.form['token']
    new_password = request.form['password']
    # Verify the token and update the user's password in the database
    if verify_password_reset_token(token):
        user = get_user_from_token(token)
        user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.session.commit()
        flash('Password reset successfully.', 'success')
    else:
        flash('Invalid or expired token.', 'error')
    return redirect(url_for('login'))




def send_reset_email(user):
    reset_link = url_for('reset_password', token=user.reset_token, _external=True)
    msg = Message('Password Reset Instructions', recipients=[user.email])
    msg.html = render_template('reset_password_email.html', reset_link=reset_link)
    mail.send(msg)

if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True)