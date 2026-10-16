from socket import *
import sys
import threading 
def gerer_client(connectionSocket, serverName, serverPortDestination):
 SocketCLIENT = None
 try:
    SocketCLIENT = socket(AF_INET, SOCK_STREAM)
    SocketCLIENT.connect((serverName, serverPortDestination))
    thread1 = threading.Thread(
        target=transmettre,
        args=(connectionSocket, SocketCLIENT)
    )
    thread2 = threading.Thread(
        target=transmettre,
        args=(SocketCLIENT, connectionSocket)
    )
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
 except gaierror:
    print("adresse du serveur introuvable")
 except timeout:
    print("délai d'attente dépassé")
 except OSError as e:
    print("Erreur réseau :", e)
 finally:
    if SocketCLIENT is not None:
        SocketCLIENT.close()
    connectionSocket.close()


def transmettre(source, destination):
 try:
    while True:
     message = source.recv(2048)
     if not message:
      break
     destination.sendall(message)
 except OSError as e:
    print("Erreur pendant la transmission :", e)
    # Arrêter les communications sur les deux sockets
    for s in (source, destination):
        try:
            s.shutdown(SHUT_RDWR)
        except OSError:
            pass
    return
 try:
    destination.shutdown(SHUT_WR)
 except OSError:
        pass
def main():
    # Vérification des arguments
    if len(sys.argv) != 3:
        print("python RelaiTCP.py <adresse_serveur> <port_serveur>")
        sys.exit(1)
    serverName = sys.argv[1]
    try:
        serverPortDestination = int(sys.argv[2])

        if not (1 <= serverPortDestination <= 65535):
            raise ValueError

    except ValueError:
        print("le port doit être compris entre 1 et 65535")
        sys.exit(1)

    serverPort = 1238

    SocketSERVER = socket(AF_INET,SOCK_STREAM)
    #SocketSERVER.bind(('127.0.0.1',serverPort))
    #permettre au relais d'accepter des connexions provenant d'autres machine
    SocketSERVER.bind(('',serverPort))
    SocketSERVER.listen(10)
    print("Relais TCP prêt sur le port", serverPort)
    while True:
        connectionSocket, address = SocketSERVER.accept()

        thread_client = threading.Thread(
            target=gerer_client,
            args=(connectionSocket, serverName, serverPortDestination)
        )

        thread_client.start()

if __name__ == "__main__":
    main()
