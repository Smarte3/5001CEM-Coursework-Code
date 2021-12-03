from flask import Flask
import os
import sqlite3
import imghdr #Used to check what file type a given "FileStorage" class is. https://tedboy.github.io/flask/generated/generated/werkzeug.FileStorage.html
from flask import flash, session, render_template, request, redirect, url_for, escape, abort, make_response
from werkzeug.security import generate_password_hash, check_password_hash  #Used for hashing passwords.
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret key" #A key required to maintain flask session and can be used to encrypt data.

coverfolder = "/home/codio/workspace/static/images/book-images/" #The folder path for book cover images.

#Provided Code (Unedited)
def array_merge( first_array , second_array ):
	if isinstance( first_array , list ) and isinstance( second_array , list ):
		return first_array + second_array
	elif isinstance( first_array , dict ) and isinstance( second_array , dict ):
		return dict( list( first_array.items() ) + list( second_array.items() ) )
	elif isinstance( first_array , set ) and isinstance( second_array , set ):
		return first_array.union( second_array )
	return False
#---

def add_new_user(u,p): #Adds registered users to the user database.
    p = generate_password_hash(p) #Hashed the new password before adding to database
    con = sqlite3.connect('registered_users.db') # Connect to user database
    try:
      con.execute('CREATE TABLE users (name TEXT, pwd INT, isadmin BOOL, UNIQUE(name))')
    except:
      pass
    
    try:
        con.execute("INSERT INTO users values(?,?,?);", (u, p, 0)) #0=Non-admin(default), 1=Admin.
    except:
        pass
    
    con.commit() #Applys the above insert statement to the database.
    con.close()  

    return render_template('login.html',page=url_for('login'))

  
#Adapted from week 1 "Lab Activity 2" sheet
def try_login(u,p): #Compares the users details with those in the user database.
    con = sqlite3.connect('registered_users.db')
    cur = con.cursor();
    try:
      cur.execute("SELECT * FROM users WHERE name=?;", (u,)) #Searches for the input username.
      RowWithUsername = cur.fetchone() #Usernames are unique in the table so only one is fetched.
      if(RowWithUsername[0] == u and check_password_hash(RowWithUsername[1],p) is True): # Checks username and unhased password in table are correct.
        if (RowWithUsername[2] == 1): #If the account logged into is an admin this is recorded in session. 
          session['isadmin'] = True
        return redirect(url_for('.products')) #Sends to products page.
    except:
      abort(403) #Wrong details error


def add_new_product(n, a, d, i, des, p, tp, rp, q): #Adds a new product to product databases' book table.
    #https://www.kite.com/python/answers/how-to-remove-all-non-numeric-characters-from-a-string-in-python.
    d = int("".join(filter(str.isdigit, d)))  #-
    i = "".join(filter(str.isdigit, i))       #-Ensures the date, ISBN number and quantity only contain numbers.
    q = int("".join(filter(str.isdigit, q)))  #-
    
    #https://stackoverflow.com/questions/4138202/using-isdigit-for-floats
    try:  #Attempts to round trade / retail price to 2 decimal places, aborts if inputs are invalid.
      tp = round(float(tp),2)
      rp = round(float(rp),2)
    except:
      print("Trade or retail price not valid")
      abort(400) #Invalid input error
        
    try:
      if (len(i) == 13 and tp <= 100 and rp <= 100 and q <= 20): #Enforces value limits from project brief feature one.
        print("Good product inputs")
      else:
        abort(400) #Invalid input error.
    except:
      abort(400) #Invalid input error.
    
    
    con = sqlite3.connect('products.db')
    #Inserts the details of the new product into the book table.
    con.execute('INSERT OR REPLACE INTO books values (?,?,?,?,?,?,?,?,?)', (n, a, d, i, des, p, tp, rp, q))
    print("Product added successfully")
    
    con.commit()
    con.close()
    
    return stock_level() #Returns user to stock levels page.

        
        
