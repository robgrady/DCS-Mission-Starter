# Air refuelling: why it's hard, and what we built

*Design note, 15 August 2026. Research across ED forums, Falcon BMS
documentation, Steam and Mudspike threads, USAF/USN refuelling doctrine and the
PIO literature. Sources at the end.*

---

## The bug underneath the complaint

Rob's report was "the generator doesn't provide the right aircraft speed." He
was right, and it was worse than a tuning issue.

Every tanker this product ever generated flew at `speed=550` — pydcs takes km/h
there — at 6,096 m. Measured out of a built mission:

> **152.8 m/s = 297 kt TAS ≈ 217 KIAS at 20,000 ft.**

Boom refuelling for fighters lives in the high 200s to low 300s KIAS. At 217 an
F-16 behind a KC-135 sits on the back of the drag curve, fighting the airplane
instead of flying the position — which to the pilot is indistinguishable from
being bad at refuelling. Nothing errored. The mission built. It simply was not
a refuelling track, and it had not been for every tanker, every receiver and
every era we have ever shipped.

The root cause is a unit confusion that is worth naming because it will happen
again: **a pilot flies IAS and a mission file stores TAS.** At 20,000 ft they
differ by about 37 %. A table written in indicated airspeed and dropped into the
file unconverted produces a tanker a third too slow.

---

## What the research actually says

I went looking for why people fail at this, because a correct tanker speed is
necessary and nowhere near sufficient.

### The single biggest fix is not in the mission

It is the **control curve**, and it lives in the pilot's controller settings.
Published recommendations for the same task range from **0 to 30** depending on
hardware:

| Hardware | Recommended curve |
|---|---|
| Thrustmaster T16000M | 25–30 |
| TM Warthog | 0–5 to 25, depending who you ask |
| VIRPIL (mechanical gimbal) | ≤10 — "20–30 is unflyable" |
| F/A-18C (Mudspike) | 15 |

**So the card gives no number, and says why.** Gimbal type dominates — plastic
ball gimbals have center play that mechanical ones do not — and a longer stick
is already a mechanical curve. Anyone who hands you a single figure is guessing
about your hardware. The principle we teach instead: add curve until small
corrections stop overshooting and no further, because curve buys precision at
center and sells it at the edges. Deadzone is a defect compensator, not a
technique aid: set it just past your stick's measured center noise, usually 0–3.

Do **not** curve the throttle. Anticipate — the spool is the lag.

### The oscillation has a name, and naming it is the lesson

This is the most valuable thing the research turned up. What people call
"chasing the basket" is **pilot-induced oscillation**, and it is a control
problem, not a character flaw:

- The pilot corrects for where the aircraft **is** rather than where it is
  **going**.
- The correction arrives after a lag — engine spool, airframe inertia, frame
  time, stick filtering.
- It overshoots. The pilot corrects harder, which *raises loop gain*.
- Push it far enough and inputs land **180° out of phase** with the response,
  and the oscillation grows instead of damping.
- Human reaction time puts the worst band around **0.5–1 Hz** — roughly one
  correction a second, which is exactly the rate a tense pilot corrects at.

That reframing changes the instruction from "be better" to **"reduce gain"**,
and gain has four levers a pilot can actually pull:

1. **Relax the grip.** Tension is gain nobody asked for.
2. **One input, then wait.** Waiting is a technique, not hesitation.
3. **Look at the tanker, not the boom or basket.** This is the one most often
   given as a comfort tip and it is not one — the basket has its own
   oscillation, so watching it inserts **a second oscillator into your control
   loop**. Looking away from it is removing a noise source.
4. **Curve the axis.** That is gain reduction in software.

The nicest corroboration: the **F-16's flight control system does lever 4 for
you in hardware** — opening the AR door drops the control gains — and the F-16
is correspondingly reported as needing little or no curve. The jet agrees with
the diagnosis.

### Pass criteria, so "practice refuelling" has a finish line

| Criterion | Value | Kind of claim |
|---|---|---|
| Pre-contact stabilised, zero closure — **the gate** | **15 s** | Doctrinal *shape* (ATP-56: stabilised, then cleared). The duration is a gate we set. |
| Pre-contact held hands-steady — **the standard** | **60 s** | **Ours.** No source in this library states a duration. |
| Closure — **approach** from pre-contact | **1–3 kt** over the tanker | Quoted (Stephenson, *Air Refueling Receiver*) |
| Closure — **last few feet** | **≈1 ft/sec** (≈0.6 kt) | Quoted (KC-46 program literature) |
| Position tolerance in contact | roughly a **3 ft box** | Tuned |

