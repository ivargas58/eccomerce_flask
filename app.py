from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuración de la base de datos SQLite
def get_db_connection():
    conn = sqlite3.connect('ecommerce.db')
    conn.row_factory = sqlite3.Row
    return conn

# Inicializar la base de datos
def initialize_database():
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

    # Agregar usuarios de ejemplo si no existen
    cursor.execute('''
    INSERT OR IGNORE INTO users (email, password, role)
    VALUES
    ('admin@example.com', 'admin123', 'admin'),
    ('client@example.com', 'client123', 'client')
    ''')

    conn.commit()
    conn.close()

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

@app.route('/client/products', methods=['GET', 'POST'])
def client_products():
    if 'email' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Filtrar productos si se selecciona una categoría
    category = request.args.get('category', default=None)

    if category:
        products = conn.execute('SELECT * FROM products WHERE category = ?', (category,)).fetchall()
    else:
        products = conn.execute('SELECT * FROM products').fetchall()

    # Obtener categorías únicas para mostrarlas en el filtro
    categories = conn.execute('SELECT DISTINCT category FROM products').fetchall()

    conn.close()

    return render_template('client_products.html', products=products, categories=categories)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)