#This function adds products to the users cart.
#Adapted from provided "Shopping cart" code.
@app.route('/add', methods=['POST'])    
def add_product_to_cart():
    cursor = None
    try:
        _quantity = int(request.form['quantity']) #Retrieves product quantity from select products quantity box.
        _code = request.form['code']
        
        if _quantity and _code and request.method == 'POST': 
            con = sqlite3.connect('products.db')
            cur = con.cursor();
            cur.execute("SELECT * FROM books WHERE ISBN=?;", [_code]) #Retrieves the details of the selected book from the books table.
            row = cur.fetchone()
            #(Below) Creates a dictionary in a dictionary in which the details from the books table are values in the inner dictionary and the single outer key being the ISBN number of the book (from the table).
            itemArray = { str(row[3]) : {'title' : row[0], 'ISBN' : row[3], 'quantity' : _quantity, 'price' : row[7], 'image' : row[5], 'total_price' : _quantity * row [7]}}
            print('itemArray is', itemArray)
            
            all_total_price = 0
            all_total_quantity = 0
            
            session.modified = True
            
            if 'cart_item' in session: #True if anything is currently present in the basket.
                print('in session')
                if str(row[3]) in session['cart_item']: #True if the book being added to basket is already in the basket.
                    for key, value in session['cart_item'].items():
                        if str(row[3]) == key:
                            old_quantity = session['cart_item'][key]['quantity'] 
                            total_quantity = old_quantity + _quantity                          #Adds the old quantity of the newly added book to the total quantity.
                            session['cart_item'][key]['quantity'] = total_quantity             #Updates the quantity of the select book in the basket.
                            session['cart_item'][key]['total_price'] = total_quantity * row[7] #Updates total_price (the combined price of however many of the given, single book are in the basket).
                else:
                    session['cart_item'] = array_merge(session['cart_item'], itemArray) #If the newly added book is not in the basket it is simply added into it.
                
                #The total price and quantity of the basket is updated, adding the total prices/quantities of each product to form a total.              
                for key, value in session['cart_item'].items(): 
                    individual_quantity = int(session['cart_item'][key]['quantity'])      #Updates individual_quantity(the quantity of an individual book in the basket)
                    individual_price = float(session['cart_item'][key]['total_price'])    #Updates individual_price(the price of an individual book in the basket)
                    all_total_quantity = all_total_quantity + individual_quantity         #The total quantity of the basket is increased for each individual book quantity.
                    all_total_price = all_total_price + individual_price                  #The total price of the basket is increased for each total book(s) price
            else: #If the basket is empty, a new dictionary "cart_item" is created in session to represent the basket, initially containing the newly added book.
                session['cart_item'] = itemArray
                all_total_quantity = all_total_quantity + _quantity
                all_total_price = all_total_price + _quantity * row[7]
                 
            session['all_total_quantity'] = all_total_quantity  #The total quantity of the basket is recorded in session
            session['all_total_price'] = all_total_price        #The total price of the basket is recorded in session
            
            return redirect(url_for('.products')) #redirects to products page.
        else:
            return 'Error while adding item to cart'
    except Exception as e:
        print(e)
    finally:
        cur.close()
        con.close()
		
#Unchanged from "Shopping Cart" code
@app.route('/delete/<string:code>') #Removes individual books from basket.
def delete_product(code):
	try:
		all_total_price = 0       #-
		all_total_quantity = 0    #-The total price and quantity are recalculated after the book is removed, thus both are initially set to 0.
		session.modified = True   #-
		
		for item in session['cart_item'].items(): #-Searches the basket for the book that needs to be deleted by it's ISBN code.
			if item[0] == code:				              #-
				session['cart_item'].pop(item[0], None) #The select book is removed from the basket.
				if 'cart_item' in session:              #Returns true if the basket is not empty.
					for key, value in session['cart_item'].items():                        #-
						individual_quantity = int(session['cart_item'][key]['quantity'])     #-After the book is removed from the basket...
						individual_price = float(session['cart_item'][key]['total_price'])   #-the total quantity and price of the basket is updated.
						all_total_quantity = all_total_quantity + individual_quantity        #-
						all_total_price = all_total_price + individual_price                 #-
				break
		
		if all_total_quantity == 0: #-If the basket only contained one item and the item was individually removed...
			empty_cart()              #-"empty_cart" is called as the basket is now empty.
		else:
			session['all_total_quantity'] = all_total_quantity   #The baskets total quantity is updated.
			session['all_total_price'] = all_total_price         #The baskets total price is updated.
		return redirect(url_for('.basket'))
	except Exception as e:
		print(e)
        

@app.route('/')   #Navigating to homepage redirects to the products page, see report for explanation.
def homepage():
    session.clear()
    return redirect(url_for('.products'))
  
@app.route('/basket')
def basket():
  return render_template('basket.html')
          
  
#Effective Homepage, adapted from provided "Shopping cart" code.
@app.route('/products')
def products():
    try:
        con = sqlite3.connect('products.db')
        cur = con.cursor();
        
        #-Retrieves all book details from book table.
        cur.execute("SELECT * FROM books")
        lines = cur.fetchall()            
        
        #Returns products page to user, passes all book details to be displayed.
        return render_template('products.html', books=lines)
    except Exception as e:
        print(e)
    finally:
        cur.close()
        con.close()

        
@app.route('/empty')
def empty_cart():
  try:
    LoginStatus = session["isadmin"]  #Records if the currently logged in user is an admin.
  except:
    pass
  session.clear()                     #Clears the session (empties baskets and whether current user is an admin or not).
  try:
    session["isadmin"] = LoginStatus  #Reads to session wheteher the current user is an admin.
  except:
    pass
  return redirect(url_for('.basket'))
  print(e)

  
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST': #Returns true if the user has submit their details on the register page.
        return add_new_user(request.form['username'], request.form['password']) #Calls add_new_user and passes the users input from the register page.
    else:
        return render_template('register.html', page=url_for('register')) #Displays register page to user.
        
        
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST': #Returns true if the user has submit their details on the login page.
        return try_login(request.form['username'], request.form['password']) #Calls try_login and passes the users input from the login page.
    else:
        return render_template('login.html',page=url_for('login')) #Displays login page to user.

    
