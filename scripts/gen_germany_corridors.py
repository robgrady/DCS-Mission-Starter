#!/usr/bin/env python3
"""Write missiongen/data/corridors/germany.json — the Central Region
corridors: the Authentic standard map detail on the DCS Cold War Germany map.

Rob (v1.102.0): "Let's do the Germany map like the previous two."

WHAT IS REAL, WHAT IS PLACED
----------------------------
The Central Region of 1985 had no published strike routes either — the
Low Level Transit Routes through the HAWK belt were "activated for specified
times only and changed frequently" (FM 100-103). What IS published, and is
drawn from the printed figure:

- The ADIZ / Flugüberwachungszone: "eine Tiefe von 25 bis 30 Seemeilen bzw.
  später durchschnittlich 40 km" west of the inner-German border, flight
  plan and ATC mandatory, USAFE clearances still issued in 1989 (dewiki
  ADIZ; DHV-Info 49/1989). Drawn as a 40 km band on a schematic border.
- The HAWK belt (Denmark to Austria, "vor dem östlichen Rand des
  Nike-Gürtels", KLu LOMEZ "ca. 50 km diep direct achter het IJzeren
  Gordijn") and the Nike Hercules belt ("die vorderen Nike-Stellungen ca.
  150 km westlich des Eisernen Vorhangs", 70 sites, North Sea to Stuttgart)
  — relikte.com, nl.wikipedia Groepen Geleide Wapens, A&SF July 1983.
  Drawn as bands; the crossing gates are ours.
- The three Berlin air corridors, 20 statute miles wide, 10,000 ft, and the
  20-mile Berlin Control Zone (FRUS 1945 vol. III doc 1206; nva-flieger.de).
  In this data the corridor centrelines are also the roads to Berlin —
  the axes every crew already knew.
- The GDR flight-restriction line (Grenzsperrstreifen) by its 27 reference
  towns, and the 99 "örtliche Fluglinien" points (nva-flieger.de "Luftraum
  der DDR") — the eastern fixes are the named towns.
- The seven 250-ft Low Flying Areas as re-published in NfL 2025-1-3686
  (the Cold War list: Cloppenburg, Borken, Holzminden, Schneverdingen,
  Itzehoe; LFA 7 lies south of the map) — full printed polygons.
- AIP Germany ENR 5.1 (AIRAC 03/24): ED-R 37 Nordhorn, 31 Bergen-Hohne,
  32 Munster, 33 Unterlüss, 34 Meppen, 10 Todendorf-Putlos, 11 Ostsee,
  13 Meldorfer Bucht — printed vertices.
- The 16th Air Army fields and the NVA/Soviet ranges: Wittstock
  "53° 5′ 10″ N, 12° 38′ 42″ O", Letzlinger Heide "52° 25′ 48″ N,
  11° 34′ 12″ O", Lieberose "51° 56′ 7″ N, 14° 19′ 40″ O" (de.wikipedia
  Truppenübungsplatz pages), Retzow "between villages of Retzow and
  Ganzlin" (16va.be).
- The NVA 41. FRBr ring round Berlin (Fürstenwalde, Prötzel, Klosterfelde,
  Beetz, Schönermark, Fehrbellin, Zachow, Markgrafpieske — de.wikipedia
  Flugabwehrraketentruppen (NVA)); drawn as a schematic ring.
- The 2 ATAF / 4 ATAF boundary: "Germany north of the city of Kassel"
  (en.wikipedia 2 ATAF), army-group line "Gottingen-Liege" (GlobalSecurity).

Everything placed on a town, a summit or a river crossing is flagged
approx:true, drawn `~`, listed in the brief as curated. The border, the
Elbe and the autobahns are schematic polylines. Sources: docs/SOURCES.md §3.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "missiongen" / "data" / "corridors" / "germany.json"


def arc(lat, lon, r_nm, a0, a1, n=12):
    pts = []
    for i in range(n + 1):
        b = math.radians(a0 + (a1 - a0) * i / n)
        dlat = r_nm / 60.0 * math.cos(b)
        dlon = r_nm / 60.0 * math.sin(b) / math.cos(math.radians(lat))
        pts.append([round(lat + dlat, 4), round(lon + dlon, 4)])
    return pts


def circle(lat, lon, r_nm, n=36):
    return arc(lat, lon, r_nm, 0, 360, n)[:-1]


def dms(d, m, s=0.0):
    return round(d + m / 60 + s / 3600, 5)


def dm(d, m):
    return round(d + m / 60, 5)


F = {}


def fx(name, lat, lon, short, kind, src, approx=False, **kw):
    d = {"lat": round(lat, 5), "lon": round(lon, 5), "short": short, "kind": kind, "src": src}
    if approx:
        d["approx"] = True
    d.update(kw)
    F[name] = d


SRC_NAV = "OurAirports navaid record (current DAFIF/FAA data), position as printed"
SRC_DCS = "DCS Cold War Germany map"
SRC_GSS = "nva-flieger.de 'Luftraum der DDR': Grenzsperrstreifen reference town"
SRC_OFL = "nva-flieger.de 'Luftraum der DDR': örtliche Fluglinie point"

# ---- 4 ATAF: the Eifel, the Hunsrück, the Pfalz -------------------------------
fx("BITBURG", 49.945, 6.564, "BITBURG", "airport", SRC_DCS)
fx("SPANGDAHLEM", 49.977, 6.699, "SPANG", "airport", SRC_DCS)
fx("HAHN", 49.948, 7.264, "HAHN", "airport", SRC_DCS)
fx("RAMSTEIN", 49.437, 7.600, "RAMSTEIN", "airport", SRC_DCS)
fx("SPA", 49.979, 6.6977, "SPA", "navaid", SRC_NAV + ": Spangdahlem TACAN 109.5", minor=True)
fx("NTM", 50.0159, 6.5318, "NTM", "navaid", SRC_NAV + ": Nattenheim VORTAC 115.3")
fx("BUE", 50.1787, 7.0695, "BUE", "navaid", SRC_NAV + ": Büchel TACAN 117.1")
fx("HND", 49.9456, 7.2677, "HND", "navaid", SRC_NAV + ": Hahn DME 116.95", minor=True)
fx("KIR", 49.8502, 7.3696, "KIR", "navaid", SRC_NAV + ": Kirn VORTAC 117.5")
fx("RMS", 49.4347, 7.5857, "RMS", "navaid", SRC_NAV + ": Ramstein TACAN 113.4", minor=True)
fx("ZWN", 49.2291, 7.4179, "ZWN", "navaid", SRC_NAV + ": Zweibrücken VOR-DME 114.8", minor=True)
fx("KOBLENZ", 50.36, 7.59, "KOBLENZ", "landmark", "The Rhine-Mosel confluence; the Eifel road's turn to the Taunus", approx=True)

# ---- Rhein-Main and the Taunus ------------------------------------------------
fx("WIB", 50.0462, 8.3108, "WIB", "navaid", SRC_NAV + ": Wiesbaden TACAN 114.1", minor=True)
fx("TAU", 50.2505, 8.1625, "TAU", "navaid", SRC_NAV + ": Taunus VORTAC 116.7")
fx("WIESBADEN", 50.050, 8.326, "WIESBADN", "airport", SRC_DCS)
fx("FRANKFURT", 50.040, 8.567, "FRANKFRT", "airport", SRC_DCS)
fx("GELNHAUSEN", 50.196, 9.167, "GELNHAUS", "airport", SRC_DCS + " (Coleman AAF)")
fx("ALSFELD", 50.75, 9.27, "ALSFELD", "landmark", "The Vogelsberg road: Alsfeld on the A5, north-east of Giessen", approx=True)
fx("FULDA", 50.540, 9.643, "FULDA", "airport", SRC_DCS + " (Sickels AAF; V US Corps, the Fulda Gap)")
fx("HUNFELD", 50.67, 9.76, "HUNFELD", "landmark", "Hünfeld, the last town before the Fulda Gap gate", approx=True)
fx("FTZ", 51.0843, 9.4152, "FTZ", "navaid", SRC_NAV + ": Fritzlar NDB 468")
fx("WRB", 51.5057, 9.1109, "WRB", "navaid", SRC_NAV + ": Warburg VOR-DME 113.7")
fx("KASSEL", 51.32, 9.50, "KASSEL", "landmark", "Kassel - the 2 ATAF / 4 ATAF and NORTHAG / CENTAG seam ('Germany north of the city of Kassel', en.wikipedia 2 ATAF)", approx=True)
fx("GOTTINGEN", 51.53, 9.93, "GOTTINGN", "landmark", "Göttingen - the army-group boundary 'Gottingen (FRG)-Liege' (GlobalSecurity)", approx=True)
fx("GOSLAR", 51.91, 10.43, "GOSLAR", "landmark", "Goslar under the Harz; I BR Corps right boundary 'from Goslar to Paderborn' (GlobalSecurity NORTHAG)", approx=True)
fx("WURZBURG", 49.79, 9.93, "WURZBURG", "landmark", "Würzburg - 69th ADA Group (HAWK) HQ; the road to the Hof corridor", approx=True)
fx("BAYREUTH", 49.95, 11.58, "BAYREUTH", "landmark", "Bayreuth - the Hof corridor's approach; an ADIZ airfield with its own corridor (dewiki ADIZ)", approx=True)

# ---- 2 ATAF: the Rhine-Ruhr, the Weser, Hannover ------------------------------
fx("NORVENICH", 50.831, 6.659, "NORVENCH", "airport", SRC_DCS)
fx("COLOGNE", 50.868, 7.148, "COLOGNE", "airport", SRC_DCS)
fx("COL", 50.7835, 7.5942, "COL", "navaid", SRC_NAV + ": Cola VORTAC 108.8")
fx("GMH", 51.1705, 7.8920, "GMH", "navaid", SRC_NAV + ": Germinghausen VOR-DME 115.4")
fx("HMM", 51.8569, 7.7083, "HMM", "navaid", SRC_NAV + ": Hamm VOR-DME 115.65")
fx("GUTERSLOH", 51.923, 8.304, "GUTERSLO", "airport", SRC_DCS + " (RAF Gütersloh - 'the nearest RAF airfield to the border')")
fx("PADERBORN", 51.72, 8.75, "PADERBRN", "landmark", "Paderborn; I BR Corps rear boundary (GlobalSecurity NORTHAG)", approx=True)
fx("OSB", 52.2017, 8.2855, "OSB", "navaid", SRC_NAV + ": Osnabrück TACAN 108.35", minor=True)
fx("PORTA", 52.25, 8.92, "PORTA", "landmark", "Porta Westfalica - the Minden Gap, NORTHAG's 'vital ground' (JMSS)", approx=True)
fx("BYC", 52.2912, 9.0910, "BYC", "navaid", SRC_NAV + ": Bückeburg NDB 368", minor=True)
fx("WUN", 52.4603, 9.4448, "WUN", "navaid", SRC_NAV + ": Wunstorf TACAN 114.85")
fx("NIE", 52.6259, 9.3720, "NIE", "navaid", SRC_NAV + ": Nienburg VOR 116.5", minor=True)
fx("DLE", 52.2503, 9.8835, "DLE", "navaid", SRC_NAV + ": Leine VOR-DME 115.2")
fx("HANNOVER", 52.454, 9.694, "HANNOVER", "airport", SRC_DCS)
fx("WUNSTORF", 52.457, 9.427, "WUNSTORF", "airport", SRC_DCS)
fx("CEL", 52.5897, 10.0295, "CEL", "navaid", SRC_NAV + ": Celle NDB 311")
fx("FSB", 52.9158, 10.1881, "FSB", "navaid", SRC_NAV + ": Fassberg NDB 284")
fx("FASSBERG", 52.919, 10.185, "FASSBERG", "airport", SRC_DCS)
fx("BRU", 52.3222, 10.6062, "BRU", "navaid", SRC_NAV + ": Braunschweig NDB 427", minor=True)
fx("HLZ", 52.3634, 10.7952, "HLZ", "navaid", SRC_NAV + ": Hehlingen VOR-DME 117.3")
fx("UELZEN", 52.96, 10.56, "UELZEN", "landmark", "Uelzen - reporting post UNITY of the Tiefflieger-Meldedienst (relikte.com)", approx=True)
fx("VISSEL", 52.99, 9.58, "VISSEL", "landmark", "Visselhövede - CRC SILVERCORK (relikte.com)", approx=True)
fx("BMN", 53.0440, 8.7821, "BMN", "navaid", SRC_NAV + ": Bremen VOR-DME 117.45", minor=True)

# ---- the Elbe: Hamburg, Lübeck, Kiel ------------------------------------------
fx("HAMBURG", 53.627, 9.981, "HAMBURG", "airport", SRC_DCS)
fx("HAM", 53.6856, 10.205, "HAM", "navaid", SRC_NAV + ": Hamburg VORTAC 113.1")
fx("LBE", 53.6542, 9.5951, "LBE", "navaid", SRC_NAV + ": Elbe VOR-DME 115.1", minor=True)
fx("LUB", 53.9407, 10.6678, "LUB", "navaid", SRC_NAV + ": Lübeck VOR 110.6")
fx("KHD", 54.3788, 10.1454, "KHD", "navaid", SRC_NAV + ": Kiel-Holtenau DME 109.5", minor=True)
fx("NDO", 53.769, 8.6535, "NDO", "navaid", SRC_NAV + ": Nordholz TACAN 117.1", minor=True)
fx("LAUENBURG", 53.37, 10.56, "LAUENBRG", "landmark", "Lauenburg - the Elbe where the border leaves it", approx=True)
fx("LUNEBURG", 53.25, 10.41, "LUNEBURG", "landmark", "Lüneburg - I NL Corps divisions 'around Lüneburg and Uelzen' (coldwardecoded)", approx=True)

# ---- the gates on the inner-German border ---------------------------------------
GATE_SRC = ("Curated crossing point on the inner-German border, placed on the named town; "
            "the LLTRs through the HAWK belt were 'activated for specified times only and changed frequently' (FM 100-103)")
fx("BOIZENBURG", 53.38, 10.72, "BOIZENBG", "gate", GATE_SRC + " - the Elbe below Lauenburg, I NL Corps; the north Berlin corridor's crossing", approx=True)
fx("DOMITZ", 53.14, 11.26, "DOMITZ", "gate", GATE_SRC + " - the Elbe bridge at Dömitz, the Wendland; I GE Corps", approx=True)
fx("HELMSTEDT", 52.23, 11.01, "HELMSTDT", "gate", GATE_SRC + " - Checkpoint Alpha / Marienborn on the A2, the center Berlin corridor's crossing; I BR Corps", approx=True)
fx("HERLESHAUSEN", 51.00, 10.17, "HERLESHN", "gate", GATE_SRC + " - Wartha / Herleshausen on the A4 over the Werra; III GE Corps / V US Corps seam", approx=True)
fx("POINT ALPHA", 50.72, 9.94, "PT ALPHA", "gate", GATE_SRC + " - OP Alpha at Rasdorf, the Fulda Gap; V US Corps 'from a line north of Kassel to a point east of Fulda' (GlobalSecurity)", approx=True)
fx("HOF", 50.32, 11.92, "HOF", "gate", GATE_SRC + " - the Hof corridor, 'from Zwickau through the so-called Hof Corridor toward Nuremberg' (warhistory.org); VII US Corps", approx=True)

# ---- the GDR: fields (DCS positions) ---------------------------------------------
fx("WERNEUCHEN", 52.632, 13.769, "WERNEUCH", "airport", SRC_DCS + " (931 ORAP MiG-25)")
fx("FINOW", 52.827, 13.694, "FINOW", "airport", SRC_DCS + " (787 IAP)")
fx("TEMPLIN", 53.032, 13.543, "TEMPLIN", "airport", SRC_DCS + " (Groß Dölln, 20 GvAPIB Su-17)")
fx("SPERENBERG", 52.137, 13.306, "SPERENBG", "airport", SRC_DCS + " (226 OSAP)")
fx("ALTES LAGER", 51.995, 12.984, "ALTLAGER", "airport", SRC_DCS + " (Jüterbog, 833 IAP MiG-23MLD)")
fx("NEURUPPIN", 52.941, 12.787, "NEURUPPN", "airport", SRC_DCS + " (730 APIB)")
fx("WITTSTOCK", 53.202, 12.523, "WITTSTCK", "airport", SRC_DCS + " (Alt Daber, 33 IAP MiG-29)")
fx("ORANIENBURG", 52.725, 13.217, "ORANIENB", "airport", SRC_DCS + " (239 GvOVP)")
fx("PARCHIM", 53.428, 11.787, "PARCHIM", "airport", SRC_DCS + " (172 / 439 OBVP)")
fx("LAAGE", 53.918, 12.279, "LAAGE", "airport", SRC_DCS + " (MFG-28 / JBG-77)")
fx("DAMGARTEN", 54.264, 12.444, "DAMGARTN", "airport", SRC_DCS + " (773 IAP MiG-29)")
fx("NEUBRANDENBURG", 53.602, 13.306, "NEUBRAND", "airport", SRC_DCS + " (Trollenhagen, JG-2)")
fx("MERSEBURG", 51.364, 11.950, "MERSEBRG", "airport", SRC_DCS + " (85 GvIAP)")
fx("FALKENBERG", 51.546, 13.216, "FALKENBG", "airport", SRC_DCS + " (31 GvIAP)")
fx("HOLZDORF", 51.768, 13.170, "HOLZDORF", "airport", SRC_DCS + " (JG-1)")
fx("STENDAL", 52.629, 11.820, "STENDAL", "airport", SRC_DCS + " (Borstel, 178 / 440 OVP)")
fx("COCHSTEDT", 51.856, 11.418, "COCHSTDT", "airport", SRC_DCS)
# the GDR by its own reference towns (Grenzsperrstreifen chain and local flight lines)
fx("SCHWERIN", 53.63, 11.41, "SCHWERIN", "landmark", SRC_GSS, approx=True)
fx("HAGENOW", 53.43, 11.19, "HAGENOW", "fix", SRC_GSS, approx=True)
fx("LUDWIGSLUST", 53.32, 11.50, "LUDWGSLT", "fix", SRC_GSS, approx=True)
fx("PERLEBERG", 53.07, 11.86, "PERLEBRG", "fix", SRC_GSS, approx=True)
fx("PRITZWALK", 53.15, 12.18, "PRITZWLK", "fix", SRC_OFL + " 123 (UT 168° / DT 059°); the Wittstock training routes' first turn", approx=True)
fx("NEUSTADT-GLEWE", 53.38, 11.59, "NEUGLEWE", "fix", SRC_OFL + " 124; Wittstock routes 023-027", approx=True)
fx("OSTERBURG", 52.78, 11.76, "OSTERBRG", "fix", SRC_GSS + "; " + SRC_OFL + " 126", approx=True)
fx("HALDENSLEBEN", 52.29, 11.41, "HALDENSL", "fix", SRC_GSS + "; " + SRC_OFL + " 143", approx=True)
fx("NAUEN", 52.60, 12.87, "NAUEN", "fix", SRC_OFL + " 136 (UT 236°)", approx=True)
fx("RATHENOW", 52.60, 12.34, "RATHENOW", "fix", "nva-flieger.de: 'Zone 064 (Rathenow)'", approx=True)
fx("MAGDEBURG", 52.13, 11.63, "MAGDEBRG", "landmark", "Magdeburg - 3rd Army HQ; MAG VOR 110.45 (OurAirports listing, position from the city)", approx=True)
fx("GRONINGEN", 51.94, 11.21, "GRONINGN", "fix", SRC_GSS, approx=True)
fx("BLANKENBURG", 51.79, 10.96, "BLANKENB", "fix", SRC_GSS, approx=True)
fx("KELBRA", 51.43, 11.04, "KELBRA", "fix", SRC_GSS + "; " + SRC_OFL + " 177", approx=True)
fx("BAD LANGENSALZA", 51.11, 10.65, "LANGENSZ", "fix", SRC_GSS + "; " + SRC_OFL + " 178", approx=True)
fx("BARCHFELD", 50.83, 10.30, "BARCHFLD", "fix", SRC_GSS, approx=True)
fx("SUHL", 50.61, 10.69, "SUHL", "fix", SRC_GSS, approx=True)
fx("POSSNECK", 50.70, 11.60, "POSSNECK", "fix", SRC_GSS, approx=True)
fx("ELSTERBERG", 50.61, 12.17, "ELSTERBG", "fix", SRC_GSS, approx=True)
fx("HALLE", 51.48, 11.97, "HALLE", "landmark", "Halle - 8th Guards Army; the south Berlin corridor's axis passes north of it", approx=True)
fx("DESSAU", 51.832, 12.193, "DESSAU", "airport", SRC_DCS)
fx("ZERBST", 52.000, 12.144, "ZERBST", "airport", SRC_DCS + " (35 IAP)")
fx("GENTHIN", 52.41, 12.16, "GENTHIN", "fix", "The center Berlin corridor's axis: Genthin on the Elbe-Havel canal (placed on the town)", approx=True)
fx("BERLIN", 52.484, 13.351, "BERLIN", "landmark", "The Berlin Control Zone's center: 'a pillar located in the cellar of the Allied Control Authority building' (en.wikipedia BASC)")
fx("EISENACH", 50.98, 10.32, "EISENACH", "fix", "Eisenach - the Wartburg; the A4 east of the Herleshausen gate (placed on the town)", approx=True)
fx("ERFURT", 50.98, 11.03, "ERFURT", "landmark", "Erfurt - the Thuringian basin (placed on the city)", approx=True)
fx("GERA", 50.88, 12.08, "GERA", "fix", "Gera - 252 ZRB (gsvg88); the Hof corridor road north (placed on the town)", approx=True)
fx("PLAUEN", 50.50, 12.14, "PLAUEN", "fix", "Plauen - the Vogtland above the Hof corridor (placed on the town)", approx=True)
fx("BRAUNSCHWEIG", 52.319, 10.554, "BRNSCHWG", "airport", SRC_DCS + " (outside the ADIZ by the 1958 exception)")
fx("MINDEN", 52.29, 8.92, "MINDEN", "landmark", "Minden - the Weser at the Porta gap", approx=True)

# ---- corridors -------------------------------------------------------------------
C = []


def cor(id_, name, role, points, block, width, notes, src, seg=0, off=(1, 0)):
    C.append({"id": id_, "name": name, "role": role, "points": points, "block_ft": list(block),
              "width_nm": width, "notes": [notes], "src": src, "label_seg": seg, "label_off": list(off)})


LLTR = ("Curated Low Level Transit Route: 'a temporary corridor of defined dimensions which allows the "
        "low-level passage of friendly aircraft through friendly air defenses' (FM 100-103, 1987). The trace is ours.")
CORR = "FRUS 1945 vol. III doc. 1206 (the corridors, 20 English miles wide); nva-flieger.de Luftraum der DDR; en.wikipedia West Berlin Air Corridor"

# 4 ATAF departures
cor("ef_out", "The Eifel road - Nattenheim to the Taunus", "departure", ["NTM", "BUE", "KOBLENZ", "TAU"], (1000, 10000), 6,
    "Out of the Eifel over the Büchel TACAN and the Rhine at Koblenz to the Taunus VORTAC - clear of the Nike sites of 6/56 ADA (Spangdahlem / Bitburg / Hahn) and 2/62 ADA's HAWK batteries round Bitburg (Balesfeld, Butzweiler, Hisel).",
    "OurAirports NTM/BUE/TAU; usarmygermany.com 108th ADA Bde", seg=1, off=(0, -1))
cor("ef_home", "Recovery into the Eifel", "recovery", ["TAU", "KOBLENZ", "BUE", "NTM"], (2000, 10000), 6,
    "Back down the Eifel road. SOC 3 Kindsbach (4 ATAF); CRC Börfink 'SCANDALISE'.",
    "ace-high-journal.eu CRC in Deutschland", seg=1, off=(0, 1))
cor("hu_out", "The Hunsrück road - Hahn to the Taunus", "departure", ["HND", "KIR", "TAU"], (1000, 10000), 6,
    "Hahn, Pferdsfeld and Büchel east over the Hunsrück to the Kirn VORTAC and the Taunus - the 94th Group's Nike sites at Dichtelbach and Wüschheim below.",
    "OurAirports HND/KIR/TAU; en.wikipedia List of Nike missile sites", seg=0, off=(0, 1))
cor("hu_home", "Recovery over the Hunsrück", "recovery", ["TAU", "KIR", "HND"], (2000, 10000), 6,
    "Kirn back to the Hahn DME.", "OurAirports HND", seg=1, off=(0, -1))
cor("pf_out", "The Kirn road - Ramstein to the Taunus", "departure", ["RMS", "KIR", "TAU"], (1000, 10000), 6,
    "Ramstein and Zweibrücken north over the Kirn VORTAC to the Taunus, between the Nike sites of 2/60 ADA (Ramstein / Pirmasens / Kaiserslautern) and the 94th Group's Hunsrück sites (Dichtelbach, Wüschheim).",
    "OurAirports RMS/KIR/TAU; usarmygermany.com 94th ADA Group", seg=0, off=(1, 0))
cor("pf_home", "Recovery via Kirn", "recovery", ["TAU", "KIR", "RMS"], (2000, 10000), 6,
    "The Kirn road back into the Pfalz; Ramstein TACAN 113.4.", "OurAirports RMS", seg=1, off=(-1, 0))
cor("rm_out", "Rhein-Main to the Taunus", "departure", ["WIB", "TAU"], (1000, 8000), 5,
    "Wiesbaden and Frankfurt out over the Taunus VORTAC to Gelnhausen, under the 10th ADA Group's HAWK (Hanau, Giessen) - SOC 3 Kindsbach's identification zone.",
    "usarmygermany.com 10th ADA Bde", seg=1, off=(0, 1))
cor("rm_home", "Recovery into Rhein-Main", "recovery", ["GELNHAUSEN", "TAU", "WIB"], (2000, 8000), 5,
    "Gelnhausen to the Taunus VORTAC and down into Wiesbaden / Rhein-Main.", "OurAirports TAU/WIB", seg=0, off=(0, -1))

# 4 ATAF transits (LLTRs to the gates)
cor("fulda", "The Fulda Gap - LLTR to Point Alpha", "transit", ["TAU", "GELNHAUSEN", "FULDA", "HUNFELD", "POINT ALPHA"], (500, 5000), 5,
    "The V US Corps road: Gelnhausen, Fulda, Hünfeld, through the HAWK belt (2/2 ADA Giessen, 1/1 ADA Wildflecken) to the gate at OP Alpha. " + LLTR,
    "GlobalSecurity ww3-fulda-gap; usarmygermany.com 10th ADA Bde", seg=2, off=(0, 1))
cor("werra", "The Werra road - LLTR to Herleshausen", "transit", ["TAU", "GELNHAUSEN", "ALSFELD", "HERLESHAUSEN"], (500, 5000), 5,
    "North of the Fulda Gap: the Vogelsberg to Alsfeld and the A4 crossing at Wartha / Herleshausen - the III GE Corps sector, FlaRakGrp 38's HAWK (Freienhagen, Flechtdorf, Rhoden) to the north. " + LLTR,
    "de.wikipedia Flugabwehrraketengruppe 38; en.wikipedia III Corps (Bundeswehr)", seg=2, off=(0, -1))
cor("harz", "The Harz road - Kassel to Helmstedt", "transit", ["TAU", "FTZ", "WRB", "GOSLAR", "HELMSTEDT"], (500, 6000), 5,
    "4 ATAF's road to the North German Plain: the Fritzlar NDB, the Warburg VOR over the ATAF seam at Kassel, Goslar under the Harz, and the Helmstedt gate. " + LLTR,
    "OurAirports FTZ/WRB; GlobalSecurity NORTHAG (Goslar-Paderborn)", seg=3, off=(0, 1))
cor("hofroad", "The Hof corridor - Würzburg to Hof", "transit", ["TAU", "WURZBURG", "BAYREUTH", "HOF"], (500, 5000), 5,
    "The VII US Corps road: Würzburg (69th ADA Group HQ), Bayreuth in the ADIZ, and the Hof gate - the Zwickau axis in reverse. " + LLTR,
    "usarmygermany.com 69th ADA Bde; GlobalSecurity ww3-hof-corridor", seg=1, off=(0, 1))

# 2 ATAF departures
cor("rr_out", "The Ruhr road - Cologne to the Porta", "departure", ["COL", "GMH", "HMM", "GUTERSLOH", "PORTA"], (1000, 8000), 6,
    "Nörvenich and Cologne east over the Cola and Germinghausen VORs to Hamm, Gütersloh and the Minden Gap at Porta Westfalica - NORTHAG's 'vital ground'. CRC Uedem 'CRABTREE', CRC Erndtebrück 'LONESHIP'.",
    "OurAirports COL/GMH/HMM; JMSS (Minden Gap); relikte.com CRC call signs", seg=2, off=(0, -1))
cor("rr_home", "Recovery into the Rhineland", "recovery", ["PORTA", "GUTERSLOH", "HMM", "GMH", "COL"], (2000, 8000), 6,
    "The Ruhr road back; SOC 2 Uedem 'MANDRIL'.", "relikte.com nds_radar", seg=2, off=(0, 1))
cor("ha_out", "The Weser road - Wunstorf to Hehlingen", "departure", ["WUN", "DLE", "BRU", "HLZ"], (1000, 6000), 6,
    "Hannover's fields east over the Leine VOR, Braunschweig (outside the ADIZ by the 1958 exception) to the Hehlingen VOR at Wolfsburg - the I BR Corps sector, the HAWK of 3 and 5 GGW (Aerzen, Velmerstot, Stolzenau) behind.",
    "dewiki ADIZ (Braunschweig); nl.wikipedia Groepen Geleide Wapens", seg=1, off=(0, -1))
cor("ha_home", "Recovery via the Leine", "recovery", ["HLZ", "DLE", "WUN"], (2000, 6000), 6,
    "Hehlingen back over the Leine VOR to Wunstorf; CRC Visselhövede 'SILVERCORK'.", "relikte.com nds_radar", seg=1, off=(0, 1))
cor("ha_north", "The Heath road - Celle to Uelzen", "departure", ["CEL", "FSB", "UELZEN"], (1000, 6000), 6,
    "Celle and Fassberg north over the Lüneburg Heath to the reporting post at Uelzen ('UNITY'), the I GE Corps sector.",
    "relikte.com nds_radar; coldwardecoded I NL Corps", seg=1, off=(-1, 0))
cor("ha_north_home", "Recovery via Fassberg", "recovery", ["UELZEN", "FSB", "CEL"], (2000, 6000), 6,
    "Uelzen back to Fassberg and Celle.", "OurAirports FSB/CEL", seg=1, off=(1, 0))
cor("el_out", "The Elbe road - Hamburg to Lauenburg", "departure", ["HAM", "LAUENBURG"], (1000, 6000), 6,
    "Hamburg's fields south-east down the Elbe to Lauenburg, where the border leaves the river - I NL Corps 'just south of Hamburg'.",
    "coldwardecoded I NL Corps; en.wikipedia Inner German border", seg=0, off=(0, -1))
cor("el_home", "Recovery up the Elbe", "recovery", ["LAUENBURG", "HAM"], (2000, 6000), 6,
    "Lauenburg back up the Elbe to Hamburg; CRC Brekendorf 'BUGLE', SOC 1 Brockzetel 'FLYFISH'.", "relikte.com nds_radar", seg=0, off=(0, 1))
cor("el_lub", "The Trave road - Lübeck to Lauenburg", "departure", ["LUB", "LAUENBURG"], (1000, 6000), 6,
    "Lübeck and Kiel south to Lauenburg; the Priwall border and the Lübeck bay Sperrgebiet to the east.",
    "de.wikipedia Innerdeutsche Grenze (Lübecker Bucht)", seg=0, off=(1, 0))

# 2 ATAF transits
cor("porta_a2", "The A2 - Porta to Helmstedt", "transit", ["PORTA", "WUN", "DLE", "BRU", "HLZ", "HELMSTEDT"], (500, 5000), 5,
    "The Minden Gap to the Helmstedt gate along the Hannover-Berlin autobahn: the center Berlin corridor's own axis, 'the shortest of the three'. " + LLTR,
    CORR, seg=4, off=(0, 1))
cor("uelzen_gate", "The Wendland - Uelzen to Dömitz", "transit", ["UELZEN", "DOMITZ"], (500, 5000), 5,
    "Uelzen to the Elbe bridge at Dömitz - the I GE Corps front, across the river into Mecklenburg. " + LLTR,
    "JMSS (I GE Corps); coldwardecoded", seg=0, off=(0, -1))
cor("hlz_gate", "Hehlingen to Helmstedt", "transit", ["HLZ", "HELMSTEDT"], (500, 5000), 5,
    "The last 15 nm from the Hehlingen VOR to the gate - through the front row of the HAWK belt at low level. " + LLTR,
    "relikte.com nds_flarak_hawk", seg=0, off=(0, -1))
cor("elbe_gate", "Lauenburg to Boizenburg", "transit", ["LAUENBURG", "BOIZENBURG"], (500, 5000), 5,
    "Down the Elbe from Lauenburg to the Boizenburg crossing - the north Berlin corridor's crossing of the border. " + LLTR,
    CORR, seg=0, off=(0, 1))

# the Berlin corridors: the axes east of the gates
cor("north_corr", "The north corridor axis - Boizenburg to Berlin", "transit", ["BOIZENBURG", "LUDWIGSLUST", "PRITZWALK", "NAUEN", "BERLIN"], (500, 10000), 5,
    "The Hamburg-Berlin corridor's centreline: 20 statute miles wide; 10,000 ft is the exercise ceiling. Below it the Wittstock 'polygon' and the 41. FRBr ring (Fehrbellin, Beetz, Schönermark).",
    CORR + "; de.wikipedia Flugabwehrraketentruppen (NVA)", seg=2, off=(0, -1))
cor("centre_corr", "The center corridor axis - Helmstedt to Berlin", "transit", ["HELMSTEDT", "MAGDEBURG", "GENTHIN", "BERLIN"], (500, 10000), 5,
    "The Bückeburg/Hannover-Berlin corridor's centreline over Magdeburg and Genthin; Stendal-Borstel's 135 helicopters north of it, the 41. FRBr's Zachow site at the Berlin end.",
    CORR, seg=1, off=(0, 1))
cor("south_corr", "The south corridor axis - Herleshausen to Berlin", "transit", ["HERLESHAUSEN", "BAD LANGENSALZA", "KELBRA", "HALLE", "DESSAU", "BERLIN"], (500, 10000), 5,
    "The Frankfurt-Berlin corridor's centreline: over the Thuringian basin, Kelbra, north of Halle and Dessau to the Control Zone - the 51. FRBr (Sprötau) and the 41. FRBr (Markgrafpieske) either side.",
    CORR + "; nva-flieger.de Grenzsperrstreifen", seg=2, off=(0, -1))

# ---- the GDR side: 16 VA / LSK departures and transits west --------------------
cor("be_out_w", "Berlin west - Nauen to Rathenow", "departure", ["NAUEN", "RATHENOW"], (1000, 6000), 6,
    "The Berlin fields join at Nauen (örtliche Fluglinie 136), clear of the Control Zone, and run west to Rathenow (Zone 064) - the center corridor's axis in reverse.",
    "nva-flieger.de Luftraum der DDR", seg=1, off=(0, -1))
cor("be_home_w", "Recovery via Nauen", "recovery", ["RATHENOW", "NAUEN"], (2000, 6000), 6,
    "Rathenow back over Nauen into the Berlin ring; Bunker Fuchsbau (Fürstenwalde) has the picture.",
    "d-d-r.de NVA Luftstreitkräfte", seg=0, off=(0, 1))
cor("be_out_nw", "Berlin north-west - Neuruppin to Pritzwalk", "departure", ["NEURUPPIN", "PRITZWALK"], (1000, 6000), 6,
    "North-west over Neuruppin (730 APIB) to Pritzwalk, the Wittstock routes' first turn (Fluglinie 123).",
    "mil-airfields.de Wittstock (routes 023-029)", seg=1, off=(-1, 0))
cor("be_home_nw", "Recovery via Neuruppin", "recovery", ["PRITZWALK", "NEURUPPIN"], (2000, 6000), 6,
    "Pritzwalk back over Neuruppin.", "mil-airfields.de Wittstock", seg=0, off=(1, 0))
cor("be_out_sw", "Berlin south-west - Sperenberg to Dessau", "departure", ["SPERENBERG", "DESSAU"], (1000, 6000), 6,
    "South-west over Sperenberg (226 OSAP) and Jüterbog to Dessau - the south corridor's axis in reverse.",
    CORR, seg=1, off=(1, 0))
cor("be_home_sw", "Recovery via Sperenberg", "recovery", ["DESSAU", "SPERENBERG"], (2000, 6000), 6,
    "Dessau back over Sperenberg into the ring.", CORR, seg=1, off=(-1, 0))
cor("gs_out", "Merseburg - the Harz foot to Kelbra", "departure", ["MERSEBURG", "KELBRA"], (1000, 6000), 6,
    "The southern fields (6 GvIAD Merseburg) west to Kelbra on the Grenzsperrstreifen chain (Fluglinie 177).",
    "nva-flieger.de; en.wikipedia 16th Air Army", seg=0, off=(0, -1))
cor("gs_home", "Recovery via Kelbra", "recovery", ["KELBRA", "MERSEBURG"], (2000, 6000), 6,
    "Kelbra back to Merseburg.", "nva-flieger.de", seg=0, off=(0, 1))
cor("gs_out_n", "Merseburg north - Cochstedt to Gröningen", "departure", ["MERSEBURG", "COCHSTEDT", "GRONINGEN"], (1000, 6000), 6,
    "North-west over Cochstedt to Gröningen on the chain - the road to the Helmstedt gate.",
    "nva-flieger.de", seg=1, off=(1, 0))
cor("gs_home_n", "Recovery via Cochstedt", "recovery", ["GRONINGEN", "COCHSTEDT", "MERSEBURG"], (2000, 6000), 6,
    "Gröningen back over Cochstedt.", "nva-flieger.de", seg=1, off=(-1, 0))
cor("gn_out", "Parchim - Neustadt-Glewe to Ludwigslust", "departure", ["PARCHIM", "NEUSTADT-GLEWE", "LUDWIGSLUST"], (1000, 6000), 6,
    "The Mecklenburg fields south-west over Neustadt-Glewe (Fluglinie 124) to Ludwigslust on the chain - the Elbe crossings beyond.",
    "nva-flieger.de", seg=2, off=(0, 1))
cor("gn_home", "Recovery via Neustadt-Glewe", "recovery", ["LUDWIGSLUST", "NEUSTADT-GLEWE", "PARCHIM"], (2000, 6000), 6,
    "Ludwigslust back over Neustadt-Glewe to Parchim.", "nva-flieger.de", seg=0, off=(0, -1))
cor("gn_out_s", "Parchim south - Perleberg to Osterburg", "departure", ["PARCHIM", "PERLEBERG", "OSTERBURG"], (1000, 6000), 6,
    "South over Perleberg and Osterburg (Fluglinie 126) on the chain - the road to the Altmark and Helmstedt.",
    "nva-flieger.de", seg=1, off=(1, 0))
cor("gn_home_s", "Recovery via Perleberg", "recovery", ["OSTERBURG", "PERLEBERG", "PARCHIM"], (2000, 6000), 6,
    "Osterburg back over Perleberg.", "nva-flieger.de", seg=0, off=(-1, 0))
# GDR-side transits to the gates
cor("r_hagenow", "Ludwigslust to Boizenburg", "transit", ["LUDWIGSLUST", "HAGENOW", "BOIZENBURG"], (500, 4000), 5,
    "The last leg to the Boizenburg crossing - under the HAWK belt's front row beyond the river (FlaRakBtl 37 Belum-Nindorf-Krempel-Gudendorf to the north-west).",
    "relikte.com nds_flarak_hawk", seg=0, off=(0, 1))
cor("r_domitz", "Ludwigslust to Dömitz", "transit", ["LUDWIGSLUST", "DOMITZ"], (500, 4000), 5,
    "Ludwigslust to the Dömitz bridge.", "nva-flieger.de", seg=0, off=(0, 1))
cor("r_pritzwalk", "Pritzwalk to Boizenburg", "transit", ["PRITZWALK", "LUDWIGSLUST", "BOIZENBURG"], (500, 4000), 5,
    "The north corridor's axis west: Pritzwalk, Ludwigslust, the Boizenburg crossing.", CORR, seg=1, off=(0, 1))
cor("r_rathenow", "Rathenow to Helmstedt", "transit", ["RATHENOW", "GENTHIN", "MAGDEBURG", "HELMSTEDT"], (500, 4000), 5,
    "The center corridor's axis west: Genthin, Magdeburg, the Marienborn crossing at Helmstedt.",
    CORR, seg=1, off=(0, 1))
cor("r_altmark", "Osterburg to Helmstedt", "transit", ["OSTERBURG", "HALDENSLEBEN", "HELMSTEDT"], (500, 4000), 5,
    "Down the Altmark over Haldensleben to the Helmstedt gate.", "nva-flieger.de", seg=0, off=(1, 0))
cor("r_groningen", "Gröningen to Helmstedt", "transit", ["GRONINGEN", "HELMSTEDT"], (500, 4000), 5,
    "Gröningen north to the Helmstedt gate.", "nva-flieger.de", seg=0, off=(1, 0))
cor("r_werra", "Kelbra to Herleshausen", "transit", ["KELBRA", "BAD LANGENSALZA", "HERLESHAUSEN"], (500, 4000), 5,
    "Kelbra, Bad Langensalza (Fluglinie 178) and the Werra crossing at Herleshausen - the south corridor's axis west.",
    "nva-flieger.de", seg=1, off=(0, 1))
cor("r_fulda", "Kelbra to Point Alpha", "transit", ["KELBRA", "SUHL", "BARCHFELD", "POINT ALPHA"], (500, 4000), 5,
    "Kelbra south-west over Suhl and Barchfeld on the chain to the Fulda Gap.", "nva-flieger.de", seg=2, off=(0, 1))
cor("r_dessau", "Dessau to Herleshausen", "transit", ["DESSAU", "HALLE", "KELBRA", "BAD LANGENSALZA", "HERLESHAUSEN"], (500, 4000), 5,
    "Berlin's road west: the south corridor's axis over Halle and Kelbra to the Werra.", CORR, seg=2, off=(0, -1))

# ---- gates ------------------------------------------------------------------
GATES = {
    "BOIZENBURG": "the Elbe crossing below Lauenburg - Hamburg, Lübeck and Kiel to the west; Schwerin, Parchim, Laage and the coast to the east",
    "DOMITZ": "the Elbe bridge in the Wendland - Uelzen, Celle and Hannover to the west; Ludwigslust, Parchim and Wittstock to the east",
    "HELMSTEDT": "Checkpoint Alpha on the A2 - Braunschweig, Hannover and the Ruhr to the west; Magdeburg, the Altmark and Berlin to the east",
    "HERLESHAUSEN": "the Werra crossing on the A4 - Kassel and Rhein-Main to the west; Eisenach, Erfurt, Halle and Berlin to the east",
    "POINT ALPHA": "the Fulda Gap - Fulda, Frankfurt and the Pfalz to the west; Suhl, Erfurt, Merseburg and Leipzig to the east",
    "HOF": "the Hof corridor - Bayreuth, Nuremberg and Würzburg to the west; Plauen, Gera, Zwickau and Chemnitz to the east",
}

# ---- sectors (targets) --------------------------------------------------------------
SECTORS = {
    "_comment": "Which family of roads a TARGET belongs to. Checked in order; the GDR sectors first, then the FRG. A target on the wrong side of the line for the home cluster still gets a plan (the data lists plans by cluster), an in-cluster target is 'local'.",
    "rules": [
        {"sector": "gdr_north", "when": "lat >= 53.2 and lat <= 54.6 and lon >= 10.7"},
        {"sector": "berlin", "when": "lat >= 52.15 and lat <= 53.2 and lon >= 12.2"},
        {"sector": "altmark", "when": "lat >= 52.15 and lat <= 53.2 and lon >= 10.7 and lon <= 12.2"},
        {"sector": "saxony", "when": "lat <= 51.3 and lon >= 12.0"},
        {"sector": "gdr_south", "when": "lat <= 52.15 and lon >= 10.4"},
        {"sector": "frg_north", "when": "lat >= 53.0 and lon <= 10.7"},
        {"sector": "hannover", "when": "lat >= 51.7 and lat <= 53.0 and lon >= 7.9 and lon <= 10.7"},
        {"sector": "ruhr", "when": "lat >= 50.5 and lat <= 51.7 and lon <= 7.9"},
        {"sector": "hessen", "when": "lat >= 50.2 and lat <= 51.7 and lon >= 7.9 and lon <= 10.4"},
        {"sector": "pfalz", "when": "lat <= 50.5 and lon <= 10.4"},
    ],
    "default": "none",
    "labels": {"gdr_north": "Mecklenburg - the northern fields and the coast", "berlin": "Berlin - the 16th Air Army's ring",
               "altmark": "the Altmark - Magdeburg and Stendal", "saxony": "Saxony - Dresden, Chemnitz and the Vogtland",
               "gdr_south": "Thuringia and the Leipzig basin", "frg_north": "the Elbe - Hamburg, Lübeck and Kiel",
               "hannover": "the North German Plain - Hannover and the Weser", "ruhr": "the Rhineland and the Ruhr",
               "hessen": "Hessen - Kassel, Fulda and the Gap", "pfalz": "Rhein-Main, the Eifel and the Pfalz",
               "local": "local"},
}


def P(out, gin, gout, back):
    return {"low": {"out": out, "gate_in": gin, "gate_out": gout, "back": back}}


PLANS = {
    # ---- NATO clusters: out = departure + LLTR + GDR transit; back = recovery
    "eifel": {
        "gdr_south": P(["ef_out", "fulda"], "POINT ALPHA", "POINT ALPHA", "ef_home"),
        "saxony":    P(["ef_out", "hofroad"], "HOF", "HOF", "ef_home"),
        "berlin":    P(["ef_out", "werra", "south_corr"], "HERLESHAUSEN", "HERLESHAUSEN", "ef_home"),
        "altmark":   P(["ef_out", "harz"], "HELMSTEDT", "HELMSTEDT", "ef_home"),
        "gdr_north": P(["ef_out", "harz", "centre_corr"], "HELMSTEDT", "HELMSTEDT", "ef_home"),
    },
    "pfalz": {
        "gdr_south": P(["pf_out", "fulda"], "POINT ALPHA", "POINT ALPHA", "pf_home"),
        "saxony":    P(["pf_out", "hofroad"], "HOF", "HOF", "pf_home"),
        "berlin":    P(["pf_out", "werra", "south_corr"], "HERLESHAUSEN", "HERLESHAUSEN", "pf_home"),
        "altmark":   P(["pf_out", "harz"], "HELMSTEDT", "HELMSTEDT", "pf_home"),
        "gdr_north": P(["pf_out", "harz", "centre_corr"], "HELMSTEDT", "HELMSTEDT", "pf_home"),
    },
    "hunsruck": {
        "gdr_south": P(["hu_out", "fulda"], "POINT ALPHA", "POINT ALPHA", "hu_home"),
        "saxony":    P(["hu_out", "hofroad"], "HOF", "HOF", "hu_home"),
        "berlin":    P(["hu_out", "werra"], "HERLESHAUSEN", "HERLESHAUSEN", "hu_home"),
        "altmark":   P(["hu_out", "harz"], "HELMSTEDT", "HELMSTEDT", "hu_home"),
        "gdr_north": P(["hu_out", "harz"], "HELMSTEDT", "HELMSTEDT", "hu_home"),
    },
    "rheinmain": {
        "gdr_south": P(["rm_out", "fulda"], "POINT ALPHA", "POINT ALPHA", "rm_home"),
        "saxony":    P(["rm_out", "fulda"], "POINT ALPHA", "POINT ALPHA", "rm_home"),
        "berlin":    P(["rm_out", "werra", "south_corr"], "HERLESHAUSEN", "HERLESHAUSEN", "rm_home"),
        "altmark":   P(["rm_out", "werra", "south_corr"], "HERLESHAUSEN", "HERLESHAUSEN", "rm_home"),
        "gdr_north": P(["rm_out", "werra", "south_corr"], "HERLESHAUSEN", "HERLESHAUSEN", "rm_home"),
    },
    "rhineruhr": {
        "berlin":    P(["rr_out", "porta_a2", "centre_corr"], "HELMSTEDT", "HELMSTEDT", "rr_home"),
        "altmark":   P(["rr_out", "porta_a2"], "HELMSTEDT", "HELMSTEDT", "rr_home"),
        "gdr_north": P(["rr_out", "porta_a2", "centre_corr"], "HELMSTEDT", "HELMSTEDT", "rr_home"),
        "gdr_south": P(["rr_out", "porta_a2", "centre_corr"], "HELMSTEDT", "HELMSTEDT", "rr_home"),
        "saxony":    P(["rr_out", "porta_a2", "centre_corr"], "HELMSTEDT", "HELMSTEDT", "rr_home"),
    },
    "hannover": {
        "berlin":    P(["ha_out", "hlz_gate", "centre_corr"], "HELMSTEDT", "HELMSTEDT", "ha_home"),
        "altmark":   P(["ha_out", "hlz_gate"], "HELMSTEDT", "HELMSTEDT", "ha_home"),
        "gdr_north": P(["ha_north", "uelzen_gate"], "DOMITZ", "DOMITZ", "ha_north_home"),
        "gdr_south": P(["ha_out", "hlz_gate", "centre_corr"], "HELMSTEDT", "HELMSTEDT", "ha_home"),
        "saxony":    P(["ha_out", "hlz_gate", "centre_corr"], "HELMSTEDT", "HELMSTEDT", "ha_home"),
    },
    "elbe": {
        "gdr_north": P(["el_out", "elbe_gate"], "BOIZENBURG", "BOIZENBURG", "el_home"),
        "berlin":    P(["el_out", "elbe_gate", "north_corr"], "BOIZENBURG", "BOIZENBURG", "el_home"),
        "altmark":   P(["el_out", "elbe_gate", "north_corr"], "BOIZENBURG", "BOIZENBURG", "el_home"),
        "gdr_south": P(["el_out", "elbe_gate", "north_corr"], "BOIZENBURG", "BOIZENBURG", "el_home"),
        "saxony":    P(["el_out", "elbe_gate", "north_corr"], "BOIZENBURG", "BOIZENBURG", "el_home"),
    },
    # ---- Warsaw Pact clusters
    "berlin": {
        "hannover":  P(["be_out_w", "r_rathenow"], "HELMSTEDT", "HELMSTEDT", "be_home_w"),
        "ruhr":      P(["be_out_w", "r_rathenow"], "HELMSTEDT", "HELMSTEDT", "be_home_w"),
        "frg_north": P(["be_out_nw", "r_pritzwalk"], "BOIZENBURG", "BOIZENBURG", "be_home_nw"),
        "hessen":    P(["be_out_sw", "r_dessau"], "HERLESHAUSEN", "HERLESHAUSEN", "be_home_sw"),
        "pfalz":     P(["be_out_sw", "r_dessau"], "HERLESHAUSEN", "HERLESHAUSEN", "be_home_sw"),
    },
    "gdr_south": {
        "hessen":    P(["gs_out", "r_werra"], "HERLESHAUSEN", "HERLESHAUSEN", "gs_home"),
        "pfalz":     P(["gs_out", "r_fulda"], "POINT ALPHA", "POINT ALPHA", "gs_home"),
        "hannover":  P(["gs_out_n", "r_groningen"], "HELMSTEDT", "HELMSTEDT", "gs_home_n"),
        "ruhr":      P(["gs_out_n", "r_groningen"], "HELMSTEDT", "HELMSTEDT", "gs_home_n"),
        "frg_north": P(["gs_out_n", "r_groningen"], "HELMSTEDT", "HELMSTEDT", "gs_home_n"),
    },
    "gdr_north": {
        "frg_north": P(["gn_out", "r_hagenow"], "BOIZENBURG", "BOIZENBURG", "gn_home"),
        "hannover":  P(["gn_out", "r_domitz"], "DOMITZ", "DOMITZ", "gn_home"),
        "ruhr":      P(["gn_out_s", "r_altmark"], "HELMSTEDT", "HELMSTEDT", "gn_home_s"),
        "hessen":    P(["gn_out_s", "r_altmark"], "HELMSTEDT", "HELMSTEDT", "gn_home_s"),
        "pfalz":     P(["gn_out_s", "r_altmark"], "HELMSTEDT", "HELMSTEDT", "gn_home_s"),
    },
}

CLUSTERS = {
    "eifel": {"label": "the Eifel (Bitburg, Spangdahlem) - 4 ATAF",
              "fields": ["Bitburg", "Spangdahlem"],
              "center": [49.96, 6.63], "local_nm": 18, "join_from_outside": False},
    "hunsruck": {"label": "the Hunsrück (Hahn, Pferdsfeld, Büchel) - 4 ATAF",
                 "fields": ["Hahn", "Pferdsfeld", "Buchel", "Mendig", "Airracing Koblenz", "Sprendlingen"],
                 "center": [49.95, 7.26], "local_nm": 18, "join_from_outside": False},
    "pfalz": {"label": "the Pfalz (Ramstein, Sembach, Zweibrücken) - 4 ATAF",
              "fields": ["Ramstein", "Sembach", "Zweibrucken", "Landstuhl", "Pottschutthohe", "Bad Durkheim"],
              "center": [49.44, 7.62], "local_nm": 20, "join_from_outside": False},
    "rheinmain": {"label": "Rhein-Main and Hessen (Wiesbaden, Frankfurt, the Army airfields) - 4 ATAF",
                  "fields": ["Wiesbaden", "Frankfurt", "Mainz Finthen", "Langenselbold", "Gelnhausen", "Ober-Morlen",
                             "Giebelstadt", "Schweinfurt", "Fritzlar", "Fulda", "Airracing Frankfurt",
                             "Worms", "Heidelberg", "Walldorf", "Hockenheim", "Herrenteich", "Adelsheim"],
                  "center": [50.05, 8.45], "local_nm": 22, "join_from_outside": False},
    "rhineruhr": {"label": "the Rhineland (Nörvenich, Cologne, Gütersloh) - 2 ATAF",
                  "fields": ["Norvenich", "Cologne", "Dusseldorf", "Gutersloh"],
                  "center": [50.85, 6.90], "local_nm": 22, "join_from_outside": False},
    "hannover": {"label": "the Weser and the Heath (Wunstorf, Bückeburg, Celle, Fassberg) - 2 ATAF",
                 "fields": ["Wunstorf", "Buckeburg", "Hannover", "Celle", "Fassberg", "Hildesheim", "Braunschweig",
                            "Rinteln", "Verden-Scharnhorst", "Bremen", "Weser Wumme", "Glindbruchkippe", "Grosse Wiese", "Ummern"],
                 "center": [52.46, 9.56], "local_nm": 22, "join_from_outside": False},
    "elbe": {"label": "the Elbe (Hamburg, Lübeck, Kiel) - 2 ATAF",
             "fields": ["Hamburg", "Hamburg Finkenwerder", "Uetersen", "Lubeck", "Kiel", "Nordholz", "Luneburg", "Sittensen",
                        "Airracing Lubeck"],
             "center": [53.63, 9.98], "local_nm": 22, "join_from_outside": False},
    "berlin": {"label": "the Berlin ring (Werneuchen, Finow, Templin, Sperenberg, Neuruppin, Wittstock) - 16th Air Army",
               "fields": ["Werneuchen", "Finow", "Templin", "Sperenberg", "Altes Lager", "Neuruppin", "Wittstock",
                          "Oranienburg", "Brand", "Marxwalde", "Schonefeld", "Tegel", "Tempelhof", "Gatow", "Briest",
                          "Perwenitz", "Bienenfarm", "Kammermark", "Larz", "Stendal", "Mahlwinkel", "Gardelegen"],
               "center": [52.48, 13.35], "local_nm": 30, "join_from_outside": False},
    "gdr_south": {"label": "the southern fields (Merseburg, Falkenberg, Holzdorf, Zerbst, Cochstedt) - 6 GvIAD",
                  "fields": ["Merseburg", "Falkenberg", "Holzdorf", "Brandis", "Leipzig Mockau", "Schkeuditz", "Kothen",
                             "Zerbst", "Cochstedt", "Dessau", "Allstedt", "Thurland", "Zollschen", "Bindersleben",
                             "Obermehler Schlotheim", "Haina", "Hasselfelde"],
                  "center": [51.55, 12.10], "local_nm": 25, "join_from_outside": False},
    "gdr_north": {"label": "Mecklenburg (Parchim, Laage, Damgarten, Tutow, Neubrandenburg) - 16 GvIAD",
                  "fields": ["Parchim", "Laage", "Damgarten", "Barth", "Tutow", "Neubrandenburg", "Peenemunde", "Garz",
                             "Wismar", "Pinnow", "Waren Vielist", "Gross Mohrdorf", "Dedelow", "Northeim"],
                  "center": [53.60, 12.30], "local_nm": 25, "join_from_outside": False},
}

# ---- fix-ups: the out-chains must end on the gate; the GDR transits west of it
# are the other side's roads and are drawn, not flown. -----------------------------
for cl, sectors in PLANS.items():
    for sec, modes in sectors.items():
        p = modes["low"]
        out = p["out"]
        # keep corridors up to and including the first one that ends on the gate
        keep = []
        for cid in out:
            keep.append(cid)
            c = next(x for x in C if x["id"] == cid)
            if c["points"][-1] == p["gate_in"]:
                break
        p["out"] = keep

# ---- geometry helpers ----------------------------------------------------------------
def offset_line(pts, km, side=1.0):
    """A polyline moved `km` to its left (side=+1) or right (-1), in a flat
    lat/lon frame. For the ADIZ and the belts, which are 'x km west of the
    border' in every source."""
    out = []
    n = len(pts)
    for i, (la, lo) in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        k = math.cos(math.radians(la))
        dx = (b[1] - a[1]) * k
        dy = (b[0] - a[0])
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L               # left normal
        dkm = km / 111.0
        out.append([round(la + side * ny * dkm, 4), round(lo + side * nx * dkm / k, 4)])
    return out


