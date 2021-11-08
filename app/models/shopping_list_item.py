from pydantic import BaseModel

class ShoppingListItem(BaseModel):
    product_name: str
    amount: int
    done: bool
