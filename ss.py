# script main
import json
import websockets
import asyncio
import ssl

users = {}
map = {}
async def handle_login(data, connection):
    if data['name'] in users:
        msg= await sendTo(connection, {"type": "server_login", "success": False})
        print(msg)
        print('login failed')
    else:
        #connection details
        users[data["name"]] = connection
        connection.name = data["name"]
        connection.otherName = None
        # store the connection name in the userlist
        map[data["name"]] = "online"
        # send response to client back with login success
        await sendTo(connection, {"type": "server_login", "success": True})
        print("Login success")
        # send updated user lists to all users
        for i in users:
            await sendUpdatedUserlist(users[i], list(map.items()))

async def handle_answer(data):
    # Get the peer user connection details
    conn = users[data["name"]]
    if conn is not None:
        # Send the answer back to requested user
        await sendTo(conn, {"type": "server_answer", "answer": data["answer"]})

async def handle_offer(data, connection):
    # Check the peer user has logged in the server
    if data["name"] in users:
        # Get the peer connection from array
        conn = users[data["name"]]
        if conn is None:
            await sendTo(connection, {"type": "server_nouser", "success": False})
        elif conn.otherName is None:
            # When user is free and availble for the offer
            await sendTo(conn, { "type": "server_offer", "offer": data["offer"], "name": connection.name });
        else:
            #User can't accept the offer
            await sendTo(connection, {"type": "server_alreadyinroom", "success": True, "name": data["name"]})
    else:
        # Error handling with invalid query
        print("offer -> server_nouser")
        await sendTo(connection, {"type": "server_nouser", "success": False})

async def handle_candidate(data):
    # Get connection details
    conn = users[data["name"]]
    if conn is not None:
        # Send candidate details to user
        await sendTo(conn, {"type": "server_candidate", "candidate": data["candidate"]})

async def handle_leave(data, connection):
    # Get connection details
    conn = users[data["name"]]
    if conn is not None:
        # Send response back to users who are in the room
        await sendTo(conn, {"type": "server_userwanttoleave"})
        await sendTo(connection, {"type": "server_userwanttoleave"})
        map[data["name"]] = "online"
        map[connection.name] = "online"
        # Update the connection status with available
        conn.otherName = None
        connection.otherName = None
        for i in users:
            await sendUpdatedUserlist(users[i], list(map.items()))
        print("end room")

async def handle_busy(data):
    # Get connection details
    conn = users.get(data["name"])
    if conn != None:
        # Send response back to user
        await sendTo(conn, { "type": "server_busyuser" })

async def handle_want_to_call(data, connection):
    conn = users.get(data["name"])
    if conn != None:
        if conn.otherName != None and map[data["name"]] == "busy":
            # User is in the room, User can't accept the offer
            await sendTo(connection, { "type": "server_alreadyinroom", "success": True, "name": data["name"] })
        else:
            # User is available, User can accept the offer
            await sendTo(connection, { "type": "server_alreadyinroom", "success": False, "name": data["name"] })
    else:
        # Error handling with invalid query
        await sendTo(connection, { "type": "server_nouser", "success": False })

async def handle_ready(data, connection):
    # Get connection details
    conn = users[data["name"]]
    if conn is not None:
        # Update the user status with peer name
        connection.otherName = data["name"]
        conn.otherName = connection.name
        map[data["name"]] = "busy"
        map[connection.name]= "busy"
        # Send response to each users
        await sendTo(conn, {"type": "server_userready", "success": True, "peername": connection.name})
        await sendTo(connection, {"type": "server_userready", "success": True, "peername": conn.name})
        # Send updated user list to all existing users
        for i in users:
            await sendUpdatedUserlist(users[i], list(map.items()))

async def handle_quit(data, connection):
    # Get the user details
    if "name" in data:
        quit_user = data["name"]
        del users[connection.name]
        map.__delitem__(quit_user)
        # Send updated user list to all existing users
        for i in users:
            await sendUpdatedUserlist(users[i], list(map.items()))

async def handle_close(connection):
    print("leaving")
    if connection.name:
        quit_user = connection.name
        # Remove from the connection
        del users[connection.name]
        map.__delitem__(quit_user)
        if connection.otherName:
            # when user is inside the room with peer user
            conn = users[connection.otherName]
            if conn is not None:
                # Update the details
                conn.otherName = None
                connection.otherName = None
                # Send the response back to peer user
                await sendTo(conn, { "type": "server_exitfrom" })
                map[conn.name]="online"
        # Send the updated userlist to all the existing users 
        for i in users:
            await sendUpdatedUserlist(users[i], list(map.items()))

async def sendUpdatedUserlist(conn, message):
    await conn.send(json.dumps({ "type": "server_userlist", "name": message }))

async def sendTo(conn, message):
    await conn.send(json.dumps(message))

def checkisJson(str):
    try:
        json.loads(str)
    except ValueError:
        return False
    return True

async def on_connection(connection):
    # Sucessful connection
    print("User has connected")
    async for message in connection:
        try:
            data=json.loads(message)
        except json.JSONDecodeError:
            if message == "clientping":
                await sendTo(connection, { "type": "server_pong", "name": "pong" })
            continue
        # Parse the messages from client 
        message_type=data.get("type")
        if message_type == "login":
            # Login request from client 
            await handle_login(data, connection)
        elif message_type == "offer":
            # Offer request from client
            await handle_offer(data, connection)
        elif message_type == "answer":
            # Answer request from client
            await handle_answer(data)
        elif message_type == "candidate":
            # Candidate request 
            await handle_candidate(data)
        elif message_type == "leave":
            # When user want to leave from room 
            await handle_leave(data, connection)
        elif message_type == "busy":
            # When user reject the offer 
            await handle_busy(data)
        elif message_type == "want_to_call":
            await handle_want_to_call(data, connection)
        elif data['type'] == "ready":
            # Once offer and answer are exchanged, ready for a room 
            await handle_ready(data, connection)
        elif message_type == "quit":
            # User quit/signout 
            await handle_quit(data, connection)
        else:
            await sendTo(connection, { "type": "server_error", "message": "Unrecognized command: " + data["type"] })
    on_close(connection)      

# When socket connection is closed 
async def on_close(connection):
    await handle_close(connection)
    print("User has disconnected")

async def start_server():
    # ssl_cert = "./cert.pem"
    # ssl_key = "./key.pem"
    # ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    # ssl_context.load_cert_chain(ssl_cert, keyfile=ssl_key)
    async with websockets.serve(on_connection, "0.0.0.0", 8000, #ssl=ssl_context
                                ):
        print("server started")
        await asyncio.Future()
        
asyncio.run(start_server())