def band(line, km0, km1, side=1.0):
    """The polygon between two offsets of a polyline."""
    a = offset_line(line, km0, side)
    b = offset_line(line, km1, side)
    return a + b[::-1]


# the inner-German border (schematic, north to south; the Bavarian-Bohemian border after Hof)
IGB = [[53.96, 10.89], [53.90, 10.80], [53.70, 10.85], [53.55, 10.75], [53.37, 10.57], [53.30, 10.75], [53.20, 11.00],
       [53.13, 11.26], [53.03, 11.57], [52.90, 11.45], [52.83, 10.95], [52.65, 10.85], [52.43, 10.97], [52.23, 11.01],
       [52.05, 10.95], [51.90, 10.60], [51.73, 10.61], [51.58, 10.62], [51.50, 10.30], [51.35, 10.05], [51.20, 10.05],
       [51.00, 10.15], [50.85, 10.00], [50.72, 9.94], [50.65, 10.00], [50.50, 10.10], [50.42, 10.30], [50.35, 10.60],
       [50.30, 10.95], [50.50, 11.40], [50.35, 11.65], [50.42, 11.87], [50.30, 12.10], [50.17, 12.20], [49.98, 12.40],
       [49.80, 12.50], [49.65, 12.50], [49.30, 12.90]]
