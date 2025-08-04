# Chat Geolocalizado com RabbitMQ

Este projeto implementa um sistema de **mensagens entre usuários com base em localização geográfica**, utilizando sockets TCP, uma interface gráfica com `Tkinter` e enfileiramento de mensagens offline com **RabbitMQ**.

---

## 📌 Funcionalidades

- Envio e recebimento de mensagens via interface gráfica
- Usuários só se comunicam se estiverem **dentro do raio geográfico** definido
- Suporte a mensagens **pendentes via fila (RabbitMQ)** caso o destinatário esteja offline ou fora de alcance
- Sistema de **favoritos**, **modo invisível**, e atualização dinâmica de usuários próximos
- Backend multi-threaded com persistência de mensagens

---

## 🚀 Executando o projeto

### Pré-requisitos

- Python 3.8 ou superior
- RabbitMQ instalado e rodando localmente

Para instalar as dependências:
```bash
pip install pika
```

### 📦 Gerar executáveis

Instale o [PyInstaller](https://www.pyinstaller.org/):
```bash
pip install pyinstaller
```

**Gerar executável do servidor:**
```bash
pyinstaller --onefile server.py
```

**Gerar executável do cliente (modo gráfico):**
```bash
pyinstaller --onefile --windowed client.py
```

Os arquivos `.exe` ficarão dentro da pasta `dist/`.

---

## 🧠 Estrutura do Projeto

```
📁 projeto-chat-geolocalizado/
├── server.py        # Servidor TCP com enfileiramento via RabbitMQ
├── client.py        # Cliente com GUI usando Tkinter
├── README.md        # Este arquivo
```

---

## 🖼️ Interface do Cliente

- Login com nome de usuário e localização (latitude, longitude, raio)
- Lista de usuários próximos atualizada automaticamente
- Envio de mensagens e histórico de conversas
- Opções para:
  - Favoritar contatos
  - Atualizar localização/raio
  - Modo invisível e voltar online

---

## ⚙️ Tecnologias Utilizadas

- Python (`socket`, `threading`, `tkinter`)
- Mensageria com **RabbitMQ** via `pika`
- Empacotamento com `PyInstaller`

---

## 🧪 Exemplo de Uso

1. Inicie o serviço RabbitMQ na sua máquina local
2. Rode o servidor:
   ```bash
   python server.py
   ```
3. Rode o cliente:
   ```bash
   python client.py
   ```
4. Cadastre dois usuários com coordenadas próximas
5. Envie mensagens entre eles para testar comunicação geográfica

---

## 🔧 Possíveis Melhorias Futuras

- Autenticação com senha
- Persistência das conversas em banco de dados (SQLite/PostgreSQL)
- Salas de bate-papo ou grupos
- Interface web
- Dockerização do ambiente (servidor e RabbitMQ)

---

## 👤 Autor

**Pedro Cavalcante de Sousa Junior**  
Projeto acadêmico para a disciplina de **Programação Paralela e Distribuída**

---

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.
