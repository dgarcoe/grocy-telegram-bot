import requests

from urllib.parse import urljoin

from .models.chore import Chore
from .models.shopping_list_item import ShoppingListItem


class Grocy:

    def __init__(self,config):
        self._host = config.GROCY_HOST.value
        self._port = config.GROCY_PORT.value
        self._api_key = config.GROCY_API_KEY.value

        self._base_url = "{}:{}/api/".format(self._host, self._port)
        self._headers = {"accept": "application/json", "GROCY-API-KEY": self._api_key}

    def _do_get_request(self, end_url: str, params={}):

        req_url = urljoin(self._base_url, end_url)
        resp = requests.get(req_url, headers=self._headers, params=params)

        if resp.status_code >= 400:
            raise Exception("Error doing GET request: {}".format(resp.status_code))

        if len(resp.content) > 0:
            return resp.json()

    def _do_post_request(self, end_url: str, param: dict):

        req_url = urljoin(self._base_url, end_url)

        resp = requests.post(
            req_url, headers=self._headers, json=param)

        if resp.status_code >= 400:
            raise Exception("Error doing POST request: {}".format(resp.status_code))
        if len(resp.content) > 0:
            return resp.json()

    def _do_put_request(self, end_url: str, data):

        req_url = urljoin(self._base_url, end_url)

        resp = requests.put(
            req_url, headers=self._headers, data=data)

        if resp.status_code >= 400:
            raise Exception("Error doing PUT request: {}".format(resp.status_code))
        if len(resp.content) > 0:
            return resp.json()

    def get_shopping_list(self):
        shopping_list = []
        shopping_list_json = self._do_get_request("objects/shopping_list")

        for object in shopping_list_json:
            if object['product_id'] :
                product_json = self._do_get_request(urljoin("objects/products/",object['product_id']))
                product_name = product_json['name']
            else :
                product_name = object['note']
            item = ShoppingListItem(id=object['id'], product_name=product_name, amount=object['amount'],
                                    done=object['done'])
            shopping_list.append(item)

        return shopping_list

    def add_item_shopping_list(self,item: dict):

        self._do_post_request("objects/shopping_list", item)

    def clear_shopping_list(self):

        param = {"list_id": 1}

        self._do_post_request("stock/shoppinglist/clear", param)

    def mark_item_done_shopping_list(self, item_id: str):

        param = {"done": "1"}

        self._do_put_request("objects/shopping_list/"+item_id, param)

    def get_chores_list(self):

        chores_list = []
        params = {"order":"next_estimated_execution_time:asc"}
        chores_list_json = self._do_get_request("chores", params=params)

        for chore in chores_list_json:
            chore = Chore(id=chore['id'], chore_name=chore['chore_name'], last_tracked_time=chore['last_tracked_time'],
                          next_estimated_execution_time=chore['next_estimated_execution_time'],
                          next_execution_assigned_to_user_id=chore['next_execution_assigned_to_user_id'])
            chores_list.append(chore)

        return chores_list
