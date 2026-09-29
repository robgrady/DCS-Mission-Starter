#!/usr/bin/env python3
"""Write missiongen/data/corridors/syria.json — the Levant's corridors.

WHY A SCRIPT WRITES THE JSON
----------------------------
The arcs (the LLR01 47-NM offshore arc, the Akrotiri ARFA, the Latakia and
Beirut CTR circles, the Al-Tanf 55-km zone) are sampled from published
center + radius here, so the file carries computed points but the SOURCE of
every one is a printed figure. Edit here, rerun; do not hand-edit the JSON.

WHAT IS DOCUMENTED (the sources are on every fix and corridor)
-----------------------------------------------------------
- Israel: AIP Israel ENR 2.1 (Tel Aviv FIR, sectors), ENR 3.1 (J14 / J15 /
  P42 / L609 / N134 fixes: ROP, BARZI, FOLKU, GAFAZ, MOCEV, NAT, ATLIT,
  RAPIV, MERVA, TAPUZ, KEREN, DAFNA, KONFO, MUVIN, RALNA), ENR 5.1 (LLR01 /
  LLR02 offshore training, LLR83, LLR36, LLR801-805, LLP15, LLP19).
- The four IAF roads into Syria as reported 2013-2024 (Al Jazeera, Times
  of Israel, TASS, The War Zone, Anadolu, Reuters via JPost): over
  Lebanon's Bekaa / Ras Baalbek / north of Tripoli; from the Mediterranean
  west of Tripoli and off Latakia; from the Golan / Mount Hermon / the
  north-east of Lake Tiberias; from Al-Tanf / Jordanian-Iraqi airspace.
- Cold War: 1973 (low over Jordan, pop up over the Golan; the sea-then-
  Lebanon GHQ raid) and 1982 Mole Cricket 19 (the Bekaa, the coast Sidon-
  Beirut) — GlobalSecurity MML, Wikipedia.
- Cyprus: UK Military AIP LCRA (ARP, TACAN AKR, ARFA, SIDs to ANANE / IREFA
  / MEZUS, the AKR 189R/11.7 hold), Israel ENR 3.1 for the Nicosia FIR fixes,
  Syria ENR 3 for NIKAS, the LCD47 SOTIA NOTAM Q-line, the Aviationist on the
  Akrotiri-to-Iraq run "via downtown Amman".
- Turkey: AIP Türkiye ENR 2.1 (Ankara FIR, Adana / Diyarbakır MTMAs,
  Gaziantep TMA, İncirlik CTR), ENR 3 / 4.4 (W74 ADA-MILBA-BABLI-KOZAN-GAZ-
  NIZIP-SURUC-ARTAR-OZBEY-ATLOM-DYB; border fixes TUNLA, NISAP, TUSYR,
  LESRI, KABAN), ENR 5.1 (LTD13, LTD19, LTR23), LTAG AD 2 (TACAN DAN).
  Northern Watch: A&SF Feb 2000, Ricks/WaPo 2000, GAO OSI-98-4 (the ROZ
  over eastern Turkey; AWACS orbit north of the border at 32,000).
- Jordan: CARC ENR 2.1 (Amman TMA), AMDT 19/2022 and ENR 3.1 2007 (OSAMA,
  AMN01, LOXER, MESLO, LUDAN, KUPRI, ASLON, NADEK, DAXEN, ORNAL, KAREM,
  KUMLO, DAPUK, PASIP, ZELAF, BUSRA, LOSAR, QAA, TAN VOR), Wikipedia for
  Muwaffaq Salti / H-5 / Mafraq / H-4.
- Syria: GACA eAIP 2026 ENR 3 / 4 (DAM, ALE, LTK, KTN, TAN, DEZ, KML, NIKAS,
  SALIM, LUBAM, TUDMU, ABBAS, BASSEM, LATEB, LOTAX, RDIMA, MURAK, LEBOR),
  Latakia CTR 15 NM; Al-Tanf garrison and the 55-km deconfliction zone
  (Wikipedia, GlobalSecurity, VOA, Military Times, Brookings, Stimson,
  TASS); the Euphrates line (Globe Post, Atlantic Council).
- Lebanon: IVAO-mirrored DGCA AD 2 OLBA (KAD VOR, Beirut CTR 20 NM).

WHAT IS CURATED (approx: true, ~ on the chart)
----------------------------------------------
The reported roads name places, not fixes: OFF SIDON, OFF BEIRUT, OFF
TRIPOLI, RAS BAALBEK, MOUNT HERMON, the Golan launch point, OFF LATAKIA,
DEIR EZ-ZOR approach points. They are placed on the named town or summit.
The coast and the borders are schematic polylines. Jordan's OJP/OJR/OJD
polygons and the Russian sea-closure polygons could not be read and are
not drawn.
"""
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "missiongen" / "data" / "corridors" / "syria.json"


def arc(lat, lon, r_nm, a0, a1, n=12):
    """Points on a circle of r_nm around (lat,lon) from bearing a0 to a1."""
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


F = {}


def fx(name, lat, lon, short, kind, src, approx=False, **kw):
    d = {"lat": round(lat, 5), "lon": round(lon, 5), "short": short, "kind": kind, "src": src}
    if approx:
        d["approx"] = True
    d.update(kw)
    F[name] = d


