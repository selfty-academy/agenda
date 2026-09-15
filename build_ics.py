#!/usr/bin/env python3
"""Génère le calendrier abonnable des Selfty Calls (calls-selfty.ics) à partir de config.json.

Usage : python3 build_ics.py
Le fichier .ics est écrit à côté de ce script. Aucune dépendance en dehors de la bibliothèque standard.
"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"
DOMAINE = "selfty-academy.github.io"
JOURS = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6}
JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

# Fuseau Europe/Paris complet (règles UE : dernier dimanche de mars / dernier dimanche d'octobre)
VTIMEZONE = [
    "BEGIN:VTIMEZONE",
    "TZID:Europe/Paris",
    "X-LIC-LOCATION:Europe/Paris",
    "BEGIN:DAYLIGHT",
    "TZOFFSETFROM:+0100",
    "TZOFFSETTO:+0200",
    "TZNAME:CEST",
    "DTSTART:19700329T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
    "END:DAYLIGHT",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:+0200",
    "TZOFFSETTO:+0100",
    "TZNAME:CET",
    "DTSTART:19701025T030000",
    "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
    "END:STANDARD",
    "END:VTIMEZONE",
]


def esc(texte):
    """Échappement des valeurs texte (RFC 5545 §3.3.11)."""
    return (str(texte)
            .replace("\\", "\\\\")
            .replace(";", "\;")
            .replace(",", "\\,")
            .replace("\r\n", "\n")
            .replace("\n", "\\n"))


def plier(ligne):
    """Pliage à 75 octets maximum par ligne, sans couper un caractère UTF-8 (RFC 5545 §3.1)."""
    if len(ligne.encode("utf-8")) <= 75:
        return [ligne]
    morceaux, courant = [], ""
    for ch in ligne:
        if len((courant + ch).encode("utf-8")) > 75:
            morceaux.append(courant)
            courant = " " + ch
        else:
            courant += ch
    morceaux.append(courant)
    return morceaux


def parse_date(s):
    return date.fromisoformat(str(s)[:10])


def parse_heure(s):
    h, m = str(s).split(":")[:2]
    return int(h), int(m)


def dt_local(d, h, m):
    return "%04d%02d%02dT%02d%02d00" % (d.year, d.month, d.day, h, m)


def en_pause(d, pauses):
    for p in pauses:
        if parse_date(p["du"]) <= d <= parse_date(p["au"]):
            return p.get("motif") or "pause"
    return None


def creneaux(cfg):
    """Liste des calls hebdomadaires : (date_prevue, semaine_k, date_reelle, heure, minute, duree).
    Plusieurs rendez-vous par semaine possibles via « rythmes » : [{"jour": "samedi", "heure": "10:00"}, ...]."""
    rythmes = cfg.get("rythmes") or [{"jour": cfg["jour"], "heure": cfg["heure"]}]
    res = []
    for r in rythmes:
        sous = dict(cfg, jour=r["jour"], heure=r.get("heure", cfg.get("heure")), duree_min=r.get("duree_min", cfg.get("duree_min", 90)))
        res += creneaux_un_jour(sous)
    return sorted(res, key=lambda c: (c[2], c[3], c[4]))


def creneaux_un_jour(cfg):
    debut = parse_date(cfg["date_debut"])
    jour = JOURS[cfg["jour"].strip().lower()]
    h, m = parse_heure(cfg["heure"])
    duree = int(cfg.get("duree_min", 90))
    semaines = int(cfg.get("semaines", 27))
    pauses = cfg.get("pauses", [])
    annulations = {str(x)[:10] for x in cfg.get("annulations", [])}
    deplacements = cfg.get("deplacements", {}) or {}
    rattraper = bool(cfg.get("rattraper_pauses", False))

    # Premier call = première occurrence du jour choisi à partir de la date de début (incluse)
    premier = debut + timedelta(days=(jour - debut.weekday()) % 7)
    fin_fenetre = debut + timedelta(days=7 * semaines)

    res, d, compte = [], premier, 0
    while d < fin_fenetre or (rattraper and compte < semaines):
        k = (d - debut).days // 7 + 1
        iso = d.isoformat()
        if en_pause(d, pauses) or iso in annulations:
            d += timedelta(days=7)
            continue
        dd, hh, mm, du = d, h, m, duree
        dep = deplacements.get(iso)
        if dep:
            if isinstance(dep, str):
                dep = {"date": dep}
            texte = dep.get("date", iso)
            dd = parse_date(texte)
            if len(texte) >= 16 and texte[10] in "T ":
                hh, mm = parse_heure(texte[11:16])
            if dep.get("heure"):
                hh, mm = parse_heure(dep["heure"])
            du = int(dep.get("duree_min", duree))
        res.append((d, k, dd, hh, mm, du))
        compte += 1
        d += timedelta(days=7)
        if compte > 200:
            break
    return res


def vevent(uid, dtstamp, seq, debut_local, fin_local, titre, description, lieu, url, rappel_min, categorie):
    lignes = [
        "BEGIN:VEVENT",
        "UID:" + uid,
        "DTSTAMP:" + dtstamp,
        "SEQUENCE:%d" % seq,
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "DTSTART;TZID=Europe/Paris:" + debut_local,
        "DTEND;TZID=Europe/Paris:" + fin_local,
        "SUMMARY:" + esc(titre),
        "DESCRIPTION:" + esc(description),
        "CATEGORIES:" + esc(categorie),
    ]
    if lieu:
        lignes.append("LOCATION:" + esc(lieu))
    if url:
        lignes.append("URL:" + url)
        if "zoom.us" in url:
            lignes.append("X-GOOGLE-CONFERENCE:" + url)
    if rappel_min and int(rappel_min) > 0:
        lignes += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:" + esc(titre + " dans " + duree_lisible(int(rappel_min))),
            "TRIGGER:-PT%dM" % int(rappel_min),
            "END:VALARM",
        ]
    lignes.append("END:VEVENT")
    return lignes


def duree_lisible(minutes):
    if minutes % 60 == 0:
        return "%d h" % (minutes // 60)
    return "%d min" % minutes


def construire(cfg):
    now = datetime.now(timezone.utc)
    dtstamp = now.strftime("%Y%m%dT%H%M%SZ")
    seq = int(cfg.get("revision", 0))
    site = cfg.get("site_url", "https://%s/agenda/" % DOMAINE)
    zoom = cfg.get("zoom", "")
    titre = cfg.get("titre", "Selfty Call avec Anaïs")
    rappel = cfg.get("rappel_min", 60)
    semaines = int(cfg.get("semaines", 27))

    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Selfty Academy//Agenda des calls//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + esc(cfg.get("nom_calendrier", "Selfty Academy · Calls")),
        "X-WR-CALDESC:" + esc("Les Selfty Calls en live avec Anaïs, avec le lien Zoom. Abonnement : " + site),
        "X-WR-TIMEZONE:Europe/Paris",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
        "URL:" + site,
    ] + VTIMEZONE

    evenements = []

    # 1. Les Selfty Calls hebdomadaires
    for (prevue, k, d, h, m, duree) in creneaux(cfg):
        debut = datetime(d.year, d.month, d.day, h, m)
        fin = debut + timedelta(minutes=duree)
        desc = cfg.get("description", "Lien Zoom : {zoom}").format(
            zoom=zoom, site=site, semaine="Semaine %d sur %d.\n\n" % (k, semaines))
        uid = "selfty-call-%s@%s" % (prevue.isoformat(), DOMAINE)
        evenements.append((debut, vevent(uid, dtstamp, seq, dt_local(d, h, m), dt_local(fin.date(), fin.hour, fin.minute),
                                         titre, desc, zoom, zoom, rappel, "Selfty Academy")))

    # 2. Calls supplémentaires ponctuels (hors rythme hebdo)
    for extra in cfg.get("calls_supplementaires", []) or []:
        d = parse_date(extra["date"])
        h, m = parse_heure(extra.get("heure", cfg["heure"]))
        duree = int(extra.get("duree_min", cfg.get("duree_min", 90)))
        debut = datetime(d.year, d.month, d.day, h, m)
        fin = debut + timedelta(minutes=duree)
        t = extra.get("titre", titre)
        lien = extra.get("zoom", zoom)
        desc = cfg.get("description", "Lien Zoom : {zoom}").format(zoom=lien, site=site, semaine="")
        if extra.get("note"):
            desc = extra["note"] + "\n\n" + desc
        uid = "selfty-call-extra-%s-%02d%02d@%s" % (d.isoformat(), h, m, DOMAINE)
        evenements.append((debut, vevent(uid, dtstamp, seq, dt_local(d, h, m), dt_local(fin.date(), fin.hour, fin.minute),
                                         t, desc, lien, lien, rappel, "Selfty Academy")))

    # 3. Pratiques entre pairs (facultatives)
    for p in cfg.get("pratiques", []) or []:
        d = parse_date(p["date"])
        h, m = parse_heure(p.get("heure", "18:00"))
        duree = int(p.get("duree_min", 90))
        debut = datetime(d.year, d.month, d.day, h, m)
        fin = debut + timedelta(minutes=duree)
        t = p.get("titre", cfg.get("pratiques_titre", "Pratique entre pairs (facultatif)"))
        lien = p.get("lien", "")
        desc = cfg.get("pratiques_description", "{lien}{note}").format(
            site=site,
            lien=("Lien visio : %s\n\n" % lien) if lien else "",
            note=(p["note"].strip() + "\n\n") if p.get("note") else "")
        uid = "selfty-pratique-%s-%02d%02d@%s" % (d.isoformat(), h, m, DOMAINE)
        evenements.append((debut, vevent(uid, dtstamp, seq, dt_local(d, h, m), dt_local(fin.date(), fin.hour, fin.minute),
                                         t, desc, lien, lien, p.get("rappel_min", rappel), "Selfty Academy · Pratique")))

    evenements.sort(key=lambda e: e[0])
    for _, ev in evenements:
        lignes += ev
    lignes.append("END:VCALENDAR")

    sortie = []
    for l in lignes:
        sortie += plier(l)
    return "\r\n".join(sortie) + "\r\n", evenements


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    contenu, evenements = construire(cfg)
    cible = HERE / cfg.get("fichier", "calls-selfty.ics")
    cible.write_bytes(contenu.encode("utf-8"))
    n_calls = sum(1 for _, ev in evenements if any(l.startswith("UID:selfty-call-") for l in ev))
    n_prat = len(evenements) - n_calls
    print("OK : %s écrit, %d call(s) + %d pratique(s)" % (cible.name, n_calls, n_prat))
    for debut, ev in evenements:
        titre = next(l[8:] for l in ev if l.startswith("SUMMARY:"))
        print("  %s %s %s  %s" % (JOURS_FR[debut.weekday()], debut.strftime("%d/%m/%Y"), debut.strftime("%H:%M"), titre))
    if "XXXXXXXX" in cfg.get("zoom", ""):
        print("ATTENTION : le lien Zoom est encore le placeholder, remplace-le dans config.json.", file=sys.stderr)


if __name__ == "__main__":
    main()
