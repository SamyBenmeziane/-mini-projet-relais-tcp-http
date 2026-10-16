from socket import *
import sys
import threading 
import re
from urllib.parse import urlsplit
#prompt : je veut une fonction qui prend le contenu du serveur et verifie si elle contient du html .
# si c'est le cas on cherche si il a un liens vers un site interdit il retire l'acces avant de l'envoyer au client 
def censurer_liens(reponse, sites_interdits):
    # Séparer les en-têtes HTTP et le contenu
    if b"\r\n\r\n" not in reponse:
        return reponse

    entetes, corps = reponse.split(b"\r\n\r\n", 1)

    # Vérifier que la réponse contient du HTML
    if not re.search(rb"(?im)^Content-Type:\s*text/html\b", entetes):
        return reponse

    # Ne pas modifier les réponses compressées
    if re.search(rb"(?im)^Content-Encoding:\s*(?!identity\s*$)\S+", entetes):
        return reponse

    # Ne pas modifier les réponses chunked
    if re.search(rb"(?im)^Transfer-Encoding:", entetes):
        return reponse

    # Fonction appelée pour chaque lien trouvé
    def remplacer(match):
        lien = match.group(2)
        url = lien.decode("utf-8", errors="replace")

        domaine = urlsplit(url).hostname

        if domaine is not None and est_interdit(domaine, sites_interdits):
            return match.group(1) + b"Interdit" + match.group(3)

        return match.group(0)

    # Rechercher et remplacer les liens interdits
    nouveau_corps = re.sub(
        rb'''(?i)(\bhref\s*=\s*["'])(https?://[^"']+)(["'])''',
        remplacer,
        corps
    )

    # Mettre à jour Content-Length si présent
    entetes = re.sub(
        rb"(?im)^Content-Length:\s*\d+",
        b"Content-Length: " + str(len(nouveau_corps)).encode("ascii"),
        entetes
    )

    return entetes + b"\r\n\r\n" + nouveau_corps
#prompt : voici ma fonction gerer_client je veut crée une fonction qui enregistre les requêtes GET 
# et les reponse http dans un fichier log.txt sachant que il faut securiser l'acces au fichier 
# pour empecher plusieurs threads d'écrire simultanémnt dans le fichier 
log_lock = threading.Lock()
def enregistrer_log(type_message, adresse_ip, uri, contenu):
    with log_lock:
        with open("log.txt", "a", encoding="utf-8") as fichier:
            fichier.write(
                type_message + " | " +
                adresse_ip + " | " +
                uri + " | " +
                contenu + "\n"
            )
def charger_sites_interdits():
    sites_interdits = []

    with open("sites_interdits.txt", "r", encoding="utf-8") as fichier:
        for ligne in fichier:
            site = ligne.strip().lower()

            if site:
                sites_interdits.append(site)

    return sites_interdits


def est_interdit(domaine, sites_interdits):
    domaine = domaine.lower()

    for site in sites_interdits:
        if domaine == site or domaine.endswith("." + site):
            return True

    return False
def gerer_client(connectionSocket, serverName, serverPortDestination, adresse_ip,sites_interdits):
    SocketCLIENT = None
    try:
        requete = recevoir_requete_http(connectionSocket)
        if not requete:
            return
        uri = extraire_uri(requete)
        host = extraire_host(requete)

        #  Vérifier si le domaine est interdit
        if host is not None:
            domaine = host.split(":")[0]

            if est_interdit(domaine, sites_interdits):
                print("Site interdit :", domaine)

                # Enregistrer l'adresse IP du client
                enregistrer_log("INTERDIT", adresse_ip, uri or "", "")

                # Répondre sans contacter le serveur
                reponse = (
                    b"HTTP/1.1 403 Forbidden\r\n"
                    b"Content-Type: text/plain; charset=utf-8\r\n"
                    b"Content-Length: 9\r\n"
                    b"Connection: close\r\n"
                    b"\r\n"
                    b"Interdit"
                )
                connectionSocket.sendall(reponse)
                return
        SocketCLIENT = socket(AF_INET, SOCK_STREAM)
        SocketCLIENT.connect((serverName, serverPortDestination))

        requete = ajouter_connection_close(requete)
        SocketCLIENT.sendall(requete)

        reponse = recevoir_reponse_http(SocketCLIENT)
        reponse = censurer_liens(reponse, sites_interdits)
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
        print("python RelaiCenseur.py <adresse_serveur> <port_serveur>")
        sys.exit(1)
    serverName = sys.argv[1]
    try:
        serverPortDestination = int(sys.argv[2])
        if not (1 <= serverPortDestination <= 65535):
            raise ValueError
    except ValueError:
        print("le port doit être compris entre 1 et 65535")
        sys.exit(1)
    sites_interdits = charger_sites_interdits()
    print("Sites interdits :", sites_interdits)
    serverPort = 1240
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
            args=(connectionSocket, serverName, serverPortDestination, address[0],sites_interdits)
        )
        thread_client.start()
if __name__ == "__main__":
    main()

