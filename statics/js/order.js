document.addEventListener("DOMContentLoaded", async function () {
    const response = await fetch("/api/accounts")
    const accounts = await response.json()
    const accountsNode = document.getElementById("account")
    accounts.forEach(account => {
        const node = document.createElement("option")
        node.value = account.username;
        node.innerText = account.username + " | " + account.broker;
        accountsNode.append(node)
    });
});

function createTdNode(value) {
    const tdNode = document.createElement("td");
    tdNode.innerText = value;
    return tdNode;
}

async function searchStock(event) {
    const label = document.getElementById("stock-search").value;
    const response = await fetch("/api/stocks?label=" + label, {
        method: 'GET',
    })

    const table = document.getElementById("stock-search-result");
    const stocks = await response.json();
    stocks.forEach((stock) => {
        const row = document.createElement("tr");
        row.append(createTdNode(stock.label));
        row.append(createTdNode(stock.value));
        row.append(createTdNode(stock.isin));
        table.appendChild(row);
    });
}

async function submitOrder(event) {
    const price = Number.parseFloat(document.getElementById("stock-price").value);
    const count = Number.parseFloat(document.getElementById("stock-count").value);
    const isin = document.getElementById("stock-isin").value;
    const deadline = new Date(document.getElementById("deadline").value);
    const account = document.getElementById("account").value;

    const response = await fetch("/api/order", {
        method: "POST",
        body: JSON.stringify({
            username: account,
            deadline: deadline.toISOString(),
            isin: isin,
            price: price,
            count: count,
        })
    })
}
function calcTotalPrice(event) {
    const count = Number.parseFloat(document.getElementById("stock-count").value);
    const price = Number.parseFloat(document.getElementById("stock-price").value);
    document.getElementById("stock-total-price").innerHTML = price * count;
}
function dateToString(d) {
    return d.getFullYear() + " " + d.getHours() + ":" + d.getMinutes() + ":" + d.getSeconds() + "." + d.getMilliseconds()
}