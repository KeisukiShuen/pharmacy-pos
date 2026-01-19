from flask import Flask, request, jsonify, render_template_string, session, redirect
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'gcares_secure_key_2026'
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

USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "staff": {"password": "staff123", "role": "staff"}
}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <title>GCares Pharmacy System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --primary: #007bff; --success: #28a745; --danger: #dc3545; --bg: #f4f7f6; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; color: #333; }
        .login-screen { display: flex; justify-content: center; align-items: center; height: 100vh; }
        .login-card { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); width: 100%; max-width: 380px; text-align: center; }
        .login-logo { width: 220px; margin-bottom: 25px; }
        nav { background: white; padding: 12px 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); display: {{ 'flex' if logged_in else 'none' }}; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; }
        .nav-brand { display: flex; align-items: center; font-weight: bold; color: var(--primary); }
        nav a { color: #555; margin-left: 20px; text-decoration: none; font-weight: 600; cursor: pointer; }
        .container { max-width: 1100px; margin: 30px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .hidden { display: none; }
        input, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #ddd; box-sizing: border-box; }
        button { background: var(--success); color: white; border: none; font-weight: bold; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 15px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #f8f9fa; font-size: 0.9rem; color: #666; }
        .low-stock { color: var(--danger); font-weight: bold; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; }
        .expired { background: #f8d7da; color: #721c24; }
        .soon { background: #fff3cd; color: #856404; }
        .search-input { padding-left: 40px; background: white url('https://www.w3schools.com/howto/searchicon.png') no-repeat 13px center; background-size: 16px; }
    </style>
</head>
<body>
{% if not logged_in %}
    <div class="login-screen">
        <div class="login-card">
            <img src="https://raw.githubusercontent.com/KeisukiShuen/pharmacy-pos/refs/heads/main/GCaresText2.png" class="login-logo" alt="GCares Logo">
            <form method="POST" action="/login">
                <input type="text" name="username" placeholder="Username" required autofocus>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit" style="background: var(--primary);">Login</button>
            </form>
        </div>
    </div>
{% else %}
    <nav>
        <div class="nav-brand"><img src="https://raw.githubusercontent.com/KeisukiShuen/pharmacy-pos/refs/heads/main/GCaresText2.png" style="height: 40px; margin-right: 10px;">GCares</div>
        <div>
            <a onclick="showPage('pos')">🛒 Checkout</a>
            {% if role == 'admin' %}
            <a onclick="showPage('admin')">⚙️ Inventory</a>
            <a onclick="showPage('reports')">📊 Reports</a>
            {% endif %}
            <a href="/logout" style="color: var(--danger);">Logout</a>
        </div>
    </nav>
    <div class="container" id="posPage">
        <h2>Process Sale</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr auto; gap: 15px;">
            <input type="text" id="selectedName" placeholder="Selected Medicine" readonly style="background: #f0f0f0;">
            <input type="number" id="qty" placeholder="Quantity">
            <input type="hidden" id="pId">
            <button onclick="sell()" style="width: 150px;">Complete Sale</button>
        </div>
        <input type="text" id="posSearch" class="search-input" placeholder="Search medicine name..." onkeyup="filter('posTable', 'posSearch')">
        <div id="posTable"></div>
    </div>
    <div class="container hidden" id="adminPage">
        <h2>Inventory Management</h2>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 25px; border: 1px solid #eee;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <input type="text" id="newName" placeholder="Medicine Name">
                <input type="number" id="newPrice" placeholder="Price (₱)">
                <input type="number" id="newStock" placeholder="Stock Level">
                <input type="date" id="newExpiry">
            </div>
            <button onclick="addProduct()" style="background: var(--primary); margin-top: 10px;">Add Product</button>
        </div>
        <input type="text" id="adminSearch" class="search-input" placeholder="Filter inventory..." onkeyup="filter('adminTable', 'adminSearch')">
        <div id="adminTable"></div>
    </div>
    <div class="container hidden" id="reportsPage">
        <h2 id="revenueText" style="text-align: center; color: var(--success);">₱0.00</h2>
        <div id="salesTable"></div>
    </div>
{% endif %}
<script>
    function showPage(p) {
        document.querySelectorAll('.container').forEach(c => c.classList.add('hidden'));
        document.getElementById(p + 'Page').classList.remove('hidden');
        loadData();
    }
    async function loadData() {
        const res = await fetch('/data');
        const data = await res.json();
        render(data, 'posTable', false);
        if(document.getElementById('adminTable')) render(data, 'adminTable', true);
    }
    function render(data, cid, isAdmin) {
        const now = new Date();
        const soon = new Date(); soon.setDate(now.getDate() + 30);
        let h = `<table><tr><th>Name</th><th>Stock</th><th>Price</th><th>Expiry</th><th>Action</th></tr><tbody id="${cid}_body">`;
        data.forEach(r => {
            const exp = r[4] ? new Date(r[4]) : null;
            let badge = r[4] || 'N/A';
            if(exp) {
                if(exp < now) badge = `<span class="badge expired">Expired</span>`;
                else if(exp <= soon) badge = `<span class="badge soon">${r[4]}</span>`;
            }
            let stockClass = r[2] < 10 ? 'class="low-stock"' : '';
            h += `<tr><td><b>${r[1]}</b></td><td ${stockClass}>${r[2]}</td><td>₱${r[3].toFixed(2)}</td><td>${badge}</td><td>
                ${isAdmin ? `<button onclick="deleteItem(${r[0]})" style="background:var(--danger); padding:5px; font-size:0.8rem;">Delete</button>` : `<button onclick="selectItem(${r[0]}, '${r[1]}')" style="background:var(--primary); padding:5px; font-size:0.8rem;">Select</button>`}
            </td></tr>`;
        });
        document.getElementById(cid).innerHTML = h + "</tbody></table>";
    }
    function selectItem(id, name) { document.getElementById('pId').value = id; document.getElementById('selectedName').value = name; }
    function filter(tid, sid) {
        let f = document.getElementById(sid).value.toUpperCase();
        let rows = document.getElementById(tid + "_body").getElementsByTagName("tr");
        for (let r of rows) { r.style.display = r.innerText.toUpperCase().includes(f) ? "" : "none"; }
    }
    async function sell() {
        const id = document.getElementById('pId').value;
        const qty = document.getElementById('qty').value;
        const res = await fetch('/sell', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, qty}) });
        const result = await res.json();
        alert(result.message || result.error); loadData();
    }
    async function addProduct() {
        const n = document.getElementById('newName').value;
        const s = document.getElementById('newStock').value;
        const p = document.getElementById('newPrice').value;
        const e = document.getElementById('newExpiry').value;
        await fetch('/add', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name:n, stock:s, price:p, expiry:e}) });
        loadData();
    }
    async function deleteItem(id) { if(confirm("Delete?")) { await fetch('/delete/' + id, { method: 'POST' }); loadData(); } }
    async function loadReports() {
        const res = await fetch('/sales_data');
        const data = await res.json();
        let t = 0; let h = "<table><tr><th>Date</th><th>Item</th><th>Total</th></tr>";
        data.forEach(r => { t += r[4]; h += `<tr><td>${r[5].substring(0,16)}</td><td>${r[2]}</td><td>₱${r[4].toFixed(2)}</td></tr>`; });
        document.getElementById('revenueText').innerText = "₱" + t.toFixed(2);
        document.getElementById('salesTable').innerHTML = h + "</table>";
    }
    {% if logged_in %} loadData(); {% endif %}
