from flask import Flask, render_template, request
from math import log, exp
import requests

app = Flask(__name__)

def fetch_exchange_data_for_bellman(api_key, currencies, neg_log=False):
    edges = []
    for currency in currencies:
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{currency}"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"API request failed with status code {response.status_code}")

        rates = response.json().get('conversion_rates', {})
        for currency_2 in currencies:
            if currency_2 != currency:
                rate = rates.get(currency_2, None)
                if rate is None:
                    continue
                weight = -log(rate) if neg_log else rate
                edges.append((currency, currency_2, weight))
    return edges

def bellman_ford_with_path(edges, source, nodes):
    distance = {node: float("inf") for node in nodes}
    parent = {node: None for node in nodes}
    distance[source] = 0

    for _ in range(len(nodes) - 1):
        for u, v, w in edges:
            if distance[u] + w < distance[v]:
                distance[v] = distance[u] + w
                parent[v] = u

    for u, v, w in edges:
        if distance[u] + w < distance[v]:
            arbitrage_cycle = []
            current = v
            for _ in range(len(nodes)):
                current = parent[current]

            cycle_node = current
            while True:
                arbitrage_cycle.append(current)
                current = parent[current]
                if current == cycle_node:
                    arbitrage_cycle.append(current)
                    break

            arbitrage_cycle.reverse()
            total_weight = 0.0
            for i in range(len(arbitrage_cycle) - 1):
                a = arbitrage_cycle[i]
                b = arbitrage_cycle[i + 1]
                edge_weight = next(w for (x, y, w) in edges if x == a and y == b)
                total_weight += edge_weight

            final_rate = exp(-total_weight)  # exp(-sum of -log(r))
            profit_percentage = (final_rate - 1) * 100
            return True, arbitrage_cycle, profit_percentage

    return False, None, None


@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        currencies = request.form.get('currencies')
        currency_list = [c.strip().upper() for c in currencies.split(',')]

        edges = fetch_exchange_data_for_bellman(api_key, currency_list, neg_log=True)
        has_cycle, cycle_path, profit_percentage = bellman_ford_with_path(edges, currency_list[0], currency_list)

        if has_cycle:
            result = {
                "path": " -> ".join(cycle_path),
                "profit": f"{profit_percentage:.4f}%"
            }
        else:
            result = {"path": None, "profit": None}

    return render_template('index.html', result=result)


if __name__ == '__main__':
    app.run(debug=True)