# ---- Israel ---------------------------------------------------------------
fx("RAMAT DAVID", 32.665, 35.179, "RAMATD", "airport", "DCS Syria map")
fx("ROP", dms(32, 58, 57), dms(35, 34, 22), "ROP", "navaid", "AIP Israel ENR 3.1: ROSH-PINA VOR/DME 325857N 0353422E")
fx("BARZI", dms(32, 50, 10.9), dms(35, 32, 36.2), "BARZI", "fix", "AIP Israel ENR 3.1 (J14)", minor=True)
fx("GAFAZ", dms(32, 33, 44), dms(35, 17, 32), "GAFAZ", "fix", "AIP Israel ENR 3.1 (J14)")
fx("MOCEV", dms(32, 24, 0), dms(35, 3, 44), "MOCEV", "fix", "AIP Israel ENR 3.1 (J14)", minor=True)
fx("NAT", dms(32, 20, 2), dms(34, 58, 8), "NAT", "navaid", "AIP Israel ENR 3.1: NATANIA VOR/DME 322002N 0345808E")
fx("ATLIT", dms(32, 41, 52), dms(34, 54, 55), "ATLIT", "fix", "AIP Israel ENR 3.1 (J15)")
fx("MERVA", dms(32, 46, 54), dms(34, 32, 38), "MERVA", "fix", "AIP Israel ENR 3.1 (P42): Nicosia arrival/departure fix")
fx("KEREN", dms(32, 22, 32), dms(34, 4, 45), "KEREN", "fix", "AIP Israel ENR 3.1 (N134): sea entry")
fx("MUVIN", dms(31, 49, 36), dms(35, 30, 14), "MUVIN", "fix", "AIP Israel ENR 3.1 (L53): Jordan border; CARC AMDT 19/2022 314858N 0353242E")
fx("HAIFA BLOCK", 32.95, 34.72, "HAIFABLK", "gate", "LLR01 offshore MIL training area (AIP Israel ENR 5.1: 7,000-40,000 ft) - the sea block off Haifa", approx=True)
fx("ROSH HANIKRA", 33.09, 35.10, "R HANIKR", "landmark", "The coast at the Lebanon border (Blue Line western end); AIP Israel ENR 2.1 FIR corner 3306N 03506E", approx=True)
fx("OFF SIDON", 33.55, 35.15, "OFFSIDON", "fix", "1982 Mole Cricket 19: 'Kfirs and Skyhawks were along the coastline from Sidon to the outskirts of Beirut' (Wikipedia); the coast off Sidon", approx=True, minor=True)
fx("OFF BEIRUT", 33.92, 35.30, "OFFBEIRU", "fix", "1973 GHQ raid 'headed out over the Mediterranean, before turning north toward Lebanon and then east toward Damascus'; the coast off Beirut", approx=True, minor=True)
fx("OFF TRIPOLI", 34.48, 35.55, "OFFTRIPO", "fix", "Al Jazeera 2 Jul 2022: strike 'from across the Mediterranean, west of Lebanon's northern city of Tripoli'; Yahoo: missiles 'from the north of the Lebanese city of Tripoli'", approx=True, minor=True)
fx("W TRIPOLI", 34.75, 35.35, "WTRIPOLI", "gate", "The sea gate west of Tripoli for the Latakia/Tartus coast (Al Jazeera 2022; TASS/TWZ 2018 'approached Latakia at low altitude from the Mediterranean')", approx=True)
fx("BEKAA", dms(33, 50), dms(35, 55), "BEKAA", "landmark", "Zahle 33°50'N 35°55'E (Wikipedia) - the Bekaa Valley, the 1982 SAM belt", approx=True)
fx("BAALBEK", 34.00634, 36.20732, "BAALBEK", "landmark", "Baalbek 34°0'22.81\"N 36°12'26.36\"E (Wikipedia)")
fx("RAS BAALBEK", 34.26, 36.42, "RASBAALB", "gate", "Anadolu 2 Nov 2017: jets 'flew at low altitude over the Lebanese border towns of Ras Baalbek and Al-Fakhah' then struck rural Homs; the town", approx=True)
fx("CHTAURA", 33.81472, 35.85472, "CHTAURA", "landmark", "Chtaura 33°48'53\"N 35°51'17\"E (Wikipedia) - Syrian Bekaa HQ 1982; halfway on the Beirut-Damascus highway")
fx("RAYAK", 33.85222, 35.99028, "RAYAK", "landmark", "Rayak Air Base 33°51'08\"N 35°59'25\"E (Wikipedia)")
fx("HERMON", 33.416, 35.857, "HERMON", "gate", "Al Jazeera 31 Jan 2013: 'The jets entered the Syrian airspace via Mount Hermon'; 1973: 'curve away west of Mount Hermon' (GlobalSecurity MML); the summit", approx=True)
fx("TIBERIAS NE", 32.90, 35.70, "TIBERNE", "fix", "Al Jazeera 17 Sep 2022: 'a missile fired from the air from the northeastern direction of Lake Tiberias'; the launch area", approx=True)
fx("KIRYAT SHMONA", 33.22, 35.60, "K SHMONA", "landmark", "DCS Syria map airfield; the Hula valley")
fx("GOLAN", 33.05, 35.85, "GOLAN", "landmark", "Al Jazeera 24 Nov 2020: raid 'from the direction of the occupied Golan Heights'; 1973 'quick pop up over the Golan plateau' (MML)", approx=True)
fx("BEN GURION", 32.01, 34.88, "BEN GUR", "airport", "DCS Syria map")
fx("BGN", dms(32, 0, 47), dms(34, 52, 31), "BGN", "navaid", "AIP Israel ENR 3.1: BEN-GURION VOR/DME 320047N 0345231E", minor=True)
fx("NEVATIM", 31.21, 35.01, "NEVATIM", "airport", "DCS Syria map")
fx("MZD", dms(31, 19, 54), dms(35, 23, 30), "MZD", "navaid", "AIP Israel ENR 3.1: METZADA VOR/DME 311954N 0352330E", minor=True)
# ---- Jordan ---------------------------------------------------------------
fx("OSAMA", dms(31, 55, 50), dms(35, 37, 6), "OSAMA", "fix", "CARC AMDT 19/2022 (A412/L200) 315550N 0353706E")
fx("AMN01", dms(32, 0, 14.65), dms(36, 3, 57.55), "AMN01", "fix", "CARC AMDT 19/2022 (L200)", minor=True)
fx("LOXER", dms(32, 1, 47.76), dms(36, 22, 51.46), "LOXER", "fix", "CARC AMDT 19/2022 (L200/L513)")
fx("LUDAN", dms(32, 2, 56.6), dms(36, 37, 13.29), "LUDAN", "fix", "CARC AMDT 19/2022 (A412/L200)", minor=True)
fx("ASLON", dms(32, 12, 11.02), dms(36, 51, 11.25), "ASLON", "fix", "CARC AMDT 19/2022 (A412/L200); 'Portion ASLON-NADEK is excluded from Prohibited area OJP9' - the Azraq corridor")
fx("NADEK", dms(32, 27, 28), dms(37, 14, 29), "NADEK", "fix", "CARC AMDT 19/2022 (A412/L200)")
fx("DAXEN", dms(32, 44, 44.79), dms(37, 41, 5.26), "DAXEN", "fix", "CARC AMDT 19/2022 (A412/L200)")
fx("KUMLO", dms(32, 58, 11.82), dms(38, 28, 7.67), "KUMLO", "fix", "CARC AMDT 19/2022 (L200)", minor=True)
fx("DAPUK", dms(33, 1, 39.44), dms(38, 40, 26.29), "DAPUK", "fix", "CARC AMDT 19/2022 (L200), last fix before the Baghdad FIR")
fx("ZELAF", dms(32, 56, 56.2), dms(37, 59, 59.26), "ZELAF", "fix", "CARC AMDT 19/2022: Amman/Damascus FIR boundary (A412); Syria ENR 3: ZELAF N32.95 E38.00")
fx("BUSRA", dms(32, 20), dms(36, 37), "BUSRA", "fix", "CARC AMDT 19/2022: Amman/Damascus FIR boundary (L513) 322000N 0363700E; Syria ENR 4.4 BUSRA N32°20'00\" E36°37'00\"")
fx("LOSAR", dms(32, 9, 30.06), dms(36, 28, 49.77), "LOSAR", "fix", "CARC AMDT 19/2022 (L513)", minor=True)
fx("QAA", dms(31, 44, 22.09), dms(36, 9, 25.12), "QAA", "navaid", "CARC ENR 3.1 (2007): QUEEN ALIA VOR/DME 314422.09N 0360925.12E")
fx("MUWAFFAQ SALTI", 31.83417, 36.78722, "AZRAQ", "airport", "Muwaffaq Salti Air Base 31°50'03\"N 036°47'14\"E (Wikipedia) - Azraq; OIR fighter base")
fx("TAN", dms(33, 28, 56.2), dms(38, 39, 11.3), "TAN", "navaid", "CARC ENR 3.1 (2007): TANF VOR/DME 332856.19786N 383911.31296E; Syria ENR 4.1 TAN N33°29' E38°39'")
fx("AT TANF", 33.50583, 38.61778, "AT TANF", "gate", "Al-Tanf garrison 33°30'21\"N 38°37'04\"E (Wikipedia); center of the 55-km deconfliction zone; Times of Israel 2019 / Al Jazeera 2024: strikes 'from the direction of al-Tanf'")
fx("RUKBAN", 33.314194, 38.702806, "RUKBAN", "landmark", "Rukban camp 33°18'51.1\"N 38°42'10.1\"E (Wikipedia), inside the DCZ")
# ---- Syria ------------------------------------------------------------------
fx("DAM", dms(33, 24, 41), dms(36, 30, 56), "DAM", "navaid", "Syria eAIP ENR 4.1: DAM DVOR/DME N33°24'41\" E36°30'56\"")
fx("RDIMA", dms(33, 2), dms(36, 32), "RDIMA", "fix", "Syria eAIP ENR 4.4 (L513) N33°02'00\" E36°32'00\"", minor=True)
fx("LOTAX", 33.9833, 36.54, "LOTAX", "fix", "Syria eAIP ENR 3 (L513/N310) N33.9833 E36.5400", minor=True)
fx("LATEB", 34.0317, 36.4010, "LATEB", "fix", "Syria eAIP ENR 3 (N310): the Beirut FIR entry toward Damascus N34.0317 E36.4010", minor=True)
fx("KTN", dms(34, 13), dms(37, 16), "KTN", "navaid", "Syria eAIP ENR 4.1: KTN VOR/DME Kariatain N34°13'00\" E37°16'00\"")
fx("SALIM", 35.4958, 36.3111, "SALIM", "fix", "Syria eAIP ENR 3 (L601/W6) N35.4958 E36.3111", minor=True)
fx("LUBAM", 35.6667, 36.5333, "LUBAM", "fix", "Syria eAIP ENR 3 (W6) N35.6667 E36.5333", minor=True)
fx("NIKAS", 35.1933, 35.7167, "NIKAS", "gate", "Syria eAIP ENR 3 (R785): the Nicosia FIR entry N35.1933 E35.7167; OSLK SID NIKAS 1-J")
fx("OFF LATAKIA", 35.45, 35.45, "OFFLATAK", "fix", "TASS 2018: F-16s 'approached the target from the Mediterranean at a low altitude'; Il-20 lost '35 km from the Syrian coast'", approx=True)
fx("TUDMU", 34.5168, 38.1261, "TUDMU", "fix", "Syria eAIP ENR 3 (B544) N34.5168 E38.1261 - Palmyra")
fx("DEZ", 35.2853, 40.1756, "DEZ", "navaid", "Syria eAIP ENR 3 (L572/L602) DEZ N35.2853 E40.1756")
fx("ABBAS", 33.4333, 37.7250, "ABBAS", "fix", "Syria eAIP ENR 3 (G202/R785) N33.4333 E37.7250", minor=True)
fx("BASSEM", 33.56, 37.6517, "BASSEM", "fix", "Syria eAIP ENR 3 (N310/R785) N33.5600 E37.6517", minor=True)
fx("TABQA", 35.7823, 38.5664, "TABQA", "fix", "Syria eAIP ENR 3 (M861/W5) N35.7823 E38.5664")
fx("DEIR EZ-ZOR W", 35.10, 39.60, "DEZ WEST", "gate", "The approach to Deir ez-Zor from the Al-Tanf axis (Times of Israel 2019: strikes on Al-Bukamal 'used Jordanian airspace ... aided by ... the Tanf garrison'); the desert west of the city", approx=True)
# ---- Cyprus -----------------------------------------------------------------
fx("AKROTIRI", dms(34, 35, 25.34), dms(32, 59, 16.01), "AKROTIRI", "airport", "UK Mil AIP LCRA: ARP N34 35 25.34 E032 59 16.01")
fx("AKR", dms(34, 35, 2.25), dms(33, 0, 45.13), "AKR", "navaid", "UK Mil AIP LCRA: TACAN AKR Ch 107X N34 35 02.25 E033 00 45.13", minor=True)
fx("IREFA", dms(34, 25, 3), dms(33, 25, 8), "IREFA", "fix", "UK Mil AIP LCRA: 'Aircraft departing Akrotiri going Eastbound are to be flight planned by IREFA (N34 25 03 E033 25 08)'")
fx("ANANE", dms(34, 17, 55), dms(32, 43, 41), "ANANE", "fix", "UK Mil AIP LCRA: westbound departures 'by ANANE (N34 17 55 E032 43 41)'")
fx("MEZUS", 34.4175, 32.0588, "MEZUS", "fix", "UK Mil AIP LCRA SID WEST 2: MEZUS N34 25.05 E032 03.53", minor=True)
fx("AKR HOLD", 34.3948, 32.9548, "AKR HOLD", "fix", "UK Mil AIP LCRA TAC Rwy 28: IAF/hold 'AKR 189R/11.7d (N34 23.69 E032 57.29)', FL100-FL140")
fx("LARNACA", 34.87, 33.62, "LARNACA", "airport", "DCS Syria map")
fx("PAPHOS", 34.72, 32.48, "PAPHOS", "airport", "DCS Syria map")
# ---- Turkey -----------------------------------------------------------------
fx("INCIRLIK", dms(37, 0, 12), dms(35, 25, 56), "INCIRLIK", "airport", "AIP Türkiye LTAG AD 2: ARP 370012N-0352556E")
fx("DAN", dms(37, 0, 56.2), dms(35, 26, 53.5), "DAN", "navaid", "AIP Türkiye LTAG: TACAN DAN CH21X 370056.2N 0352653.5E", minor=True)
fx("ADA", dms(36, 56, 26), dms(35, 12, 37), "ADA", "navaid", "AIP Türkiye ENR 4.4: ADANA VOR ADA 365626N-0351237E")
fx("MILBA", dms(36, 57, 5), dms(36, 28, 46), "MILBA", "fix", "AIP Türkiye ENR 4.4 (W74) 365705N-0362846E")
fx("BABLI", dms(36, 57, 12), dms(36, 51, 47), "BABLI", "fix", "AIP Türkiye ENR 4.4 (W74)", minor=True)
fx("GAZ", dms(36, 57, 5.8), dms(37, 28, 22.7), "GAZ", "navaid", "AIP Türkiye ENR 4.4: GAZİANTEP VOR/DME GAZ 365705.8N 0372822.7E")
fx("NIZIP", dms(36, 59, 5), dms(37, 46), "NIZIP", "fix", "AIP Türkiye ENR 4.4 (W74)", minor=True)
fx("SURUC", dms(37, 3, 48), dms(38, 32, 24), "SURUC", "fix", "AIP Türkiye ENR 4.4 (W74) 370348N-0383224E")
fx("OZBEY", dms(37, 14, 31), dms(39, 6), "OZBEY", "fix", "AIP Türkiye ENR 4.4 (W74)", minor=True)
fx("ATLOM", dms(37, 23, 8), dms(39, 20, 55), "ATLOM", "fix", "AIP Türkiye ENR 4.4 (W74)", minor=True)
fx("DYB", dms(37, 52, 25), dms(40, 12, 30), "DYB", "navaid", "AIP Türkiye ENR 4.4: DİYARBAKIR VOR DYB 375225N-0401230E; the Northern Watch 'ROZ over eastern Turkey' where the package refuelled (A&SF Feb 2000; Ricks/WaPo 2000)")
fx("HTY", dms(36, 21, 46), dms(36, 17, 24), "HTY", "navaid", "AIP Türkiye ENR 4.4: HATAY VOR HTY 362146N-0361724E")
fx("TUNLA", dms(35, 53), dms(36, 2), "TUNLA", "gate", "AIP Türkiye ENR 4.4: TUNLA 355300N-0360200E, Ankara/Damascus FIR boundary (UL601) south of Hatay; Syria ENR 3 L601 TUNLA-SALIM-KTN")
fx("NISAP", dms(36, 47, 4), dms(36, 38, 29), "NISAP", "gate", "AIP Türkiye ENR 4.4: NISAP 364704N-0363829E, FIR boundary (UM861) near Kilis; Syria M861 NISAP-ALE")
fx("TUSYR", dms(36, 38, 56), dms(37, 22, 59), "TUSYR", "gate", "AIP Türkiye ENR 4.4: TUSYR 363856N-0372259E, FIR boundary (UB36) south of Gaziantep; Syria B544 ALE-TUSYR")
fx("LESRI", dms(37, 4, 20), dms(41, 13, 49), "LESRI", "gate", "AIP Türkiye ENR 4.4: LESRI 370420N-0411349E, FIR boundary (UP975/UT333) near Nusaybin; Syria L573 KML-LESRI")
fx("ALE", dms(36, 10, 37), dms(37, 13, 29), "ALE", "navaid", "Syria eAIP ENR 4.1: ALE DVOR/DME Aleppo N36°10'37\" E37°13'29\"")
fx("KML", 37.0167, 41.20, "KML", "navaid", "Syria eAIP ENR 4.1: KML DVOR/DME Kamishly N37°01' E41°12'")
fx("GAZIANTEP", 36.95, 37.48, "GAZIANTP", "airport", "DCS Syria map")
fx("HATAY", 36.36, 36.28, "HATAY", "airport", "DCS Syria map")

