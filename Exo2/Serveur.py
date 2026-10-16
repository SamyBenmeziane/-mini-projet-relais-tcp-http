from socket import *
import threading 
def gerer_client(connectionSocket):
 try:
    # Recevoir le message complet
    donnees = b""

    while True:
        morceau = connectionSocket.recv(2048)
        if not morceau:
            break
        donnees += morceau
    message = donnees.decode('utf-8')
    print('message recu: ' + message)
    modifiedMessage = "RECU: " + message
    connectionSocket.sendall(modifiedMessage.encode('utf-8'))
 except OSError as e:
    print("Erreur réseau :", e)
 finally:
    connectionSocket.close()   
def main():
 serverPort = 1235
 serverSocket = socket(AF_INET,SOCK_STREAM)
 serverSocket.bind(('127.0.0.1',serverPort))
 serverSocket.listen(10)
 print("Serveur prêt sur le port", serverPort)
 while True:
    connectionSocket, address = serverSocket.accept()
    t = threading.Thread(
        target=gerer_client,
        args=(connectionSocket,)
    )
    t.start()

if __name__ == "__main__":
    main()