from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# Configuración de la base de datos SQLite
def get_db_connection():
    conn = sqlite3.connect('ecommerce.db')
    conn.row_factory = sqlite3.Row
    return conn


# Inicializar la base de datos
def initialize_database():
    # Si deseas eliminar la base de datos existente para iniciar de nuevo, descomenta la siguiente línea:
    # os.remove('ecommerce.db')  # Descomentar para borrar la base de datos actual y comenzar de nuevo

    conn = get_db_connection()
    cursor = conn.cursor()

    # Crear la tabla de usuarios
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    ''')

    # Crear la tabla de productos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        image TEXT,
        description TEXT,
        price REAL NOT NULL,
        category TEXT NOT NULL
    )
    ''')

    # Crear la tabla de pedidos
    cursor.execute("PRAGMA table_info(orders);")
    columns = cursor.fetchall()
    if not any(col[1] == "user_id" for col in columns):
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
    else:
        cursor.execute('''
        ALTER TABLE orders ADD COLUMN user_id INTEGER NOT NULL;
        ''')

    # Crear la tabla de elementos de pedido
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')

    # Crear la tabla de detalles de envío y pago
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shipping_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        address TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # Agregar usuarios de ejemplo si no existen
    cursor.execute('''
    INSERT OR IGNORE INTO users (email, password, role)
    VALUES
    ('admin@example.com', 'admin123', 'admin'),
    ('client@example.com', 'client123', 'client')
    ''')

    conn.commit()
    conn.close()


# Función para crear un pedido
def create_order(address, city, postal_code, phone):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (session['email'],)).fetchone()
    
    # Guardar el pedido
    total = sum(item['price'] * item['quantity'] for item in session.get('cart', []))  # Total del carrito
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO orders (user_id, total) VALUES (?, ?)
    ''', (user['id'], total))
    order_id = cursor.lastrowid

    # Guardar los artículos del pedido
    for item in session.get('cart', []):
        cursor.execute('''
        INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)
        ''', (order_id, item['id'], item['quantity'], item['price']))
    
    # Guardar los detalles de envío
    cursor.execute('''
    INSERT INTO shipping_details (user_id, address, phone_number, payment_method)
    VALUES (?, ?, ?, ?)
    ''', (user['id'], address, phone, postal_code))

    conn.commit()
    conn.close()

    # Limpiar el carrito después de crear el pedido
    session.pop('cart', None)

    return order_id


# Rutas principales
@app.route('/')
def login():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login_post():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()

        if user:
            session['email'] = user['email']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Credenciales inválidas")
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', role=session['role'])


# Gestión de productos para administradores
@app.route('/admin/products', methods=['GET', 'POST'])
def manage_products():
    if 'email' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        image = request.form['image']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']

        try:
            price = float(price)
        except ValueError:
            return render_template('admin_products.html', error="El precio debe ser un número.")

        conn = get_db_connection()
        conn.execute('INSERT INTO products (name, image, description, price, category) VALUES (?, ?, ?, ?, ?)',
                     (name, image, description, price, category))
        conn.commit()
        conn.close()

        return redirect(url_for('manage_products'))

    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()

    return render_template('admin_products.html', products=products)


@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if 'email' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        image = request.form['image']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']

        conn.execute('UPDATE products SET name = ?, image = ?, description = ?, price = ?, category = ? WHERE id = ?',
                     (name, image, description, price, category, id))
        conn.commit()
        conn.close()
        return redirect(url_for('manage_products'))

    product = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('edit_product.html', product=product)


@app.route('/admin/products/delete/<int:id>', methods=['GET'])
def delete_product(id):
    if 'email' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_products'))


# Gestión de productos para clientes
@app.route('/client_products', methods=['GET'])
def client_products():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('client_products.html', products=products)


# Carrito de compras
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))

    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()

    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append({
        'id': product['id'],
        'name': product['name'],
        'price': product['price'],
        'quantity': quantity
    })
    session.modified = True

    # Redirigir al carrito después de agregar el producto
    return redirect(url_for('view_cart'))


@app.route('/view_cart', methods=['GET'])
def view_cart():
    cart = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    return render_template('cart.html', cart=cart, total=total)


@app.route('/cart/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != product_id]
        session.modified = True
    return redirect(url_for('view_cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        address = request.form.get('address')
        city = request.form.get('city')
        postal_code = request.form.get('postal_code')
        phone = request.form.get('phone')
        payment_method = request.form.get('payment_method')

        order_id = create_order(address, city, postal_code, phone)
        return redirect(url_for('order_confirmation', order_id=order_id))

    return render_template('checkout.html')


@app.route('/order_confirmation/<int:order_id>', methods=['GET'])
def order_confirmation(order_id):
    return render_template('order_confirmation.html', order_id=order_id)


if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)