# ---- corridors ----------------------------------------------------------------
C = []


def cor(id_, name, role, points, block, width, notes, src, seg=0, off=(1, 0)):
    C.append({"id": id_, "name": name, "role": role, "points": points, "block_ft": list(block),
              "width_nm": width, "notes": [notes], "src": src, "label_seg": seg, "label_off": list(off)})


# Israel
cor("il_j14", "J14 north - Rosh Pina", "departure", ["NAT", "MOCEV", "GAFAZ", "BARZI", "ROP"], (8000, 24000), 4,
    "The published airway north from Netanya to the Rosh Pina VOR: NAT-MOCEV-GAFAZ-BARZI-ROP. The northern sector is IDFAF ACC 'PLUTO control'.",
    "AIP Israel ENR 3.1 (J14); ENR 2.1 (northern sector, PLUTO control)", seg=1, off=(-1, 0))
cor("il_coast", "The coast road north", "departure", ["NAT", "ATLIT", "HAIFA BLOCK", "ROSH HANIKRA"], (7000, 24000), 5,
    "Up the coast through LLR01, the IDF/AF offshore training area (7,000-40,000 ft), to the Lebanon border at Rosh HaNikra.",
    "AIP Israel ENR 3.1 (J15 ATLIT); ENR 5.1 LLR01", seg=1, off=(-1, 0))
cor("il_bekaa", "The Bekaa road", "transit", ["ROSH HANIKRA", "OFF SIDON", "BEKAA", "BAALBEK", "RAS BAALBEK"], (10000, 26000), 6,
    "Over Lebanon: the coast, then the Bekaa - Zahle, Baalbek - to the border towns of Ras Baalbek and Al-Fakhah, from where Homs, Masyaf and T-4 are struck. Reported low over the border 2017; stand-off from Lebanese airspace 2018.",
    "Anadolu 2 Nov 2017; Times of Israel / Defense Post 9 Apr 2018 (T-4); Times of Israel 9 Apr 2022; Wikipedia Mole Cricket 19", seg=2, off=(-1, 0))
cor("il_sea", "The sea road - west of Tripoli", "transit", ["ROSH HANIKRA", "OFF SIDON", "OFF BEIRUT", "OFF TRIPOLI", "W TRIPOLI"], (500, 20000), 8,
    "Offshore all the way: Sidon, Beirut, Tripoli, then the gate west of Tripoli for the Latakia and Tartus coast. 'Approached Latakia at low altitude from the Mediterranean' (2018).",
    "TASS 18 Sep 2018; The War Zone 2018; Al Jazeera 28 Dec 2021, 2 Jul 2022", seg=3, off=(-1, 0))