# the border's west side is the polyline's left going north->south? No: going south the west is to the right.
ADIZ = band(IGB, 0.0, 40.0, side=-1.0)
HAWK = band(IGB, 12.0, 55.0, side=-1.0)
NIKE = band(IGB, 105.0, 155.0, side=-1.0)


def poly_dm(s):
    """'53°11.50′N 007°13.00′E | ...' -> [[lat, lon], ...]"""
    out = []
    for tok in s.split("|"):
        tok = tok.strip().replace("′", "").replace("°", " ")
        la, lo = tok.split("N")
        lo = lo.strip().rstrip("E")
        d, m = la.split(); D, M = lo.split()
        out.append([dm(int(d), float(m)), dm(int(D), float(M))])
    return out


def poly_dms(s):
    """'N 52 26 00 E 007 12 00 – ...' -> [[lat, lon], ...]"""
    out = []
    for tok in s.replace("–", "-").split(" - "):
        tok = tok.strip()
        if not tok:
            continue
        parts = tok.replace("N", " ").replace("E", " ").split()
        la = dms(int(parts[0]), int(parts[1]), int(parts[2]))
        lo = dms(int(parts[3]), int(parts[4]), int(parts[5]))
        out.append([la, lo])
    return out


NFL = "NfL 2025-1-3686 'Bekanntmachung über Tiefflüge' (the seven 250-ft areas re-published with the Cold War names; de.wikipedia Tiefflug)"
ENR51 = "AIP Germany ENR 5.1, AIRAC AMDT 03/24 (21 MAR 2024)"

