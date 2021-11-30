from pydantic import BaseModel

class ShoppingListItem(BaseModel):
    id: int
    product_name: str
    amount: int
    done: bool