cor("il_golan", "The Golan road - Hermon", "transit", ["ROP", "KIRYAT SHMONA", "HERMON"], (5000, 22000), 5,
    "Rosh Pina, the Hula valley, then over Mount Hermon into the Damascus basin. 1973: low over Jordan, pop up over the Golan, away west of Hermon; 2013: 'entered the Syrian airspace via Mount Hermon'.",
    "Al Jazeera 31 Jan 2013; GlobalSecurity MML (1973); Al Jazeera 24 Nov 2020, 17 Sep 2022", seg=1, off=(1, 0))
cor("il_amman", "The Amman road - Al-Tanf", "transit", ["MUVIN", "OSAMA", "LOXER", "LUDAN", "ASLON", "NADEK", "DAXEN", "KUMLO", "DAPUK", "AT TANF"], (12000, 30000), 8,
    "The published L200 airway across Jordan - Amman, past Azraq, to the Iraqi corner - and the Al-Tanf deconfliction zone: 'the planes used Jordanian airspace and were aided by American forces stationed at the Tanf garrison'. The route 'enables Israeli forces to avoid Syrian early-warning radar'.",
    "CARC AMDT 19/2022 (L200); Times of Israel 9 Sep 2019; Washington Institute; Al Jazeera 20 Nov 2024", seg=4, off=(0, -1))
cor("il_home_coast", "Recovery down the coast", "recovery", ["ROSH HANIKRA", "HAIFA BLOCK", "ATLIT", "NAT"], (7000, 20000), 5,
    "Back through the LLR01 block to the Netanya VOR and home; 'TEL-AVIV control' 121.4 over the water.",
    "AIP Israel ENR 2.1 / 3.1 / 5.1", seg=1, off=(1, 0))
cor("il_home_rop", "Recovery via Rosh Pina", "recovery", ["HERMON", "ROP", "GAFAZ", "NAT"], (6000, 18000), 4,
    "Off Hermon back over the Rosh Pina VOR and down J14.", "AIP Israel ENR 3.1 (J14)", seg=2, off=(1, 0))
cor("il_home_amman", "Recovery down the Amman road", "recovery", ["AT TANF", "DAPUK", "DAXEN", "NADEK", "ASLON", "LOXER", "OSAMA", "MUVIN"], (12000, 30000), 8,
    "L200 westbound: the Iraqi corner, Azraq, Amman, the Jordan valley at MUVIN.", "CARC AMDT 19/2022 (L200)", seg=4, off=(0, 1))
# Cyprus
cor("cy_east", "EAST SID 3 - IREFA", "departure", ["AKROTIRI", "IREFA"], (2000, 9000), 4,
    "Runway heading, no turns before DER, direct IREFA; 'Aircraft departing Akrotiri going Eastbound are to be flight planned by IREFA'. Flamingo Ops 234.05 outbound.",
    "UK Mil AIP LCRA AD 2.22 and SID EAST 3", seg=0, off=(0, 1))
cor("cy_west", "WEST SID 1 - ANANE", "departure", ["AKROTIRI", "ANANE"], (2000, 9000), 4,
    "Runway heading to 580/1880 ft, then direct ANANE - the westbound and the southern-sea departure.",
    "UK Mil AIP LCRA SID WEST 1", seg=0, off=(-1, 0))
cor("cy_levant", "The Levant sea road", "transit", ["IREFA", "NIKAS"], (15000, 30000), 8,
    "IREFA to NIKAS, the Damascus FIR entry off Latakia - across the sea south of the Il-20 position of 2018. Russian sea-closure areas off Latakia are declared by NOTAM; their polygons are not published.",
    "UK Mil AIP LCRA; Syria eAIP ENR 3 (R785 NIKAS); safeairspace Cyprus", seg=0, off=(0, -1))
cor("cy_amman", "The Amman run", "transit", ["IREFA", "MERVA", "NAT", "MUVIN"], (15000, 30000), 8,
    "IREFA to the Israeli coast at MERVA, the Netanya VOR, and the Jordan border at MUVIN - the Akrotiri-to-Iraq run 'via downtown Amman'. Continues on the Amman road to Al-Tanf.",
    "The Aviationist 5 Feb 2019 (Tornado GR4, 'via downtown Amman Jordan'); AIP Israel ENR 3.1 (MERVA, NAT, MUVIN)", seg=1, off=(0, -1))
cor("cy_home", "STAR ALPHA - the TACAN", "recovery", ["IREFA", "AKR HOLD", "AKROTIRI"], (5000, 14000), 4,
    "From IREFA 'AKR 291 to 15.7 DME', the 13.7 DME arc; hold AKR 189R/11.7d FL100-FL140; talkdown 125.7.",
    "UK Mil AIP LCRA STAR ALPHA / TAC Rwy 28", seg=1, off=(1, 0))
# Turkey
cor("tr_w74", "W74 east - the Northern Watch road", "transit", ["ADA", "MILBA", "GAZ", "SURUC", "OZBEY", "DYB"], (9500, 28000), 8,
    "The airway east across south-east Turkey to the Diyarbakır MTMA - the 'ROZ over eastern Turkey' where the Northern Watch package topped off before turning south, the Syrian border 20 miles to the right.",
    "AIP Türkiye ENR 3.1 (W74) / ENR 4.4; A&SF Feb 2000; Ricks/WaPo 25 Oct 2000; GAO OSI-98-4", seg=2, off=(0, -1))
cor("tr_hatay", "The Hatay gate - TUNLA", "transit", ["ADA", "HTY", "TUNLA"], (9500, 26000), 6,
    "Adana VOR, Hatay VOR, then TUNLA on the FIR boundary south of Hatay - the Syrian coast and the Orontes valley (L601 TUNLA-SALIM-KTN).",
    "AIP Türkiye ENR 4.4 (TUNLA, HTY); Syria eAIP ENR 3 (L601)", seg=1, off=(1, 0))
cor("tr_kilis", "The Kilis gate - NISAP", "transit", ["ADA", "MILBA", "NISAP"], (9500, 26000), 6,
    "W74 to MILBA then south to NISAP on the border near Kilis; Aleppo is 40 nm beyond (M861 NISAP-ALE).",
    "AIP Türkiye ENR 4.4 (NISAP); Syria eAIP ENR 3 (M861)", seg=1, off=(1, 0))
cor("tr_nusaybin", "The Nusaybin gate - LESRI", "transit", ["DYB", "LESRI"], (12000, 28000), 6,
    "From the Diyarbakır MTMA south to LESRI on the border near Nusaybin; Qamishli, Hasakah and the Euphrates beyond (L573 KML-LESRI, L572 to Deir ez-Zor).",
    "AIP Türkiye ENR 4.4 (LESRI); Syria eAIP ENR 3 (L572/L573)", seg=0, off=(1, 0))
cor("tr_home", "Recovery to Incirlik", "recovery", ["MILBA", "ADA", "INCIRLIK"], (6000, 15000), 6,
    "Back along W74 into the Adana MTMA (50 nm, FL280 down to 2,000): İncirlik Approach 120.2, TACAN DAN Ch 21X.",
    "AIP Türkiye ENR 2.1 (Adana MTMA); LTAG AD 2", seg=0, off=(0, 1))
cor("tr_home_east", "Recovery from the east - the ROZ", "recovery", ["LESRI", "DYB", "SURUC", "GAZ", "MILBA", "ADA", "INCIRLIK"], (9500, 28000), 8,
    "Out through LESRI, into the ROZ at Diyarbakır for gas, then W74 westbound - the Northern Watch return.",
    "A&SF Feb 2000; AIP Türkiye ENR 3.1 (W74)", seg=3, off=(0, 1))
# Jordan
cor("jo_amman", "Amman TMA departure", "departure", ["MUWAFFAQ SALTI", "ASLON"], (5500, 15500), 4,
    "Out of the Amman TMA (5,500-FL155, Class C, 128.9) to ASLON on the L200/A412 corridor that OJP9 leaves open.",
    "CARC ENR 2.1 (Amman TMA); AMDT 19/2022 (ASLON-NADEK excluded from OJP9)", seg=0, off=(0, 1))
cor("jo_tanf", "L200 east - Al-Tanf", "transit", ["ASLON", "NADEK", "DAXEN", "KUMLO", "DAPUK", "AT TANF"], (12000, 30000), 8,
    "The Amman-Baghdad airway to the Iraqi corner, then the Al-Tanf zone: 'a 55-kilometer radius from the al-Tanf base'. Muwaffaq Salti is 'significantly closer to At Tanf than Al Dhafra'.",
    "CARC AMDT 19/2022 (L200); VOA / Military Times 2017; TWZ 2019", seg=3, off=(0, 1))
