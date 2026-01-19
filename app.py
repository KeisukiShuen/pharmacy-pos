from flask import Flask, request, jsonify, render_template_string, session, redirect
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'gcares_secure_key_2026'

# Path for Render Persistent Disk (Use 'pharmacy.db' for local testing)
DB_FILE = os.environ.get('DB_PATH', 'pharmacy.db')

# --- USER ACCOUNTS ---
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "staff": {"password": "staff123", "role": "staff"}
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, stock INTEGER, price REAL, expiry_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, product_name TEXT, qty INTEGER, total REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# --- STYLES AND INTERFACE ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>GCares Pharmacy System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; margin: 0; color: #333; }
        .login-screen { display: flex; justify-content: center; align-items: center; height: 100vh; background: #e9ecef; }
        .login-card { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); width: 100%; max-width: 360px; text-align: center; }
        .login-logo { width: 180px; margin-bottom: 25px; }
        
        nav { background: #ffffff; padding: 10px 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); display: {{ 'flex' if logged_in else 'none' }}; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 1000; }
        .nav-brand { display: flex; align-items: center; font-weight: bold; font-size: 1.2em; color: #007bff; }
        nav a { color: #555; margin-left: 20px; text-decoration: none; font-weight: 600; transition: 0.3s; }
        nav a:hover { color: #007bff; }
        
        .container { max-width: 1000px; margin: 40px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); }
        .hidden { display: none; }
        
        input, select { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 1px solid #ddd; font-size: 1em; box-sizing: border-box; }
        button { width: 100%; padding: 14px; margin: 10px 0; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; transition: 0.3s; font-size: 1em; }
        .btn-main { background: #28a745; color: white; }
        .btn-main:hover { background: #218838; }
        .btn-select { background: #007bff; color: white; width: auto; padding: 5px 10px; font-size: 0.85em; margin: 0; }
        .btn-del { background: #dc3545; color: white; width: auto; padding: 6px 12px; font-size: 0.85em; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background: #f8f9fa; padding: 15px; text-align: left; border-bottom: 2px solid #dee2e6; }
        td { padding: 15px; border-bottom: 1px solid #eee; }
        
        .badge-low { color: #d9534f; font-weight: bold; background: #f9d6d5; padding: 3px 8px; border-radius: 5px; }
        .badge-expired { color: white; background: #dc3545; padding: 4px 8px; border-radius: 5px; font-weight: bold; }
        .badge-soon { color: #856404; background: #fff3cd; padding: 4px 8px; border-radius: 5px; font-weight: bold; }
        
        .search-bar { position: relative; }
        .search-bar input { padding-left: 45px; }
        .search-bar::before { content: "🔍"; position: absolute; left: 15px; top: 22px; color: #888; }
    </style>
</head>
<body>

{% if not logged_in %}
    <div class="login-screen">
        <div class="login-card">
            <img src="https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/GCaresText2.png" class="login-logo" alt="GCares Pharmacy">
            <form method="POST" action="/login">
                <input type="text" name="username" placeholder="Username" required autofocus>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit" class="btn-main" style="background: #007bff;">Login to POS</button>
            </form>
        </div>
    </div>
{% else %}
    <nav>
        <div class="nav-brand">
            <img src="https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/GCaresText2.png" style="height: 35px; margin-right: 10px;">
            GCares
        </div>
        <div>
            <a href="javascript:void(0)" onclick="showPage('pos')">🛒 Checkout</a>
            {% if role == 'admin' %}
            <a href="javascript:void(0)" onclick="showPage('admin')">⚙️ Inventory</a>
            <a href="javascript:void(0)" onclick="showPage('reports')">📊 Reports</a>
            {% endif %}
            <a href="/logout" style="color: #dc3545;">Logout</a>
        </div>
    </nav>

    <div class="container" id="posPage">
        <h2>Sales Transaction</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr auto; gap: 15px; align-items: center;">
            <input type="text" id="pId" placeholder="Selected Item ID (Select from list below)" readonly style="background: #e9ecef;">
            <input type="number" id="qty" placeholder="Enter Quantity">
            <button onclick="sell()" class="btn-main" style="width: 150px;">Process Sale</button>
        </div>
        <div class="search-bar">
            <input type="text" id="posSearch" placeholder="Type medicine name to find it..." onkeyup="filterTable('posTable', 'posSearch')">
        </div>
        <div id="posTable"></div>
    </div>

    <div class="container hidden" id="adminPage">
        <h2>Inventory Management</h2>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
            <h4 style="margin-top: 0;">Add New Stock</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <input type="text" id="newName" placeholder="Medicine Name">
                <input type="number" id="newPrice" placeholder="Price (₱)">
                <input type="number" id="newStock" placeholder="Stock Level">
                <input type="date" id="newExpiry">
            </div>
            <button onclick="addProduct()" class="btn-main" style="background: #007bff;">Save Product</button>
        </div>
        <div class="search-bar" style="margin-top: 20px;">
            <input type="text" id="adminSearch" placeholder="Search inventory..." onkeyup="filterTable('adminTable', 'adminSearch')">
        </div>
        <div id="adminTable"></div>
    </div>

    <div class="container hidden" id="reportsPage">
        <div style="text-align: center;">
            <p style="color: #666; margin: 0;">Total Revenue Generated</p>
            <h1 id="revenueText" style="color: #28a745; margin: 10px 0;">₱0.00</h1>
        </div>
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
        renderTable(data, 'posTable', false);
        if(document.getElementById('adminTable')) renderTable(data, 'adminTable', true);
    }

    function selectItem(id, name) {
        document.getElementById('pId').value = id;
        document.getElementById('qty').focus();
        // Visual feedback
        alert("Selected: " + name);
    }

    function renderTable(data, containerId, isAdmin) {
        const now = new Date();
        const nextMonth = new Date();
        nextMonth.setDate(now.getDate() + 30);

        let html = `<table><tr><th>ID</th><th>Name</th><th>Stock</th><th>Price</th><th>Expiry</th><th>Action</th></tr><tbody id="${containerId}_body">`;
        data.forEach(r => {
            const exp = r[4] ? new Date(r[4]) : null;
            let badge = r[4] || 'N/A';
            if(exp) {
                if(exp < now) badge = `<span class="badge-expired">Expired</span>`;
                else if(exp <= nextMonth) badge = `<span class="badge-soon">${r[4]}</span>`;
            }
            let stockClass = r[2] < 10 ? 'class="badge-low"' : '';
            
            html += `<tr>
                <td>${r[0]}</td>
                <td style="font-weight: bold;">${r[1]}</td>
                <td><span ${stockClass}>${r[2]}</span></td>
                <td>₱${parseFloat(r[3]).toFixed(2)}</td>
                <td>${badge}</td>
                <td>
                    ${isAdmin ? 
                        `<button class="btn-del" onclick="deleteItem(${r[0]})">Delete</button>` : 
                        `<button class="btn-select" onclick="selectItem(${r[0]}, '${r[1]}')">Select</button>`
                    }
                </td>
            </tr>`;
        });
        document.getElementById(containerId).innerHTML = html + "</tbody></table>";
    }

    function filterTable(tableId, inputId) {
        let filter = document.getElementById(inputId).value.toUpperCase();
        let rows = document.getElementById(tableId + "_body").getElementsByTagName("tr");
        for (let row of rows) {
            let name = row.getElementsByTagName("td")[1].textContent.toUpperCase();
            row.style.display = name.includes(filter) ? "" : "none";
        }
    }

    async function sell() {
        const id = document.getElementById('pId').value;
        const qty = document.getElementById('qty').value;
        if(!id || !qty) return alert("Please select a medicine from the list and enter quantity.");

        const res = await fetch('/sell', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id, qty})
        });
        const result = await res.json();
        if(result.error) alert(result.error);
        else { 
            alert(result.message); 
            document.getElementById('pId').value = "";
            document.getElementById('qty').value = "";
            loadData(); 
        }
    }

    async function addProduct() {
        const name = document.getElementById('newName').value;
        const price = document.getElementById('newPrice').value;
        const stock = document.getElementById('newStock').value;
        const expiry = document.getElementById('newExpiry').value;
        
        if(!name || !price || !stock) return alert("Please fill Name, Price, and Stock");

        await fetch('/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, price, stock, expiry})
        });
        alert("Medicine added successfully!");
        loadData();
    }

    async function deleteItem(id) {
        if(confirm("Permanently delete this item from inventory?")) {
            await fetch('/delete/' + id, { method: 'POST' });
            loadData();
        }
    }

    async function loadReports() {
        const res = await fetch('/reports_data');
        const data = await res.json();
        let total = 0;
        let html = "<table><tr><th>Date</th><th>Product</th><th>Qty</th><th>Total</th></tr>";
        data.forEach(r => {
            total += r[4];
            html += `<tr><td>${r[5].substring(0,16)}</td><td>${r[2]}</td><td>${r[3]}</td><td>₱${r[4].toFixed(2)}</td></tr>`;
        });
        document.getElementById('revenueText').innerText = "₱" + total.toFixed(2);
        document.getElementById('salesTable').innerHTML = html + "</table>";
    }

    {% if logged_in %} loadData(); {% endif %}
</script>
</body>
</html>
'''
# ... [Rest of the Python Server Routes remain the same as the previous step]