> **Why two closure numbers.** One knot is 1.688 ft/sec, so 1–3 kt is
> 1.7–5.1 ft/sec — two to five times the ≈1 ft/sec figure. They are not in
> conflict; they are different phases. 1–3 kt moves you up from pre-contact,
> and you bleed it to about a foot a second in the last few feet. Printing
> only the first, as the card did until v1.74.0, asks a pilot to arrive at the
> boom at the approach rate.
| Progression | 1–3 s connections → a plug you can hold → a full transfer |
| Real-world benchmark | boom hookup **40.8 s**, drogue **85.0 s** |

### And an honest expectation

The figure the community converges on is **about thirty minutes a day for two
weeks**, with explicit warnings that marathon sessions make it worse. Telling
someone that is kinder and more useful than implying it should click today. The
card says so, and says "you are not the exception."

---

## Hardware: two corrections and a negative finding

A second research pass covered force feedback and VR, which the first missed.

### Force feedback: we looked, and there is nothing

You would expect a direct-drive base to help — no cam breakout at center means
cleaner micro-inputs. **Nobody has written down that it does.** The main ED FFB
experience thread covers helicopters, warbirds, stall buffet and trim at length
and contains zero mentions of refuelling or formation. The VPforce Rhino
threads, the Mudspike review, the Moza AB9 review and VPforce's own DCS settings
page — nothing. The one thread asking the question directly ends with the
community diagnosing the pilot's **tanker speed**, not his stick.

So the card says: if you have one, good; if you are buying one to fix your
refuelling, that is not a supported reason.

**One hole in that search, stated because it changes the strength of the
claim.** Reddit was not reachable from the research environment — three
different query shapes returned shopping results, and direct fetches are
refused for URLs that have not appeared in conversation. **r/hoggit is one of
the largest DCS discussion venues and none of it was read.** So the defensible
claim is "no evidence in everything we could search", not "no evidence
anywhere", and the card now says exactly that. Closing this gap needs someone
to paste r/hoggit URLs in, at which point they can be fetched and read.

### But FFB makes our own curve advice wrong

This is the correction that matters. VPforce's documentation is categorical:

> "If you have axis curves or saturation settings in the DCS axis tune configs,
> you will need to disable those as both curves and saturation are incompatible
> with FFB."

The reason is structural. On a spring stick DCS only **reads** position, so a
curve is a harmless remap. On FFB, DCS also **writes** position — it commands a
physical stick offset to represent the trim point — and a curve desynchronises
"where DCS is pushing the stick" from "what deflection DCS thinks that means."

The FFB substitutes, reasoned from the effect definitions rather than quoted
(nobody has published AAR-specific FFB settings):

- **Spring gradient up** — more force per degree, so a smaller displacement for
  the same hand force. The honest substitute for a curve.
- **Damping up** — resistance proportional to how fast you are moving the stick,
  so it suppresses the fast panicky input and leaves the slow deliberate one
  alone. Rate-dependent gain reduction, which is arguably *better* than a curve.
- **Not friction** — it adds a breakout you must overcome, recreating the
  step-input problem you were escaping.
- **Not inertia** — it adds lag to reversals, and reversals are the whole task.

And a real gotcha: **on FFB the stick physically moves to the trim point.** Trim
*before* pre-contact, never at the boom.

### VR helps, but not where people say

VR is genuinely better for this and the mechanism is stereo depth — which has a
range limit, because depth resolution falls off as the **square** of distance.

The US Navy's simulator requirement (SBIR N251-008) asks for accurate depth
judgement **between 5 and 100 ft**. That is the defensible number:

| Range | Depth resolution, typical observer |
|---|---|
| 20 ft | ~8 cm |
| 50 ft (contact) | ~50 cm |
| 100 ft | ~2 m |
| **1 nm astern** | **~7.7 km** |

So **VR does not help you find the tanker or fly the rejoin.** Out there you use
angular size, perspective and closure rate — all available on a flat screen. VR
helps in the last hundred feet, which happens to be the hard part.

The strongest corroboration is not from the sim community: the **KC-46 Remote
Vision System** — real boom operators working from camera displays instead of a
window — has spent a decade failing on exactly this, and a Wright State study of
stereo displays for it found stereo and hyper-stereo *improved* refuelling
performance.

