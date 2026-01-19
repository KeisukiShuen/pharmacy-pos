from flask import Flask, request, jsonify, render_template_string
import sqlite3

app = Flask(__name__)
DB_FILE = 'pharmacy.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, stock INTEGER, price REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, product_name TEXT, qty INTEGER, total REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Pharmacy Management System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; margin: 0; padding: 0; }
        nav { background: #007bff; padding: 15px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        nav a { color: white; margin: 0 15px; text-decoration: none; font-weight: bold; cursor: pointer; }
        .container { max-width: 900px; margin: 30px auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .hidden { display: none; }
        input, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 6px; border: 1px solid #ddd; }
        button { background: #28a745; color: white; border: none; font-weight: bold; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #eee; padding: 12px; text-align: left; }
        th { background: #f8f9fa; }
        .stat-card { background: #e7f3ff; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    </style>
</head>
<body>

<nav>
    <a onclick="showPage('pos')">🛒 Checkout</a>
    <a onclick="showPage('admin')">⚙️ Inventory</a>
    <a onclick="showPage('reports')">📊 Sales Report</a>
</nav>

<div class="container" id="posPage">
    <h2>Pharmacy Checkout</h2>
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
    <button style="background: #007bff;" onclick="addProduct()">Add Medicine</button>
    <div id="adminTableContainer"></div>
</div>

<div class="container hidden" id="reportsPage">
    <h2>Sales Performance</h2>
    <div class="stat-card">
        <h3 id="totalRevenue">Total Revenue: ₱0.00</h3>
    </div>
    <h3>Recent Transactions</h3>
    <div id="salesTableContainer"></div>
</div>

<script>
    function showPage(page) {
        document.getElementById('posPage').classList.add('hidden');
        document.getElementById('adminPage').classList.add('hidden');
        document.getElementById('reportsPage').classList.add('hidden');
        document.getElementById(page + 'Page').classList.remove('hidden');
        if(page === 'reports') loadReports();
        else loadData();
    }

    async function loadData() {
        const res = await fetch('/data');
        const data = await res.json();
        let html = "<table><tr><th>ID</th><th>Name</th><th>Stock</th><th>Price</th></tr>";
        data.forEach(row => {
            html += `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td><td>₱${row[3].toFixed(2)}</td></tr>`;
        });
        document.getElementById('posTableContainer').innerHTML = html + "</table>";
        document.getElementById('adminTableContainer').innerHTML = html + "</table>";
    }

    async function loadReports() {
        const res = await fetch('/sales_data');
        const data = await res.json();
        let total = 0;
        let html = "<table><tr><th>Date</th><th>Item</th><th>Qty</th><th>Total</th></tr>";
        data.forEach(row => {
            total += row[4];
            html += `<tr><td>${row[5]}</td><td>${row[2]}</td><td>${row[3]}</td><td>₱${row[4].toFixed(2)}</td></tr>`;
        });
        document.getElementById('totalRevenue').innerText = `Total Revenue: ₱${total.toFixed(2)}`;
        document.getElementById('salesTableContainer').innerHTML = html + "</table>";
    }

    async function sell() {
        const res = await fetch('/sell', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: document.getElementById('pId').value, qty: document.getElementById('qty').value})
        });
        const result = await response = await res.json();
        alert(result.message || result.error);
        loadData();
    }

    async function addProduct() {
        await fetch('/add_product', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: document.getElementById('newName').value, stock: document.getElementById('newStock').value, price: document.getElementById('newPrice').value})
        });
        alert("Product Added!");
        loadData();
    }

    loadData();
</script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def get_data():
    conn = sqlite3.connect(DB_FILE)
    data = conn.execute("SELECT * FROM inventory").fetchall()
    conn.close()
    return jsonify(data)

@app.route('/sales_data')
def get_sales():
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
    return jsonify({"m": "ok"})

@app.route('/sell', methods=['POST'])
def sell():
    req = request.json
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT stock, price, name FROM inventory WHERE id=?", (req['id'],))
    item = cur.fetchone()
    if item and item[0] >= int(req['qty']):
        new_stock = item[0] - int(req['qty'])
        total_price = int(req['qty']) * item[1]
        cur.execute("UPDATE inventory SET stock=? WHERE id=?", (new_stock, req['id']))
        cur.execute("INSERT INTO sales (product_id, product_name, qty, total) VALUES (?,?,?,?)", (req['id'], item[2], req['qty'], total_price))
        conn.commit()
        msg = {"message": "Success!"}
    else:
        msg = {"error": "Stock unavailable!"}
    conn.close()
    return jsonify(msg)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)