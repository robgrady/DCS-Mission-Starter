# 70th Tactical Fighter Squadron — coached B'NAI, WSO recording sheet

*Generated from `missiongen/wk_brief.py` and `missiongen/wk_coach.py` — the same two lists the mission's triggers are built from. Do not hand-edit: run `scripts/build_wk_voiceover_sheet.py` instead, or the filenames here and the filenames the mission asks for will drift apart.*

## Where the files go

```
missiongen/data/wk_brief/vo/     <- the brief pages
missiongen/data/wk_coach/vo/     <- the cues in the air
```

Drop a WAV in and the next build wires it to its cue. Drop nothing in and that cue still shows its picture and prints its text — the line is optional, one line at a time, so a half-recorded set is a perfectly good build.

## How to record them

- **Format.** WAV, mono, 44.1 kHz, 16-bit. DCS will play anything it can decode, but that is what the rest of the product's audio is and matching it means one fewer thing to rule out when a cue is silent.
- **Level.** These play as a COCKPIT sound, not a radio transmission — the WSO is a foot behind your head, not on a frequency. No radio filter, no squelch, no compression artifacts. Dry and close.
- **Length — the CUES only.** Keep every cue take under four seconds. Its picture holds for 6 seconds and its text for 8, and a call still talking after the moment it describes has passed is worse than no call. The BRIEF pages have no such limit: they stay up until the pilot presses SPACE.
- **Takes.** Record them in any order. The mission checks each file separately, so thirteen sessions of one line each works exactly as well as one session of thirteen.

## Part one — the brief

6 pages, played before the sortie starts while the pilot's controls are locked. These are LONGER than the cue lines and the four-second rule does not apply to them — a page stays up until he presses SPACE, so take the time the sentence needs.

### B1. `wk_brief_situation.wav`

> You are a new wingman in the 70th Tactical Fighter Squadron, the White Knights, flying F-4E Phantoms with tail code MY under the callsign REX — on the sim's radio, Enfield. From the tenth of July to the third of October, nineteen eighty, twelve of the squadron's aircraft deployed to Cairo West in Egypt for exercise Proud Phantom. That is where you are sitting. Your squadron commander is Lt Col Barry M. Meuse.

- **On screen:** the page headed **SITUATION**.
- **Delivery:** Unhurried, slightly formal. This is the opening of a mass brief and everybody in the room already knows most of it.

### B2. `wk_brief_target.wav`

> Your target is on the Egyptian range, thirty miles down the run-in axis. There is an SA-6 in this mission. That is not scenery — the attack you are about to fly was designed to survive exactly that missile, by an air force that had to solve it in a real war, and the whole shape of the thing only makes sense once you know what it is avoiding.

- **On screen:** the page headed **TARGET AND THREAT**.
- **Delivery:** Level, then harden on the SA-6 sentence. That is the one fact in the brief that explains the whole shape of the attack.

### B3. `wk_brief_attack.wav`

> The B'NAI. Designed by the Israelis in the 1973 Mid East war to improve visual cross-coverage during a pop up attack in an SA-6 environment. Because of this greater SAM threat, the SA-6 was considered a primary threat and MIGs were secondary. You will fly it as a 2 to 3 mile in-trail formation. Approach the IP at nearly ninety degrees angle off, with lead on the side of the formation nearest the target. At the IP lead turns inbound and you turn away, then back in behind him. From that point to the pop, nobody is covering your six.

- **On screen:** the page headed **THE ATTACK**.
- **Delivery:** Instructional. Slow down on the IP turn — it is the sentence he will get wrong first.

### B4. `wk_brief_pop.wav`

> Off the low angle low drag sheet. Pull up 11,400 feet from the target and climb 30 degrees. Roll in at 4,200 feet — that is below your apex of 5,700, and it is not a misprint, because you begin the pull-down at roll-in and the airplane coasts up to apex as the nose comes through. Release at 2,000 feet, 15 degrees, 500 knots, 121 mils. Six Mark eighty-twos, low drag.

- **On screen:** the page headed **THE POP**.
- **Delivery:** Numbers, clearly, with a beat between them. The roll-in-below-apex aside deserves its own pace; it is the thing pilots assume is a typo.

### B5. `wk_brief_wingman.wav`

> Your number two is in YOUR flight, on your wing. He starts when you start, taxis when you taxi, and forms up after takeoff — no separate schedule, no airplane flying the mission without you. The two-ship geometry on the card is yours to fly; when you want his bombs on the target, send him with the radio menu — Flight, Engage. The doctrine is unchanged: one aircraft attacks while the other stays low covering his six, and off target you both keep turning until you are on egress heading or line abreast, whichever matters more at the time.

