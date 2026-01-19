from flask import Flask, request, jsonify, render_template_string, session, redirect
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'gcares_secure_key_2026'

# FIX: This handles both local testing and Render's persistent disk
if os.path.exists('/data'):
    DB_FILE = '/data/pharmacy.db'
else:
    DB_FILE = 'pharmacy.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, stock INTEGER, price REAL, expiry_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, product_name TEXT, qty INTEGER, total REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# --- USER ACCOUNTS ---
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "staff": {"password": "staff123", "role": "staff"}
}

# --- THE UI (HTML) ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>GCares Pharmacy System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; color: #333; }
        .login-screen { display: flex; justify-content: center; align-items: center; height: 100vh; }
        .login-card { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 380px; text-align: center; }
        nav { background: #ffffff; padding: 10px 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: {{ 'flex' if logged_in else 'none' }}; align-items: center; justify-content: space-between; }
        .container { max-width: 1000px; margin: 30px auto; background: white; padding: 25px; border-radius: 12px; }
        .hidden { display: none; }
        input, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #ddd; box-sizing: border-box; }
        button { background: #28a745; color: white; border: none; font-weight: bold; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border-bottom: 1px solid #eee; padding: 12px; text-align: left; }
        .btn-select { background: #007bff; width: auto; padding: 5px 10px; }
    </style>
</head>
<body>
{% if not logged_in %}
    <div class="login-screen">
        <div class="login-card">
            <h2>GCares Pharmacy</h2>
            <form method="POST" action="/login">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </div>
{% else %}
    <nav>
        <b>GCares POS</b>
        <div>
            <a onclick="showPage('pos')">🛒 Checkout</a>
            {% if role == 'admin' %}
            <a onclick="showPage('admin')">⚙️ Inventory</a>
            <a onclick="showPage('reports')">📊 Reports</a>
            {% endif %}
            <a href="/logout" style="color: red; margin-left: 15px;">Logout</a>
        </div>
    </nav>
    <div class="container" id="posPage">
        <h2>Checkout</h2>
        <input type="text" id="pId" placeholder="ID (Select from list)" readonly>
        <input type="number" id="qty" placeholder="Qty">
        <button onclick="sell()">Process Sale</button>
        <input type="text" id="posSearch" placeholder="Search medicine..." onkeyup="filterTable('posTable', 'posSearch')">
        <div id="posTable"></div>
    </div>
    <div class="container hidden" id="adminPage">
        <h2>Inventory</h2>
        <input type="text" id="newName" placeholder="Medicine Name">
        <input type="number" id="newPrice" placeholder="Price">
        <input type="number" id="newStock" placeholder="Stock">
        <input type="date" id="newExpiry">
        <button onclick="addProduct()">Add Product</button>
        <div id="adminTable"></div>
    </div>
    <div class="container hidden" id="reportsPage">
        <h2>Total Sales: <span id="rev">0</span></h2>
        <div id="salesTable"></div>
    </div>
{% endif %}
<script>
    function showPage(p) { 
        document.querySelectorAll('.container').forEach(c => c.classList.add('hidden')); 
        document.getElementById(p+'Page').classList.remove('hidden'); 
        if(p==='reports') loadReports(); else loadData();
    }
    async function loadData() {
        const r = await fetch('/data');
        const d = await r.json();
        render(d);
    }
    function render(data) {
        let h = "<table><tr><th>ID</th><th>Name</th><th>Stock</th><th>Price</th><th>Action</th></tr><tbody id='posTable_body'>";
        data.forEach(i => {
            h += `<tr><td>${i[0]}</td><td>${i[1]}</td><td>${i[2]}</td><td>${i[3]}</td><td><button class='btn-select' onclick='selectItem(${i[0]})'>Select</button></td></tr>`;
        });
        document.getElementById('posTable').innerHTML = h + "</tbody></table>";
        if(document.getElementById('adminTable')) document.getElementById('adminTable').innerHTML = h + "</tbody></table>";
    }
    function selectItem(id) { document.getElementById('pId').value = id; }
    function filterTable(tid, sid) {
        let f = document.getElementById(sid).value.toUpperCase();
        let rows = document.getElementById(tid+'_body').getElementsByTagName('tr');
        for (let r of rows) { r.style.display = r.innerText.toUpperCase().includes(f) ? '' : 'none'; }
    }
    async function sell() {
        const id = document.getElementById('pId').value;
        const q = document.getElementById('qty').value;
        await fetch('/sell', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, qty:q}) });
        loadData();
    }
    async function addProduct() {
        const n = document.getElementById('newName').value;
        const p = document.getElementById('newPrice').value;
        const s = document.getElementById('newStock').value;
        const e = document.getElementById('newExpiry').value;
        await fetch('/add', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name:n, price:p, stock:s, expiry:e}) });
        loadData();
    }
    async function loadReports() {
        const r = await fetch('/reports_data');
        const d = await r.json();
        let t = 0;
        let h = "<table><tr><th>Date</th><th>Item</th><th>Total</th></tr>";
        d.forEach(s => { t += s[4]; h += `<tr><td>${s[5]}</td><td>${s[2]}</td><td>${s[4]}</td></tr>`; });
        document.getElementById('rev').innerText = "₱" + t.toFixed(2);
        document.getElementById('salesTable').innerHTML = h + "</table>";
    }
    {% if logged_in %} loadData(); {% endif %}
</script>
</body>
</html>
'''

# --- SERVER ROUTES ---
@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE, logged_in='user' in session, role=session.get('role'))

@app.route('/login', methods=['POST'])
def login():
    u, p = request.form.get('username'), request.form.get('password')
    if u in USERS and USERS[u]['password'] == p:
        session['user'], session['role'] = u, USERS[u]['role']
    return redirect('/')

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

@app.route('/data')
def get_data():
    conn = sqlite3.connect(DB_FILE); d = conn.execute("SELECT * FROM inventory").fetchall(); conn.close()
    return jsonify(d)

@app.route('/add', methods=['POST'])
def add():
    r = request.json; conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO inventory (name, stock, price, expiry_date) VALUES (?,?,?,?)", (r['name'], r['stock'], r['price'], r['expiry']))
    conn.commit(); conn.close(); return jsonify({"ok": True})

@app.route('/sell', methods=['POST'])
def sell():
    r = request.json; conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
    cur.execute("SELECT stock, price, name FROM inventory WHERE id=?", (r['id'],))
    i = cur.fetchone()
    if i and i[0] >= int(r['qty']):
        cur.execute("UPDATE inventory SET stock=? WHERE id=?", (i[0]-int(r['qty']), r['id']))
        cur.execute("INSERT INTO sales (product_id, product_name, qty, total) VALUES (?,?,?,?)", (r['id'], i[2], r['qty'], int(r['qty'])*i[1]))
        conn.commit()
    conn.close(); return jsonify({"ok": True})

@app.route('/reports_data')
def reports_data():
    conn = sqlite3.connect(DB_FILE); d = conn.execute("SELECT * FROM sales").fetchall(); conn.close()
    return jsonify(d)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)