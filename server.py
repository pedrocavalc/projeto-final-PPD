import socket
import threading
import math
import pika

HOST = "127.0.0.1"
PORT = 12345

users = {}
users_lock = threading.Lock()

rabbitmq_connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
rabbitmq_channel = rabbitmq_connection.channel()
rabbitmq_lock = threading.Lock()

def ensure_queue(username):
    with rabbitmq_lock:
        rabbitmq_channel.queue_declare(queue=username, durable=True)

def distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

def deliver_queued_messages(username):
    with users_lock:
        if username not in users or users[username]["status"] != "ONLINE":
            return
    ensure_queue(username)
    temp_messages = []
    with rabbitmq_lock:
        while True:
            method_frame, properties, body = rabbitmq_channel.basic_get(queue=username, auto_ack=False)
            if not method_frame:
                break
            msg_text = body.decode('utf-8')
            parts = msg_text.split(';', 1)
            if len(parts) < 2:
                sender, msg = parts[0], ""
            else:
                sender, msg = parts
            with users_lock:
                # Se remetente não existe mais ou destinatário não está online, recoloca na fila
                if sender not in users or username not in users or users[username]["status"] != "ONLINE":
                    temp_messages.append((sender, msg))
                    rabbitmq_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                    continue
                
                # Se remetente está online, verifica distância
                if users[sender]["status"] == "ONLINE":
                    dist = distance(users[sender]["lat"], users[sender]["lon"], 
                                  users[username]["lat"], users[username]["lon"])
                    if dist > users[sender]["raio"]:
                        temp_messages.append((sender, msg))
                        rabbitmq_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                        continue
                
                # Entrega a mensagem
                try:
                    users[username]["conn"].send(f"MESSAGE;{sender};(Pendente) {msg}\n".encode('utf-8'))
                except Exception as e:
                    print(f"Erro ao entregar mensagem pendente para {username}: {e}")
                    temp_messages.append((sender, msg))
            
            rabbitmq_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        
        # Recoloca mensagens que não puderam ser entregues
        for sender, msg in temp_messages:
            rabbitmq_channel.basic_publish(
                exchange='',
                routing_key=username,
                body=f"{sender};{msg}",
                properties=pika.BasicProperties(delivery_mode=2)
            )

def broadcast_refresh():
    with users_lock:
        for username, user_info in users.items():
            if user_info["status"] != "ONLINE":
                continue
            in_range = []
            u_lat = user_info["lat"]
            u_lon = user_info["lon"]
            u_raio = user_info["raio"]
            for outro, info in users.items():
                if outro == username:
                    continue
                if distance(u_lat, u_lon, info["lat"], info["lon"]) <= u_raio and info.get("status", "ONLINE") == "ONLINE":
                    in_range.append(outro)
            lista = ",".join(in_range)
            try:
                user_info["conn"].send(f"REFRESHED;{lista}\n".encode('utf-8'))
            except:
                pass

