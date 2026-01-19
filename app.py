from flask import Flask, request, jsonify, render_template_string, session, redirect
import sqlite3

app = Flask(__name__)
app.secret_key = 'pharmacy_secret_key' # Required for login sessions
DB_FILE = 'pharmacy.db'

# --- CONFIGURATION (Change your passwords here) ---
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "staff": {"password": "staff123", "role": "staff"}
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, stock INTEGER, price REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, product_name TEXT, qty INTEGER, total REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# --- HTML INTERFACE WITH LOGIN ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Pharmacy System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; margin: 0; }
        .login-box { max-width: 300px; margin: 100px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        nav { background: #007bff; padding: 15px; text-align: center; display: {{ 'block' if logged_in else 'none' }}; }
        nav a { color: white; margin: 0 15px; text-decoration: none; font-weight: bold; cursor: pointer; }
        .container { max-width: 800px; margin: 30px auto; background: white; padding: 25px; border-radius: 12px; }
        .hidden { display: none; }
        input, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 6px; border: 1px solid #ddd; }
        button { background: #28a745; color: white; border: none; font-weight: bold; cursor: pointer; }
        .logout { background: #dc3545; margin-top: 20px; }
    </style>
</head>
<body>

{% if not logged_in %}
    <div class="login-box">
        <h2>🔑 Login</h2>
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
{% else %}
    <nav>
        <a onclick="showPage('pos')">🛒 Checkout</a>
        {% if role == 'admin' %}
        <a onclick="showPage('admin')">⚙️ Inventory</a>
        <a onclick="showPage('reports')">📊 Reports</a>
        {% endif %}
        <a href="/logout" style="color: #ffcccc;">Logout</a>
    </nav>

    <div class="container" id="posPage">
        <h2>Pharmacy Checkout (Logged in as: {{ role }})</h2>
        <input type="number" id="pId" placeholder="Medicine ID">
        <input type="number" id="qty" placeholder="Quantity">
        <button onclick="sell()">Process Sale</button>
        <div id="posTableContainer"></div>
    </div>

    <div class="container hidden" id="adminPage">
        <h2>Inventory Management</h2>
        <input type="text" id="newName" placeholder="Medicine Name">
        <input type="number" id="newStock" placeholder="Initial Stock">
        <input type="number" step="0.01" id="newPrice" placeholder="Price">
        <button onclick="addProduct()">Add Medicine</button>
        <div id="adminTable"></div>
    </div>

    <div class="container hidden" id="reportsPage">
        <h2>Sales Report</h2>
        <h3 id="totalRev">Total: ₱0.00</h3>
        <div id="salesTable"></div>
    </div>
{% endif %}

<script>
    function showPage(page) {
        ['posPage', 'adminPage', 'reportsPage'].forEach(p => {
            const el = document.getElementById(p);
            if(el) el.classList.add('hidden');
        });
        document.getElementById(page + 'Page').classList.remove('hidden');
        if(page === 'reports') loadReports(); else loadData();
    }

    async function loadData() {
        const res = await fetch('/data');
        const data = await res.json();
        let html = "<table><tr><th>ID</th><th>Name</th><th>Stock</th><th>Price</th></tr>";
        data.forEach(row => { html += `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td><td>₱${row[3]}</td></tr>`; });
        document.getElementById('posTableContainer').innerHTML = html + "</table>";
        if(document.getElementById('adminTable')) document.getElementById('adminTable').innerHTML = html + "</table>";
    }

    async function sell() {
        const res = await fetch('/sell', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: document.getElementById('pId').value, qty: document.getElementById('qty').value})
        });
        const result = await res.json();
        alert(result.message || result.error);
        loadData();
    }

    async function loadReports() {
        const res = await fetch('/sales_data');
        const data = await res.json();
        let total = 0;
        let html = "<table><tr><th>Item</th><th>Qty</th><th>Total</th></tr>";
        data.forEach(row => { total += row[4]; html += `<tr><td>${row[2]}</td><td>${row[3]}</td><td>₱${row[4]}</td></tr>`; });
        document.getElementById('totalRev').innerText = "Total Revenue: ₱" + total.toFixed(2);
        document.getElementById('salesTable').innerHTML = html + "</table>";
    }

    {% if logged_in %} loadData(); {% endif %}
</script>
</body>
</html>
'''

# --- LOGIN ROUTES ---
@app.route('/', methods=['GET'])
def home():
    return render_template_string(HTML_TEMPLATE, logged_in='user' in session, role=session.get('role'))

@app.route('/login', methods=['POST'])
def login():
    user = request.form.get('username')
    pw = request.form.get('password')
    if user in USERS and USERS[user]['password'] == pw:
        session['user'] = user
        session['role'] = USERS[user]['role']
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- DATA ROUTES (Inventory & Sales) ---
@app.route('/data')
def get_data():
    conn = sqlite3.connect(DB_FILE)
    data = conn.execute("SELECT * FROM inventory").fetchall()
    conn.close()
    return jsonify(data)

@app.route('/sell', methods=['POST'])
def sell():
    req = request.json
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT stock, price, name FROM inventory WHERE id=?", (req['id'],))
    item = cur.fetchone()
    if item and item[0] >= int(req['qty']):
        new_stock = item[0] - int(req['qty'])
        total = int(req['qty']) * item[1]
        cur.execute("UPDATE inventory SET stock=? WHERE id=?", (new_stock, req['id']))
        cur.execute("INSERT INTO sales (product_id, product_name, qty, total) VALUES (?,?,?,?)", (req['id'], item[2], req['qty'], total))
        conn.commit()
        msg = {"message": "Success!"}
    else: msg = {"error": "Failed!"}
    conn.close()
    return jsonify(msg)

@app.route('/sales_data')
def sales_data():
    if session.get('role') != 'admin': return jsonify([])
    conn = sqlite3.connect(DB_FILE)
    data = conn.execute("SELECT * FROM sales").fetchall()
    conn.close()
    return jsonify(data)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
