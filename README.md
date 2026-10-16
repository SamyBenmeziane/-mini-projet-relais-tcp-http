# Mini-projet PROGRES — Relais TCP et HTTP

## Binôme :

-Foudad Ryadh 21212710
-Benmeziane Samy 21619550

## Présentation et démarche du binôme

Ce mini-projet a été réalisé à partir des connaissances acquises dans le **cours 1 de PROGRES**, en particulier la programmation réseau en Python avec les sockets TCP et la gestion de clients concurrents. L'objectif est de construire progressivement un relais TCP, puis de le spécialiser pour trois usages HTTP : cache, journalisation (sniffeur) et censure.

Nous avons choisi une démarche **incrémentale** : partir d'un programme qui fonctionne, le réutiliser et modifier seulement les parties nécessaires pour la question suivante. Les commandes ci-dessous permettent de reproduire les essais sous **Windows PowerShell**.

### Exercice 1 — Construction du relais TCP

**Point de départ.** Nous avons utilisé les opérations sur les sockets vues en cours :

- `socket(AF_INET, SOCK_STREAM)` : créer une socket TCP ;
- `bind()`, `listen()` et `accept()` : attendre les connexions entrantes ;
- `connect()` : connecter le relais au serveur de destination ;
- `recv()` et `send()` / `sendall()` : recevoir et transmettre des données ;
- `close()` : fermer les sockets ;
- `threading.Thread` : traiter plusieurs clients sans bloquer la boucle principale d'acceptation.

Le relais possède deux rôles simultanés : **serveur TCP vis-à-vis du client** et **client TCP vis-à-vis du serveur final**. Notre première version utilisait une séquence simple : recevoir un message, le transmettre, recevoir une réponse et la retransmettre. Nous l’avons ensuite fait évoluer pour gérer plusieurs clients et le transfert dans les deux sens : une fonction de gestion par client, des threads pour les transferts, `sendall()` pour éviter de supposer qu'un seul `send()` transmet tout, et une gestion de la fin de transmission (`shutdown(SHUT_WR)`) et de la fermeture des sockets.

**Choix de concurrence.** Nous avons retenu la méthode **un thread par client**, car elle est simple à mettre en œuvre et suffisante pour un nombre limité de clients dans ce projet académique. Nous **n’avons pas implémenté de pool de threads**. Deux alternatives possibles, que nous n’avons pas mises en œuvre, sont pertinentes pour un serveur plus chargé :

1. **Pool fixe de threads** : limiter le nombre de threads créés et réutiliser des travailleurs pour traiter les connexions, ce qui borne la consommation de ressources ;
2. **Multiplexage avec `poll()`** (ou `select()`) : surveiller plusieurs sockets sans créer systématiquement un thread par connexion ; cette approche est plus adaptée à un grand nombre de connexions en attente, mais demande une gestion plus complexe des états et des lectures/écritures partielles.

Ces alternatives ne sont pas automatiquement « meilleures » dans tous les contextes : elles deviennent surtout intéressantes lorsque la charge augmente. La méthode choisie reste acceptable pour les tests limités de ce mini-projet.

**Pour tester l'exercice 1**, se placer dans le dossier `Exo1`, puis ouvrir trois terminaux :

```powershell
# Terminal 1 : serveur TCP
python Serveur.py
```

```powershell
# Terminal 2 : relais vers le serveur sur le port 1235
python RelaiTCP.py 127.0.0.1 1235
```

```powershell
# Terminal 3 : clients de test
python Client.py
```

Le client de test crée dix threads et envoie des messages `Ping de ...`. Le serveur répond avec le préfixe `RECU:`. **Attention :** la version initiale du relais archivée dans `Exo1.zip` traite les échanges de façon séquentielle ; les améliorations décrites ci-dessus correspondent à la version travaillée ensuite. Vérifier que le fichier `RelaiTCP.py` présent dans le dossier final contient bien ces améliorations avant de revendiquer le test de concurrence du relais.

### Exercice 2, question 1 — Du relais TCP au relais cache HTTP

Nous avons repris l’architecture du relais TCP de l'exercice 1, puis nous avons ajouté ou modifié les éléments suivants dans **`RelaiCache.py`** :

