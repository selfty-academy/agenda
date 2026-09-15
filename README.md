# Agenda des Selfty Calls

Calendrier abonnable (fichier iCalendar `.ics`) des Selfty Calls de la Selfty Academy, hébergé sur GitHub Pages.
Chaque élève s'abonne une fois depuis la page, et son agenda (Google Agenda, Apple Calendrier, Outlook) se met à jour tout seul quand le fichier change.

- Page pour les élèves : https://selfty-academy.github.io/agenda/
- Fichier du calendrier : https://selfty-academy.github.io/agenda/calls-selfty.ics
- Abonnement Google Agenda : https://calendar.google.com/calendar/r?cid=webcal%3A%2F%2Fselfty-academy.github.io%2Fagenda%2Fcalls-selfty.ics
- Abonnement Apple / iPhone : webcal://selfty-academy.github.io/agenda/calls-selfty.ics

Anaïs peut s'abonner à la même adresse depuis son Google Agenda (Autres agendas > + > À partir de l'URL) : les calls apparaissent chez elle aussi, avec le lien Zoom.

## Les 3 fichiers qui comptent

| Fichier | Rôle |
|---|---|
| `config.json` | Tous les réglages : jour, heure, durée, dates, pauses, lien Zoom, textes. C'est le seul fichier à modifier à la main. |
| `build_ics.py` | Fabrique `calls-selfty.ics` à partir de `config.json` (Python 3, aucune dépendance). |
| `calls-selfty.ics` | Le calendrier publié. Ne pas l'éditer à la main : il est regénéré à chaque `python3 build_ics.py`. |

`index.html` est la page d'explication (elle lit `calls-selfty.ics` pour afficher les prochains calls), `assets/logo-selfty.png` le logo.

## D'où viennent les dates

Tout est recopié le 16/09/2026 de l'agenda **Selfty Academy** créé par `anaisbrault86@gmail.com` (partagé avec Alex, et dupliqué à l'identique sur le compte `selfty.academy@gmail.com`) :

- **Selfty Call** : samedi 10:00 – 11:30, du 17/10/2026 au 17/04/2027 (20 calls, avec les semaines de coupure déjà retirées).
- **Selfty - Pratique** : lundi 18:30 – 20:00, du 19/10/2026 au 19/04/2027 (20 séances).
- **Ouverture des portes - Module 1** : lundi 12/10/2026 18:30 ; **Call Q&A Certification + explication du portail- Ambre** : mardi 01/12/2026 18:30 (`calls_supplementaires`).
- Les dates clés de la promo (ouverture du portail, examens, challenges, fin de cohorte) sont des événements « toute la journée » dans `jalons`.

Les semaines sans call sont dans `annulations` (une date par rendez-vous supprimé), pas dans `pauses`.

⚠️ **Fuseau horaire** : chez Anaïs, ces événements sont enregistrés dans un fuseau UTC+2/+3 (type Athènes), donc ils tombent une heure trop tôt en heure de Paris (9h le samedi, 17h30 le lundi). Ici tout est en **heure de Paris** : samedi 10h, lundi 18h30. À faire corriger dans son Google Agenda.

Reste à confirmer : **le lien Zoom récurrent des calls** (`zoom`), encore sur le placeholder `https://us06web.zoom.us/j/XXXXXXXX`. Ne pas reprendre le lien du webinaire.

## Modifier le calendrier (la routine)

```bash
cd /Users/alex/Alex/selfty-agenda
# 1. modifier config.json
# 2. regénérer le .ics
python3 build_ics.py
# 3. publier
git add -A && git commit -m "Agenda : <ce qui change>" && git push
```

Les agendas abonnés se mettent à jour tout seuls : Apple et Outlook en quelques heures, Google Agenda sous 24 h environ (parfois plus lentement, Google décide de sa cadence). Rien à refaire côté élèves.

Conseil : quand une date change, augmenter `revision` de 1 dans `config.json` (c'est le `SEQUENCE` des événements, il aide certaines applications à comprendre qu'un événement a bougé).

## Cas concrets

### Changer le jour ou l'heure de tous les calls
Dans `rythmes` : `[{"jour": "samedi", "heure": "10:00", "titre": "Selfty Call"}, {"jour": "lundi", "heure": "18:30", "titre": "Selfty - Pratique"}]` (un objet par rendez-vous hebdomadaire, `duree_min` et `titre` possibles). Sans `rythmes`, `jour` + `heure` servent encore. Les identifiants des événements restent stables : dans les agendas abonnés, les calls se déplacent, ils ne se dupliquent pas.

### Déplacer un seul call
Dans `deplacements`, la clé est la date prévue au départ, la valeur la nouvelle date (et l'heure si elle change) :

```json
"deplacements": {
  "2026-11-10": "2026-11-12T19:00",
  "2027-02-02": { "date": "2027-02-03", "heure": "18:00", "duree_min": 60 }
}
```

### Annuler un call
```json
"annulations": ["2026-12-15"]
```
Le call disparaît des agendas abonnés.

### Ajouter une pause
```json
"pauses": [
  { "du": "2026-12-21", "au": "2027-01-03", "motif": "Vacances de Noël" },
  { "du": "2027-02-15", "au": "2027-02-21", "motif": "Vacances d'hiver" }
]
```
Par défaut les semaines de pause ne sont pas rattrapées (27 semaines de programme, moins les pauses = 25 calls). Pour avoir 27 calls quoi qu'il arrive, en ajoutant des semaines à la fin : `"rattraper_pauses": true`.

### Ajouter un call ponctuel (hors rythme hebdo)
```json
"calls_supplementaires": [
  { "date": "2026-10-10", "heure": "10:00", "duree_min": 60, "titre": "Call de rentrée", "note": "On se retrouve pour lancer l'aventure." }
]
```
`zoom` peut être précisé sur ce call s'il diffère du lien habituel.

### Ajouter ou changer le lien Zoom
`"zoom": "https://us06web.zoom.us/j/..."`. Il est repris dans le lieu, l'URL et la description de chaque call.

### Pratiques entre pairs (facultatif)
Si Anaïs veut aussi mettre les séances de pratique dans l'agenda :
```json
"pratiques": [
  { "date": "2026-10-24", "heure": "10:00", "duree_min": 90, "lien": "https://meet.google.com/...", "note": "En duo, thème libre." }
]
```
Sans `titre`, l'événement s'appelle « Pratique entre pairs (facultatif) ». Liste vide = aucun événement de pratique.

## Ce que contient le .ics

- `METHOD:PUBLISH`, `X-WR-CALNAME` (nom de l'agenda chez l'élève), `REFRESH-INTERVAL` et `X-PUBLISHED-TTL` à 1 h.
- `VTIMEZONE` Europe/Paris complet, `DTSTART`/`DTEND` en `TZID=Europe/Paris` (heure d'hiver et heure d'été gérées).
- Un `VEVENT` par call, `UID` stable (`selfty-call-<date prévue>@selfty-academy.github.io`), rappel (`VALARM`) 1 h avant, lien Zoom en `LOCATION` + `URL` + description.
- Lignes pliées à 75 octets, fins de ligne CRLF (RFC 5545).

Vérification rapide après un build (module `icalendar` installé avec `pip3 install --user icalendar`) :
```bash
python3 -c "from icalendar import Calendar; c=Calendar.from_ical(open('calls-selfty.ics','rb').read()); print(len(c.walk('VEVENT')), 'événements')"
```

## Hébergement

Repo public `selfty-academy/agenda`, GitHub Pages sur la branche `main`, racine `/`. GitHub Pages sert les `.ics` en `text/calendar`. La publication prend 1 à 2 minutes après le push.