cor("jo_busra", "L513 north - Busra", "transit", ["QAA", "LOXER", "LOSAR", "BUSRA"], (12000, 28000), 6,
    "The Amman-Damascus airway north to BUSRA on the FIR boundary; RDIMA and Damascus beyond (L513).",
    "CARC AMDT 19/2022 (L513); Syria eAIP ENR 3 (L513)", seg=2, off=(1, 0))
cor("jo_zelaf", "A412 - Zelaf", "transit", ["ASLON", "NADEK", "DAXEN", "ZELAF"], (12000, 30000), 8,
    "A412 to ZELAF on the FIR boundary; Palmyra (TUDMU) and the central desert beyond (B544 TAN-TUDMU-ALE).",
    "CARC AMDT 19/2022 (A412); Syria eAIP ENR 3", seg=2, off=(1, 0))
cor("jo_home", "Recovery to Azraq", "recovery", ["DAPUK", "DAXEN", "NADEK", "ASLON", "MUWAFFAQ SALTI"], (10000, 28000), 6,
    "L200 westbound into the Amman TMA.", "CARC AMDT 19/2022 (L200)", seg=2, off=(0, 1))
cor("jo_home_busra", "Recovery via Busra", "recovery", ["BUSRA", "LOSAR", "LOXER", "MUWAFFAQ SALTI"], (10000, 26000), 6,
    "L513 southbound, then east into the Azraq field.", "CARC AMDT 19/2022 (L513)", seg=1, off=(1, 0))

GATES = {
    "RAS BAALBEK": "Homs, Masyaf, T-4 (Tiyas) and the Hama plain - the reported launch area over north-east Lebanon",
    "W TRIPOLI": "the Syrian coast - Latakia, Bassel Al-Assad / Khmeimim, Tartus, Baniyas",
    "HERMON": "the Damascus basin - Mezzeh, Damascus, Marj Ruhayyil, Dumayr, Sayqal, Khalkhalah",
    "AT TANF": "the east - Deir ez-Zor, Al-Bukamal, Palmyra - and the central desert from the south-east",
    "HAIFA BLOCK": "the offshore training block LLR01 (7,000-40,000 ft)",
    "NIKAS": "the Latakia coast from the sea - Khmeimim, Latakia, Bassel Al-Assad; Hama and Aleppo inland",
    "TUNLA": "the Orontes valley - Latakia coast, Hama, Homs (L601 to Kariatain)",
    "NISAP": "Aleppo, Minakh, Kuweires, Jirah - 40 nm south",
    "TUSYR": "Aleppo from the north-east",
    "LESRI": "the north-east - Qamishli, Hasakah, the Euphrates at Deir ez-Zor",
    "BUSRA": "the Damascus basin from the south - Khalkhalah, Tha'lah, Damascus",
    "ZELAF": "Palmyra, Tiyas / T-4, the central desert",
    "DEIR EZ-ZOR W": "Deir ez-Zor and Al-Bukamal from the Al-Tanf axis",
}

# ---- sectors (targets) -------------------------------------------------------
SECTORS = {
    "_comment": "Which corridor family a TARGET belongs to. Checked in order. Targets in Israel, Jordan, Cyprus and Turkey match no rule and get the generic route.",
    "rules": [
        {"sector": "lebanon", "when": "lat >= 33.05 and lat <= 34.75 and lon >= 35.05 and lon <= 36.0"},
        {"sector": "lebanon", "when": "lat >= 33.95 and lat <= 34.75 and lon >= 36.0 and lon <= 36.5"},
        {"sector": "damascus", "when": "lat >= 32.85 and lat <= 34.05 and lon >= 36.0 and lon <= 37.6"},
        {"sector": "coast", "when": "lat >= 34.3 and lat <= 36.0 and lon >= 35.3 and lon <= 36.4"},
        {"sector": "north", "when": "lat >= 35.6 and lat <= 37.2 and lon >= 36.4 and lon <= 38.6"},
        {"sector": "east", "when": "lat >= 32.9 and lat <= 37.3 and lon >= 38.5 and lon <= 42.0"},
        {"sector": "central", "when": "lat >= 34.0 and lat <= 35.65 and lon >= 36.35 and lon <= 38.6"},
    ],
    "default": "none",
    "labels": {"lebanon": "the Bekaa and Lebanon", "damascus": "the Damascus basin", "coast": "the Syrian coast",
               "north": "northern Syria - Aleppo and Idlib", "east": "the Euphrates and the east",
               "central": "central Syria - Homs, Hama and the desert fields", "local": "local"},
}

# ---- plans -------------------------------------------------------------------
def P(out, gin, gout, back):
    return {"out": out, "gate_in": gin, "gate_out": gout, "back": back}

PLANS = {
    "israel": {
        "lebanon":  {"low": P(["il_coast", "il_bekaa"], "RAS BAALBEK", "RAS BAALBEK", "il_home_coast")},
        "damascus": {"low": P(["il_j14", "il_golan"], "HERMON", "HERMON", "il_home_rop")},
        "coast":    {"low": P(["il_coast", "il_sea"], "W TRIPOLI", "W TRIPOLI", "il_home_coast")},
        "central":  {"low": P(["il_coast", "il_bekaa"], "RAS BAALBEK", "RAS BAALBEK", "il_home_coast")},
        "north":    {"low": P(["il_coast", "il_sea"], "W TRIPOLI", "W TRIPOLI", "il_home_coast")},
        "east":     {"low": P(["il_amman"], "AT TANF", "AT TANF", "il_home_amman")},
    },
    "cyprus": {
        "coast":    {"low": P(["cy_east", "cy_levant"], "NIKAS", "NIKAS", "cy_home")},
        "north":    {"low": P(["cy_east", "cy_levant"], "NIKAS", "NIKAS", "cy_home")},
        "central":  {"low": P(["cy_east", "cy_levant"], "NIKAS", "NIKAS", "cy_home")},
        "lebanon":  {"low": P(["cy_east", "cy_levant"], "NIKAS", "NIKAS", "cy_home")},
        "damascus": {"low": P(["cy_east", "cy_amman", "il_amman"], "AT TANF", "AT TANF", "cy_home")},
        "east":     {"low": P(["cy_east", "cy_amman", "il_amman"], "AT TANF", "AT TANF", "cy_home")},
    },
    "turkey": {
        "coast":    {"low": P(["tr_hatay"], "TUNLA", "TUNLA", "tr_home")},
        "central":  {"low": P(["tr_hatay"], "TUNLA", "TUNLA", "tr_home")},
        "lebanon":  {"low": P(["tr_hatay"], "TUNLA", "TUNLA", "tr_home")},
        "damascus": {"low": P(["tr_hatay"], "TUNLA", "TUNLA", "tr_home")},
        "north":    {"low": P(["tr_kilis"], "NISAP", "NISAP", "tr_home")},
        "east":     {"low": P(["tr_w74", "tr_nusaybin"], "LESRI", "LESRI", "tr_home_east")},
    },
    "jordan": {
        "east":     {"low": P(["jo_amman", "jo_tanf"], "AT TANF", "AT TANF", "jo_home")},
        "central":  {"low": P(["jo_amman", "jo_zelaf"], "ZELAF", "ZELAF", "jo_home")},
        "north":    {"low": P(["jo_amman", "jo_zelaf"], "ZELAF", "ZELAF", "jo_home")},
        "damascus": {"low": P(["jo_busra"], "BUSRA", "BUSRA", "jo_home_busra")},
        "lebanon":  {"low": P(["jo_busra"], "BUSRA", "BUSRA", "jo_home_busra")},
        "coast":    {"low": P(["jo_busra"], "BUSRA", "BUSRA", "jo_home_busra")},
    },
}

CLUSTERS = {
    "israel": {"label": "northern Israel (Ramat David and the Galilee fields)",
               "fields": ["Ramat David", "Rosh Pina", "Megiddo", "Haifa", "Eyn Shemer", "Kiryat Shmona",
                          "Ben Gurion", "Hatzor", "Palmachim", "Nevatim", "Kedem"],
               "center": [32.665, 35.179], "local_nm": 22, "join_from_outside": False},
    "cyprus": {"label": "RAF Akrotiri and the Cyprus fields",
               "fields": ["Akrotiri", "Paphos", "Larnaca", "Kingsfield", "Lakatamia", "Ercan", "Gecitkale", "Pinarbashi"],
               "center": [34.5904, 32.9878], "local_nm": 20, "join_from_outside": False},
    "turkey": {"label": "Incirlik and the Adana MTMA",
               "fields": ["Incirlik", "Adana Sakirpasa", "Hatay", "Gaziantep", "Chukurova", "Kahramanmaras"],
               "center": [37.0033, 35.4322], "local_nm": 25, "join_from_outside": False},
    "jordan": {"label": "Muwaffaq Salti (Azraq) and the Jordanian fields",
               "fields": ["Muwaffaq Salti", "Prince Hassan", "King Hussein Air College", "Marka", "King Abdullah II", "Zarqa", "Ruwayshid"],
               "center": [31.83417, 36.78722], "local_nm": 20, "join_from_outside": False},
}

