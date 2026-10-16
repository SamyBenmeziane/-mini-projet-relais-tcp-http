
def rechercher_clients(uri_recherchee):
 adresses_ip = set()
 try:
    with open("log.txt", "r", encoding="utf-8") as fichier:
        for ligne in fichier:
            parties = ligne.split(" | ", 3)
            if len(parties) != 4:
                continue

            type_message = parties[0]
            adresse_ip = parties[1]
            uri = parties[2]
            contenu = parties[3].strip()
            if (type_message == "REPONSE"
                    and uri_recherchee in uri
                    and contenu):
                adresses_ip.add(adresse_ip)
 except FileNotFoundError:
    print("Le fichier log.txt n'existe pas encore.")
    return

 if adresses_ip:
    print("Clients ayant reçu une réponse non vide :")
    for adresse_ip in sorted(adresses_ip):
        print(adresse_ip)
 else:
    print("Aucun client trouvé pour cette URI.")


def main():
 uri_recherchee = input("Entrez une URI ou une partie d'URI : ")
 rechercher_clients(uri_recherchee)
if __name__ == "__main__":
    main()