LFA1 = poly_dm("53°11.50′N 007°13.00′E | 53°09.50′N 007°34.00′E | 53°10.67′N 007°40.50′E | 53°07.00′N 007°57.00′E | 53°04.08′N 008°10.55′E | 53°03.43′N 008°13.50′E | 52°57.50′N 008°41.33′E | 52°51.70′N 008°42.50′E | 52°50.00′N 008°42.75′E | 52°48.50′N 008°39.91′E | 52°47.00′N 008°38.00′E | 52°43.25′N 008°32.25′E | 52°42.00′N 008°28.67′E | 52°43.25′N 008°18.67′E | 52°43.00′N 008°16.50′E | 52°41.00′N 008°14.45′E | 52°39.08′N 008°13.50′E | 52°26.33′N 007°58.00′E | 52°31.33′N 007°40.25′E | 52°39.33′N 007°29.70′E | 52°41.00′N 007°28.00′E | 52°42.00′N 007°24.00′E | 52°53.00′N 007°32.50′E | 52°57.00′N 007°36.00′E | 52°58.00′N 007°26.00′E | 52°56.00′N 007°24.50′E | 52°42.00′N 007°15.00′E | 52°41.00′N 007°15.17′E | 52°43.08′N 007°03.83′E")
LFA2 = poly_dm("52°12.67′N 007°05.00′E | 52°12.17′N 007°09.80′E | 52°12.50′N 007°11.33′E | 52°11.65′N 007°13.22′E | 52°09.50′N 007°18.83′E | 52°08.00′N 007°21.00′E | 52°02.50′N 007°30.00′E | 51°54.67′N 007°30.00′E | 51°52.00′N 007°22.00′E | 51°53.50′N 007°16.00′E | 51°50.50′N 007°06.25′E | 51°43.50′N 007°06.25′E | 51°43.50′N 007°05.50′E | 51°45.08′N 007°01.53′E | 51°43.42′N 007°01.00′E | 51°41.77′N 006°53.72′E | 51°41.00′N 006°51.00′E | 51°40.00′N 006°40.50′E | 51°39.67′N 006°35.50′E | 51°39.67′N 006°31.00′E | 51°45.08′N 006°25.25′E | 51°45.50′N 006°23.00′E | 51°46.00′N 006°20.00′E | 51°47.83′N 006°25.17′E | 51°50.33′N 006°27.65′E | 51°48.67′N 006°34.83′E | 51°50.17′N 006°40.08′E | 51°51.10′N 006°41.00′E | 51°53.83′N 006°43.00′E | 52°08.58′N 006°52.75′E")
LFA3 = poly_dm("51°09.33′N 007°58.00′E | 51°10.50′N 008°00.20′E | 51°16.25′N 008°11.50′E | 51°15.00′N 008°12.50′E | 51°20.42′N 008°16.00′E | 51°21.00′N 008°19.00′E | 51°21.40′N 008°22.00′E | 51°22.13′N 008°24.63′E | 51°22.00′N 008°27.58′E | 51°21.80′N 008°30.50′E | 51°18.17′N 008°35.50′E | 51°18.50′N 008°38.00′E | 51°43.67′N 008°59.83′E | 51°44.00′N 009°03.00′E | 51°45.50′N 009°05.50′E | 51°47.00′N 009°02.58′E | 51°50.25′N 009°05.50′E | 51°51.18′N 009°06.07′E | 51°53.17′N 009°06.00′E | 51°56.80′N 009°14.77′E | 51°58.33′N 009°16.30′E | 52°02.50′N 009°23.00′E | 51°59.08′N 009°29.50′E | 51°58.83′N 009°32.50′E | 51°52.67′N 009°53.00′E | 51°50.00′N 009°49.00′E | 51°39.50′N 009°46.00′E | 51°39.42′N 009°40.00′E | 51°38.67′N 009°38.50′E | 51°37.67′N 009°34.00′E | 51°38.83′N 009°24.75′E | 51°40.40′N 009°24.30′E | 51°39.70′N 009°21.20′E | 51°37.00′N 009°23.00′E | 51°10.50′N 008°53.00′E | 51°05.00′N 008°50.00′E | 50°56.00′N 008°43.00′E | 50°52.50′N 008°45.50′E | 50°53.67′N 008°32.33′E | 50°55.25′N 008°30.33′E | 50°55.50′N 008°26.58′E | 50°55.83′N 008°23.50′E | 50°57.17′N 008°18.33′E | 50°58.00′N 008°09.00′E | 50°58.60′N 008°07.00′E | 50°59.50′N 008°06.17′E | 50°58.53′N 008°05.50′E | 50°57.50′N 008°01.00′E | 50°58.42′N 007°58.50′E | 51°02.25′N 007°52.50′E | 51°02.75′N 007°50.00′E | 51°07.00′N 007°53.33′E | 51°07.92′N 007°56.00′E")
LFA5 = poly_dm("52°57.50′N 009°25.00′E | 53°04.33′N 009°27.00′E | 53°09.25′N 009°29.00′E | 53°10.83′N 009°27.50′E | 53°12.75′N 009°20.00′E | 53°16.83′N 009°17.00′E | 53°18.42′N 009°15.42′E | 53°28.50′N 009°09.50′E | 53°18.67′N 009°48.50′E | 53°01.17′N 009°51.00′E | 52°59.00′N 009°47.33′E | 52°58.75′N 009°36.50′E | 52°58.58′N 009°33.50′E")
LFA6 = poly_dm("54°01.00′N 009°16.00′E | 54°04.58′N 009°04.67′E | 54°05.00′N 009°03.17′E | 54°06.00′N 009°00.00′E | 54°08.50′N 008°55.00′E | 54°15.75′N 008°53.50′E | 54°22.33′N 009°00.00′E | 54°21.00′N 009°03.67′E | 54°22.00′N 009°04.83′E | 54°17.00′N 009°21.00′E | 54°14.50′N 009°21.50′E | 54°15.17′N 009°26.50′E | 54°12.83′N 009°29.50′E | 54°13.00′N 009°39.67′E | 54°15.33′N 009°42.83′E | 54°16.42′N 009°44.83′E | 54°11.00′N 009°50.50′E | 54°09.42′N 009°52.50′E | 54°07.25′N 009°56.25′E | 54°01.67′N 009°57.00′E | 53°59.67′N 009°56.00′E | 53°58.67′N 009°56.00′E | 53°54.67′N 009°53.00′E | 53°47.58′N 009°52.75′E | 53°46.67′N 009°40.33′E | 53°46.33′N 009°37.50′E | 53°44.00′N 009°27.50′E | 53°47.17′N 009°24.67′E | 53°48.08′N 009°24.42′E | 53°52.67′N 009°17.33′E")