# ---- chart -------------------------------------------------------------------
# LLR01 per AIP Israel ENR 5.1: the 47-NM arc centered on BGN 320051N 0345232E
BGN = (dms(32, 0, 51), dms(34, 52, 32))
llr01 = [[dms(33, 5, 11), dms(34, 54, 55)], [dms(32, 53, 56), dms(34, 54, 59)], [dms(32, 26, 26), dms(34, 46, 29)],
         [dms(32, 29, 56), dms(34, 26, 29)], [dms(32, 38, 37), dms(34, 19, 26)]] + arc(BGN[0], BGN[1], 47, 322, 348, 6) + \
        [[dms(32, 44, 52), dms(34, 32, 49)], [dms(32, 46, 36), dms(34, 32, 36)], [dms(32, 51, 48), dms(34, 33, 42)],
         [dms(33, 5, 18), dms(34, 36, 30)], [dms(33, 6), dms(34, 43)]]
llr02 = [[dms(31, 42, 14), dms(34, 27, 11)], [dms(31, 24, 58), dms(34, 11, 3)], [dms(31, 24, 8), dms(34, 10, 18)],
         [dms(31, 50, 35), dms(33, 58, 38)]] + arc(BGN[0], BGN[1], 47, 275, 283, 3) + \
        [[dms(32, 0, 10), dms(33, 57, 19)], [dms(31, 59, 10), dms(34, 5, 1)], [dms(31, 52, 41), dms(34, 16, 8)]]
llp19 = [[31.6494, 34.4881], [31.5725, 34.6194], [31.4917, 34.6033], [31.4092, 34.5383], [31.3333, 34.4694], [31.2597, 34.4139],
         [31.1731, 34.2839], [31.1897, 34.2361], [31.3425, 34.1958], [31.4625, 34.2875], [31.6494, 34.4881]]
llp15 = [[31.0497, 35.1803], [31.0311, 35.1958], [30.9403, 35.1458], [30.9428, 35.1139], [30.9719, 35.0742],
         [31.0164, 35.0653], [31.0367, 35.0972], [31.0381, 35.1422]]
llr83 = [[dms(32, 33, 2), dms(35, 20, 54)], [dms(32, 30, 43), dms(35, 28, 18)], [dms(32, 5, 2), dms(35, 26, 42)],
         [dms(32, 11, 18), dms(35, 13, 45)], [dms(32, 15, 40), dms(35, 2, 56)], [dms(32, 17, 26), dms(35, 3, 24)],
         [dms(32, 22, 34), dms(35, 9, 5)]]
negev = [[31.19, 34.33], [31.21, 34.48], [31.0, 34.75], [30.79, 34.98], [30.50, 34.93], [30.33, 35.04], [30.34, 34.82],
         [30.62, 34.68], [30.63, 34.47], [30.92, 34.44]]
amman_tma = [[dms(32, 3, 56), dms(35, 51, 59)], [dms(32, 3, 56), dms(36, 10, 59)], [dms(32, 10, 26), dms(36, 27, 59)],
             [dms(32, 4, 26), dms(36, 36, 59)], [dms(31, 52, 56), dms(36, 25, 29)], [dms(31, 12, 56), dms(36, 34, 59)],
             [dms(31, 7, 56), dms(35, 54, 59)], [dms(31, 42, 56), dms(35, 42, 59)]]
ltd13 = [[dms(36, 26), dms(35, 29)], [dms(36, 17), dms(35, 24)], [dms(36, 32), dms(34, 42)], [dms(36, 40), dms(34, 52)]]
arfa = [[dms(34, 34, 13), dms(33, 11, 26)], [dms(34, 39, 26), dms(32, 52, 16)], [dms(34, 30, 51), dms(32, 48, 51)]] + \
       arc(dms(34, 35, 42), dms(32, 59, 27), 10, 200, 340, 8)

AREAS = [
    {"id": "LLR01", "kind": "restricted", "label": "LLR01\nIDF/AF OFFSHORE TRAINING", "alt": "7,000-40,000 ft", "poly": llr01, "label_at": [32.55, 34.40], "src": "AIP Israel ENR 5.1 (AIRAC 2025-10-02)"},
    {"id": "LLR02", "kind": "restricted", "label": "LLR02\nIDF/AF TRAINING", "alt": "5,000-FL400 H24", "poly": llr02, "label_at": [31.75, 34.05], "src": "AIP Israel ENR 5.1"},
    {"id": "LLP19", "kind": "restricted_box", "label": "LLP19\nGAZA - PROHIBITED", "alt": "GND-UNL", "poly": llp19, "label_at": [31.42, 34.15], "src": "AIP Israel ENR 5.1"},
    {"id": "LLP15", "kind": "restricted_box", "label": "LLP15\nDIMONA - PROHIBITED", "alt": "GND-UNL", "poly": llp15, "label_at": [30.90, 35.30], "src": "AIP Israel ENR 5.1"},
    {"id": "LLR83", "kind": "restricted", "label": "LLR83\nJORDAN VALLEY MIL", "alt": "GND-11,000", "poly": llr83, "label_at": [31.95, 35.45], "src": "AIP Israel ENR 5.1"},
    {"id": "NEGEV", "kind": "restricted", "label": "LLR36 / 500-series / 801-805\nNEGEV RANGES", "alt": "GND-14,500 (LLR36 UNL)", "approx": True, "poly": negev, "label_at": [30.65, 34.35], "src": "AIP Israel ENR 5.1 (LLR36, LLR500-618, LLR801-805) - merged outline"},
    {"id": "AMMAN TMA", "kind": "tma", "label": "AMMAN TMA", "alt": "5,500-FL155 Class C", "poly": amman_tma, "label_at": [31.45, 36.15], "src": "CARC ENR 2.1 (AMDT 45/2007)"},
    {"id": "BEIRUT CTR", "kind": "tma", "label": "BEIRUT CTR", "alt": "SFC-4,000, 20 NM", "poly": circle(dms(33, 48, 26.7), dms(35, 29, 9.5), 20, 24), "label_at": [33.95, 34.95], "src": "DGCA Lebanon AD 2 OLBA (IVAO mirror): circle 20 NM on KAD VOR"},
    {"id": "LATAKIA CTR", "kind": "tma", "label": "LATAKIA CTR", "alt": "15 NM · 119.9", "poly": circle(dms(35, 28, 49), dms(35, 56, 32), 15, 24), "label_at": [35.85, 35.10], "src": "Syria eAIP ENR 2.1"},
    {"id": "DCZ", "kind": "zone", "label": "AL-TANF DECONFLICTION ZONE", "alt": "55 km radius", "poly": circle(33.50583, 38.61778, 55 / 1.852, 36), "label_at": [33.85, 38.62], "src": "Wikipedia Al-Tanf; VOA / Military Times 2017; TASS 2019"},
    {"id": "ADANA MTMA", "kind": "tma", "label": "ADANA MTMA", "alt": "2,000-FL280 · İncirlik App 120.2", "poly": circle(dms(36, 59, 56), dms(35, 25, 59), 50, 36), "label_at": [37.65, 35.85], "src": "AIP Türkiye ENR 2.1"},
    {"id": "DIYARBAKIR MTMA", "kind": "tma", "label": "DİYARBAKIR MTMA\nthe Northern Watch ROZ", "alt": "3,300-FL280", "poly": circle(dms(37, 51, 14), dms(40, 12, 56), 50, 36), "label_at": [38.12, 39.95], "src": "AIP Türkiye ENR 2.1; A&SF Feb 2000 (ROZ over eastern Turkey)"},
    {"id": "GAZIANTEP TMA", "kind": "tma", "label": "GAZİANTEP TMA", "alt": "3,500-FL240", "poly": circle(dms(36, 56, 56), dms(37, 27, 59), 15, 24), "label_at": [37.22, 37.47], "src": "AIP Türkiye LTAJ AD 2"},
    {"id": "LTD13", "kind": "moa", "label": "LTD13 ADANA\nair-to-air firing", "alt": "MSL-35,000 by NOTAM", "poly": ltd13, "label_at": [36.30, 34.95], "src": "AIP Türkiye ENR 5.1"},
    {"id": "ARFA", "kind": "tma", "label": "AKROTIRI ARFA", "alt": "SFC-3,000", "poly": arfa, "label_at": [34.05, 33.30], "src": "UK Mil AIP LCRA"},
    {"id": "LCD47", "kind": "moa", "label": "LCD47 SOTIA\nRAF/CNG military flying", "alt": "SFC-FL280 by NOTAM", "approx": True, "poly": circle(34.10, 33.017, 33, 30), "label_at": [33.70, 33.0], "src": "NOTAM LCCC Q-line 3406N03301E033 (a 33-NM circle; the polygon is not published)"},
]