def handle_client(conn, addr):
    username = None
    try:
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break
            linhas = data.strip().split('\n')
            for linha in linhas:
                partes = linha.strip().split(';')
                if not partes:
                    continue
                comando = partes[0]
                if comando == "REGISTER":
                    if len(partes) < 5:
                        conn.send("ERROR;Formato incorreto para REGISTER\n".encode('utf-8'))
                        continue
                    username = partes[1]
                    lat = float(partes[2])
                    lon = float(partes[3])
                    raio = float(partes[4])
                    with users_lock:
                        users[username] = {"conn": conn, "addr": addr, "lat": lat, "lon": lon, "raio": raio, "status": "ONLINE"}
                    conn.send(f"REGISTERED;{username}\n".encode('utf-8'))
                    broadcast_refresh()
                elif comando == "UPDATE":
                    if len(partes) < 5:
                        conn.send("ERROR;Formato incorreto para UPDATE\n".encode('utf-8'))
                        continue
                    username = partes[1]
                    lat = float(partes[2])
                    lon = float(partes[3])
                    raio = float(partes[4])
                    with users_lock:
                        if username in users:
                            users[username]["lat"] = lat
                            users[username]["lon"] = lon
                            users[username]["raio"] = raio
                    conn.send(f"UPDATED;{username}\n".encode('utf-8'))
                    deliver_queued_messages(username)
                    broadcast_refresh()
                elif comando == "SEND":
                    if len(partes) < 4:
                        conn.send("ERROR;Formato incorreto para SEND\n".encode('utf-8'))
                        continue
                    sender = partes[1]
                    recipient = partes[2]
                    mensagem = ';'.join(partes[3:])
                    with users_lock:
                        if sender not in users:
                            conn.send("ERROR;Remetente não registrado\n".encode('utf-8'))
                            continue
                        if recipient not in users:
                            conn.send("ERROR;Destinatário não encontrado\n".encode('utf-8'))
                            continue
                        
                        sender_status = users[sender]["status"]
                        recipient_status = users[recipient]["status"]
                        
                        # Se remetente está OFFLINE, sempre enfileira para entrega posterior
                        if sender_status != "ONLINE":
                            ensure_queue(recipient)
                            with rabbitmq_lock:
                                rabbitmq_channel.basic_publish(
                                    exchange='',
                                    routing_key=recipient,
                                    body=f"{sender};{mensagem}",
                                    properties=pika.BasicProperties(delivery_mode=2)
                                )
                            conn.send(f"QUEUED;{recipient}\n".encode('utf-8'))
                            continue
                        
                        # Se remetente está ONLINE, verifica destinatário e distância
                        s_lat = users[sender]["lat"]
                        s_lon = users[sender]["lon"]
                        dist = distance(s_lat, s_lon, users[recipient]["lat"], users[recipient]["lon"])
                        
                        # Entrega imediata se destinatário ONLINE e dentro do raio
                        if recipient_status == "ONLINE" and dist <= users[sender]["raio"]:
                            try:
                                users[recipient]["conn"].send(f"MESSAGE;{sender};{mensagem}\n".encode('utf-8'))
                                conn.send(f"ENVIADO;{recipient}\n".encode('utf-8'))
                            except Exception as e:
                                conn.send(f"ERROR;Falha ao enviar mensagem para {recipient}\n".encode('utf-8'))
                        else:
                            # Enfileira se destinatário OFFLINE ou fora do raio
                            ensure_queue(recipient)
                            with rabbitmq_lock:
                                rabbitmq_channel.basic_publish(
                                    exchange='',
                                    routing_key=recipient,
                                    body=f"{sender};{mensagem}",
                                    properties=pika.BasicProperties(delivery_mode=2)
                                )
                            conn.send(f"QUEUED;{recipient}\n".encode('utf-8'))
                elif comando == "REFRESH":
                    if len(partes) < 2:
                        conn.send("ERROR;Formato incorreto para REFRESH\n".encode('utf-8'))
                        continue
                    username = partes[1]
                    in_range = []
                    with users_lock:
                        if username not in users:
                            conn.send("ERROR;Usuário não registrado\n".encode('utf-8'))
                            continue
                        u_lat = users[username]["lat"]
                        u_lon = users[username]["lon"]
                        u_raio = users[username]["raio"]
                        for outro, info in users.items():
                            if outro == username:
                                continue
                            if distance(u_lat, u_lon, info["lat"], info["lon"]) <= u_raio and info.get("status", "ONLINE") == "ONLINE":
                                in_range.append(outro)
                    lista = ",".join(in_range)
                    conn.send(f"REFRESHED;{lista}\n".encode('utf-8'))
                    deliver_queued_messages(username)
                elif comando == "LOGOUT":
                    if len(partes) < 2:
                        conn.send("ERROR;Formato incorreto para LOGOUT\n".encode('utf-8'))
                        continue
                    username = partes[1]
                    with users_lock:
                        if username in users:
                            users[username]["status"] = "OFFLINE"
                            del users[username]
                    conn.send(f"LOGGED_OUT;{username}\n".encode('utf-8'))
                    broadcast_refresh()
                    break
                elif comando == "STATUS":
                    if len(partes) < 3:
                        conn.send("ERROR;Formato incorreto para STATUS\n".encode('utf-8'))
                        continue
                    username = partes[1]
                    novo_status = partes[2]
                    with users_lock:
                        if username in users:
                            users[username]["status"] = novo_status
                    conn.send(f"STATUS_SET;{username};{novo_status}\n".encode('utf-8'))
                    
                    # Entrega mensagens pendentes quando usuário fica ONLINE
                    if novo_status == "ONLINE":
                        deliver_queued_messages(username)
                    
                    broadcast_refresh()
                else:
                    conn.send("ERROR;Comando desconhecido\n".encode('utf-8'))
    except Exception as e:
        print(f"Erro com o cliente {addr}: {e}")
    finally:
        if username:
            with users_lock:
                if username in users:
                    del users[username]
        conn.close()

def periodic_delivery():
    while True:
        with users_lock:
            current_users = list(users.keys())
        for username in current_users:
            deliver_queued_messages(username)

def start_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((HOST, PORT))
    server_sock.listen(5)
    print(f"Servidor ouvindo em {HOST}:{PORT}")
    periodic_thread = threading.Thread(target=periodic_delivery, daemon=True)
    periodic_thread.start()
    while True:
        conn, addr = server_sock.accept()
        print(f"Conexão de {addr}")
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.daemon = True
        client_thread.start()

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("Encerrando servidor...")
    finally:
        rabbitmq_connection.close()