EDR31 = poly_dms("N 52 55 00 E 009 55 30 – N 52 49 00 E 009 57 00 – N 52 45 00 E 009 58 00 – N 52 42 50 E 009 58 10 – N 52 42 55 E 009 50 55 – N 52 42 35 E 009 44 23 – N 52 43 57 E 009 41 35 – N 52 46 00 E 009 40 00 – N 52 51 00 E 009 42 00 – N 52 55 00 E 009 48 00 – N 52 57 00 E 009 53 00")
EDR32A = poly_dms("N 53 02 20 E 009 59 30 – N 52 58 40 E 010 10 30 – N 52 57 00 E 010 10 00 – N 52 54 00 E 010 07 30 – N 52 49 00 E 009 57 00 – N 52 55 00 E 009 55 30 – N 52 57 00 E 009 53 00 – N 53 00 00 E 009 55 00")
EDR32B = poly_dms("N 53 05 30 E 010 06 00 – N 53 03 00 E 010 16 00 – N 53 00 00 E 010 16 00 – N 52 58 40 E 010 10 30 – N 53 02 20 E 009 59 30")
EDR33A = poly_dms("N 53 00 00 E 010 15 00 – N 53 00 00 E 010 18 30 – N 52 56 00 E 010 18 30 – N 52 56 00 E 010 19 40 – N 52 51 00 E 010 19 40 – N 52 51 00 E 010 15 00")
EDR34A = poly_dms("N 52 42 00 E 007 17 39 – N 52 43 27 E 007 15 59 – N 52 56 00 E 007 24 30 – N 52 53 00 E 007 32 30 – N 52 42 00 E 007 24 00")
EDR34C = poly_dms("N 52 57 00 E 007 36 00 – N 52 57 00 E 007 53 49 – N 52 48 39 E 007 54 04 – N 52 42 00 E 007 24 00 – N 52 53 00 E 007 32 30")
EDR10A = poly_dms("N 54 30 00 E 010 25 00 – N 54 32 39 E 010 31 37 – N 54 30 39 E 010 39 12 – N 54 32 32 E 010 53 00 – N 54 26 00 E 010 53 00 – N 54 25 00 E 010 50 00 – N 54 25 00 E 010 40 00 – N 54 20 00 E 010 40 00 – N 54 15 19 E 010 40 00 – N 54 20 00 E 010 25 00")
EDR11B = poly_dms("N 54 45 00 E 010 09 24 – N 54 35 35 E 010 20 24 – N 54 32 39 E 010 31 37 – N 54 30 00 E 010 25 00 – N 54 29 30 E 010 17 00 – N 54 34 00 E 010 08 00 – N 54 41 00 E 010 08 00 – N 54 42 30 E 010 06 30")
EDR13B = poly_dms("N 54 02 00 E 008 51 00 – N 53 59 00 E 008 44 30 – N 54 02 00 E 008 05 00 – N 54 08 30 E 008 05 00 – N 54 14 30 E 008 23 00 – N 54 12 30 E 008 42 00 – N 54 06 29 E 008 52 23 – N 54 07 00 E 008 44 00 – N 54 04 00 E 008 44 00")


