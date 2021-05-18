from dataclasses import dataclass
import sqlite3

def __generate_list(lst):
    for i in __cur__.fetchall():
        name = i[0]
        emoji = i[1]
        lst.append(Item(name, emoji))

@dataclass
class Item:
    name: str
    emoji: str

def get(name):
    for item in __all_items__:
        if item.name == name:
            return item
    return None

__con__ = sqlite3.connect('objects.db')
__cur__ = __con__.cursor()

__cur__.execute('SELECT * FROM items')
__all_items__ = []
__generate_list(__all_items__)