**VR tips that are actually VR-specific:** hold your head still at contact (head
movement is its own input, and flat-screen pilots have been known to switch head
tracking off for the plug — you can't); don't zoom at the boom, because zoom
changes the projection and corrupts the stereo cue you came for; DCS's VR "IPD"
is world scale, not eye spacing, and community values run 45–55; approach about
45° off for better closure perception; the right basket is harder because you
lose the tanker's references.

**And one known DCS defect, so pilots stop blaming their eyes:** the KC-135's
director lights *are not lights*. They are a pre-rendered texture — confirmed by
an ED beta tester, reported since 2021, still open. A community mod brightens
them. A real KC-135 receiver instructor notes in the same thread that they are
hard to see in the airplane too.

### The thing nobody talks about: the throttle

Consistent across sources and under-appreciated — **the bottleneck is usually
throttle resolution, not stick precision.** A separate throttle unit wins on
travel alone. Tune out the afterburner detent bump near 90% on Warthog-style
throttles; it is a sensitivity discontinuity in the middle of the task. Use
speedbrake to move the engine into a more responsive RPM band. And **feet
completely off the rudder pedals** — one instruction, no dissent found anywhere.

---

## What we built

### `missiongen/aar.py` — six tankers, each on a track its receivers can fly

| Tanker | Type | Track | For |
|---|---|---|---|
| **KC-135** | boom | 300 KIAS / 20,000 ft | F-16, F-15, A-10, **F-4E** |
| **KC-135MPRS** | drogue | 250 KIAS / 18,000 ft | probe jets, land-based |
| **KC-130** | drogue | 210 KIAS / 12,000 ft | Hornet, Harrier, helicopters |
| **S-3B Viking** | drogue | 230 KIAS / 12,000 ft | carrier organic, modern |
| **KA-6D / A-6E buddy** | drogue | 250 KIAS / 15,000 ft | carrier organic, Cold War |
| **IL-78M** | drogue | 250 KIAS / 18,000 ft | red side |

Each entry carries a `basis` field saying where its number came from. These are
**tuned operating points**, chosen so the receiver can hold contact in DCS and
sitting inside the real band — not quotations from a document, because no
document in our source library states AAR airspeed bands. That is a weaker kind
of claim than the BFM perches and it is labelled as one.

**Matching is automatic and never silently wrong.** Boom receivers get boom
tankers; probe receivers get drogues. A boom tanker behind a probe jet is worse
than no tanker at all — the mission builds, the tanker flies, the pilot joins,
and nothing happens, which reads as "the tool is broken." Off the boat you get
the air wing's own tanker: a Viking in the modern era, an Intruder with a buddy
pack in the Cold War. Ask for something incompatible and you get a **warning**,
not a silent swap.

An aircraft that cannot refuel at all gets **no tanker and a warning**. The
first version of that warned "no tanker placed" and then placed one through the
legacy fallback — a warning saying the opposite of the file, which is exactly
what `tests/test_library_promises.py` exists to stop.

### The time problem, solved by deleting the commute

Refuelling is thirty seconds of skill wrapped in half an hour of commuting, and
the commuting teaches nothing. So the AAR cards start you **in the pre-contact
position: 1 nm astern the tanker, 1,000 ft below, already at his speed.**

Below, always — the escape from a bad approach is down, and the tanker is the
one thing up there you must not climb into.

### The progression

| Card | What it is |
|---|---|
| **Tanker Time** | Open practice. Start at the boom, plug until bored. |
| **AAR 1 — The Join-Up** | Arrive at observation and *sit there*. **Do not plug.** Pass = 30 s hands-steady on the wing. |
| **AAR 2 — Pre-Contact and Contact** | The rep: contact → fuel → back out → stabilise → again. Pass = three consecutive contacts, ≤1 back-out each. |
| **AAR 3 — Probe and Drogue** | A genuinely different task, so it gets its own ride rather than a paragraph. |
| **AAR 4 — Night Tanking** | Same procedure, no horizon, cues gone. |
| **AAR — Off the Boat** | S-3B or KA-6D. No cat shot, deliberately. |

AAR 1's "do not plug on this ride" is the single most important design decision
in the set, and it comes straight from the research: **the biggest reason people
cannot refuel is that they went for contact before they could hold formation,
and then practiced being out of control.**

---

## What we did not do

- **No universal curve number.** See above — it would be confidently wrong for
  most readers.
- **No claim that these speeds are doctrine.** They are tuned; `basis` says so.
- **No scripted in-cockpit coaching.** Rob mentioned Jester's cues in the F-4E,
  and that is the right model — a voice that tells you "you're low, you're
  aft." We cannot generate that. The F-4E does get a boom KC-135 so Jester's own
  cues work, but the coaching in our cards is a kneeboard, not a crew member.
- **No automatic pass/fail scoring.** The criteria are stated so the pilot can
  self-grade; DCS gives us no hook to measure boom contact time.

---

## Sources

- [ED — Air-to-air refueling tips needed](https://forum.dcs.world/topic/232602-air-to-air-refueling-tips-needed/) · [Air refueling axis curvature and joystick model](https://forum.dcs.world/topic/211779-air-refueling-axis-curvature-and-joystick-model/) · [AV-8B in-flight refueling](https://forum.dcs.world/topic/186378-in-flight-refueling-dying-of-frustration/) · [DCS Fuel School (F/A-18C)](https://forum.dcs.world/topic/187548-complete-air-to-air-refuelling-tutorial-dcs-fuel-school-fa-18c/) · [AAR training missions](https://forum.dcs.world/topic/352861-air-to-air-refueling-training-missions/)
- [Falcon BMS — Air-to-air refueling tutorial](https://forum.falcon-bms.com/topic/346/air-to-air-refueling-tutorial) (the deepest written AAR corpus in the sim community)
- [Mudspike — F/A-18C AAR tips](https://forums.mudspike.com/t/dcs-f-a-18c-hornet-air-to-air-refueling-tips/6221)
- [ATP-56 Air-to-Air Refuelling](https://bloximages.chicago2.vip.townnews.com/militarynews.com/content/tncms/assets/v3/editorial/5/ca/5ca69442-c74c-11e8-97a8-fff1004e63f5/5bb528e613e83.pdf.pdf) — the zero-closure gate before clearance to contact
- [Stephenson, *Air Refueling Receiver*](https://media.defense.gov/2017/Dec/29/2001862128/-1/-1/0/T_STEPHENSON_AIR_REFUELING_RECEIVER.PDF) — closure rates
- [CARI study](https://ojs.library.okstate.edu/osu/index.php/CARI/article/download/7559/6960/15150) — boom 40.8 s vs drogue 85.0 s hookup times
- [Pilot-induced oscillation](https://en.wikipedia.org/wiki/Pilot-induced_oscillation) · [Porto — PIO](https://ryanporto.com/wiki/aerospace/pilot-induced-oscillations/) — the phase-lag and gain explanation
- [Hagerty — a fighter pilot breaks down aerial refueling](https://www.hagerty.com/media/opinion/on-the-98th-anniversary-of-aerial-refueling-our-tame-fighter-pilot-breaks-it-down/) — the 3 ft box

**Hardware pass:**

- [VPforce — game-specific FFB settings](https://docs.vpforce.eu/rhino/game-specific-ffb-settings-tips-and-tricks/) (curves incompatible with FFB) · [Using the Rhino](https://docs.vpforce.eu/rhino/using-the-rhino/) (spring/damper/friction/inertia definitions)
- ED Forums: [My experience with FFB](https://forum.dcs.world/topic/272322-my-experience-with-force-feedback-in-dcs/) · [AAR with Rhino/FFBeast](https://forum.dcs.world/topic/351163-has-anyone-able-to-get-full-tank-air-refuel-using-either-rhino-or-ffbeast-ffb-stick/) · [F-4E FFB settings](https://forum.dcs.world/topic/349269-force-feedback-settings-discussion/) · [FFB and autopilot (Viggen bug)](https://forum.dcs.world/topic/385148-ffb-and-autopilot/) · [Refueling — precision flying](https://forum.dcs.world/topic/71330-refueling-precision-flying/) · [Throttle during AAR](https://forum.dcs.world/topic/216595-how-do-manage-the-throttle-during-air-refueling/) · [AAR the Hornet in VR](https://forum.dcs.world/topic/380238-any-suggestion-to-air-refuel-the-18-in-vr/) · [KC-135 PDI lights too dim](https://forum.dcs.world/topic/277509-kc-135-aar-pdi-lights-too-dim/) · [KC-135 PDL lighting](https://forum.dcs.world/topic/371774-kc-135-pdl-lighting/)
- [Navy SBIR N251-008](https://www.navysbir.com/n25_1/N251-008.htm) — the 5–100 ft depth requirement
- [Wright State — stereoscopic RVS displays](https://corescholar.libraries.wright.edu/etd_all/1310/) · [AFRL KC-46 RVS](https://afresearchlab.com/technology/kc-46-remote-vision-system-rvs/) · [Air & Space Forces — Eyes On the Boom](https://www.airandspaceforces.com/article/eyes-on-the-boom-re-visioning-the-kc-46/)
- [Stereoscopic acuity](https://en.wikipedia.org/wiki/Stereoscopic_acuity) — the range-squared falloff
- [YoYo's KC-135 improved PDL lights mod](https://files.digitalcombatsimulator.com/en/files/3332394/)