LINES = [
    {"kind": "coast", "name": "Levant coast", "pts": [[31.25, 34.27], [31.50, 34.45], [31.80, 34.63], [32.08, 34.77], [32.48, 34.88], [32.82, 34.96], [32.92, 35.07], [33.09, 35.10], [33.27, 35.19], [33.56, 35.37], [33.90, 35.48], [34.12, 35.65], [34.43, 35.83], [34.65, 35.98], [34.89, 35.88], [35.18, 35.95], [35.52, 35.78], [35.85, 35.85], [36.08, 35.93], [36.40, 35.87], [36.58, 36.17], [36.75, 36.10], [36.72, 35.60], [36.55, 35.38], [36.72, 34.90], [36.80, 34.63], [36.60, 34.30], [36.30, 33.95], [36.05, 32.83], [36.27, 32.32], [36.54, 32.00]]},
    {"kind": "coast", "name": "Cyprus", "pts": [[34.77, 32.42], [34.63, 32.65], [34.57, 32.95], [34.68, 33.04], [34.75, 33.30], [34.92, 33.63], [34.96, 34.08], [35.12, 33.94], [35.34, 34.00], [35.69, 34.58], [35.55, 34.20], [35.34, 33.32], [35.40, 32.92], [35.20, 32.95], [35.15, 32.57], [35.10, 32.28], [34.90, 32.30], [34.77, 32.42]]},
    {"kind": "border", "name": "Israel-Lebanon (Blue Line)", "pts": [[33.09, 35.10], [33.10, 35.30], [33.28, 35.55], [33.27, 35.62]]},
    {"kind": "border", "name": "Golan / Syria-Lebanon", "pts": [[33.27, 35.62], [33.42, 35.85], [33.80, 36.05], [34.30, 36.45], [34.62, 36.30], [34.65, 35.98]]},
    {"kind": "border", "name": "Israel-Syria (1974 line)", "pts": [[33.27, 35.62], [32.95, 35.75], [32.72, 35.65]]},
    {"kind": "border", "name": "Israel/Jordan-Syria", "pts": [[32.72, 35.65], [32.70, 36.00], [32.55, 36.50], [32.35, 37.00], [32.30, 37.50], [33.10, 38.30], [33.40, 38.80]]},
    {"kind": "border", "name": "Syria-Iraq", "pts": [[33.40, 38.80], [34.30, 40.85], [34.65, 41.10], [35.30, 41.35], [36.30, 41.30], [36.60, 41.40], [37.10, 42.35]]},
    {"kind": "border", "name": "Syria-Turkey", "pts": [[35.90, 36.00], [35.95, 36.15], [36.20, 36.42], [36.60, 36.45], [36.80, 36.60], [36.70, 37.00], [36.65, 37.40], [36.75, 38.00], [36.90, 38.40], [36.90, 39.00], [37.10, 40.10], [37.10, 41.20], [37.30, 42.00]]},
    {"kind": "border", "name": "Israel-Jordan", "pts": [[32.72, 35.65], [32.40, 35.57], [31.80, 35.55], [31.50, 35.48], [31.20, 35.35], [30.90, 35.20]]},
    {"kind": "deconfliction", "name": "Euphrates line", "label": "EUPHRATES DECONFLICTION LINE (2017)", "pts": [[35.83, 38.40], [35.70, 38.95], [35.55, 39.40], [35.35, 39.95], [35.05, 40.45], [34.70, 40.85]]},
]

ROADS = [
    {"name": "Beirut-Damascus hwy", "pts": [[33.89, 35.50], [33.815, 35.855], [33.72, 35.93], [33.51, 36.29]]},
    {"name": "M2 - Baghdad hwy", "pts": [[33.51, 36.40], [33.55, 37.20], [33.50, 38.00], [33.50, 38.61], [33.43, 38.93]]},
    {"name": "M5", "pts": [[33.51, 36.30], [34.20, 36.70], [34.73, 36.72], [35.13, 36.75], [35.60, 36.85], [36.20, 37.15]]},
    {"name": "Hwy 4 - Euphrates", "pts": [[34.45, 40.92], [35.00, 40.45], [35.33, 40.15], [35.85, 39.05], [35.95, 38.60]]},
]

PLACES = [
    {"name": "Damascus", "lat": 33.51, "lon": 36.29, "kind": "city"}, {"name": "Beirut", "lat": 33.89, "lon": 35.50, "kind": "city"},
    {"name": "Aleppo", "lat": 36.20, "lon": 37.16, "kind": "city"}, {"name": "Homs", "lat": 34.73, "lon": 36.72, "kind": "city"},
    {"name": "Latakia", "lat": 35.52, "lon": 35.79, "kind": "city"}, {"name": "Amman", "lat": 31.95, "lon": 35.93, "kind": "city"},
    {"name": "Tel Aviv", "lat": 32.08, "lon": 34.78, "kind": "city"}, {"name": "Haifa", "lat": 32.82, "lon": 34.99, "kind": "city"},
    {"name": "Nicosia", "lat": 35.17, "lon": 33.36, "kind": "city"}, {"name": "Adana", "lat": 37.00, "lon": 35.32, "kind": "city"},
    {"name": "Diyarbakır", "lat": 37.91, "lon": 40.24, "kind": "city"},
    {"name": "Tripoli", "lat": 34.43, "lon": 35.84, "kind": "town"}, {"name": "Sidon", "minor": True, "lat": 33.56, "lon": 35.37, "kind": "town"},
    {"name": "Tyre", "minor": True, "lat": 33.27, "lon": 35.20, "kind": "town"}, {"name": "Zahle", "minor": True, "lat": 33.85, "lon": 35.90, "kind": "town"},
    {"name": "Palmyra", "lat": 34.56, "lon": 38.28, "kind": "town"}, {"name": "Deir ez-Zor", "minor": True, "lat": 35.33, "lon": 40.14, "kind": "town"},
    {"name": "Al-Bukamal", "lat": 34.45, "lon": 40.92, "kind": "town"}, {"name": "Hama", "lat": 35.13, "lon": 36.75, "kind": "town"},
    {"name": "Tartus", "lat": 34.89, "lon": 35.89, "kind": "town"}, {"name": "Masyaf", "lat": 35.06, "lon": 36.34, "kind": "town"},
    {"name": "Azraq", "lat": 31.83, "lon": 36.83, "kind": "town"}, {"name": "Mafraq", "lat": 32.34, "lon": 36.21, "kind": "town"},
    {"name": "Daraa", "lat": 32.62, "lon": 36.10, "kind": "town"}, {"name": "Quneitra", "lat": 33.13, "lon": 35.82, "kind": "town"},
    {"name": "Raqqa", "lat": 35.95, "lon": 39.01, "kind": "town"}, {"name": "Qamishli", "lat": 37.05, "lon": 41.22, "kind": "town"},
    {"name": "Gaziantep", "minor": True, "lat": 37.07, "lon": 37.38, "kind": "town"}, {"name": "Kilis", "minor": True, "lat": 36.72, "lon": 37.12, "kind": "town"},
    {"name": "Limassol", "minor": True, "lat": 34.68, "lon": 33.04, "kind": "town"},
    {"name": "Ramat David", "lat": 32.665, "lon": 35.179, "kind": "airfield"}, {"name": "Rosh Pina", "lat": 32.98, "lon": 35.57, "kind": "airfield"},
    {"name": "Nevatim", "lat": 31.21, "lon": 35.01, "kind": "airfield"}, {"name": "Akrotiri", "lat": 34.59, "lon": 32.99, "kind": "airfield"},
    {"name": "Incirlik", "lat": 37.00, "lon": 35.43, "kind": "airfield"}, {"name": "Muwaffaq Salti", "lat": 31.834, "lon": 36.787, "kind": "airfield"},
    {"name": "Khmeimim", "lat": 35.41, "lon": 35.95, "kind": "airfield"}, {"name": "Damascus Intl", "lat": 33.41, "lon": 36.51, "kind": "airfield"},
    {"name": "T-4 Tiyas", "lat": 34.52, "lon": 37.63, "kind": "airfield"}, {"name": "Shayrat", "lat": 34.49, "lon": 36.91, "kind": "airfield"},
    {"name": "Al-Tanf", "lat": 33.506, "lon": 38.618, "kind": "airfield"}, {"name": "Deir ez-Zor AB", "lat": 35.285, "lon": 40.176, "kind": "airfield"},
    {"name": "Rayak", "minor": True, "lat": 33.85, "lon": 35.99, "kind": "airfield"}, {"name": "Prince Hassan H-5", "lat": 32.16, "lon": 37.15, "kind": "airfield"},
]

