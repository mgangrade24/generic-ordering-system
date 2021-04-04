from flask import Flask, render_template, request, session, logging, url_for, redirect, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from passlib.hash import sha256_crypt
from datetime import date
import time
from flask_mail import Mail, Message

app = Flask(__name__)

app.secret_key = '12345'


# configuration of mail
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'mgangrade24@gmail.com'
app.config['MAIL_PASSWORD'] = 'Dhanraj@123'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)




#database connection details
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'register'

# Intialize MySQL
mysql = MySQL(app)


@app.route("/")
def home():
    return render_template("home.html")

# register
@app.route("/register", methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm = request.form['confirm']
        secure_password = sha256_crypt.hash(str(password))

        if password == confirm and 'name' in request.form and 'password' in request.form and 'email' in request.form and 'phone' in request.form and 'confirm' in request.form:
            # Check if account exists using MySQL
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            account = cursor.fetchone()
            # If account exists show error and validation checks
            if account:
                flash("Account already exists!","danger")
                return render_template('register.html')
            else:
                #if account is new
                cursor.execute('INSERT INTO users VALUES (NULL, %s, %s, %s, %s)', (name, email, phone, secure_password))
                mysql.connection.commit()
                flash("Registration Successfull. You can login now!","success")
                return redirect(url_for('login'))

        else:
            flash("Password doesn't match or the fields are empty. Try again!","danger")
            return render_template('register.html')

    return render_template("register.html")

#login
@app.route("/login",methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        secure_password = sha256_crypt.hash(str(password))

        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        # Fetch one record and return result
        account = cursor.fetchone()
        

        # If account exists in accounts table in our database
        if account:
            if sha256_crypt.verify(password,account['password']):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account['id']
                session['email'] = account['email']
                session['phone'] = account['phone']
                session['name'] = account['name']
                # Redirect to home page
                
                return redirect(url_for('order'))
            else:
                #Incorrect
                flash("Invalid Credentials!","danger")
                return render_template("login.html")

            
        else:
            # Account doesnt exist
            flash("No such user!","danger")
            return render_template("login.html")

        
    return render_template("login.html")

@app.route("/order",methods=['GET','POST'])
def order():
    # Check if user is loggedin
    if 'loggedin' in session:
        if request.method == 'POST':

            fname = request.form['fname']
            lname = request.form['lname']
            name = fname + " " + lname
            quant = request.form['quant']
            streetadd = request.form['streetadd']
            streetadd2 = request.form['streetadd2']
            city = request.form['city']
            zip = request.form['zip']
            region = request.form['region']
            country = request.form['country']
            
            t = time.localtime()
            current_time = time.strftime("%H:%M", t)
            today = date.today()
            d2 = today.strftime("%B %d, %Y")
            datetimenow = current_time + " " + d2

            total = int(quant) * 45
            tax = total * 0.18
            grandtotal = total + tax

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO orders VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s, %s, %s, %s)', (name, quant, streetadd, streetadd2, city, zip, region, country, session['id'], total, tax, grandtotal, datetimenow))
            
            mysql.connection.commit()

            return redirect(url_for('shipping'))
        # User is loggedin show them the home page
        return render_template('order.html', name=session['name'],)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route("/shipping",methods=['GET','POST'])
def shipping():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * from orders WHERE orderid=(SELECT MAX(orderid) FROM orders);')
        orderdetails = cursor.fetchone()
        cursor.execute('SELECT * from users where id = %s;',(session['id'],))
        userdetails = cursor.fetchone()
        if request.method == 'POST':
            cursor.execute('UPDATE orders SET payment=TRUE WHERE orderid=%s;',(orderdetails['orderid'],))
            mysql.connection.commit()

            msg = Message(
                "Order Confirm",
                sender ='mgangrade24@gmail.com',
                recipients = [userdetails['email']]
               )
            msg.body = "Hello " + userdetails['name'] + "\nYour order for biodiesel is confirmed."+"\n\nShipped to: "+orderdetails['name']+"\n\nAddress: "+orderdetails['streetadd']+", "+orderdetails['streetadd2']+"\n"+orderdetails['city']+" "+orderdetails['zip']+"\n"+orderdetails['region']+", "+orderdetails['country']+"\n\nQuantity: "+str(orderdetails['quant'])+" Litres"+"\n"+"Total Ammount Paid (Inclusive of 18% GST): $"+str(orderdetails['grandtotal'])
            
            mail.send(msg)

            flash("Order Successfull ! A confirmation mail has been sent to you.","success")
            return redirect(url_for('orders'))
    return render_template("shipping.html",orderdetails=orderdetails, userdetails=userdetails,)

@app.route("/orders")
def orders():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * from orders WHERE custid=%s ORDER BY orderid DESC',(session['id'],))
        orders = cursor.fetchall()
        cursor.execute('SELECT * from users where id = %s;',(session['id'],))
        userdetails = cursor.fetchone()
        return render_template("orders.html",orders=orders, userdetails=userdetails,)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route("/support",methods = ['GET', 'POST'])
def support():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
      
        cursor.execute('SELECT * from users where id = %s;',(session['id'],))
        userdetails = cursor.fetchone()
        

        if request.method == 'POST':
            subject = request.form['subject']
            query = request.form['query']

            cursor.execute('INSERT INTO query VALUES (NULL, %s, %s, %s, %s, %s, %s)', (session['id'], subject, query, session['name'], userdetails['email'], userdetails['phone'],))
            mysql.connection.commit()

            msg = Message(
                subject,
                sender =userdetails['email'],
                recipients = ['mgangrade24@gmail.com']
               )
            msg.body = query + "\n[Sender : " + userdetails['name'] + " | Email : " + userdetails['email'] + " | Phone : " + userdetails['phone'] + " ]"
            mail.send(msg)

            flash("Your query has been sent!","success")
            return redirect(url_for('support'))
        return render_template("support.html",userdetails=userdetails,)



    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/login/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('name', None)
   # Redirect to login page
   flash("You are now logged out!","success")
   return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