def strip(p0, p1, half_nm):
    """A straight corridor of +-half_nm about the line p0-p1 (the Berlin
    corridors: 'ten miles each side of the center line')."""
    return band([list(p0), list(p1)], -half_nm * 1.852, half_nm * 1.852, side=1.0)


def box(lat, lon, w_km, h_km):
    dl = h_km / 2 / 111.0
    dn = w_km / 2 / (111.0 * math.cos(math.radians(lat)))
    return [[round(lat + dl, 4), round(lon - dn, 4)], [round(lat + dl, 4), round(lon + dn, 4)],
            [round(lat - dl, 4), round(lon + dn, 4)], [round(lat - dl, 4), round(lon - dn, 4)]]


AREAS = [
    {"id": "ADIZ", "kind": "zone", "label": "ADIZ / FLUGÜBERWACHUNGSZONE", "alt": "40 km - flight plan + ATC, USAFE clearance", "approx": True, "poly": ADIZ,
     "label_at": [53.72, 10.2], "src": "dewiki ADIZ: 'eine Tiefe von 25 bis 30 Seemeilen bzw. später durchschnittlich 40 km' west of the border (band on a schematic border)"},
    {"id": "HAWK", "kind": "moa", "label": "HAWK BELT (LOMEZ)", "alt": "I-HAWK 40 km / 17,700 m - Denmark to Austria", "approx": True, "poly": HAWK,
     "label_at": [52.65, 10.5], "src": "relikte.com nds_flarak_hawk; nl.wikipedia GGW: LOMEZ 'ca. 50 km diep direct achter het IJzeren Gordijn'; A&SF July 1983"},
    {"id": "NIKE", "kind": "alert", "label": "NIKE HERCULES BELT (MEZ)", "alt": "'ca. 150 km westlich des Eisernen Vorhangs' - North Sea to Stuttgart", "approx": True, "poly": NIKE,
     "label_at": [53.3, 8.55], "src": "relikte.com nds_flarak_nike; de.wikipedia Nike (Rakete): 70 sites; bahnjdbund.de 'Dach über Europa'"},
    {"id": "LFA1", "kind": "tma", "label": "LFA 1\n250 ft", "alt": "Cloppenburg", "poly": LFA1, "label_at": [52.75, 7.75], "src": NFL},
    {"id": "LFA2", "kind": "tma", "label": "LFA 2\n250 ft", "alt": "Borken", "poly": LFA2, "label_at": [51.95, 6.75], "src": NFL},
    {"id": "LFA3", "kind": "tma", "label": "LFA 3\n250 ft", "alt": "Holzminden", "poly": LFA3, "label_at": [51.92, 9.15], "src": NFL},
    {"id": "LFA5", "kind": "tma", "label": "LFA 5\n250 ft", "alt": "Schneverdingen", "poly": LFA5, "label_at": [53.32, 9.35], "src": NFL},
    {"id": "LFA6", "kind": "tma", "label": "LFA 6\n250 ft", "alt": "Itzehoe", "poly": LFA6, "label_at": [54.05, 9.35], "src": NFL},
    {"id": "ED-R 37", "kind": "restricted", "label": "ED-R 37\nNORDHORN RANGE", "alt": "FL 100 / GND", "poly": circle(dms(52, 26, 0), dms(7, 12, 0), 5, 24), "label_at": [52.33, 7.12], "src": ENR51 + ": 'Circle with a radius of 5 NM centered at N 52 26 00 E 007 12 00'; RAF range 1945-2001"},
    {"id": "ED-R 34", "kind": "restricted", "label": "ED-R 34\nMEPPEN WTD 91", "alt": "30,000 ft MSL / GND", "poly": EDR34A, "label_at": [52.60, 7.30], "src": ENR51 + " (34A)"},
    {"id": "ED-R 34C", "kind": "restricted", "label": "", "alt": "FL 80 / GND", "poly": EDR34C, "label_at": [52.85, 7.75], "src": ENR51 + " (34C)"},
    {"id": "ED-R 31", "kind": "restricted", "label": "ED-R 31\nBERGEN-HOHNE", "alt": "14,000 ft MSL / GND", "poly": EDR31, "label_at": [52.60, 9.85], "src": ENR51},
    {"id": "ED-R 32A", "kind": "restricted", "label": "ED-R 32\nMUNSTER", "alt": "14,000 ft MSL / GND", "poly": EDR32A, "label_at": [53.12, 9.75], "src": ENR51},
    {"id": "ED-R 32B", "kind": "restricted", "label": "", "alt": "10,500 ft MSL / GND", "poly": EDR32B, "label_at": [53.1, 10.3], "src": ENR51},
    {"id": "ED-R 33", "kind": "restricted", "label": "ED-R 33\nUNTERLÜSS", "alt": "24,000 ft MSL / GND", "poly": EDR33A, "label_at": [52.95, 10.55], "src": ENR51 + " (33A)"},
    {"id": "ED-R 10", "kind": "restricted", "label": "ED-R 10\nTODENDORF-PUTLOS", "alt": "40,000 ft MSL / GND", "poly": EDR10A, "label_at": [54.62, 10.55], "src": ENR51 + " (10A)"},
    {"id": "ED-R 11", "kind": "restricted", "label": "ED-R 11\nOSTSEE", "alt": "48,000 ft MSL", "poly": EDR11B, "label_at": [54.72, 9.75], "src": ENR51 + " (11B)"},
    {"id": "ED-R 13", "kind": "restricted", "label": "ED-R 13\nMELDORFER BUCHT", "alt": "24,500 ft MSL", "poly": EDR13B, "label_at": [54.22, 8.15], "src": ENR51 + " (13B)"},
    {"id": "ED-R 116", "kind": "restricted", "label": "ED-R 116\nBAUMHOLDER", "alt": "23,000 ft MSL / GND", "approx": True, "poly": box(49.633, 7.373, 14, 12), "label_at": [49.55, 7.20], "src": "openaip ED-R 116 (limits; the outline is a box on the point 49.6329, 7.3727)"},
    {"id": "ED-R 136", "kind": "restricted", "label": "ED-R 136\nGRAFENWÖHR", "alt": "30,000 ft MSL / GND, H24", "approx": True, "poly": box(49.678, 11.782, 18, 16), "label_at": [49.83, 11.85], "src": "openaip ED-R 136 (limits; box on the point 49.6782, 11.7822); LSG Amberg script 'immer aktiv'"},
    {"id": "WILDFLECKEN", "kind": "restricted", "label": "WILDFLECKEN\n1/1 ADA HAWK", "alt": "TrÜbPl - ED-R not found", "approx": True, "poly": box(50.40, 9.95, 10, 10), "label_at": [50.28, 10.15], "src": "usarmygermany.com 10th ADA Bde (1/1 ADA at Wildflecken); the outline is a box on the training area"},
    {"id": "TRA LAUTER", "kind": "alert", "label": "TRA 205 LAUTER\n(ex TRA 204 EIFEL)", "alt": "FL 100 - UNL", "approx": True, "poly": [[50.25, 6.4], [50.25, 7.9], [49.35, 7.9], [49.35, 6.4]], "label_at": [49.6, 6.7], "src": "flugzeugforum: 'südöstlich des Funkfeuers Nattenheim ... beginnt in Flugfläche 100', ~40 by 80 nm; Bundestag 16/10116 (TRA 204/304 Eifel absorbed 2003) - outline approximate"},
    {"id": "CORR-N", "approx": True, "kind": "tma", "label": "NORTH CORRIDOR (Hamburg)\n20 SM / 10k exercise", "alt": "BASC", "poly": strip((53.40, 10.70), (52.484, 13.351), 8.69), "label_at": [53.3, 12.1], "src": "FRUS 1945 III/1206: 'Each of the above corridors is 20 English miles (32 kilometers) wide, i.e., 10 miles (16 kilometers) each side of the center line' - drawn from the border crossing to the Control Zone"},
    {"id": "CORR-C", "approx": True, "kind": "tma", "label": "CENTRE CORRIDOR (Bückeburg)\n20 SM / 10k exercise", "alt": "BASC", "poly": strip((52.23, 11.00), (52.484, 13.351), 8.69), "label_at": [52.08, 12.0], "src": "FRUS 1945 III/1206 - the Bückeburg/Hannover corridor, 'the shortest of the three'"},
    {"id": "CORR-S", "approx": True, "kind": "tma", "label": "SOUTH CORRIDOR (Frankfurt)\n20 SM / 10k exercise", "alt": "BASC", "poly": strip((50.80, 10.07), (52.484, 13.351), 8.69), "label_at": [51.72, 11.4], "src": "FRUS 1945 III/1206 - the Frankfurt corridor"},
    {"id": "BCZ", "approx": True, "kind": "tma", "label": "BERLIN CONTROL ZONE\n20 SM / 10k exercise", "alt": "BASC", "poly": circle(52.484, 13.351, 17.38, 36), "label_at": [52.33, 13.7], "src": "FRUS 1945 vol. III doc. 1206: 'a radius of 20 miles (32 kilometers) from the Allied Control Authority Building'"},
    {"id": "FRBR41", "kind": "alert", "label": "41. FRBr RING\nS-75 / S-125 / S-200", "alt": "Fürstenwalde · Prötzel · Klosterfelde · Beetz · Schönermark · Fehrbellin · Zachow · Markgrafpieske", "approx": True, "poly": circle(52.55, 13.30, 30, 36), "label_at": [53.08, 13.0], "src": "de.wikipedia Flugabwehrraketentruppen (NVA): the 41. FRBr's Abteilungen by town; drawn as a 30-NM ring"},
    {"id": "WITTSTOCK", "kind": "restricted", "label": "WITTSTOCK POLYGON\n'Bitburg East'", "alt": "Bombodrom 1952-93; the Bitburg replica", "approx": True, "poly": box(dms(53, 5, 10), dms(12, 38, 42), 11, 11), "label_at": [52.99, 12.65], "src": "de.wikipedia TrÜbPl Wittstock '53° 5′ 10″ N, 12° 38′ 42″ O', 118.99 km²; mil-airfields.de replica N530503 E0124004; 16va.be LABS"},
    {"id": "RETZOW", "kind": "restricted", "label": "RETZOW RANGE", "alt": "Mi-24 and APIB range", "approx": True, "poly": box(53.33, 12.22, 6, 5), "label_at": [53.45, 12.4], "src": "16va.be 'between villages of Retzow and Ganzlin' - box on the villages"},
    {"id": "LETZLINGEN", "kind": "restricted", "label": "LETZLINGER HEIDE", "alt": "TrÜbPl Altmark 232 km²", "approx": True, "poly": box(dms(52, 25, 48), dms(11, 34, 12), 15, 15), "label_at": [52.55, 11.45], "src": "de.wikipedia TrÜbPl Altmark '52° 25′ 48″ N, 11° 34′ 12″ O', 232 km² - box on the center"},
    {"id": "LIEBEROSE", "kind": "restricted", "label": "LIEBEROSE\nair-to-ground range", "alt": "25,500 ha, 28 x 12 km", "approx": True, "poly": box(dms(51, 56, 7), dms(14, 19, 40), 28, 12), "label_at": [51.95, 13.85], "src": "de.wikipedia Lieberoser Heide '51° 56′ 7″ N, 14° 19′ 40″ O', 'Luft-Boden-Schießplatz' - box on the center"},
    {"id": "JUTERBOG", "kind": "restricted", "label": "JÜTERBOG RANGE", "alt": "Schießplatz since 1864", "approx": True, "poly": box(52.06, 12.98, 10, 8), "label_at": [52.12, 12.80], "src": "urbex.nl Altes Lager (Schießplatz Jüterbog) - box north of the field"},
]