- **Lecture d'une requête HTTP complète au niveau des en-têtes** : `recevoir_requete_http()` accumule les octets reçus jusqu'à `\r\n\r\n`, plutôt que de supposer qu'un seul `recv(2048)` suffit.
- **Identification de la ressource demandée** : `extraire_uri()` récupère l'URI d'une requête `GET` ; `extraire_host()` récupère l'en-tête `Host`.
- **Clé du cache** : utilisation du couple `(host, uri)` pour distinguer les requêtes selon l'hôte et le chemin demandé.
- **Cache partagé en mémoire** : dictionnaire `cache = {}` accessible par les threads ; une réponse déjà mémorisée peut être renvoyée directement, sans contacter le serveur.
- **Protection des accès concurrents** : `threading.Lock()` (`cache_lock`) autour des lectures et écritures du dictionnaire.
- **Réception de la réponse** : `recevoir_reponse_http()` assemble les morceaux reçus jusqu'à la fermeture de la connexion par le serveur.
- **Gestion de HTTP/1.1** : `ajouter_connection_close()` retire un éventuel en-tête `Connection` existant et ajoute `Connection: close`. Cette fonction a été proposée avec l'aide de ChatGPT après avoir étudié le comportement des connexions HTTP/1.1, souvent persistantes par défaut. Elle évite, dans nos tests, d'attendre indéfiniment la fin de réponse.
- **Transmission et nettoyage** : envoi de la requête au serveur lors d'un défaut de cache, enregistrement de la réponse puis retransmission au client, avec fermeture des sockets en `finally`.

**Limites** : il s'agit d'un cache pédagogique, non d'un proxy HTTP complet. Le verrou protège chaque accès au dictionnaire, mais **ne garantit pas qu'une seule requête amont sera envoyée** si deux clients demandent simultanément la même ressource absente du cache. La lecture jusqu'à fermeture suppose que le serveur termine la connexion ; les réponses HTTP persistantes, certains corps de requête et d'autres cas particuliers ne sont pas entièrement gérés.

### Exercice 2, question 2 — Du cache au sniffeur HTTP

Pour **`RelaiSniffeur.py`**, nous avons repris `RelaiCache.py`, puis :

- **Supprimé** le dictionnaire `cache`, `cache_lock` et la logique « réponse trouvée / absente du cache » ;
- **Conservé** les fonctions de lecture des requêtes et réponses HTTP, d'extraction de l'URI et de fermeture de connexion ;
- **Modifié** `gerer_client()` pour transmettre **chaque requête** au serveur, sans servir de réponse mémorisée ;
- **Ajouté** le paramètre `adresse_ip` dans `gerer_client()` et transmis `address[0]` depuis `accept()` ;
- **Ajouté** `enregistrer_log()` pour écrire dans `log.txt` en mode ajout (`"a"`) ;
- **Ajouté** `log_lock = threading.Lock()` pour éviter que les écritures de plusieurs threads s'entremêlent ;
- **Enregistré** les URI des requêtes `GET` et les réponses HTTP non vides associées, en conservant une représentation textuelle des octets (`repr(reponse)`) ;
- **Créé** `RechercheLog.py`, un programme séparé qui parcourt le journal, accepte une URI complète ou partielle et affiche les adresses IP distinctes associées aux entrées `REPONSE`.

Le fichier de recherche est un **choix d'organisation** : l'énoncé demande un programme Python de recherche, mais n'impose pas ce nom de fichier. En chaîne, l'IP visible par le sniffeur peut être celle du relais précédent, et non celle du client d'origine.

### Exercice 2, question 3 — Du sniffeur au censeur HTTP

Pour **`RelaiCenseur.py`**, nous avons repris `RelaiSniffeur.py`, puis :

