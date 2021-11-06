import requests

from urllib.parse import urljoin

from models.shopping_list_item import ShoppingListItem


class Grocy:

    def __init__(self,config):
        self._host = config.GROCY_HOST.value
        self._port = config.GROCY_PORT.value
        self._api_key = config.GROCY_API_KEY.value

        self._base_url = "{}:{}/api/".format(self._host, self._port)
        self._headers = {"accept": "application/json", "GROCY-API-KEY": self._api_key}

    def _do_get_request(self, end_url: str):

        req_url = urljoin(self._base_url, end_url)
        resp = requests.get(req_url, headers=self._headers)

        if resp.status_code >= 400:
            #raise error
            print(resp.status_code)

        if len(resp.content) > 0:
            return resp.json()

    def get_shopping_list(self):
        shopping_list = []
        shopping_list_json = self._do_get_request("objects/shopping_list")
        
        for object in shopping_list_json:
            if object['product_id'] != None:
                product_json = self._do_get_request(urljoin("objects/products/",object['product_id']))
                product_name = product_json['name']
            else :
                product_name = object['note']
            item = ShoppingListItem(product_name=product_name,amount=int(object['amount']),
                                    done=True if '1' else False)
            shopping_list.append(item)

        return shopping_list
