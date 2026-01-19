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

# --- ACCESS CREDENTIALS ---
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "staff": {"password": "staff123", "role": "staff"}
}

# --- THE UI (HTML/CSS/JS) ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <title>GCares Pharmacy System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --primary: #007bff; --success: #28a745; --danger: #dc3545; --dark: #343a40; --light: #f8f9fa; }
        body { font-family: 'Segoe UI', sans-serif; background: #eef2f7; margin: 0; display: flex; flex-direction: column; height: 100vh; }
        
        /* Login Design */
        .login-screen { display: flex; justify-content: center; align-items: center; height: 100vh; width: 100%; }
        .login-card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); width: 350px; text-align: center; }
        .login-logo { width: 180px; margin-bottom: 20px; }

        /* Top Bar */
        header { background: white; padding: 10px 25px; display: {{ 'flex' if logged_in else 'none' }}; align-items: center; justify-content: space-between; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .brand { display: flex; align-items: center; font-weight: bold; font-size: 1.2rem; color: var(--primary); }
        
        /* Layout & Sidebar */
        .main-layout { display: {{ 'flex' if logged_in else 'none' }}; flex: 1; overflow: hidden; }
        .sidebar { width: 220px; background: var(--dark); color: white; padding: 20px 0; display: flex; flex-direction: column; }
        .nav-item { padding: 15px 25px; cursor: pointer; transition: 0.3s; color: #adb5bd; text-decoration: none; }
        .nav-item.active { background: var(--primary); color: white; border-right: 4px solid white; }
        
        /* Content Area */
        .content { flex: 1; padding: 25px; overflow-y: auto; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .hidden { display: none; }
        
        /* Stats Widgets */
        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 25px; }
        .stat-box { padding: 15px; border-radius: 10px; color: white; text-align: center; }

        /* Multi-Order Cart Styling */
        .cart-section { border: 2px solid var(--primary); background: #f0f7ff; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .cart-total { font-size: 1.5rem; font-weight: bold; text-align: right; color: var(--primary); margin-top: 10px; }

        /* Forms & Buttons */
        input, button { padding: 12px; margin: 5px 0; border-radius: 8px; border: 1px solid #ddd; width: 100%; box-sizing: border-box; }
        .btn-main { background: var(--success); color: white; border: none; font-weight: bold; cursor: pointer; }
        .btn-blue { background: var(--primary); }
        .btn-del { background: var(--danger); width: auto; padding: 5px 10px; }

        /* Table Styling */
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { font-size: 0.8rem; color: #888; text-transform: uppercase; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
        .expired { background: #f8d7da; color: #721c24; }
        .soon { background: #fff3cd; color: #856404; }
        .low { color: var(--danger); font-weight: bold; }
    </style>
</head>
<body>

{% if not logged_in %}
    <div class="login-screen">
        <div class="login-card">
            <img src="https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/GCaresText2.png" class="login-logo" alt="GCares Logo">
            <form method="POST" action="/login">
                <input type="text" name="username" placeholder="Username" required autofocus>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit" class="btn-main" style="background:var(--primary);">Login to System</button>
            </form>
        </div>
    </div>
{% else %}
    <header>
        <div class="brand"><img src="https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/GCaresText2.png" style="height:35px; margin-right:10px;"> GCares Pharmacy</div>
        <div>User: <b>{{ role|capitalize }}</b></div>
    </header>

    <div class="main-layout">
        <div class="sidebar">
            <div class="nav-item active" id="nav-pos" onclick="showPage('pos')">🛒 Checkout</div>
            {% if role == 'admin' %}
            <div class="nav-item" id="nav-admin" onclick="showPage('admin')">📦 Inventory</div>
            <div class="nav-item" id="nav-reports" onclick="showPage('reports')">📊 Sales Report</div>
            {% endif %}
            <a href="/logout" class="nav-item" style="color:var(--danger); margin-top:auto;">🚪 Logout</a>
        </div>

        <div class="content">
            <div class="stats-grid">
                <div class="stat-box" style="background: #4e73df;">
                    <small>TOTAL REVENUE</small>
                    <div id="stat-rev" style="font-size: 1.4rem; font-weight: bold;">₱0.00</div>
                </div>
                <div class="stat-box" style="background: #1cc88a;">
                    <small>INVENTORY ITEMS</small>
                    <div id="stat-items" style="font-size: 1.4rem; font-weight: bold;">0</div>
                </div>
                <div class="stat-box" style="background: #f6c23e;">
                    <small>LOW STOCK ALERTS</small>
                    <div id="stat-low" style="font-size: 1.4rem; font-weight: bold;">0</div>
                </div>
            </div>

            <div class="card" id="posPage">
                <h3>Current Shopping Cart</h3>
                <div id="cartSection" class="cart-section hidden">
                    <table>
                        <thead><tr><th>Item Name</th><th>Qty</th><th>Price</th><th>Subtotal</th><th>Action</th></tr></thead>
                        <tbody id="cartBody"></tbody>
                    </table>
                    <div class="cart-total">Grand Total: <span id="grandTotal">₱0.00</span></div>
                    <button onclick="checkout()" class="btn-main" style="margin-top:15px;">Finalize Multi-Order Sale</button>
                </div>
                <div id="emptyMsg" style="text-align:center; color:#999; padding:20px;">Cart is empty. Select medicines from the list below.</div>
                
                <hr style="margin:25px 0; border:0; border-top:1px solid #eee;">
                
                <h3>Search Medicines</h3>
                <input type="text" id="posSearch" placeholder="🔍 Type medicine name here..." onkeyup="filter('posTable', 'posSearch')">
                <div id="posTable"></div>
            </div>

            <div class="card hidden" id="adminPage">
                <h3>Add New Inventory</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <input type="text" id="newName" placeholder="Medicine Name">
                    <input type="number" id="newPrice" placeholder="Price (₱)">
                    <input type="number" id="newStock" placeholder="Stock Level">
                    <input type="date" id="newExpiry">
                </div>
                <button onclick="addProduct()" class="btn-main" style="background:var(--primary); margin-top:10px;">Add to Stock</button>
                <div id="adminTable" style="margin-top:20px;"></div>
            </div>

            <div class="card hidden" id="reportsPage">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3>Transaction History</h3>
                    <button onclick="window.print()" style="width:auto; padding:5px 15px; background:#666;">🖨️ Print Report</button>
                </div>
                <div id="salesTable"></div>
            </div>
        </div>
    </div>
{% endif %}

<script>
    let cart = [];

    function showPage(p) {
        document.querySelectorAll('.card').forEach(c => c.classList.add('hidden'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.getElementById(p + 'Page').classList.remove('hidden');
        document.getElementById('nav-' + p).classList.add('active');
        if(p === 'reports') loadReports(); else loadData();
    }

    async function loadData() {
        const res = await fetch('/data');
        const data = await res.json();
        
        // Update Dashboard
        document.getElementById('stat-items').innerText = data.length;
        document.getElementById('stat-low').innerText = data.filter(i => i[2] < 10).length;

        renderList(data, 'posTable', false);
        if(document.getElementById('adminTable')) renderList(data, 'adminTable', true);
    }

    function renderList(data, cid, isAdmin) {
        const now = new Date();
        const soon = new Date(); soon.setDate(now.getDate() + 30);

        let h = `<table><tr><th>Medicine Name</th><th>Stock</th><th>Price</th><th>Expiry</th><th>Action</th></tr><tbody id="${cid}_body">`;
        data.forEach(r => {
            const exp = r[4] ? new Date(r[4]) : null;
            let badge = r[4] || 'N/A';
            if(exp) {
                if(exp < now) badge = `<span class="badge expired">Expired</span>`;
                else if(exp <= soon) badge = `<span class="badge soon">${r[4]}</span>`;
            }
            let stockDisplay = r[2] < 10 ? `<span class="low">${r[2]} Low</span>` : r[2];
            
            h += `<tr><td><b>${r[1]}</b></td><td>${stockDisplay}</td><td>₱${r[3].toFixed(2)}</td><td>${badge}</td><td>
                ${isAdmin ? `<button onclick="deleteItem(${r[0]})" class="btn-del" style="color:white; border:none; cursor:pointer;">Del</button>` : 
                `<button onclick="addToCart(${r[0]}, '${r[1]}', ${r[3]}, ${r[2]})" class="btn-blue" style="width:auto; padding:5px; color:white; border:none; cursor:pointer;">+ Add Order</button>`}
            </td></tr>`;
        });
        document.getElementById(cid).innerHTML = h + "</tbody></table>";
    }

    function addToCart(id, name, price, stock) {
        let qty = prompt(`How many units of ${name}? (Current Stock: ${stock})`, 1);
        if (!qty || isNaN(qty) || qty <= 0) return;
        if (qty > stock) return alert("Not enough stock in inventory!");

        cart.push({ id, name, price, qty: parseInt(qty), total: price * qty });
        updateCartUI();
    }

    function updateCartUI() {
        const body = document.getElementById('cartBody');
        const section = document.getElementById('cartSection');
        const msg = document.getElementById('emptyMsg');
        
        if (cart.length === 0) {
            section.classList.add('hidden');
            msg.classList.remove('hidden');
            return;
        }

        section.classList.remove('hidden');
        msg.classList.add('hidden');
        
        let h = ""; let gTotal = 0;
        cart.forEach((item, index) => {
            gTotal += item.total;
            h += `<tr><td>${item.name}</td><td>${item.qty}</td><td>₱${item.price.toFixed(2)}</td><td>₱${item.total.toFixed(2)}</td>
                  <td><button onclick="removeFromCart(${index})" style="background:#888; color:white; border:none; width:auto; padding:3px 8px;">Remove</button></td></tr>`;
        });
        body.innerHTML = h;
        document.getElementById('grandTotal').innerText = "₱" + gTotal.toFixed(2);
    }

    function removeFromCart(i) { cart.splice(i, 1); updateCartUI(); }

    async function checkout() {
        if (!confirm("Sell these items and record transaction?")) return;
        const res = await fetch('/bulk_sell', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({items: cart})
        });
        const result = await res.json();
        alert(result.message);
        cart = []; updateCartUI(); loadData();
    }

    async function addProduct() {
        const n = document.getElementById('newName').value;
        const s = document.getElementById('newStock').value;
        const p = document.getElementById('newPrice').value;
        const e = document.getElementById('newExpiry').value;
        if(!n || !s || !p) return alert("Please fill Name, Price, and Stock!");
        await fetch('/add', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name:n, stock:s, price:p, expiry:e}) });
        alert("Added!"); loadData();
    }

    async function deleteItem(id) {
        if(confirm("Delete item forever?")) { await fetch('/delete/' + id, { method: 'POST' }); loadData(); }
    }

    async function loadReports() {
        const res = await fetch('/sales_data');
        const data = await res.json();
        let total = 0;
        let h = "<table><tr><th>Date</th><th>Item</th><th>Qty</th><th>Total</th></tr>";
        data.forEach(r => { total += r[4]; h += `<tr><td>${r[5].substring(0,16)}</td><td>${r[2]}</td><td>${r[3]}</td><td>₱${r[4].toFixed(2)}</td></tr>`; });
        document.getElementById('stat-rev').innerText = "₱" + total.toFixed(2);
        document.getElementById('salesTable').innerHTML = h + "</table>";
    }

    function filter(tid, sid) {
        let f = document.getElementById(sid).value.toUpperCase();
        let rows = document.getElementById(tid + "_body").getElementsByTagName("tr");
        for (let r of rows) { r.style.display = r.innerText.toUpperCase().includes(f) ? "" : "none"; }
    }

    {% if logged_in %} loadData(); loadReports(); {% endif %}
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

@app.route('/bulk_sell', methods=['POST'])
def bulk_sell():
    r = request.json; conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
    for item in r['items']:
        cur.execute("UPDATE inventory SET stock = stock - ? WHERE id=?", (item['qty'], item['id']))
        cur.execute("INSERT INTO sales (product_id, product_name, qty, total) VALUES (?,?,?,?)", 
                    (item['id'], item['name'], item['qty'], item['total']))
    conn.commit(); conn.close(); return jsonify({"message": "Multi-item transaction successful!"})

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