- **Supprimé** la journalisation systématique de chaque `GET` et de chaque réponse : le censeur ne doit journaliser ici que les tentatives d'accès interdit ;
- **Conservé** la fonction `enregistrer_log()` et son verrou afin d'enregistrer l'adresse IP du client en cas de blocage ;
- **Créé** `sites_interdits.txt`, fichier de configuration contenant un domaine interdit par ligne ;
- **Ajouté** `charger_sites_interdits()` : le fichier est lu **une seule fois au démarrage** et les domaines sont stockés dans la liste `sites_interdits` ;
- **Modifié** `main()` pour transmettre cette liste à chaque thread ;
- **Ajouté** `est_interdit(domaine, sites_interdits)` : comparaison du domaine demandé avec la liste, en prenant également en compte les sous-domaines ;
- **Modifié** `gerer_client()` pour extraire `Host`, vérifier le domaine **avant** `connect()` et, s'il est interdit, journaliser l'IP puis renvoyer `HTTP/1.1 403 Forbidden` avec le texte `Interdit` ;
- **Ajouté** `censurer_liens(reponse, sites_interdits)` : séparer les en-têtes HTTP du corps HTML, chercher les URL absolues dans les attributs `href`, extraire le véritable domaine avec `urlsplit()`, remplacer les URL interdites par `Interdit` et actualiser `Content-Length` si nécessaire ;
- **Modifié** l'envoi de la réponse pour appeler `censurer_liens()` **après** `recevoir_reponse_http()` et **avant** `connectionSocket.sendall()`.

Le choix de charger une seule fois la liste évite les lectures répétées du fichier, mais **une modification de `sites_interdits.txt` nécessite un redémarrage** du censeur. La censure HTML actuelle cible surtout les liens absolus HTTP/HTTPS de réponses non compressées et non `chunked` ; elle ne couvre pas toutes les formes de HTML et de HTTP.

### Exercice 2, question 4 — Tester les relais en chaîne

Chaque relais peut être **serveur pour le relais précédent** et **client pour le relais suivant**. Pour tester plusieurs relais sur une même machine, chacun doit avoir un **port d'écoute distinct**. Les destinations se règlent avec les deux arguments de lancement : adresse et port du relais suivant (ou du serveur final).

La suite du document propose les tests individuels et quatre scénarios de chaînage représentatifs, dont une configuration où deux relais sont clients d’un même relais. Il n’est pas nécessaire de tester toutes les permutations possibles.

### Utilisation de ChatGPT

Ce mini-projet a été réalisé en binôme, en nous appuyant principalement sur les connaissances acquises lors du premier cours de PROGRES : programmation réseau avec les sockets TCP, gestion de plusieurs clients et communication entre processus. Nous avons utilisé ChatGPT comme outil complémentaire d’apprentissage, de recherche d’informations, de conseil technique, de débogage et de correction orthographique.

Nous l’avons notamment consulté pour comprendre les problèmes rencontrés, comparer des approches et discuter de propositions de code, avant de les adapter et de les tester. Les exemples ci-dessous sont **des reformulations de nos questions pour en améliorer la lisibilité**, et non une transcription littérale de tous les échanges.

#### Exercice 1 — Relais TCP

- « Dans notre relais TCP, lorsque toutes les données ont été transmises au serveur, le thread peut rester bloqué sur `recv()` en attendant une réponse. Comment signaler la fin de l’envoi sans fermer la réception ? Est-ce que `close()` risque de fermer les deux sens de communication ? »
- « Quelle est la différence entre `close()` et `shutdown()` sur une socket TCP ? Est-ce que `shutdown(SHUT_WR)` permet d’indiquer la fin de l’envoi tout en continuant à recevoir des données ? »
- « Pour gérer plusieurs clients simultanément, nous avons choisi de créer un thread par client. Quelles sont les limites de cette méthode ? Existe-t-il des solutions plus adaptées à un grand nombre de connexions ? »
- « Pour assurer une communication bidirectionnelle, pouvons-nous utiliser deux threads, chacun chargé de transmettre les données dans un sens différent ? »

#### Exercice 2 — Question 1 : relais cache HTTP

- « Pour enregistrer les réponses HTTP dans le cache, pouvons-nous utiliser un dictionnaire Python dont la clé serait un tuple composé du domaine `Host` et de l’URI, et dont la valeur serait la réponse HTTP complète ? »
- « Si deux clients demandent simultanément la même URI, comment protéger l’accès au dictionnaire utilisé comme cache ? Est-ce que `threading.Lock` permet d’éviter les problèmes d’accès concurrent ? »
- « Une requête HTTP est-elle toujours reçue en un seul appel à `recv()` ? Sinon, comment déterminer que tous les en-têtes ont été reçus ? »
- « D’après nos recherches, HTTP/1.1 conserve les connexions ouvertes par défaut. Comme notre relais utilise une boucle `recv()` jusqu’à la fermeture de la connexion, comment ajouter l’en-tête `Connection: close` pour éviter un blocage ? »

#### Question 2 — Relais sniffeur HTTP

