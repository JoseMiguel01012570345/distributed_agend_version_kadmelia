import json
import threading
import time

from Kademlia.utils.StoreAction import StoreAction

lock = threading.Lock()


class Event:
    def __init__(self, key, name, description, implied_users, start, end):
        self.key = key
        self.name = name
        self.description = description
        self.users_invitation = [
            {"accepted": False, "user": user} for user in implied_users
        ]
        self.start = start
        self.end = end

    def to_dict(self):
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "users_invitation": self.users_invitation,  # Ahora es una lista serializable
            "start": self.start,
            "end": self.end,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["key"],
            data["name"],
            data["description"],
            [
                item["user"] for item in data["users_invitation"]
            ],  # Convertir de vuelta a usuarios implicados
            data["start"],
            data["end"],
        )

    def __eq__(self, o):
        return self.key == o.key

    def __hash__(self):
        return int(self.name, 16)


class User:
    def __init__(self, name, passw, id):
        self.name = name
        self.passw = passw
        self.id = id

    def to_dict(self):
        return {
            "name": self.name,
            "passw": self.passw,
            "id": self.id,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["name"], data["passw"], data["id"])

    def __eq__(self, o):
        return self.id == o.id

    def __str__(self):
        return f"{{name:{self.name},password:{self.passw}, id:{self.id}}}"


class Group:
    def __init__(self, id, users, events, user_jerarquy):
        self.id = id
        self.users = users
        self.users_jerarquy = user_jerarquy
        self.events = events

    def to_dict(self):
        return {
            "users": [user.to_dict() for user in self.users],
            "users_jerarquy": self.users_jerarquy,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, data):
        users = [User.from_dict(user_data) for user_data in data["users"]]
        events = [Event.from_dict(event_data) for event_data in data["events"]]
        return cls(users, events, data["users_jerarquy"])


class DataBaseManager:
    def __init__(self):
        self.saved = {"users": [], "events": [], "groups": []}

        loaded = self.load_from_json("/tmp/data/data.json")
        if loaded:
            self.saved = loaded
        self.actions_registered = []

    def get_all(self, entity, filter=None):
        if filter is not None:
            selected = []
            match = True
            for element in self.saved[entity]:
                for field, value in filter.items():
                    if value != getattr(element, field):
                        match = False
                if match:
                    selected.append(frozenset(element.to_dict().items()))
            return selected
        return [frozenset(element.to_dict().items()) for element in self.saved[entity]]

    def get_by_id(self, entity, id):
        element = None
        with lock:
            for el in self.saved[entity]:
                if el.id == id:
                    element = el
                    break
        return element.to_dict() if element else None

    def make_action(self, action: StoreAction, entity, data, order: int):
        with lock:
            self.actions_registered.append((action, entity, data, order))
            self.actions_registered.sort(key=lambda x: x[3])

        action, entity, data, _ = self.actions_registered.pop()
        if action == StoreAction.INSERT:
            self.add_element(entity, data)
        elif action == StoreAction.UPDATE:
            if data not in self.saved[entity]:
                self.saved[entity].append(data)
            else:
                self.saved[entity] = [
                    data if item.id == data.id else item for item in self.saved[entity]
                ]
        elif action == StoreAction.DELETE:
            self.saved[entity].remove(data)
        self.saved_to_json("/tmp/data/data.json")

    def add_element(self, entity, data):
        self.saved[entity].append(data)

    def to_dafter(self):
        return {
            "users": [user.to_dict() for user in self.saved["users"]],
            "events": [event.to_dict() for event in self.saved["events"]],
            "groups": [group.to_dict() for group in self.saved["groups"]],
        }

    @classmethod
    def from_dict(cls, data):
        manager = cls()
        manager.saved = {
            "users": [User.from_dict(user_data) for user_data in data["users"]],
            "events": [Event.from_dict(event_data) for event_data in data["events"]],
            "groups": [Group.from_dict(group_data) for group_data in data["groups"]],
        }
        return manager

    # Métodos para guardar y cargar en JSON
    def saved_to_json(self, filename):
        with open(filename, "w") as f:
            json.dump(self.to_dafter(), f, indent=2)

    @classmethod
    def load_from_json(cls, filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            print(f"Error loading from JSON: {e}")
            return None