@app.route('/stocklevels')
def stock_level():
    con = sqlite3.connect('products.db')
    #Creates a new books table if one is not already present, sets primary key to ISBN number.
    con.execute('CREATE TABLE IF NOT EXISTS books (title TEXT, author TEXT, publication DATE, ISBN BIGINT NOT NULL, description TEXT, picture TINYTEXT, trade_price FLOAT, retail_price FLOAT, quantity TINYINT, PRIMARY KEY(ISBN))')
    
    booklist = con.execute("SELECT title, ISBN, picture, quantity FROM books").fetchall() #As required from assessment brief feature 2, only the title, ISBN number, picture and quantity need to be displayed.
    con.close()
    return render_template('stock.html', rows = booklist) #Displays stocklevels page to user, passes details of all books to be displayed.
  
        
@app.route('/addstock', methods=['GET', 'POST'])
def add_stock():
    #https://flask.palletsprojects.com/en/2.0.x/patterns/fileuploads/
    if request.method == 'POST': #Returns true if the user has submit the books details on the add stock page.
        secureimagename = secure_filename(request.files['image'].filename) #Retrieves the filename of the input picture and secures it such that it cannot be used to access other files on the server.
        
        if secureimagename != '' and imghdr.what(request.files['image']) in ('jpeg', 'png'): #Returns true if the filename is not empty and the uploaded file is a jpeg or png.
          request.files['image'].save(os.path.join(coverfolder, secureimagename)) #Saves the uploaded image to the book-images folder.
          #Passed all user input details to add_new_product.
          return add_new_product(request.form['name'], request.form['author'], request.form['date'], request.form['ISBN'], request.form['description'], secureimagename, request.form['tradeprice'], request.form['retailprice'], request.form['quantity'])
        else:
          abort(400)
    else:
        return render_template('addstock.html', page=url_for('.add_stock')) #Displays addstock page to user.
    
@app.route('/checkout')
def checkout():
  
  #https://stackoverflow.com/questions/843277/how-do-i-check-if-a-variable-exists
  try:
    session['cart_item']  #If the basket contains anything, program continues.
  except: #If the basket is empty, the user will be redirected to the homepage and be notified the basket must contain something to check-out.
    return redirect(url_for('.products')), flash("Checkout cancelled, please add something to cart before continuing.")  
  
  con = sqlite3.connect('products.db')
  cur = con.cursor();
  cur.execute("SELECT ISBN FROM books WHERE quantity < 1")  #Retrieves the ISBN code of all in-stock products from books table.
  rows = cur.fetchall()
  con.close()
  
  
  nostockmessage = "" #A warning message for if a product(s) is out of stock, defualt empty.
  try:
    #https://www.geeksforgeeks.org/python-get-dictionary-keys-as-a-list/
    for key in session['cart_item'].keys(): #Iterates over the keys (ISBN codes) of each book present in the basket.
      for row in rows: #Iterates over each ISBN code in the list of books that are out of stock
        if str(key) in str(row): #Returns true if a given book in the basket is out of stock in the books table.
          #The no-stock message alerts the user to remove out-of-stock product(s) from their basket before checking out.
          nostockmessage = nostockmessage + ("Item " + session['cart_item'][key]['title'] + " is out of stock, please remove this item before continuing.") + "\n"
          session['cart_item'][key]['quantity'] = 0 #Used to determine whether "NO STOCK" is shown in checkout table
  except:
    pass   
  #Displays checkout page to user, passes nostockmessage to be displayed (always displayed but not visible if empty).
  return render_template('checkout.html', nostockmessage = nostockmessage)

@app.route('/pay')
def pay():
  return render_template('payment.html')
  
  
@app.route('/final')
def final():
  sessionkeys = list(session['cart_item'].keys()) #Sets sessionkeys as a list of all the keys(ISBN codes) of the books in the checkout basket.
  
  con = sqlite3.connect('products.db')
  cur = con.cursor();
  for key in sessionkeys: #Iterates over each book key in the checkout basket.
    q = session['cart_item'][key]['quantity'] #q is set as the quantity of a given book that was ordered.
    #The quantities of individual books are updated to reflect that books have been ordered and need to be removed from stock.
    cur.execute('UPDATE books SET quantity = (quantity - ?) WHERE ISBN = (?)', (q ,key))  
    con.commit()
    
  con.close()
  empty_cart() #Since a hypothtical order has been placed, basket is emptied.
  
  #After hypothetical order is placed, user is returned to homepage and notified the stock levels have been updated.
  return redirect(url_for('.products')), flash("Stock levels updated, returned to homepage.") 
      
    
@app.errorhandler(403) #Incorrect details have been entered on login or register page. 
def wrong_details(error):
  return render_template('wrong_details.html'), 403

@app.errorhandler(400) #Invalid details have been entered on add_stock page (quantitiies are too large or book cover image filename is empty or malicious).
def invalid_input(error):
  return render_template('bad_input.html', ), 400

		
if __name__ == "__main__":
    app.run()