- **On screen:** the page headed **YOUR WINGMAN**.
- **Delivery:** Deliberate. Every clause here is somebody covering somebody.

### B6. `wk_brief_coaching.wav`

> 13 calls, one at every decision, each with the squadron's own drawing and a ring around where you are. The route itself is marked with training gates — green boxes over each waypoint, drawn the moment you take the airplane. The cues cannot see your dive angle or your mil setting — a trigger reads position, altitude and speed, and that is the entire list. About 20 seconds after the egress point the whole sequence re-arms, so come back round to the IP and fly it again. Source for everything you have just heard: 70 TFS Conventional Tactics, 27 Jan 1980. You have the airplane.

- **On screen:** the page headed **HOW THIS RIDE COACHES YOU**.
- **Delivery:** Warmer, and end on 'You have the airplane' as a handover, not as a sign-off. That line is the moment his controls come back.


## Part two — the cues in the air

13 lines, in the order you hear them.

### C1. `wk_bnai_lowlevel.wav`

> Level at three hundred, four hundred knots. Lead's on the target side of the formation.

- **On screen:** the ring on **run in**, with **300 FEET** across the bottom.
- **Delivery:** Settled, unhurried. Nothing is happening yet and he wants it to stay that way.

### C2. `wk_bnai_trail.wav`

> Set your trail. Two to three miles. IP coming up ninety left.

- **On screen:** the ring on **split**, with **TRAIL 2-3** across the bottom.
- **Delivery:** Businesslike. This is housekeeping before the work starts.

### C3. `wk_bnai_ip.wav`

> IP. Lead turns inbound now. You turn away, then back in behind him.

- **On screen:** the ring on **split**, with **TURN INBOUND** across the bottom.
- **Delivery:** A shade quicker. The turn is happening now, not in a moment.

### C4. `wk_bnai_runin.wav`

> Run-in. No cross coverage from here to the pop. Eyes out.

- **On screen:** the ring on **run in**, with **NO COVER** across the bottom.
- **Delivery:** Flat and quiet. This is the line that should make him uncomfortable — nobody is watching your six.

### C5. `wk_bnai_pup.wav`

> Pull-up point. Pull to thirty degrees. Now.

- **On screen:** the ring on **pup**, with **PULL UP — 30** across the bottom.
- **Delivery:** Sharp. This is a cue with a two-second window and the whole attack hangs off it. Loudest line on the sheet.

### C6. `wk_bnai_rollin.wav`

> Roll-in. Roll and pull, target off the nose.

- **On screen:** the ring on **rollin**, with **ROLL IN** across the bottom.
- **Delivery:** Urgent, but not a shout. He is telling you where to look.

### C7. `wk_bnai_apex.wav`

> Apex. Nose coming through — find the target.

- **On screen:** the ring on **apex**, with **APEX** across the bottom.
- **Delivery:** Half a beat calmer. The airplane is doing the work here.

### C8. `wk_bnai_track.wav`

> Track point. Wings level, one twenty-one mils, five hundred knots.

- **On screen:** the ring on **track**, with **TRACK** across the bottom.
- **Delivery:** Clipped, one parameter at a time, like reading a checklist with the target in the windscreen.

### C9. `wk_bnai_release.wav`

> Two thousand feet. Pickle, pickle.

- **On screen:** the ring on **track**, with **PICKLE** across the bottom.
- **Delivery:** The only line that repeats a word. Say it twice because that is how it is said.

### C10. `wk_bnai_pullout.wav`

> Off target, turning recovery. Get to the deck and take the egress heading.

- **On screen:** the ring on **pullout**, with **OFF AND DOWN** across the bottom.
- **Delivery:** Hard and downward. Get out.

### C11. `wk_bnai_twos_pass.wav`

> Two is in from the other side. You are covering his six now.

- **On screen:** the ring on **egress**, with **COVER TWO** across the bottom.
- **Delivery:** Alert. You have gone from attacker to cover and the job changed completely.

### C12. `wk_bnai_egress.wav`

> Keep the turn in until you are on egress heading or line abreast, whichever matters more right now.

- **On screen:** the ring on **egress**, with **LINE ABREAST** across the bottom.
- **Delivery:** Level again. The work is done and the decision is a judgment call, so it should sound like one.

### C13. `wk_bnai_reattack.wav`

> Good pass. Come back round to the IP and we will run the whole thing again.

- **On screen:** the ring on **run in**, with **AGAIN** across the bottom.
- **Delivery:** Warm. This is the only line on the sheet that is allowed to sound pleased.

## What happens after the last line

About 20 seconds past the egress point the sequence re-arms from **IP**, so lines 3 onward play again on every re-attack. Lines 1 and 2 are heard once per sortie; the rest are heard as many times as the pilot flies it. Record them like something you would not mind hearing eight times.