- « Nous pensions qu’un sniffeur devait uniquement observer les communications. Pourquoi le relais sniffeur doit-il également transmettre les requêtes et les réponses entre le client et le serveur ? »
- « Nous souhaitons créer une fonction qui enregistre les requêtes GET et les réponses HTTP non vides dans un fichier `log.txt`. Comment organiser les informations pour retrouver les adresses IP des clients à partir d’une URI complète ou partielle ? »
- « Comme plusieurs threads peuvent écrire simultanément dans le fichier de logs, comment sécuriser les écritures pour éviter les conflits ? »
- « Pour rechercher les adresses IP dans le fichier de logs, pouvons-nous utiliser un `set` afin de ne pas afficher plusieurs fois la même adresse ? »

#### Question 3 — Relais censeur HTTP

- « Pour gérer les sites interdits, vaut-il mieux consulter le fichier de configuration à chaque requête ou charger son contenu une seule fois au démarrage ? Quels sont les avantages et les inconvénients de ces deux méthodes ? »
- « Comment récupérer le domaine demandé à partir de l’en-tête HTTP `Host` et vérifier s’il figure dans la liste des sites interdits avant de contacter le serveur ? »
- « Pour remplacer les liens vers des sites interdits dans une page HTML, pouvons-nous utiliser les expressions régulières du module `re` ? Comment éviter de remplacer des liens autorisés ? »
- « Si nous modifions le contenu HTML d’une réponse HTTP, faut-il mettre à jour l’en-tête `Content-Length` ? »

#### Question 4 — Tests en chaîne

- « Le professeur demande de tester les relais en chaîne. Qu’est-ce que cela signifie exactement ? Un relais peut-il être à la fois serveur pour un autre relais et client d’un troisième relais ? »
- « Si nous plaçons le relais cache avant le relais sniffeur, les requêtes déjà présentes dans le cache seront-elles visibles par le sniffeur ? Que se passe-t-il si nous inversons leur ordre ? »
- « Comment organiser les ports et les connexions pour tester plusieurs relais simultanément sans modifier leur logique interne ? »

#### Débogage et validation

- « Python affiche `AttributeError: 'str' object has no attribute 'decode'` lorsque nous utilisons `repr(reponse)`. Pourquoi cette erreur apparaît-elle et quelle est la différence entre `str` et `bytes` ? »
- « Lorsque nous utilisons `curl` pour contacter notre relais HTTP, nous obtenons une erreur de connexion. Comment vérifier si le relais écoute sur le bon port ? »
- « Comment vérifier expérimentalement que le relais cache contacte le serveur uniquement lors de la première requête, puis renvoie directement la réponse mémorisée ? »

#### Bilan

ChatGPT nous a aidés à approfondir certaines notions, à comprendre des erreurs et à comparer des choix techniques. Nous l’avons aussi utilisé pour proposer et expliquer certains fragments de code et pour améliorer la rédaction de la documentation. Les solutions retenues ont été intégrées progressivement au projet et vérifiées par des tests locaux. Cette assistance complète notre travail de binôme et les connaissances acquises en cours ; elle ne constitue pas une validation exhaustive du logiciel.

---

## Prérequis

