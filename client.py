import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 12345

class ChatClientGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Chat Client")
        self.sock = None
        self.username = None
        self.latitude = None
        self.longitude = None
        self.raio = None
        self.running = False
        self.conversations = {}
        self.favoritos = set()
        self.login_frame = tk.Frame(master)
        self.chat_frame = tk.Frame(master)
        self.create_login_frame()
    
    def create_login_frame(self):
        self.login_frame.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(self.login_frame, text="Username:").grid(row=0, column=0, sticky="e")
        self.entry_username = tk.Entry(self.login_frame)
        self.entry_username.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(self.login_frame, text="Latitude:").grid(row=1, column=0, sticky="e")
        self.entry_lat = tk.Entry(self.login_frame)
        self.entry_lat.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(self.login_frame, text="Longitude:").grid(row=2, column=0, sticky="e")
        self.entry_lon = tk.Entry(self.login_frame)
        self.entry_lon.grid(row=2, column=1, padx=5, pady=5)
        tk.Label(self.login_frame, text="Raio:").grid(row=3, column=0, sticky="e")
        self.entry_raio = tk.Entry(self.login_frame)
        self.entry_raio.grid(row=3, column=1, padx=5, pady=5)
        self.login_button = tk.Button(self.login_frame, text="Login", command=self.login)
        self.login_button.grid(row=4, column=0, columnspan=2, pady=10)
    
    def create_chat_frame(self):
        self.chat_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.text_area = scrolledtext.ScrolledText(self.chat_frame, state='disabled', wrap=tk.WORD, width=70, height=20)
        self.text_area.grid(row=0, column=0, columnspan=6, padx=5, pady=5)
        tk.Label(self.chat_frame, text="Chat with:").grid(row=1, column=0, sticky="e")
        self.recipient_var = tk.StringVar(self.chat_frame)
        self.recipient_var.set("Nenhum")
        self.recipient_menu = tk.OptionMenu(self.chat_frame, self.recipient_var, "Nenhum")
        self.recipient_menu.config(width=15)
        self.recipient_menu.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.recipient_var.trace("w", self.change_conversation)
        self.entry_message = tk.Entry(self.chat_frame, width=35)
        self.entry_message.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        self.entry_message.bind("<Return>", lambda event: self.send_message())
        self.send_button = tk.Button(self.chat_frame, text="Send", command=self.send_message)
        self.send_button.grid(row=1, column=3, padx=5, pady=5)
        self.refresh_button = tk.Button(self.chat_frame, text="Refresh Users", command=self.refresh)
        self.refresh_button.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        tk.Label(self.chat_frame, text="Update Lat:").grid(row=2, column=1, sticky="e")
        self.update_lat = tk.Entry(self.chat_frame, width=10)
        self.update_lat.grid(row=2, column=2, padx=5, pady=5, sticky="w")
        tk.Label(self.chat_frame, text="Lon:").grid(row=2, column=3, sticky="e")
        self.update_lon = tk.Entry(self.chat_frame, width=10)
        self.update_lon.grid(row=2, column=4, padx=5, pady=5, sticky="w")
        tk.Label(self.chat_frame, text="Raio:").grid(row=2, column=5, sticky="e")
        self.update_raio = tk.Entry(self.chat_frame, width=10)
        self.update_raio.grid(row=2, column=6, padx=5, pady=5, sticky="w")
        self.update_button = tk.Button(self.chat_frame, text="Update Location/Raio", command=self.update_location)
        self.update_button.grid(row=2, column=7, padx=5, pady=5)
        self.favorito_button = tk.Button(self.chat_frame, text="Favoritar contato", command=self.toggle_favorito)
        self.favorito_button.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.invis_button = tk.Button(self.chat_frame, text="Ficar Invisível", command=self.go_invisible)
        self.invis_button.grid(row=3, column=2, padx=5, pady=5, sticky="w")
        self.online_button = tk.Button(self.chat_frame, text="Ficar Online", command=self.go_online)
        self.online_button.grid(row=3, column=3, padx=5, pady=5, sticky="w")
        self.chat_frame.grid_rowconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(2, weight=1)
    
    def toggle_favorito(self):
        contato = self.recipient_var.get()
        if contato == "Nenhum":
            return
        if contato in self.favoritos:
            self.favoritos.remove(contato)
            messagebox.showinfo("Contato", f"{contato} removido dos favoritos")
        else:
            self.favoritos.add(contato)
            messagebox.showinfo("Contato", f"{contato} adicionado aos favoritos")
        self.update_recipient_menu(','.join(self.recipient_menu["menu"].entrycget(i, "label") for i in range(self.recipient_menu["menu"].index("end")+1) if self.recipient_menu["menu"].entrycget(i, "label") != "Nenhum"))

    def go_invisible(self):
        try:
            invis_cmd = f"STATUS;{self.username};INVISIBLE\n"
            self.sock.send(invis_cmd.encode('utf-8'))
            messagebox.showinfo("Status", "Você está invisível/offline!")
        except Exception as e:
            print(f"Erro ao mudar status: {e}")

    def go_online(self):
        try:
            online_cmd = f"STATUS;{self.username};ONLINE\n"
            self.sock.send(online_cmd.encode('utf-8'))
            messagebox.showinfo("Status", "Você está online!")
        except Exception as e:
            print(f"Erro ao mudar status: {e}")

    def change_conversation(self, *args):
        partner = self.recipient_var.get().replace(" ★", "")
        if partner not in self.conversations:
            self.conversations[partner] = ""
        self.text_area.config(state='normal')
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, self.conversations[partner])
        self.text_area.config(state='disabled')
    
    def login(self):
        self.username = self.entry_username.get().strip()
        lat_str = self.entry_lat.get().strip()
        lon_str = self.entry_lon.get().strip()
        raio_str = self.entry_raio.get().strip()
        if not self.username or not lat_str or not lon_str or not raio_str:
            messagebox.showerror("Error", "Preencha todos os campos")
            return
        try:
            self.latitude = float(lat_str)
            self.longitude = float(lon_str)
            self.raio = float(raio_str)
        except ValueError:
            messagebox.showerror("Error", "Latitude, Longitude e Raio devem ser numéricos")
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
        except Exception as e:
            messagebox.showerror("Error", f"Não foi possível conectar: {e}")
            return
        register_cmd = f"REGISTER;{self.username};{self.latitude};{self.longitude};{self.raio}\n"
        self.sock.send(register_cmd.encode('utf-8'))
        self.login_frame.forget()
        self.create_chat_frame()
        self.running = True
        self.user_label = tk.Label(self.chat_frame, text=f"Usuário: {self.username}")
        self.user_label.grid(row=0, column=4, padx=5, pady=5, sticky="ne")
        threading.Thread(target=self.receive_messages, daemon=True).start()
        threading.Thread(target=self.periodic_refresh, daemon=True).start()
    
    def receive_messages(self):
        while self.running:
            try:
                data = self.sock.recv(1024).decode('utf-8')
                if not data:
                    break
                for linha in data.strip().split('\n'):
                    partes = linha.split(';')
                    if partes[0] == "MESSAGE":
                        sender = partes[1]
                        msg = ';'.join(partes[2:])
                        if sender not in self.conversations:
                            self.conversations[sender] = ""
                        self.conversations[sender] += f"{sender}: {msg}\n"
                        if self.recipient_var.get().replace(" ★", "") == sender:
                            self.change_conversation()
                    elif partes[0] == "REFRESHED":
                        lista = partes[1] if len(partes) > 1 else ""
                        self.update_recipient_menu(lista)
            except Exception as e:
                print(f"Erro ao receber mensagem: {e}")
                break
    
    def update_recipient_menu(self, lista):
        users_from_refresh = [u.strip() for u in lista.split(",") if u.strip()]
        # Remove the line that adds conversation keys - only use users from refresh
        all_users = set(users_from_refresh)
        if "Nenhum" in all_users:
            all_users.remove("Nenhum")
        all_users = list(all_users)
        if not all_users:
            all_users = ["Nenhum"]
        current = self.recipient_var.get().replace(" ★", "")
        menu = self.recipient_menu["menu"]
        menu.delete(0, "end")
        for user in all_users:
            label = user
            if user in self.favoritos:
                label += " ★"
            menu.add_command(label=label, command=lambda value=user: self.recipient_var.set(value if user not in self.favoritos else value + " ★"))
        if current not in all_users:
            self.recipient_var.set(all_users[0] if all_users[0] != "Nenhum" else "Nenhum")
        else:
            if current in self.favoritos:
                self.recipient_var.set(current + " ★")
            else:
                self.recipient_var.set(current)
    
    def periodic_refresh(self):
        while self.running:
            time.sleep(120)
            try:
                refresh_cmd = f"REFRESH;{self.username}\n"
                self.sock.send(refresh_cmd.encode('utf-8'))
            except Exception as e:
                print(f"Erro no refresh: {e}")
                break
    
    def send_message(self):
        msg_text = self.entry_message.get().strip()
        partner = self.recipient_var.get().replace(" ★", "")
        if not msg_text:
            return
        if partner in ["Nenhum", "Selecione"]:
            return
        send_cmd = f"SEND;{self.username};{partner};{msg_text}\n"
        try:
            self.sock.send(send_cmd.encode('utf-8'))
            if partner not in self.conversations:
                self.conversations[partner] = ""
            self.conversations[partner] += f"You: {msg_text}\n"
            if self.recipient_var.get().replace(" ★", "") == partner:
                self.change_conversation()
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
        self.entry_message.delete(0, tk.END)
    
    def refresh(self):
        try:
            refresh_cmd = f"REFRESH;{self.username}\n"
            self.sock.send(refresh_cmd.encode('utf-8'))
        except Exception as e:
            print(f"Erro ao enviar refresh: {e}")
    
    def update_location(self):
        lat_str = self.update_lat.get().strip()
        lon_str = self.update_lon.get().strip()
        raio_str = self.update_raio.get().strip()
        if not lat_str or not lon_str or not raio_str:
            messagebox.showerror("Error", "Preencha todos os campos de localização")
            return
        try:
            new_lat = float(lat_str)
            new_lon = float(lon_str)
            new_raio = float(raio_str)
        except ValueError:
            messagebox.showerror("Error", "Valores devem ser numéricos")
            return
        
        # Update local variables
        self.latitude = new_lat
        self.longitude = new_lon
        self.raio = new_raio
        
        update_cmd = f"UPDATE;{self.username};{new_lat};{new_lon};{new_raio}\n"
        try:
            self.sock.send(update_cmd.encode('utf-8'))
            # Clear the input fields
            self.update_lat.delete(0, tk.END)
            self.update_lon.delete(0, tk.END)
            self.update_raio.delete(0, tk.END)
            messagebox.showinfo("Success", "Localização atualizada com sucesso!")
            refresh_cmd = f"REFRESH;{self.username}\n"
            self.sock.send(refresh_cmd.encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Error", f"Erro ao atualizar localização: {e}")

    def on_closing(self):
        self.running = False
        if self.sock:
            try:
                logout_cmd = f"LOGOUT;{self.username}\n"
                self.sock.send(logout_cmd.encode('utf-8'))
            except Exception:
                pass
            self.sock.close()
        self.master.destroy()

def main():
    root = tk.Tk()
    client_gui = ChatClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", client_gui.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