# ---- lines: the border, the coast, the Elbe, the ATAF seam, the GDR line ----------
COAST_N = [[53.35, 6.5], [53.45, 6.9], [53.6, 7.2], [53.72, 7.6], [53.6, 8.05], [53.85, 8.15], [53.9, 8.6], [53.87, 9.0],
           [54.0, 8.85], [54.15, 8.85], [54.3, 8.65], [54.5, 8.85], [54.75, 8.6], [54.85, 8.6]]
COAST_B = [[54.85, 9.6], [54.7, 10.0], [54.45, 10.2], [54.4, 10.6], [54.35, 10.85], [54.1, 10.8], [53.96, 10.9], [53.98, 11.2],
           [53.9, 11.45], [54.0, 11.5], [54.15, 11.9], [54.18, 12.1], [54.35, 12.4], [54.45, 12.5], [54.35, 12.8], [54.3, 13.1],
           [54.1, 13.4], [54.05, 13.75], [53.85, 14.2], [53.9, 14.35], [53.65, 14.6], [53.55, 14.9]]
RUGEN = [[54.3, 13.1], [54.6, 13.25], [54.68, 13.4], [54.55, 13.7], [54.35, 13.75], [54.28, 13.4]]
FEHMARN = [[54.53, 11.0], [54.53, 11.3], [54.42, 11.25], [54.42, 11.05]]
LOLLAND = [[54.95, 11.0], [54.95, 12.2], [54.6, 12.05], [54.65, 11.1]]
ELBE = [[53.87, 9.0], [53.75, 9.35], [53.6, 9.6], [53.55, 9.95], [53.45, 10.3], [53.37, 10.57], [53.2, 10.95], [53.13, 11.26],
        [53.03, 11.57], [52.9, 11.85], [52.6, 12.0], [52.4, 12.05], [52.2, 11.75], [52.1, 11.65], [51.85, 12.3], [51.7, 12.4]]
GSS = [[53.93, 14.05], [54.34, 13.73], [54.67, 13.40], [54.47, 12.50], [54.25, 12.25], [54.09, 12.14], [53.87, 11.19],
       [53.75, 11.25], [53.63, 11.41], [53.43, 11.19], [53.32, 11.50], [53.07, 11.86], [52.95, 11.95], [52.78, 11.76],
       [52.65, 11.39], [52.29, 11.41], [51.94, 11.21], [51.79, 10.96], [51.43, 11.04], [51.33, 10.46], [51.11, 10.65],
       [50.83, 10.30], [50.61, 10.69], [50.58, 11.13], [50.70, 11.60], [50.61, 12.17], [50.43, 12.72]]
LINES = [
    {"kind": "coast", "name": "North Sea coast", "pts": COAST_N},
    {"kind": "coast", "name": "Baltic coast", "pts": COAST_B},
    {"kind": "coast", "name": "Rügen", "pts": RUGEN + [RUGEN[0]]},
    {"kind": "coast", "name": "Fehmarn", "pts": FEHMARN + [FEHMARN[0]]},
    {"kind": "border", "name": "Inner-German border", "pts": IGB},
    {"kind": "border", "name": "Elbe", "pts": ELBE},
    {"kind": "border", "name": "2 ATAF / 4 ATAF seam (Kassel - Göttingen)", "pts": [[51.15, 6.3], [51.25, 8.0], [51.32, 9.5], [51.53, 9.93], [51.55, 10.3]]},
    {"kind": "deconfliction", "name": "GDR flight-restriction line (Grenzsperrstreifen)", "label": "GDR FLIGHT-RESTRICTION LINE", "label_at": [50.62, 11.35], "pts": GSS},
]
LAND = [
    [[53.35, 6.2]] + COAST_N + [[54.9, 8.6], [54.9, 9.6]] + COAST_B + [[53.55, 15.2], [49.1, 15.2], [49.1, 6.2]],
    RUGEN, FEHMARN, LOLLAND,
]
ROADS = [
    {"name": "A2", "pts": [[51.45, 6.8], [51.55, 7.5], [51.9, 8.3], [52.25, 8.92], [52.4, 9.7], [52.3, 10.5], [52.23, 11.01], [52.15, 11.6], [52.4, 12.2], [52.5, 13.0]]},
    {"name": "A7", "pts": [[54.8, 9.4], [54.3, 9.9], [53.6, 9.95], [53.25, 10.2], [52.9, 10.2], [52.6, 9.8], [52.15, 9.95], [51.55, 9.95], [51.32, 9.5], [50.85, 9.7], [50.55, 9.68], [50.05, 10.0], [49.8, 9.95]]},
    {"name": "A4", "pts": [[50.75, 7.1], [50.6, 8.7], [50.85, 9.7], [51.0, 10.15], [50.98, 10.32], [50.98, 11.03], [50.93, 11.59], [50.88, 12.08], [50.83, 12.92], [51.05, 13.74]]},
    {"name": "A9", "pts": [[52.4, 13.2], [51.9, 12.7], [51.5, 12.3], [51.05, 12.1], [50.7, 11.95], [50.32, 11.92], [49.95, 11.58], [49.5, 11.2]]},
    {"name": "A24", "pts": [[53.55, 10.2], [53.42, 10.85], [53.3, 11.6], [53.15, 12.2], [52.9, 12.8], [52.6, 13.1]]},
]
PLACES = [
    {"name": "Berlin", "lat": 52.52, "lon": 13.40, "kind": "city"}, {"name": "Hamburg", "lat": 53.55, "lon": 10.0, "kind": "city"},
    {"name": "Hannover", "lat": 52.37, "lon": 9.74, "kind": "city"}, {"name": "Köln", "lat": 50.94, "lon": 6.96, "kind": "city"},
    {"name": "Frankfurt", "lat": 50.11, "lon": 8.68, "kind": "city"}, {"name": "Leipzig", "lat": 51.34, "lon": 12.37, "kind": "city"},
    {"name": "Dresden", "lat": 51.05, "lon": 13.74, "kind": "city"}, {"name": "Magdeburg", "lat": 52.13, "lon": 11.63, "kind": "city"},
    {"name": "Kassel", "lat": 51.32, "lon": 9.50, "kind": "city"}, {"name": "Nürnberg", "lat": 49.45, "lon": 11.08, "kind": "city"},
    {"name": "Bremen", "lat": 53.08, "lon": 8.80, "kind": "city"}, {"name": "Kiel", "lat": 54.32, "lon": 10.13, "kind": "city"},
    {"name": "Rostock", "lat": 54.09, "lon": 12.14, "kind": "city"}, {"name": "Schwerin", "lat": 53.63, "lon": 11.41, "kind": "town", "minor": True},
    {"name": "Erfurt", "lat": 50.98, "lon": 11.03, "kind": "town"}, {"name": "Chemnitz", "lat": 50.83, "lon": 12.92, "kind": "town"},
    {"name": "Cottbus", "lat": 51.76, "lon": 14.33, "kind": "town"}, {"name": "Lübeck", "lat": 53.87, "lon": 10.69, "kind": "town"},
    {"name": "Kaiserslautern", "lat": 49.44, "lon": 7.77, "kind": "town", "minor": True}, {"name": "Trier", "lat": 49.75, "lon": 6.64, "kind": "town"},
    {"name": "Koblenz", "lat": 50.36, "lon": 7.59, "kind": "town", "minor": True}, {"name": "Würzburg", "lat": 49.79, "lon": 9.93, "kind": "town", "minor": True},
    {"name": "Fulda", "lat": 50.55, "lon": 9.68, "kind": "town", "minor": True}, {"name": "Göttingen", "lat": 51.53, "lon": 9.93, "kind": "town", "minor": True},
    {"name": "Braunschweig", "lat": 52.27, "lon": 10.52, "kind": "town", "minor": True}, {"name": "Wolfsburg", "lat": 52.42, "lon": 10.79, "kind": "town", "minor": True},
    {"name": "Lüneburg", "lat": 53.25, "lon": 10.41, "kind": "town", "minor": True}, {"name": "Uelzen", "lat": 52.96, "lon": 10.56, "kind": "town", "minor": True},
    {"name": "Minden", "lat": 52.29, "lon": 8.92, "kind": "town", "minor": True}, {"name": "Paderborn", "lat": 51.72, "lon": 8.75, "kind": "town", "minor": True},
    {"name": "Halle", "lat": 51.48, "lon": 11.97, "kind": "town", "minor": True}, {"name": "Dessau", "lat": 51.83, "lon": 12.24, "kind": "town", "minor": True},
    {"name": "Stendal", "lat": 52.60, "lon": 11.85, "kind": "town", "minor": True}, {"name": "Neubrandenburg", "lat": 53.56, "lon": 13.26, "kind": "town", "minor": True},
    {"name": "Stralsund", "lat": 54.31, "lon": 13.09, "kind": "town", "minor": True}, {"name": "Frankfurt/O.", "lat": 52.35, "lon": 14.55, "kind": "town", "minor": True},
    {"name": "Szczecin", "lat": 53.43, "lon": 14.55, "kind": "town"}, {"name": "Hof", "lat": 50.32, "lon": 11.92, "kind": "town", "minor": True},
    {"name": "Plauen", "lat": 50.50, "lon": 12.14, "kind": "town", "minor": True}, {"name": "Gera", "lat": 50.88, "lon": 12.08, "kind": "town", "minor": True},
    {"name": "Bitburg", "lat": 49.945, "lon": 6.564, "kind": "airfield"}, {"name": "Spangdahlem", "lat": 49.977, "lon": 6.699, "kind": "airfield"},
    {"name": "Hahn", "lat": 49.948, "lon": 7.264, "kind": "airfield"}, {"name": "Ramstein", "lat": 49.437, "lon": 7.600, "kind": "airfield"},
    {"name": "Sembach", "lat": 49.506, "lon": 7.863, "kind": "airfield", "minor": True}, {"name": "Zweibrücken", "lat": 49.210, "lon": 7.401, "kind": "airfield", "minor": True},
    {"name": "Büchel", "lat": 50.174, "lon": 7.064, "kind": "airfield", "minor": True}, {"name": "Pferdsfeld", "lat": 49.855, "lon": 7.605, "kind": "airfield", "minor": True},
    {"name": "Wiesbaden", "lat": 50.050, "lon": 8.326, "kind": "airfield"}, {"name": "Gütersloh", "lat": 51.923, "lon": 8.304, "kind": "airfield"},
    {"name": "Nörvenich", "lat": 50.831, "lon": 6.659, "kind": "airfield"}, {"name": "Wunstorf", "lat": 52.457, "lon": 9.427, "kind": "airfield"},
    {"name": "Bückeburg", "lat": 52.279, "lon": 9.083, "kind": "airfield", "minor": True}, {"name": "Celle", "lat": 52.591, "lon": 10.024, "kind": "airfield", "minor": True},
    {"name": "Fassberg", "lat": 52.919, "lon": 10.185, "kind": "airfield"}, {"name": "Nordholz", "lat": 53.768, "lon": 8.659, "kind": "airfield", "minor": True},
    {"name": "Werneuchen", "lat": 52.632, "lon": 13.769, "kind": "airfield"}, {"name": "Finow", "lat": 52.827, "lon": 13.694, "kind": "airfield", "minor": True},
    {"name": "Templin", "lat": 53.032, "lon": 13.543, "kind": "airfield"}, {"name": "Sperenberg", "lat": 52.137, "lon": 13.306, "kind": "airfield"},
    {"name": "Altes Lager", "lat": 51.995, "lon": 12.984, "kind": "airfield", "minor": True}, {"name": "Neuruppin", "lat": 52.941, "lon": 12.787, "kind": "airfield", "minor": True},
    {"name": "Wittstock", "lat": 53.202, "lon": 12.523, "kind": "airfield"}, {"name": "Parchim", "lat": 53.428, "lon": 11.787, "kind": "airfield"},
    {"name": "Laage", "lat": 53.918, "lon": 12.279, "kind": "airfield"}, {"name": "Damgarten", "lat": 54.264, "lon": 12.444, "kind": "airfield", "minor": True},
    {"name": "Tutow", "lat": 53.922, "lon": 13.219, "kind": "airfield", "minor": True}, {"name": "Peenemünde", "lat": 54.159, "lon": 13.774, "kind": "airfield", "minor": True},
    {"name": "Merseburg", "lat": 51.364, "lon": 11.950, "kind": "airfield"}, {"name": "Falkenberg", "lat": 51.546, "lon": 13.216, "kind": "airfield", "minor": True},
    {"name": "Holzdorf", "lat": 51.768, "lon": 13.170, "kind": "airfield", "minor": True}, {"name": "Zerbst", "lat": 52.000, "lon": 12.144, "kind": "airfield", "minor": True},
    {"name": "Brand", "lat": 52.037, "lon": 13.746, "kind": "airfield", "minor": True}, {"name": "Marxwalde", "lat": 52.613, "lon": 14.243, "kind": "airfield", "minor": True},
    {"name": "Stendal", "lat": 52.629, "lon": 11.820, "kind": "airfield", "minor": True}, {"name": "Cochstedt", "lat": 51.856, "lon": 11.418, "kind": "airfield", "minor": True},
    {"name": "Gatow", "lat": 52.475, "lon": 13.138, "kind": "airfield", "minor": True}, {"name": "Tegel", "lat": 52.558, "lon": 13.293, "kind": "airfield", "minor": True},
]

