import json
from Database.database_connectiom import Event, User, Group
from Kademlia.KBucket import sha1_hash
from Kademlia.utils.StoreAction import StoreAction
from KademliaNodeInit import init_node
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import io
import time
import threading
from pydub import AudioSegment

# el send es para enviar eventos sin nombreado y el emit tiene nombrado
from flask_socketio import SocketIO, send, emit

kademliaNode = init_node()

UPLOAD_FOLDER = "uploads"


def create_app():
    global kademliaNode
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    @app.route("/")
    def index():
        # Leer el contenido del archivo /tmp/data/store.json
        response = (
            "<h6>Informacion del nodo"
            + f" {kademliaNode.ip}, de ip:  "
            + f" {kademliaNode.id}</h6>"
        )

        response += "<h4>Nodos Conocidos</h4>"
        for node in kademliaNode.routing_table.get_all_nodes():
            response += "<ul>"
            response += (
                f"<li>{kademliaNode.routing_table.get_bucket_index(node.id)} :"
                + f" {node.ip}</li>"
            )
            response += "</ul>"

        response += "<h3>Contenido</h3>"
        for key, elem in kademliaNode.database.saved.items():
            response += f"<b>{key}</b>"
            response += "<ul>"
            for data in elem:
                response += f"<li>{data}</li>"
            response += "</ul>"

        return response

    @app.route("/auth", methods=["POST"])
    def authenticate_user():
        data = request.get_json()
        username = data["username"]
        password = data["password"]

        users = kademliaNode.get_all("users", {"name": username, "passw": password})
        if len(users) > 0:
            return jsonify(users), 200  # Devolver el evento creado
        else:
            return "error", 404

    # Ruta para crear un Event
    @app.route("/create_event", methods=["POST"])
    def create_event():
        try:
            data = request.get_json()
            # Crear un nuevo evento a partir del JSON recibido
            event = Event(
                key=f"{time.time()}",
                name=data["name"],
                description=data["description"],
                implied_users=data["implied_users"],
                start=data["start"],
                end=data["end"],
            )
            kademliaNode.store_data(StoreAction.INSERT, "events", event)
            return jsonify(event.to_dict()), 201  # Devolver el evento creado
        except KeyError as e:
            return jsonify({"error": f"Missing field: {str(e)}"}), 400

    # Ruta para crear un User
    @app.route("/create_user", methods=["POST"])
    def create_user():
        try:
            data = request.get_json()
            # Crear un nuevo usuario a partir del JSON recibido
            user = User(
                name=data["name"],
                passw=data["passw"],
                id=f"{data['name']}:{time.time()}",
            )
            kademliaNode.store_data(StoreAction.INSERT, "users", user)
            return jsonify(user.to_dict()), 201  # Devolver el usuario creado
        except KeyError as e:
            return jsonify({"error": f"Missing field: {str(e)}"}), 400

    # Ruta para crear un Group
    @app.route("/create_group", methods=["POST"])
    def create_group():
        try:
            data = request.get_json()
            # Crear una lista de usuarios
            users = [User.from_dict(user_data) for user_data in data["users"]]
            # Crear una lista de eventos
            events = [Event.from_dict(event_data) for event_data in data["events"]]
            # Crear el grupo a partir del JSON recibido
            group = Group(
                id=f"{time.time()}",
                users=users,
                events=events,
                user_jerarquy=data["user_jerarquy"],
            )
            kademliaNode.store_data(StoreAction.INSERT, "groups", group)
            return jsonify(group.to_dict()), 201  # Devolver el grupo creado
        except KeyError as e:
            return jsonify({"error": f"Missing field: {str(e)}"}), 400

    # ------- ENDPOINTS GET -----------

    # # Ruta para obtener todos los eventos
    @app.route("/events", methods=["GET"])
    def get_all_events():
        data = request.get_json()
        events = kademliaNode.get_all("events", data["filter"])
        return jsonify(events), 200

    # # Ruta para obtener evento por ID (key)
    @app.route("/events/<key>", methods=["GET"])
    def get_event_by_id(key):
        event = kademliaNode.get_data("event", key)
        if event:
            return jsonify(event.to_dict()), 200
        else:
            return jsonify({"error": "Event not found"}), 404

    # Ruta para obtener todos los usuarios
    @app.route("/users", methods=["POST"])
    def get_all_users():
        data = request.get_json()
        users = kademliaNode.get_all("users", data["filter"])
        return jsonify(users), 200

    # Ruta para obtener usuario por ID
    @app.route("/users/<id>", methods=["GET"])
    def get_user_by_id(id):
        user = kademliaNode.get_data("users", id)
        if user:
            return jsonify(user), 200
        else:
            return jsonify({"error": "User not found"}), 404

    # Ruta para obtener todos los grupos
    @app.route("/groups", methods=["POST"])
    def get_all_groups():
        data = request.get_json()
        groups = kademliaNode.get_all("groups", data["filter"])
        return jsonify(groups), 200

    # Ruta para obtener grupo por ID
    @app.route("/groups/<int:id>", methods=["GET"])
    def get_group_by_id(id):
        group = kademliaNode.get_data("group", id)
        if group:
            return jsonify(group), 200
        else:
            return jsonify({"error": "Group not found"}), 404

    # ------- PUT: Actualizar entidades -----------

    # Actualizar un evento por ID (key)
    @app.route("/events", methods=["PUT"])
    def update_event():
        data = request.get_json()
        old_event = kademliaNode.get_data("events", data["key"])
        if old_event is None:
            return jsonify({"error": "Event not found"}), 404
        save_event = Event(
            key=data.get("key"),
            name=data.get("name", old_event["key"]),
            description=data.get("description", old_event["description"]),
            implied_users=data.get("implied_users", old_event["users_invitation"]),
            start=data.get("start", old_event["start"]),
            end=data.get("end", old_event["end"]),
        )

        event = kademliaNode.store_data(StoreAction.UPDATE, "events", save_event)
        if event:
            return jsonify(event), 200
        else:
            return jsonify({"error": "Event not found"}), 404

    # Actualizar un usuario por ID
    @app.route("/users", methods=["PUT"])
    def update_user():
        data = request.get_json()
        old_user = kademliaNode.get_data("users", data["id"])
        if old_user is None:
            return jsonify({"error": "User not found"}), 404

        save_user = User(
            name=data.get("name", old_user["name"]),
            passw=data.get("passw", old_user["passw"]),
            id=data["id"],
        )

        user = kademliaNode.store_data(StoreAction.UPDATE, "users", save_user)
        if user:
            # Actualizar los campos del usuario
            return jsonify(user), 200
        else:
            return jsonify({"error": "User not found"}), 404

    # Actualizar un grupo por ID
    @app.route("/groups", methods=["PUT"])
    def update_group():
        data = request.get_json()
        old_group = kademliaNode.get_data("groups", data["id"])
        if old_group is None:
            return jsonify({"error": "Group not found"}), 404
        save_group = Group(
            users=[
                User.from_dict(user_data)
                for user_data in data.get(
                    "users", [user.to_dict() for user in old_group["users"]]
                )
            ],
            events=[
                Event.from_dict(event_data)
                for event_data in data.get(
                    "events",
                    [event.to_dict() for event in old_group["events"]],
                )
            ],
            user_jerarquy=data.get("user_jerarquy", old_group["user_jerarquy"]),
        )
        group = kademliaNode.store_data(StoreAction.UPDATE, "groups", save_group)
        if group:
            # Actualizar los campos del grupo
            return jsonify(group), 200
        else:
            return jsonify({"error": "Group not found"}), 404

    # ------- DELETE: Eliminar entidades -----------

    # Eliminar un evento por ID (key)
    @app.route("/events/<id>", methods=["DELETE"])
    def delete_event(id):
        to_delete_event = Event(
            key=id, name=None, description=None, implied_users=[], start=None, end=None
        )
        event = kademliaNode.store_data(StoreAction.DELETE, "events", to_delete_event)
        if event:
            return jsonify({"message": "Event deleted"}), 200
        else:
            return jsonify({"error": "Event not found"}), 404

    # Eliminar un usuario por ID
    @app.route("/users/<id>", methods=["DELETE"])
    def delete_user(id):
        to_delete_user = User(None, None, id)
        user = kademliaNode.store_data(StoreAction.DELETE, "users", to_delete_user)
        if user:
            return jsonify({"message": "User deleted"}), 200
        else:
            return jsonify({"error": "User not found"}), 404

    # Eliminar un grupo por ID
    @app.route("/groups/<id>", methods=["DELETE"])
    def delete_group(id):
        to_delete_group = Group(id, [], [], [])
        group = kademliaNode.store_data(StoreAction.DELETE, "groups", to_delete_group)
        if group:
            return jsonify({"message": "Group deleted"}), 200
        else:
            return jsonify({"error": "Group not found"}), 404

    app.run(
        host=kademliaNode.ip,
        port=54321,
        debug=True,
    )


create_app()
