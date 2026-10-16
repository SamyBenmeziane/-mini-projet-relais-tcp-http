from socket import *
import sys
import threading 

def gerer_client(connectionSocket, serverName, serverPortDestination):
 SocketCLIENT = None
 try:
    requete = recevoir_requete_http(connectionSocket)
    uri = extraire_uri(requete)
    host = extraire_host(requete)
    if uri is not None and host is not None:
        cle_cache = (host, uri)
        with cache_lock:
            reponse_cache = cache.get(cle_cache)
        if reponse_cache is not None:
            print("Réponse trouvée dans le cache :", cle_cache)
            connectionSocket.sendall(reponse_cache)
            return
        else:
            print("Réponse absente du cache :", cle_cache)
    else:
        cle_cache = None
    SocketCLIENT = socket(AF_INET, SOCK_STREAM)
    SocketCLIENT.connect((serverName, serverPortDestination))
    requete = ajouter_connection_close(requete)
    SocketCLIENT.sendall(requete)  
    reponse = recevoir_reponse_http(SocketCLIENT)
    if cle_cache is not None and reponse:
        with cache_lock:
            cache[cle_cache] = reponse
    connectionSocket.sendall(reponse)
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

cache = {}
cache_lock = threading.Lock()
def extraire_uri(message):
    premiere_ligne = message.split(b'\r\n', 1)[0]
    parties = premiere_ligne.split()
    if len(parties) < 3:
        return None
    if parties[0] != b'GET':
        return None
    uri = parties[1].decode('ascii')
    return uri

def extraire_host(message):
 lignes = message.split(b'\r\n')
 for ligne in lignes:
    if ligne.lower().startswith(b'host:'):
        host = ligne.split(b':', 1)[1].strip()
        return host.decode('ascii')

 return None
def recevoir_requete_http(connectionSocket):
 message = b''
 while b'\r\n\r\n' not in message:
    morceau = connectionSocket.recv(2048)
    if not morceau:
        break
    message += morceau
 return message
#fonction proposer par chatgpt pour car d'aprés mes recherche 
#HTTP/1.1 laisse la connexion ouverte par défaut donc on remplace 
#l'ancien en-tête par Connection: close
def ajouter_connection_close(requete):
    lignes = requete.split(b'\r\n')
    nouvelles_lignes = []

    for ligne in lignes:
        if ligne.lower().startswith(b'connection:'):
            continue
        nouvelles_lignes.append(ligne)
    requete = b'\r\n'.join(nouvelles_lignes)
    position = requete.find(b'\r\n\r\n')
    if position == -1:
        return requete
    requete = (
        requete[:position]
        + b'\r\nConnection: close'
        + requete[position:]
    )
    return requete

def recevoir_reponse_http(SocketCLIENT):
 message = b''
 while True:
    morceau = SocketCLIENT.recv(2048)
    if not morceau:
        break
    message += morceau
 return message
def main():
    # Vérification des arguments
    if len(sys.argv) != 3:
        print("python RelaiCache.py <adresse_serveur> <port_serveur>")
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
