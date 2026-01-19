from flask import Flask, request, jsonify, render_template_string, session, redirect
import sqlite3

app = Flask(__name__)
app.secret_key = 'gcares_secure_key_2026' # Protects your login sessions
DB_FILE = 'pharmacy.db'

# --- CONFIGURATION: Define your passwords here ---
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "staff": {"password": "staff123", "role": "staff"}
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Inventory table tracks stock levels automatically
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, stock INTEGER, price REAL)''')
    # Sales table records every transaction for the reports
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, product_name TEXT, qty INTEGER, total REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# --- CENTERED LOGIN & MAIN DASHBOARD UI ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>GCares Pharmacy System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; }
        
        /* Centered Login Design */
        .login-screen { display: flex; justify-content: center; align-items: center; height: 100vh; }
        .login-card { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 380px; text-align: center; }
        .login-logo { width: 220px; margin-bottom: 20px; }
        
        /* Main Navigation */
        nav { background: #ffffff; padding: 10px 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: {{ 'flex' if logged_in else 'none' }}; align-items: center; justify-content: space-between; }
        nav a { color: #333; margin-left: 20px; text-decoration: none; font-weight: 600; cursor: pointer; }
        nav a:hover { color: #28a745; }
        
        .container { max-width: 900px; margin: 30px auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }
        .hidden { display: none; }
        input, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #ddd; box-sizing: border-box; }
        button { background: #28a745; color: white; border: none; font-weight: bold; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border-bottom: 1px solid #eee; padding: 12px; text-align: left; }
        th { background: #f8f9fa; }
        .low-stock { color: #dc3545; font-weight: bold; }
        
        /* Search Bar Styling */
        .search-container { position: relative; margin-top: 15px; }
        .search-input { padding-left: 40px; background: #fff url('https://www.w3schools.com/howto/searchicon.png') no-repeat 13px center; background-size: 15px; }
    </style>
</head>
<body>

{% if not logged_in %}
    <div class="login-screen">
        <div class="login-card">
            <img src="https://raw.githubusercontent.com/KeisukiShuen/pharmacy-pos/refs/heads/main/GCaresText2.png" class="login-logo" alt="GCares Pharmacy">
            <h2>Welcome Back</h2>
            <form method="POST" action="/login">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit" style="background: #007bff;">Log In</button>
            </form>
        </div>
    </div>
{% else %}
    <nav>
        <div style="display: flex; align-items: center;">
            <img src="https://raw.githubusercontent.com/KeisukiShuen/pharmacy-pos/refs/heads/main/GCaresText2.png" style="height: 40px;">
        </div>
        <div>
            <a onclick="showPage('pos')">🛒 Checkout</a>
            {% if role == 'admin' %}
            <a onclick="showPage('admin')">⚙️ Inventory</a>
            <a onclick="showPage('reports')">📊 Sales Report</a>
            {% endif %}
            <a href="/logout" style="color: #dc3545;">Logout</a>
        </div>
    </nav>

    <div class="container" id="posPage">
        <h2>POS Checkout</h2>
        <div style="display: flex; gap: 10px;">
            <input type="number" id="pId" placeholder="Product ID" style="flex: 1;">
            <input type="number" id="qty" placeholder="Qty" style="flex: 1;">
        </div>
        <button onclick="sell()">Complete Transaction</button>
        <div class="search-container">
            <input type="text" id="posSearch" class="search-input" placeholder="Search medicines by name..." onkeyup="filterTable('posTable', 'posSearch')">
        </div>
        <div id="posTable"></div>
    </div>

    <div class="container hidden" id="adminPage">
        <h2>Inventory Management</h2>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h4>Add New Product</h4>
            <input type="text" id="newName" placeholder="Medicine Name">
            <input type="number" id="newStock" placeholder="Initial Stock">
            <input type="number" step="0.01" id="newPrice" placeholder="Price (₱)">
            <button onclick="addProduct()" style="background: #007bff;">Add to Inventory</button>
        </div>
        <div class="search-container">
            <input type="text" id="adminSearch" class="search-input" placeholder="Search inventory..." onkeyup="filterTable('adminTable', 'adminSearch')">
        </div>
        <div id="adminTable"></div>
    </div>

    <div class="container hidden" id="reportsPage">
        <div style="text-align: center; background: #e7f3ff; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="margin:0;">Total Revenue: <span id="revenueText" style="color: #28a745;">₱0.00</span></h2>
        </div>
        <h3>Transaction History</h3>
        <div id="salesTable"></div>
    </div>
{% endif %}

<script>
    function showPage(page) {
        document.querySelectorAll('.container').forEach(c => c.classList.add('hidden'));
        document.getElementById(page + 'Page').classList.remove('hidden');
        if(page === 'reports') loadReports(); else loadData();
    }

    async function loadData() {
        const res = await fetch('/data');
        const data = await res.json();
        renderTable(data, 'posTable');
        if(document.getElementById('adminTable')) renderTable(data, 'adminTable');
    }

    function renderTable(data, containerId) {
        let html = `<table><thead><tr><th>ID</th><th>Name</th><th>Stock</th><th>Price</th></tr></thead><tbody id="${containerId}_body">`;
        data.forEach(r => {
            let stockWarn = r[2] < 10 ? 'class="low-stock"' : '';
            html += `<tr><td>${r[0]}</td><td>${r[1]}</td><td ${stockWarn}>${r[2]}</td><td>₱${r[3].toFixed(2)}</td></tr>`;
        });
        document.getElementById(containerId).innerHTML = html + "</tbody></table>";
    }

    // Search Filtering Logic
    function filterTable(containerId, searchId) {
        let input = document.getElementById(searchId).value.toUpperCase();
        let rows = document.getElementById(containerId + "_body").getElementsByTagName("tr");
        for (let i = 0; i < rows.length; i++) {
            let nameCol = rows[i].getElementsByTagName("td")[1];
            if (nameCol) {
                let txtValue = nameCol.textContent || nameCol.innerText;
                rows[i].style.display = txtValue.toUpperCase().indexOf(input) > -1 ? "" : "none";
            }
        }
    }

    async function sell() {
        const id = document.getElementById('pId').value;
        const qty = document.getElementById('qty').value;
        if(!id || !qty) return alert("Enter Product ID and Quantity");

        const res = await fetch('/sell', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id, qty})
        });
        const result = await res.json();
        alert(result.message || result.error);
        loadData();
    }

    async function addProduct() {
        const name = document.getElementById('newName').value;
        const stock = document.getElementById('newStock').value;
        const price = document.getElementById('newPrice').value;
        if(!name || !stock || !price) return alert("Fill all fields");

        await fetch('/add_product', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, stock, price})
        });
        alert("Product Added!");
        loadData();
    }

    async function loadReports() {
        const res = await fetch('/sales_data');
        const data = await res.json();
        let total = 0;
        let html = "<table><tr><th>Date</th><th>Item</th><th>Qty</th><th>Total</th></tr>";
        data.forEach(r => { 
            total += r[4]; 
            html += `<tr><td>${r[5]}</td><td>${r[2]}</td><td>${r[3]}</td><td>₱${r[4].toFixed(2)}</td></tr>`; 
        });
        document.getElementById('revenueText').innerText = "₱" + total.toFixed(2);
        document.getElementById('salesTable').innerHTML = html + "</table>";
    }

    {% if logged_in %} loadData(); {% endif %}
</script>
</body>
</html>
'''

# --- BACKEND ROUTES ---
@app.route('/')
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
        msg = {"message": "Transaction Successful!"}
    else:
        msg = {"error": "Invalid Product ID or Insufficient Stock!"}
    conn.close()
    return jsonify(msg)

@app.route('/sales_data')
def sales_data():
    if session.get('role') != 'admin': return jsonify([])
    conn = sqlite3.connect(DB_FILE)
    data = conn.execute("SELECT * FROM sales ORDER BY date DESC").fetchall()
    conn.close()
    return jsonify(data)

@app.route('/add_product', methods=['POST'])
def add_product():
    req = request.json
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO inventory (name, stock, price) VALUES (?,?,?)", (req['name'], req['stock'], req['price']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)