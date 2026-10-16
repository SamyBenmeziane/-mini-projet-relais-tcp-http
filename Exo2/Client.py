from socket import *
import threading 
def func(id):
 serverName = '127.0.0.1'
 serverPort = 1238
 clientSocket = None
 try:
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((serverName, serverPort))
    message = ("Ping de " + id).encode('utf-8')
    clientSocket.sendall(message)
    clientSocket.shutdown(SHUT_WR)
    # Recevoir la réponse complète
    modifiedMessage = b""
    while True:
        morceau = clientSocket.recv(2048)
        if not morceau:
            break
        modifiedMessage += morceau
    print(modifiedMessage.decode('utf-8'))
 except OSError as e:
    print("Erreur réseau pour le client", id, ":", e)
 finally:
    if clientSocket is not None:
        clientSocket.close()

threads = []
for i in range(10):
    t = threading.Thread(target=func, args=(str(i),))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

print("Tous les clients ont terminé")