</script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, logged_in='user' in session, role=session.get('role'))

@app.route('/login', methods=['POST'])
def login():
    u, p = request.form.get('username'), request.form.get('password')
    if u in USERS and USERS[u]['password'] == p:
        session['user'], session['role'] = u, USERS[u]['role']
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

@app.route('/data')
def get_data():
    conn = sqlite3.connect(DB_FILE); d = conn.execute("SELECT * FROM inventory ORDER BY name ASC").fetchall(); conn.close()
    return jsonify(d)

@app.route('/add', methods=['POST'])
def add():
    r = request.json; conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO inventory (name, stock, price, expiry_date) VALUES (?,?,?,?)", (r['name'], r['stock'], r['price'], r['expiry']))
    conn.commit(); conn.close(); return jsonify({"ok": True})

@app.route('/sell', methods=['POST'])
def sell():
    r = request.json; conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
    cur.execute("SELECT stock, price, name, expiry_date FROM inventory WHERE id=?", (r['id'],))
    i = cur.fetchone()
    if i:
        if i[3] and datetime.strptime(i[3], '%Y-%m-%d') < datetime.now(): return jsonify({"error": "Expired!"})
        if i[0] >= int(r['qty']):
            cur.execute("UPDATE inventory SET stock=? WHERE id=?", (i[0]-int(r['qty']), r['id']))
            cur.execute("INSERT INTO sales (product_id, product_name, qty, total) VALUES (?,?,?,?)", (r['id'], i[2], r['qty'], int(r['qty'])*i[1]))
            conn.commit(); msg = {"message": "Success!"}
        else: msg = {"error": "Low stock!"}
    else: msg = {"error": "Not found!"}
    conn.close(); return jsonify(msg)

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    conn = sqlite3.connect(DB_FILE); conn.execute("DELETE FROM inventory WHERE id=?", (id,)); conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route('/sales_data')
def sales_data():
    conn = sqlite3.connect(DB_FILE); d = conn.execute("SELECT * FROM sales ORDER BY date DESC").fetchall(); conn.close()
    return jsonify(d)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)