PANELS = [
    {"id": "israel", "cluster": "israel", "title": "NORTHERN ISRAEL - the Galilee fields, J14 and the coast", "tag": "NORTHERN ISRAEL - see panel",
     "bounds": {"lat": [32.15, 33.55], "lon": [34.0, 36.3]}, "grid": 0.25, "declutter": True,
     "labels": {"il_coast": {"seg": 2, "off": [-1, 0]}, "il_golan": {"seg": 1, "off": [0, 1]},
                "il_home_coast": {"seg": 1, "off": [1, 0], "nudge": [8, 16]}},
     "lanes": ["il_j14", "il_coast", "il_golan", "il_home_coast", "il_home_rop"]},
    {"id": "cyprus", "cluster": "cyprus", "title": "AKROTIRI - SIDs, the ARFA, the TACAN recovery", "tag": "AKROTIRI - see panel",
     "bounds": {"lat": [34.05, 35.05], "lon": [32.3, 33.8]}, "grid": 0.25, "declutter": True,
     "labels": {"cy_east": {"seg": 0, "off": [0, -1], "nudge": [40, -10]}, "cy_home": {"seg": 0, "off": [0, 1], "nudge": [0, 10]}, "cy_west": {"seg": 0, "off": [-1, 0], "nudge": [-10, 10]}},
     "lanes": ["cy_east", "cy_west", "cy_home", "cy_levant", "cy_amman"]},
    {"id": "turkey", "cluster": "turkey", "title": "INCIRLIK - the Adana MTMA and the border gates", "tag": "INCIRLIK - see panel",
     "bounds": {"lat": [35.75, 37.45], "lon": [34.5, 38.0]}, "grid": 0.5, "declutter": True,
     "labels": {"tr_w74": {"seg": 1, "off": [0, -1]}, "tr_kilis": {"seg": 1, "off": [0, 1], "nudge": [-20, 14]},
                "tr_home": {"seg": 0, "off": [0, 1], "nudge": [-40, 12]}, "tr_hatay": {"seg": 1, "off": [-1, 0]}},
     "lanes": ["tr_w74", "tr_hatay", "tr_kilis", "tr_home"]},
    {"id": "jordan", "cluster": "jordan", "title": "AMMAN - the TMA and the L200 corridor", "tag": "AMMAN - see panel",
     "bounds": {"lat": [31.1, 32.7], "lon": [35.4, 37.9]}, "grid": 0.5, "declutter": True,
     "labels": {"jo_home": {"seg": 3, "off": [1, 0], "nudge": [0, 14]}, "jo_amman": {"seg": 0, "off": [1, 0], "nudge": [55, -30]},
                "jo_busra": {"seg": 2, "off": [-1, 0]}, "jo_home_busra": {"seg": 1, "off": [-1, 0]}},
     "lanes": ["jo_amman", "jo_tanf", "jo_busra", "jo_zelaf", "jo_home", "jo_home_busra"]},
]

TEXT = {
    "chart_title": "LEVANT CORRIDORS",
    "md_line": "**{summary}** — {sector}, {mode} road. Entry gate **{gate_in}** (WP1), exit at **{gate_out}**. The flight plan is threaded through the published structure - the airways, the FIR fixes and the roads the IAF is reported to fly; nobody goes direct across the border.",
    "md_title": "Levant corridors",
    "chart_subtitle": "The Syria map - how a flight gets from Israel, Cyprus, Turkey or Jordan to the fight and back. Airways and FIR fixes from the AIPs; the reported IAF roads; the Al-Tanf zone. Not for real-world navigation.",
    "kneeboard_subtitle": "The Levant - your road in red",
    "brief_page_subtitle": "The Syria map — this mission's road in red",
    "brief_title": "LEVANT CORRIDORS - HOW YOU GET TO THE FIGHT",
    "brief_intro": ["The flight plan is threaded through the published structure - the airways and",
                    "FIR boundary fixes of the Israeli, Jordanian, Turkish, Cypriot and Syrian AIPs -",
                    "and the roads the IAF is reported to fly: over the Bekaa, west of Tripoli, over",
                    "Hermon, via Al-Tanf. Israel's northern sector is PLUTO control; Jordan's Amman",
                    "TMA is Class C; Incirlik's MTMA is 50 nm; NATO's Akrotiri talks to Flamingo Ops."],
    "brief_sources": ["Sources: AIP Israel ENR 2.1/3.1/5.1; CARC Jordan ENR 2.1/3.1 and AMDT 19/2022; AIP",
                      "Turkiye ENR 2.1/3.1/4.4/5.1; UK Mil AIP LCRA; Syria GACA eAIP ENR 3/4; press",
                      "reporting of IAF strikes 2013-2024 (Al Jazeera, Times of Israel, TASS, TWZ, Anadolu);",
                      "GlobalSecurity MML (1973); Wikipedia (Mole Cricket 19, Al-Tanf)."],
    "known_issues": ["DCS draws no airways or FIR boundaries; the corridors and gates on the F10 map are ours, from the published structure. The AI controllers do not know PLUTO, Flamingo Ops or the Amman TMA exist."],
    "sources_line": "AIP Israel · CARC Jordan · AIP Türkiye · UK Mil AIP LCRA · Syria GACA eAIP · Al Jazeera / ToI / TASS / TWZ 2013-2024 · GlobalSecurity MML 1973 · Wikipedia",
    "legend": ["Restricted area: navy, hatched (Israel's LLR training blocks, the Negev ranges; LLP prohibited areas cross-hatched). Control area / CTR: thin dashed blue. Firing area: dashed magenta. Deconfliction zone / line: dashed amber.",
               "Gate ring = the entry/exit point of a road. Fix triangle = a published fix (AIP). ~ = curated: a reported road placed on the named town or summit, or an outline merged/approximated. Coast and borders are schematic."],
}

# Land polygons for the sea fill: the mainland is the Levant coast closed
# around the east and south of the chart (Sinai/Nile-delta coast schematic);
# Cyprus is its own closed coast. Schematic - the coast lines above are the
# drawn edge, these only decide what is painted sea.
_levant = next(l for l in LINES if l["name"] == "Levant coast")["pts"]
_cyprus = next(l for l in LINES if l["name"] == "Cyprus")["pts"]
LAND = [
    [[31.55, 31.5], [31.30, 32.30], [31.10, 33.20], [31.10, 33.90]] + _levant
    + [[36.60, 31.5], [38.5, 31.5], [38.5, 42.0], [30.5, 42.0], [30.5, 31.5]],
    _cyprus,
]


DATA = {
    "_comment": "Levant corridors (v1.102.0) - the Authentic standard map detail for the Syria map. Written by scripts/gen_syria_corridors.py; edit there. See that script's docstring for what is documented and what is curated.",
    "map": "syria", "label": "Levant corridors",
    "fixes": F, "corridors": C, "gates": GATES, "clusters": CLUSTERS, "sectors": SECTORS, "plans": PLANS,
    "text": TEXT,
    "chart": {
        "bounds": {"lat": [30.9, 38.2], "lon": [31.8, 41.6]},
        "sea": True,
        "land": LAND,
        "page": [1800, 1040],
        "panel_cols": 2,
        "panel_col_frac": 0.44,
        "overview_title": "THEATRE OVERVIEW",
        "hide_fixes": ["RAMAT DAVID", "BEN GURION", "NEVATIM", "AKROTIRI", "INCIRLIK", "LARNACA", "PAPHOS", "GAZIANTEP", "HATAY", "MUWAFFAQ SALTI"],
        "overview_landmarks": ["ROSH HANIKRA", "BAALBEK"],
        "labels": {"cy_amman": {"seg": 0, "off": [0, 1]}, "il_amman": {"seg": 6, "off": [0, 1], "nudge": [30, 6]},
                   "jo_tanf": {"hide": True}, "il_golan": {"hide": True}, "jo_busra": {"hide": True},
                   "jo_zelaf": {"hide": True}, "il_bekaa": {"seg": 3, "off": [-1, 0]}},
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