PANELS = [
    {"id": "rheinmain", "clusters": ["rheinmain"], "cluster": "rheinmain", "title": "RHEIN-MAIN - THE TAUNUS TO THE GAP", "tag": "RHEIN-MAIN - see panel",
     "bounds": {"lat": [49.9, 51.2], "lon": [7.6, 10.4]}, "grid": 0.5, "declutter": True,
     "lanes": ["rm_out", "rm_home", "fulda", "werra"],
     "labels": {"rm_out": {"seg": 0, "off": [0, 1]}, "rm_home": {"seg": 1, "off": [0, -1], "nudge": [0, -10]}, "fulda": {"seg": 1, "off": [0, 1]}, "werra": {"seg": 1, "off": [0, -1]}}},
    {"id": "eifel", "clusters": ["eifel", "hunsruck", "pfalz"], "cluster": "eifel", "title": "4 ATAF - EIFEL, HUNSRÜCK, PFALZ", "tag": "4 ATAF - see panel",
     "bounds": {"lat": [49.2, 50.5], "lon": [6.3, 8.4]}, "grid": 0.5, "declutter": True,
     "lanes": ["ef_out", "ef_home", "hu_out", "hu_home", "pf_out", "pf_home"],
     "labels": {"ef_out": {"seg": 1, "off": [0, -1]}, "ef_home": {"seg": 1, "off": [0, 1]}, "hu_out": {"seg": 0, "off": [0, 1]}, "hu_home": {"seg": 1, "off": [0, -1], "nudge": [30, -4]},
                "pf_out": {"seg": 0, "off": [1, 0]}, "pf_home": {"seg": 1, "off": [-1, 0]}}},
    {"id": "rhineruhr", "clusters": ["rhineruhr"], "cluster": "rhineruhr", "title": "2 ATAF - THE RHINELAND TO THE PORTA", "tag": "RHINELAND - see panel",
     "bounds": {"lat": [50.6, 52.4], "lon": [6.4, 9.3]}, "grid": 0.5, "declutter": True,
     "lanes": ["rr_out", "rr_home"],
     "labels": {"rr_out": {"seg": 1, "off": [0, -1]}, "rr_home": {"seg": 2, "off": [0, 1]}}},
    {"id": "hannover", "clusters": ["hannover"], "cluster": "hannover", "title": "2 ATAF - THE WESER AND THE HEATH", "tag": "WESER - see panel",
     "bounds": {"lat": [51.9, 53.3], "lon": [8.8, 11.7]}, "grid": 0.5, "declutter": True,
     "lanes": ["ha_out", "ha_home", "ha_north", "ha_north_home", "hlz_gate", "uelzen_gate"],
     "labels": {"ha_out": {"seg": 1, "off": [0, 1]}, "ha_home": {"seg": 0, "off": [0, -1]}, "ha_north": {"seg": 1, "off": [-1, 0]},
                "ha_north_home": {"seg": 0, "off": [1, 0]}, "hlz_gate": {"seg": 0, "off": [0, 1]}, "uelzen_gate": {"seg": 0, "off": [0, -1]}}},
    {"id": "elbe", "clusters": ["elbe"], "cluster": "elbe", "title": "2 ATAF - THE ELBE, HAMBURG TO LAUENBURG", "tag": "ELBE - see panel",
     "bounds": {"lat": [53.2, 54.5], "lon": [9.4, 11.9]}, "grid": 0.5, "declutter": True,
     "lanes": ["el_out", "el_home", "el_lub", "elbe_gate"],
     "labels": {"el_out": {"seg": 0, "off": [0, -1]}, "el_home": {"seg": 0, "off": [0, 1], "nudge": [-30, 6]}, "el_lub": {"seg": 0, "off": [1, 0]}, "elbe_gate": {"seg": 0, "off": [0, 1]}}},
    {"id": "berlin", "clusters": ["berlin"], "cluster": "berlin", "title": "BERLIN - THE CORRIDORS AND THE RING", "tag": "BERLIN - see panel",
     "bounds": {"lat": [51.9, 53.4], "lon": [12.0, 14.2]}, "grid": 0.5, "declutter": True,
     "lanes": ["be_out_w", "be_home_w", "be_out_nw", "be_home_nw", "be_out_sw", "be_home_sw"],
     "labels": {"be_out_w": {"seg": 0, "off": [0, -1]}, "be_home_w": {"seg": 0, "off": [0, 1]}, "be_out_nw": {"seg": 0, "off": [-1, 0]},
                "be_home_nw": {"seg": 0, "off": [1, 0], "nudge": [0, 14]}, "be_out_sw": {"seg": 0, "off": [1, 0]}, "be_home_sw": {"seg": 0, "off": [-1, 0]}}},
    {"id": "gdr_south", "clusters": ["gdr_south"], "cluster": "gdr_south", "title": "THE SOUTHERN FIELDS - TO THE WERRA", "tag": "MERSEBURG - see panel",
     "bounds": {"lat": [50.5, 52.2], "lon": [9.7, 13.3]}, "grid": 0.5, "declutter": True,
     "lanes": ["gs_out", "gs_home", "gs_out_n", "gs_home_n", "r_werra", "r_fulda", "r_groningen"],
     "labels": {"gs_out": {"seg": 0, "off": [0, -1]}, "gs_home": {"seg": 0, "off": [0, 1]}, "gs_out_n": {"seg": 0, "off": [0, 1]},
                "gs_home_n": {"seg": 0, "off": [1, 0]}, "r_werra": {"seg": 1, "off": [0, 1]}, "r_fulda": {"seg": 1, "off": [0, 1]}, "r_groningen": {"seg": 0, "off": [1, 0]}}},
    {"id": "gdr_north", "clusters": ["gdr_north"], "cluster": "gdr_north", "title": "MECKLENBURG - PARCHIM TO THE ELBE", "tag": "MECKLENBURG - see panel",
     "bounds": {"lat": [52.9, 54.4], "lon": [10.3, 13.6]}, "grid": 0.5, "declutter": True,
     "lanes": ["gn_out", "gn_home", "gn_out_s", "gn_home_s", "r_hagenow", "r_domitz"],
     "labels": {"gn_out": {"seg": 0, "off": [0, -1]}, "gn_home": {"seg": 1, "off": [0, 1]}, "gn_out_s": {"seg": 1, "off": [1, 0]},
                "gn_home_s": {"seg": 0, "off": [-1, 0]}, "r_hagenow": {"seg": 1, "off": [0, -1]}, "r_domitz": {"seg": 0, "off": [1, 0]}}},
]

TEXT = {
    "chart_title": "CENTRAL REGION CORRIDORS",
    "md_title": "Central Region corridors",
    "md_line": "**{summary}** — {sector}, {mode} road. Gate **{gate_in}** (WP1), exit at **{gate_out}**. The flight plan is threaded through the structure of 1985 - the ADIZ, the HAWK and Nike belts, the Berlin corridors, the GDR's own flight lines; nobody goes direct across the border.",
    "chart_subtitle": "The Cold War Germany map - how a flight gets from the Eifel, the Weser or the Berlin ring to the other side and back. The ADIZ, the belts and the ranges from the printed sources; the crossing gates are ours. Not for real-world navigation.",
    "kneeboard_subtitle": "The Central Region - your road in red",
    "brief_page_subtitle": "The Cold War Germany map — this mission's road in red",
    "brief_title": "CENTRAL REGION CORRIDORS - HOW YOU GET TO THE FIGHT",
    "brief_intro": ["The flight plan is threaded through the Central Region of 1985: the ADIZ 40 km",
                    "west of the border (flight plan and ATC mandatory, USAFE clearance), the HAWK belt",
                    "in front of the Nike Hercules belt 150 km back, the three 20-mile Berlin corridors,",
                    "the GDR's flight-restriction line and its 'örtliche Fluglinien'. The Low Level",
                    "Transit Routes through the belt were never published - 'activated for specified",
                    "times only and changed frequently' - so the crossing gates are ours, on the",
                    "checkpoints and river crossings the corps sectors used. SOC 1 Brockzetel FLYFISH,",
                    "SOC 2 Uedem MANDRIL, SOC 3 Kindsbach; CRC Erndtebrück LONESHIP, Börfink SCANDALISE.",
                    "East of the line: Bunker Fuchsbau (Fürstenwalde) and the 41. FRBr ring round Berlin."],
    "brief_sources": ["Sources: FM 100-103 (1987) Ch. 2; dewiki ADIZ / DHV-Info 49 (1989); relikte.com",
                      "(Nike, HAWK, SOC/CRC); nl.wikipedia Groepen Geleide Wapens; A&SF Jul 1983; FRUS 1945",
                      "III/1206 (Berlin corridors); nva-flieger.de Luftraum der DDR; de.wikipedia FlaRak-",
                      "truppen (NVA), TrÜbPl Wittstock/Altmark/Lieberose; AIP Germany ENR 5.1 (03/24);",
                      "NfL 2025-1-3686 (LFAs); OurAirports navaids; GlobalSecurity (corps sectors)."],
    "known_issues": ["DCS draws no ADIZ, no belts and no Berlin corridors; the bands, the corridors and the gates on the F10 map are ours, from the published structure. The AI controllers know nothing of FLYFISH, MANDRIL or the BASC; the Nike and HAWK belts are not in the mission unless you place them."],
    "sources_line": "FM 100-103 · dewiki ADIZ · relikte.com · nl.wikipedia GGW · FRUS 1945 III/1206 · nva-flieger.de · de.wikipedia FlaRak (NVA) / TrÜbPl · AIP Germany ENR 5.1 · NfL 2025-1-3686 · OurAirports · GlobalSecurity",
    "gate_in_label": "GATE IN",
    "gate_out_label": "GATE OUT",
    "legend": ["Bands: amber = the ADIZ (40 km); magenta fill = the HAWK belt (LOMEZ); thin magenta = the Nike Hercules belt and the 41. FRBr ring. Thin dashed blue = a 250-ft Low Flying Area, the Berlin Control Zone. Navy hatched = a range (ED-R, or a Soviet Truppenübungsplatz, ~). Dashed amber line = the GDR flight-restriction line.",
               "Gate diamond = a crossing point on the inner-German border (all curated, ~). Fix triangle = a navaid or a GDR reference town (~ = placed on the town). The three wide blue lanes are the Berlin air corridors, 20 statute miles wide; 10,000 ft is an exercise ceiling, not a universal historical limit. The border, the Elbe and the autobahns are schematic."],
}

DATA = {
    "map": "germany", "label": "Cold War Germany", "eras": ["coldwar"],
    "fixes": F, "corridors": C, "gates": GATES, "clusters": CLUSTERS, "sectors": SECTORS, "plans": PLANS,
    "text": TEXT,
    "chart": {
        "bounds": {"lat": [49.3, 54.75], "lon": [6.3, 14.9]},
        "sea": True, "land": LAND,
        "page": [2400, 1250], "panel_cols": 4, "panel_col_frac": 0.55, "panel_frac": 0.8,
        "overview_title": "CENTRAL REGION OVERVIEW",
        "hide_fixes": ["BITBURG", "SPANGDAHLEM", "HAHN", "RAMSTEIN", "WIESBADEN", "FRANKFURT", "NORVENICH", "COLOGNE", "GUTERSLOH", "HANNOVER", "WUNSTORF", "FASSBERG", "HAMBURG",
                       "WERNEUCHEN", "FINOW", "TEMPLIN", "SPERENBERG", "ALTES LAGER", "NEURUPPIN", "WITTSTOCK", "ORANIENBURG", "PARCHIM", "LAAGE", "DAMGARTEN", "NEUBRANDENBURG",
                       "MERSEBURG", "FALKENBERG", "HOLZDORF", "STENDAL", "COCHSTEDT", "DESSAU", "ZERBST", "BRAUNSCHWEIG", "GELNHAUSEN", "FULDA"],
        "overview_landmarks": ["KASSEL", "GOTTINGEN", "BERLIN"],
        "labels": {"porta_a2": {"seg": 1, "off": [0, 1]}, "harz": {"seg": 2, "off": [0, -1]}, "centre_corr": {"seg": 2, "off": [0, 1]},
                   "werra": {"seg": 1, "off": [0, -1]}, "fulda": {"seg": 3, "off": [0, 1]}, "south_corr": {"seg": 3, "off": [0, 1]}, "north_corr": {"seg": 1, "off": [0, -1]},
                   "hlz_gate": {"hide": True}, "elbe_gate": {"hide": True}, "uelzen_gate": {"hide": True}, "r_groningen": {"hide": True},
                   "r_domitz": {"hide": True}, "r_hagenow": {"hide": True}, "r_altmark": {"hide": True}, "r_dessau": {"hide": True},
                   "r_pritzwalk": {"hide": True}, "r_rathenow": {"hide": True}, "r_werra": {"hide": True}, "r_fulda": {"hide": True}},
        "areas": AREAS, "lines": LINES, "roads": ROADS, "places": PLACES, "panels": PANELS,
    },
}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(DATA, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(F)} fixes, {len(C)} corridors, {len(AREAS)} areas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
