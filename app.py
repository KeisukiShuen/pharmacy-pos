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
        input, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #ddd; box-sizing: border-box; font-size: 1rem; }
        button { background: var(--success); color: white; border: none; font-weight: bold; cursor: pointer; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 15px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #f8f9fa; font-size: 0.9rem; text-transform: uppercase; color: #666; }
        
        .low-stock { color: var(--danger); font-weight: bold; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; }
        .expired { background: #f8d7da; color: #721c24; }
        .soon { background: #fff3cd; color: #856404; }
        
        .search-input { padding-left: 40px; background: white url('https://www.w3schools.com/howto/searchicon.png') no-repeat 13px center; background-size: 16px; }
        .btn-sm { width: auto; padding: 6px 12px; font-size: 0.85rem; margin: 0; }
        .btn-blue { background: var(--primary); }
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
        <div class="nav-brand">
            <img src="https://raw.githubusercontent.com/KeisukiShuen/pharmacy-pos/refs/heads/main/GCaresText2.png" style="height: 40px; margin-right: 10px;">
            GCares
        </div>
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
            <input type="text" id="selectedName" placeholder="Selected Medicine Name" readonly style="background: #f0f0f0;">
            <input type="number" id="qty" placeholder="Quantity to Sell">
            <input type="hidden" id="pId"> 
            <button onclick="sell()" style="width: 180px;">Complete Sale</button>
        </div>
        <hr style="margin: 25px 0; border: 0; border-top: 1px solid #eee;">
        <input type="text" id="posSearch" class="search-input" placeholder="Type medicine name to search..." onkeyup="filterTable('posTable', 'posSearch')">
        <div id="posTable"></div>
    </div>

    <div class="container hidden" id="adminPage">
        <h2>Inventory Management</h2>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 25px; border: 1px solid #eee;">
            <h4>Add New Stock</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <input type="text" id="newName" placeholder="Medicine Name">
                <input type="number" id="newPrice" placeholder="Price (₱)">
                <input type="number" id="newStock" placeholder="Stock Level">
                <input type="date" id="newExpiry">
            </div>
            <button onclick="addProduct()" style="background: var(--primary); margin-top: 15px;">Add Product</button>
        </div>
        <input type="text" id="adminSearch" class="search-input" placeholder="Search inventory..." onkeyup="filterTable('adminTable', 'adminSearch')">
        <div id="adminTable"></div>
    </div>

    <div class="container hidden" id="reportsPage">
        <div style="text-align: center; background: #e7f3ff; padding: 25px; border-radius: 15px; margin-bottom: 30px;">
            <h2 style="margin:0; color: var(--success);" id="revenueText">₱0.00</h2>
            <p style="margin:0; color: #666;">Total Sales Revenue</p>
        </div>
        <div id="salesTable"></div>
    </div>
{% endif %}

<script>
    function showPage(page) {
        document.querySelectorAll('.container').forEach(c => c.classList.add('hidden'));
        document.getElementById(page + 'Page').classList.remove('hidden');
        loadData();
    }

    async function loadData() {
        const res = await fetch('/data');
        const data = await res.json();
        renderTable(data, 'posTable', false);
        if(document.getElementById('adminTable')) renderTable(data, 'adminTable', true);
    }

    function selectItem(id, name) {
        document.getElementById('pId').value = id;
        document.getElementById('selectedName').value = name;
        document.getElementById('qty').focus();
    }

    function renderTable(data, containerId, isAdmin) {
        const now = new Date();
        const soon = new Date(); soon.setDate(now.getDate() + 30);

        let html = `<table><thead><tr><th>Medicine Name</th><th>Remaining Stock</th><th>Price</th><th>Expiry</th><th>Action</th></tr></thead><tbody id="${containerId}_body">`;
        data.forEach(r => {
            const exp = r[4] ? new Date(r[4]) : null;
            let expBadge = r[4] || 'N/A';
            if(exp) {
                if(exp < now) expBadge = `<span class="badge expired">Expired</span>`;
                else if(exp <= soon) expBadge = `<span class="badge soon">${r[4]}</span>`;
            }
            let stockDisplay = r[2] < 10 ? `<span class="low-stock">${r[2]} (Low)</span>` : r[2];
            
            html += `<tr><td style="font-weight: bold;">${r[1]}</td><td>${stockDisplay}</td><td>₱${r[3].toFixed(2)}</td><td>${expBadge}</td><td>
                ${isAdmin ? `<button class="btn-sm btn-red" onclick="deleteItem(${r[0]})" style="background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 5px;">Delete</button>` : `<button class="btn-sm btn-blue" onclick="selectItem(${r[0]}, '${r[1]}')">Select Name</button>`}
            </td></tr>`;
        });
        document.getElementById(containerId).innerHTML = html + "</tbody></table>";
    }

    function filterTable(tid, sid) {
        let input = document.getElementById(sid).value.toUpperCase();
        let rows = document.getElementById(tid + "_body").getElementsByTagName("tr");
        for (let row of rows) {
            let txt = row.getElementsByTagName("td")[0].textContent.toUpperCase();
            row.style.display = txt.includes(input) ? "" : "none";
        }
    }

    async function sell() {
        const id = document.getElementById('pId').value;
        const qty = document.getElementById('qty').value;
        if(!id || !qty) return alert("Please select a medicine by name first!");
        const res = await fetch('/sell', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, qty}) });
        const result = await res.json();
        if(result.error) alert(result.error); else { 
            alert(result.message); 
            document.getElementById('selectedName').value = "";
            document.getElementById('pId').value = "";
            document.getElementById('qty').value = "";
            loadData(); 
        }
    }

    async function addProduct() {
        const name = document.getElementById('newName').value;
        const stock = document.getElementById('newStock').value;
        const price = document.getElementById('newPrice').value;
        const expiry = document.getElementById('newExpiry').value;
        if(!name || !stock || !price) return alert("Fill Name, Stock, and Price!");
        await fetch('/add', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name, stock, price, expiry}) });
        loadData();
    }

    async function deleteItem(id) {
        if(confirm("Delete this medicine?")) {
            await fetch('/delete/' + id, { method: 'POST' });
            loadData();
        }
    }

    async function loadReports() {
        const res = await fetch('/sales_data');
        const data = await res.json();
        let total = 0;
        let html = "<table><thead><tr><th>Date</th><th>Item</th><th>Qty</th><th>Total</th></tr></thead>";
        data.forEach(r => { total += r[4]; html += `<tr><td>${r[5].substring(0,16)}</td><td>${r[2]}</td><td>${r[3]}</td><td>₱${r[4].toFixed(2)}</td></tr>`; });
        document.getElementById('revenueText').innerText = "₱" + total.toFixed(2);
        document.getElementById('salesTable').innerHTML = html + "</table>";
    }
    {% if logged_in %} loadData(); {% endif %}
</script>
</body>
</html>
'''

# ... [Back-end routes remain identical to previous version]