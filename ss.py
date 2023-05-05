import json
import websockets
import asyncio

users = {}
map = {}

async def handle_login(data, connection):
    try:
        if data['name'] in users:
            msg= await sendTo(connection, {"type": "server_login", "success": False})
            print('login failed')
        else:
            #connection details
            users[data["name"]] = connection
            connection.name = data["name"]
            connection.otherName = None
            print(data["name"])
            # store the connection name in the userList
            map[data["name"]] = "online"
            # send response to client back with login success
            await sendTo(connection, {"type": "server_login", "success": True})
            print("Login success")
            # send updated user lists to all users
            for i in users:
                await sendUpdatedUserlist(users[i], list(map.items()))
    except Exception as e:
        print("handle login error",e)

async def handle_answer(data):
    try:
        # Get the peer user connection details
        conn = users[data["name"]]
        if conn is not None:
            # Send the answer back to requested user
            await sendTo(conn, {"type": "server_answer", "answer": data["answer"]})
            print("answer sended")
    except Exception as e:
        print("handle answer error",e)

async def handle_offer(data, connection):
    try:
        # Check the peer user has logged in the server
        if data["name"] in users:
            # Get the peer connection from array
            conn = users[data["name"]]
            if conn is None:
                await sendTo(connection, {"type": "server_no_user", "success": False})
            elif conn.otherName is None:
                # When user is free and available for the offer
                await sendTo(conn, { "type": "server_offer", "offer": data["offer"], "name": connection.name })
                print("offer sended")
            else:
                #User can't accept the offer
                await sendTo(connection, {"type": "server_already_in_room", "success": True, "name": data["name"]})
        else:
            # Error handling with invalid query
            await sendTo(connection, {"type": "server_no_user", "success": False})
    except Exception as e:
        print("handle offer error",e)
        

async def handle_candidate(data):
    try:
        # Get connection details
        conn = users[data["name"]]
        if conn is not None:
            # Send candidate details to user
            await sendTo(conn, {"type": "server_candidate", "candidate": data["candidate"]})
            print("candidate details sended")
    except Exception as e:
        print("handle candidate error",e)

async def handle_leave(data, connection):
    try:
        # Get connection details
        conn = users[data["name"]]
        if conn is not None:
            # Send response back to users who are in the room
            await sendTo(conn, {"type": "server_user_want_to_leave"})
            await sendTo(connection, {"type": "server_user_want_to_leave"})
            map[data["name"]] = "online"
            map[connection.name] = "online"
            # Update the connection status with available
            conn.otherName = None
            connection.otherName = None
            for i in users:
                await sendUpdatedUserlist(users[i], list(map.items()))
            print("end room")
    except Exception as e:
        print("handle leave error",e)

async def handle_busy(data):
    try:
        # Get connection details
        conn = users(data["name"])
        if conn != None:
            # Send response back to user
            await sendTo(conn, { "type": "server_busy_user" })
            print("busy")
    except Exception as e:
        print("handle busy error",e)

async def handle_want_to_call(data, connection):
    try:
        # Get connection details
        conn = users[data["name"]]
        if conn != None:
            if conn.otherName != None and map[data["name"]] == "busy":
                # User is in the room, User can't accept the offer
                await sendTo(connection, { "type": "server_already_in_room", "success": True, "name": data["name"] })
            else:
                # User is available, User can accept the offer
                await sendTo(connection, { "type": "server_already_in_room", "success": False, "name": data["name"] })
                print("want to call")
        else:
            # Error handling with invalid query
            await sendTo(connection, { "type": "server_already_in_room", "success": False })
    except Exception as e:
        print("handle want to call error",e)

async def handle_ready(data, connection):
    try:
        # Get connection details
        conn = users[data["name"]]
        if conn is not None:
            # Update the user status with peer name
            connection.otherName = data["name"]
            conn.otherName = connection.name
            map[data["name"]] = "busy"
            map[connection.name]= "busy"
            # Send response to each users
            await sendTo(conn, {"type": "server_user_ready", "success": True, "peer_name": connection.name})
            await sendTo(connection, {"type": "server_user_ready", "success": True, "peer_name": conn.name})
            print("ready")
            # Send updated user list to all existing users
            for i in users:
                await sendUpdatedUserlist(users[i], list(map.items()))
    except Exception as e:
        print("handle ready error",e)

async def handle_quit(data, connection):
    try:
        # Get the user details
        if "name" in data:
            quit_user = data["name"]
            del users[connection.name]
            map.__delitem__(quit_user)
            # Send updated user list to all existing users
            for i in users:
                await sendUpdatedUserlist(users[i], list(map.items()))
            print("quit")
    except Exception as e:
        print("handle quit error",e)

async def handle_close(connection):
    try:
        # Get the user details
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
                    await sendTo(conn, { "type": "server_exit_from" })
                    map[conn.name]="online"
            # Send the updated userlist to all the existing users 
            for i in users:
                await sendUpdatedUserlist(users[i], list(map.items()))
            print("leaving")
    except Exception as e:
        print("handle close error",e)

async def sendUpdatedUserlist(conn, message):
    try:
        await conn.send(json.dumps({ "type": "server_user_list", "name": message }))
        print("updated userList sended")
    except Exception as e:
        print("send updated userlist error",e)

async def sendTo(conn, message):
    try:
        await conn.send(json.dumps(message))
    except Exception as e :
        print("send message to socket error",e)

async def on_connection(connection):
    try:
        # Successful connection
        print("User has connected")
        async for message in connection:
            try:
                data=json.loads(message)
                for obj in data:
                    print(data,obj,type(obj))
                # Parse the messages from client 
                message_type=data["type"]
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
                    # User quit/Logout 
                    await handle_quit(data, connection)
                else:
                    await sendTo(connection, { "type": "server_error", "message": "Unrecognized command: " + data["type"] })
            except json.JSONDecodeError:
                #print("c'est pas un JSON")
                if message == "client_ping":
                    await sendTo(connection, { "type": "server_pong", "name": "pong" })          
        await on_close(connection)
    except Exception as e:
        print("on connection error",e)

# When socket connection is closed 
async def on_close(connection):   
    await handle_close(connection)
    print("User has disconnected")

async def start_server():
    port=8000
    async with websockets.serve(on_connection, "0.0.0.0", port):
        print("server started at port: ",port)
        await asyncio.Future()
    await stop
    await server.close(close_connections=False)
        
asyncio.run(start_server())