import requests

def get_woolworths_deals():

    url = "https://www.woolworths.com.au/apis/ui/browse/category"

    params = {
        "categoryId": "0",
        "pageNumber": 1,
        "pageSize": 30,
        "sortType": "Special"
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(url, params=params, headers=headers, timeout=20)

    data = r.json()

    deals = {}

    try:
        products = data["Bundles"]

        for item in products:
            name = item.get("Name")
            price = item.get("Price")

            if name and price:
                deals[name] = f"{price}"

    except:
        pass

    return deals