- Python 3 installé et accessible avec la commande `python`.
- Windows PowerShell (les commandes `curl.exe` évitent l'alias PowerShell `curl`).
- Se placer dans le dossier `Exo2` dans **chaque terminal**.
- Ouvrir un terminal différent pour chaque programme. Laisser les programmes en cours d'exécution pendant les tests ; les arrêter avec `Ctrl + C`.

**Ports configurés dans les fichiers Python :**

| Programme            | Port d'écoute |
| -------------------- | ------------- |
| Serveur HTTP de test | `1235`        |
| `RelaiCache.py`      | `1238`        |
| `RelaiSniffeur.py`   | `1239`        |
| `RelaiCenseur.py`    | `1240`        |

> Les trois relais utilisent des ports d’écoute distincts et peuvent fonctionner simultanément. **Aucune modification des ports dans les fichiers Python n’est nécessaire.** Pour changer la chaîne, utiliser uniquement les commandes de lancement indiquées ci-dessous.

## Préparer une page de test

Créer un fichier `test.html` dans le dossier `Exo2` :

```html
<html>
  <body>
    <a href="https://facebook.com">Facebook</a>
    <a href="https://google.com">Google</a>
  </body>
</html>
```

Créer également `sites_interdits.txt` :

```text
facebook.com
tiktok.com
```

Dans un premier terminal, lancer le serveur HTTP de test :

```powershell
python -m http.server 1235
```

Il doit rester actif pendant les essais. Pour éviter de confondre les requêtes, on peut surveiller les lignes `GET /test.html` qu'il affiche.

## Question 1 — Tester le relais cache

**Terminal 2 :**

```powershell
python RelaiCache.py 127.0.0.1 1235
```

**Terminal 3 :** exécuter deux fois la même commande :

```powershell
curl.exe --http1.1 -H "Connection: close" http://127.0.0.1:1238/test.html
```

**Résultats attendus :**

- Première requête : le cache indique `Réponse absente du cache` et le serveur reçoit un `GET /test.html`.
- Deuxième requête : le cache indique `Réponse trouvée dans le cache` ; le serveur ne reçoit pas de deuxième `GET /test.html`.
- Le client reçoit la page HTML les deux fois.

Le cache étant conservé en mémoire, **redémarrer `RelaiCache.py` pour le vider** avant de refaire un test de première requête.

## Question 2 — Tester le relais sniffeur

Arrêter le relais cache (`Ctrl + C`). Laisser le serveur HTTP actif.

**Terminal 2 :**

```powershell
python RelaiSniffeur.py 127.0.0.1 1235
```

**Terminal 3 :**

```powershell
curl.exe --http1.1 -H "Connection: close" http://127.0.0.1:1239/test.html
```

Consulter le fichier de journalisation :

```powershell
Get-Content log.txt
```

**Résultat attendu :** des entrées `GET` et `REPONSE` associées à l'URI `/test.html` et à l'adresse IP du client. Une réponse HTTP non vide doit être enregistrée.

Tester ensuite le programme de recherche :

```powershell
python RechercheLog.py
```

À la question `Entrez une URI ou une partie d'URI :`, saisir :

```text
test
```

**Résultat attendu :** affichage d'au moins une adresse IP correspondant à une réponse non vide pour une URI contenant `test` (sur la machine locale, généralement `127.0.0.1`).

> `log.txt` est créé lors de l'enregistrement des premiers événements ; ne pas le créer manuellement. Il peut contenir des traces de tests précédents.

## Question 3 — Tester le relais censeur

Arrêter le sniffeur (`Ctrl + C`). Laisser le serveur HTTP actif.

**Terminal 2 :**

```powershell
python RelaiCenseur.py 127.0.0.1 1235
```

Vérifier que `facebook.com` et `tiktok.com` sont affichés dans la liste chargée au démarrage.

### Test A — Censurer un lien dans une page autorisée

**Terminal 3 :**

```powershell
curl.exe --http1.1 -H "Connection: close" http://127.0.0.1:1240/test.html
```

**Résultat attendu :**

```html
<a href="Interdit">Facebook</a> <a href="https://google.com">Google</a>
```

Le relais a contacté le serveur pour obtenir `test.html`, puis a modifié le lien interdit avant de renvoyer la page.

### Test B — Bloquer directement un domaine interdit

**Terminal 3 :**

```powershell
curl.exe -i -H "Host: facebook.com" http://127.0.0.1:1240/
```

**Résultats attendus :**

- Réponse `HTTP/1.1 403 Forbidden`, avec le texte `Interdit`.
- Message `Site interdit : facebook.com` dans le terminal du censeur.
- Aucune nouvelle requête dans le terminal du serveur HTTP pour ce test.
- Une entrée `INTERDIT` dans `log.txt`, avec l'adresse IP du client.

Le fichier `sites_interdits.txt` est lu **une seule fois au démarrage** : redémarrer le censeur après toute modification de cette liste.

## Question 4 — Tester les relais en chaîne

Les ports d’écoute sont déjà fixés : cache `1238`, sniffeur `1239`, censeur `1240`. Garder le serveur HTTP sur `1235`. **Avant chaque scénario, arrêter les relais utilisés dans le scénario précédent avec `Ctrl + C`, puis exécuter les commandes indiquées.** Aucun changement du code Python n’est nécessaire.

### Chaîne A — Client → Cache → Sniffeur → Serveur

**Terminal 2 — Sniffeur :**

```powershell
python RelaiSniffeur.py 127.0.0.1 1235
```

**Terminal 3 — Cache :**

```powershell
python RelaiCache.py 127.0.0.1 1239
```

**Terminal 4 — Client :** exécuter deux fois :

```powershell
curl.exe --http1.1 -H "Connection: close" http://127.0.0.1:1238/test.html
```

**Résultats attendus :** première requête transmise au sniffeur et au serveur ; deuxième requête servie directement par le cache. Le sniffeur n'enregistre normalement qu'une requête pour ces deux appels, si le cache était vide au départ.

### Chaîne B — Client → Sniffeur → Cache → Serveur

Arrêter **les deux relais** avec `Ctrl + C`, puis les relancer avec ces destinations :

**Terminal 2 — Cache :**

```powershell
python RelaiCache.py 127.0.0.1 1235
```

**Terminal 3 — Sniffeur :**

```powershell
python RelaiSniffeur.py 127.0.0.1 1238
```

**Terminal 4 — Client :** exécuter deux fois :

```powershell
curl.exe --http1.1 -H "Connection: close" http://127.0.0.1:1239/test.html
```

**Résultats attendus :** le sniffeur reçoit et journalise les deux requêtes ; le cache contacte le serveur uniquement lors de la première requête.

### Chaîne C — Client → Censeur → Cache → Serveur

Le censeur écoute déjà sur le port `1240`. Arrêter les relais précédents, puis lancer :

**Terminal 2 — Cache :**

```powershell
python RelaiCache.py 127.0.0.1 1235
```

**Terminal 3 — Censeur :**

```powershell
python RelaiCenseur.py 127.0.0.1 1238
```

**Terminal 4 — Client :**

```powershell
curl.exe --http1.1 -H "Connection: close" http://127.0.0.1:1240/test.html
```

**Résultat attendu :** la page est fournie via le cache et le lien Facebook est remplacé par `Interdit` avant d'arriver au client.

Tester également le blocage direct :

```powershell
curl.exe -i -H "Host: facebook.com" http://127.0.0.1:1240/
```

**Résultat attendu :** réponse `403 Forbidden` du censeur, sans passage par le cache ni par le serveur.

Le censeur conserve le port `1240` pour tous les essais, individuels ou en chaîne.

### Chaîne D — Plusieurs relais clients du même censeur

Cette configuration vérifie que **le cache et le sniffeur peuvent contacter simultanément le même relais censeur** :

```text
Client A → Cache (1238) ────┐
                            ├→ Censeur (1240) → Serveur HTTP (1235)
Client B → Sniffeur (1239) ─┘
```

Après avoir arrêté les relais du test précédent, garder le serveur HTTP sur `1235`, puis ouvrir un terminal par relais :

**Terminal 2 — Censeur :**

```powershell
python RelaiCenseur.py 127.0.0.1 1235
```

**Terminal 3 — Cache :**

```powershell
python RelaiCache.py 127.0.0.1 1240
```

**Terminal 4 — Sniffeur :**

```powershell
python RelaiSniffeur.py 127.0.0.1 1240
```

**Terminal 5 — Client A :**

```powershell
curl.exe --http1.1 -H "Connection: close" http://127.0.0.1:1238/test.html
```

**Terminal 6 — Client B :**

```powershell
curl.exe --http1.1 -H "Connection: close" http://127.0.0.1:1239/test.html
```

Les deux clients doivent recevoir la page avec le lien Facebook censuré. Le sniffeur doit enregistrer le GET provenant du client B. Ce test vérifie le partage d’un relais de destination, sans constituer à lui seul un test de charge.

## Remarques et limites

- Les tests utilisent un serveur HTTP local : aucune connexion aux domaines interdits n'est nécessaire.
- Les adresses IP enregistrées par un relais en chaîne peuvent correspondre au **relais précédent** plutôt qu'au client d'origine.
- La censure HTML implémentée cible principalement les URL HTTP/HTTPS absolues dans les attributs `href`, pour des réponses HTML non compressées et non `chunked` ; ce n'est pas un proxy HTTP complet.
- Pour tester les effets du cache de manière reproductible, redémarrer le processus du cache entre les scénarios.
- Si une connexion échoue, vérifier que chaque processus écoute sur le port indiqué et qu'aucun autre programme n'utilise déjà ce port.
