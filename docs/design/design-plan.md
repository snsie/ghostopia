# Spirit Realm Survival Game — Design Plan

Nov 15, 2026 · Scott

## High concept

You play a cute basic ghost who wakes up in the Veil, a voxel afterlife built from the memories of the dead, and you grow by scaring the living people whose world bleeds through into it. Every scare earns Fright, which levels you up along the path that matches how you scared them. Every scare also makes the living remember, and remembrance is what keeps the land, your walls, and your graveyard from eroding into void.

The tone is cute-spooky with a melancholy undertone: a chunky, hand-painted cartoon look (soft shadows, glowing shaders, expressive faces, as on the Basic Ghost board) wrapped around a world made of half-remembered lives.

## Design pillars

- **Scare to grow.** Progression comes from scares, not kills. Haunting objects, possessing things, and telekinesis each reward a different play style and level a different path.
- **Memory is both the resource and the threat.** Terrain, buildings, and defenses hold together only while someone remembers them. Neglect is what summons enemies.
- **Build a home for the dead.** Mausoleums and gravestones are your base, your workforce, and your respawn point all at once.
- **Folklore is the rulebook.** Salt, iron, bells, running water, thresholds, and straight spirit roads work the way players already half-know from ghost stories.
- **Minecraft feel.** Chunky voxels, a procedural open world, tool tiers, free-form building, a wiring system for contraptions, and a day/night rhythm (inverted: night is your time).

## The world: the Veil

The Veil is a procedurally generated voxel world stitched together from memories. Places the living still think about are vivid, solid, and populated by living people who can't normally see you. Places nobody remembers fade, crumble, and eventually fall into the Hollow, a void that eats unremembered chunks.

**Memory voxels.** Every chunk has a Remembrance value. It decays slowly over time and is restored by scares nearby (the living tell stories about the haunting), by tended graves, by residents living there, and by blocks crafted from memory. As Remembrance drops, blocks desaturate, then flicker, then crumble from the edges inward. Mining any natural block can release a memory fragment: a one-line vignette or short audio clip from someone's life, collected in a journal and used as a crafting material.

**Why the living matter.** The living are real people in a parallel mortal world that bleeds through into the Veil, not echoes or memories, and they are the only source of new remembrance in the world. Scaring them is how you level up, and it is also how you keep your corner of the afterlife from dissolving. That single link ties progression, survival, and base-building together.

| Biome | Memory flavor | The living here | Key resources | Danger |
|---|---|---|---|---|
| Open Plains | A half-remembered old farming village | Superstitious villagers: scare easily, hang charms quickly | Fiber, wood, graveyard dirt | Tier 1: weak angry mobs |
| Suburban Block | A 1970s suburb rendered slightly wrong (streets that loop, rooms that repeat) | Families and skeptical neighbors | Scrap, hauntable furniture, appliances | Tier 2 |
| Urban | A vivid present-day city, heavily remembered | Crowds, skeptics, and Ghost Hunters with detection gear | Advanced scrap, electronics | Tier 3: hunter raids |
| Hellscape | Where regret pools and memories burn | None; demons hold it | Hellstone, ember | Tier 4: demon strongholds and invasions |

Smaller memory pockets can appear between biomes as rare landmarks: a foggy battlefield, a childhood beach where the sand is the wrong color, a hospital corridor that never ends. These hold dense memory fragments and unique residents.

Beneath all of it lies the **Underveil**, where land the Hollow eats sinks and the forgotten dead live in warring clans (see The Underveil).

## Core gameplay loop

Scaring the living sits at the center of the loop: it is the only source of Fright for leveling and the main source of Remembrance that keeps your land intact.

A typical night: gather near home at dusk, check on your graves, drift to a living town to scare, then return before daylight with Fright to spend. Scaring too hard raises Heat and skipping chores breeds neglect, and both bring attacks that pay out relics and new residents once defended.

## Scaring and progression

Scaring the living is the only way to earn Fright, and the method you use decides which path it levels. Every scare also feeds a shared Presence level that raises your HP, scare radius, and how long you can stay manifested.

### The scare: read, build, break

Every scare plays as three beats, so it works like a small puzzle with a timing payoff rather than an ability you spam.

**Read the target.** Every living NPC has a personality, a Belief level, and a hidden fear (the dark, dolls, mirrors, being alone, loud noises). Players learn fears by observing: drifting close to overhear muttered thoughts, watching what an NPC avoids, or peeking into their memories. Exploiting a target's specific fear multiplies the payout. Skeptics have low Belief and shrug off small scares, but breaking one turns them into a believer who remembers you far longer.

**Build the tension.** Small acts (a creak, a flicker, a door drifting open) raise an Unease meter, and the NPC visibly escalates: glancing over a shoulder, calling out "hello?", clutching a candle, walking faster. The skill is pushing Unease to the top without tipping them over too early. Push too hard and they bolt for a weak payout, or get suspicious and fetch salt or a lantern, which makes them harder to scare. Like the tension in a fishing minigame, there is a sweet spot, and finding it is the fun.

**Break them.** The big scare lands when tension peaks and the target is vulnerable: alone, back turned, standing in the doorway you rigged. The reaction is big and funny, with an exaggerated leap, a flying hat, a dropped lantern, a scream that echoes through the house, and a brief slow-motion beat. Each scare is graded like a style score (Spooked, Terrified, Legendary), so players chase better execution rather than more volume. Fright is paid to every path whose abilities were used in the scare.

### Keeping the 50th scare fresh

- **Chain reactions:** a fleeing villager can trip into your rigged wardrobe, wake the dog, and panic the whole household. Combined with Wisp Wiring, players build Rube Goldberg haunts, which is where the Minecraft redstone instinct pays off.
- **Combos:** chaining abilities from different paths in one scare grants bonus Fright to each path used.
- **Towns that adapt:** villages remember your tricks, hang charms, and salt the doors you used last time, forcing new approaches. Adaptation is the scaring equivalent of enemies getting tougher.
- **Failure that's entertaining:** a botched scare doesn't just lose Fright. The villager might laugh it off and grow braver, or spot you and summon a Ghost Hunter, so mistakes create new situations instead of dead ends.
- **A legend system:** each town builds a myth about you from your signature style ("the Rocking Chair Ghost of Millbrook"), retold in taverns and remembered by NPCs. Witnesses spread it faster, and a growing legend raises Remembrance across the area.

**Example.** The widow at the mill fears dolls. You overhear her muttering about her late daughter's doll, possess it, and leave it in a different chair each time she turns around. Her Unease climbs as she starts checking every corner. When she reaches for her candle, you snuff it with Flicker and the doll drops from the shelf at her feet: a Legendary scare from three cheap abilities used well.

Scaring too much in one area raises Heat, which eventually sends Ghost Hunters after you (see Defense).

### Path 1: Haunting (Traps tech path)

You bind yourself to objects and furniture, set them up, and let them do the scaring. This path levels whenever a haunted object breaks someone's Nerve, and it doubles as your base-defense tree.

| Level | Unlock | What it does |
|---|---|---|
| 1 | Creak | Haunt doors and floorboards to make noise as someone passes |
| 2 | Flicker | Haunt candles and lamps to dim or snuff them |
| 3 | Haunted Furniture | Rocking chairs that rock, wardrobes that slam, portraits whose eyes follow |
| 4 | Wisp Wiring | Link haunted objects with spectral wire and pressure triggers, like redstone |
| 5 | Cursed Heirloom | A haunted trinket follows its owner home and scares them remotely |
| Capstone | Haunted House | Bind a whole building into one trap network you can trigger in sequence |

### Path 2: Possession

You slip inside things and drive them. This path levels whenever a possessed creature, object, or person breaks someone's Nerve.

| Level | Unlock | What it does |
|---|---|---|
| 1 | Chill | Pass through a person to give them a cold shiver |
| 2 | Familiar | Possess cats, crows, and dogs to scout and act strangely |
| 3 | Puppet | Possess dolls, scarecrows, and suits of armor and walk them around |
| 4 | Borrowed Body | Briefly possess a living person and make them do odd things in front of witnesses |
| 5 | Lingering Host | Leave a possessed object running on its own while you move on |
| Capstone | Hostile Takeover | Possess enemies in raids and dungeons and turn them on their allies |

### Path 3: Telekinesis (Poltergeist)

You move the world without touching it. This path levels whenever thrown, lifted, or moved objects break someone's Nerve, and it is also the strongest building utility.

| Level | Unlock | What it does |
|---|---|---|
| 1 | Nudge | Slide small items and tip over cups |
| 2 | Toss | Throw objects at walls and across rooms |
| 3 | Lift | Carry furniture and place blocks at range |
| 4 | Hold | Pin doors shut and freeze people in place |
| 5 | Whirl | Spin every loose object in a room into a vortex |
| Capstone | Tantrum | A room-scale poltergeist event that breaks everyone inside |

### Ghost evolution

You start as the Basic Ghost (HP 10, Spectral). Reaching level 3 in a path changes your look, and mixing paths unlocks hybrid forms, while staying cute throughout.

- **Haunter** (Haunting): carries a little lantern and trails chains; bound objects glow faintly near you.
- **Shade** (Possession): darker and blurrier at the edges, briefly takes the outline of whatever it last possessed.
- **Poltergeist** (Telekinesis): small debris orbits it constantly and it crackles when excited.
- **Hybrids**, such as Haunter plus Poltergeist, combine the visual traits and grant one cross-path ability.

## Ghost physics

Being a ghost changes how you move, carry, and fight, and the rules are consistent enough that players can plan around them.

- **Phasing:** you pass through soft blocks (wood, dirt, glass, plants) but not iron, salt-cured stone, or blessed blocks. Your own builds can be flagged phase-through for residents and solid for enemies.
- **Drifting:** you hover a few blocks up, glide instead of falling, and take no fall damage. Climbing higher costs Ectoplasm.
- **Weightlessness:** the Basic Ghost can only hold spectral items, like the spectral tools on the gathering board. Moving physical objects needs Telekinesis, Possession, or worker ghosts, which makes all three valuable early.
- **Inverted day and night:** daylight from the living world slowly drains you, so night is your working time and day is when you shelter in the mausoleum or work underground.
- **Running water:** you can't cross it unaided until you build a bridge or unlock a crossing ability, following the folklore rule.
- **Visibility:** the living see you only when you manifest to scare. Ghost Hunters can see you anytime with their gear.
- **Respawn:** at zero HP you scatter back to your mausoleum and drop some carried Fright Essence where you fell.

## Gathering and crafting

Physical materials come from three spectral tools, and intangible materials come from scares and memories; the best items need both.

Physical gathering follows the gathering board: one tool per node type, upgraded in tiers to reach harder nodes.

| Tool | Node | Yields | Upgrade path |
|---|---|---|---|
| Scythe | Weeds and grave growth | Fiber, wood, grave moss | Tiers I to IV: faster cutting, rare plants |
| Shovel | Graveyard dirt | Dirt, bones, buried trinkets | Tiers I to IV: deeper digging, sealed coffins |
| Sledgehammer | Eerie ore | Spectral stone, iron, crystal shards | Tiers I to IV: harder ore, hellstone |

### Intangible materials

- **Fright Essence:** bottled screams left behind by a broken scare; the main currency for abilities and wards.
- **Memory fragments:** released when you mine natural blocks; collectible in your journal and refined into emotions.
- **Ectoplasm:** produced by worker ghosts and gravestones; fuels drifting, Ethereal building, and repairs.
- **Refined emotions** (made from memory fragments at the Memory Loom): Nostalgia strengthens buildings against erosion, Grief powers wards and boundaries, Regret makes powerful dark gear but attracts demons, and Joy is rare and needed for Ethereal tier and for helping souls move on.

### Crafting stations

- **Spectral Workbench:** tools, tool upgrades, furniture, and building blocks.
- **Memory Loom:** refines memory fragments into emotions and weaves memory-forged blocks.
- **Ritual Altar:** salt lines, bells, blessed blocks, epitaphs, and other folklore defenses.

## Graveyard base

Your graveyard is base, workforce, and respawn point in one, and keeping it tended is what keeps it safe.

- **Mausoleum:** your home, respawn point, and storage hub. Upgrading it widens your consecrated ground, the area where you can build and where residents work.
- **Gravestones:** each one adds +1 ghost supply, raising your worker cap. Worker ghosts spawn from graves and gather, haul, and build automatically, and graves produce Ectoplasm over time.
- **Named residents:** completing a set of memory fragments about one person lets you give them a grave. Residents bring a skill from their life (a blacksmith speeds tool upgrades, a gardener grows grave moss) and want a resting place that suits them.
- **Tending:** graves need weeding, candles, and offerings. A neglected resident becomes Restless and works less; left longer, they become a Forgotten Soul that attacks your base.
- **Epitaphs:** carved on gravestones and walls, they raise local Remembrance and make nearby blocks tougher.

You can build freely block by block, or place modular blueprints like the mausoleum shown under construction on the concept board.

**Building tiers.** Higher tiers are tougher against raids and slower to erode when Remembrance falls.

| Tier | Material | Durability | Erosion resistance | Cost |
|---|---|---|---|---|
| 1: Rough Wood | Timber and scrap | Low; easily damaged | Low | Wood, fiber |
| 2: Stone | Cut spectral stone | Medium; resists basic raids | Medium | Stone, mortar |
| 3: Metal | Riveted iron and steel | High; withstands advanced raids | Medium; also blocks spirit phasing | Iron, scrap metal |
| 4: Ethereal | Floating ghostly structures | Very high; auto-repairs | Highest; repairs itself from local Remembrance | Crystal shards, Ectoplasm, Joy |

## Defense

Attacks are not on a timer; each threat is triggered by something the player did or neglected, and defenses are built from folklore rules, memory, and your own haunting abilities.

### Threats and what triggers them

| Threat | Trigger | Behavior | Best counters |
|---|---|---|---|
| Forgotten Souls | Neglected graves, yours or abandoned ones nearby | Travel straight spirit roads toward the grave that wronged them | Salt lines, mazes, tending; or bind and re-bury them as residents |
| The Hollow | A chunk's Remembrance hits zero | Erodes blocks from the edges inward, no army to fight | Remembrance, memory lanterns, Nostalgia blocks, Ethereal tier |
| Ghost Hunters | Too much Heat from scaring in suburbs and cities | Night raids with detection gear, salt guns, iron nets, and spirit jars | Haunted traps, possessing their gear, telekinetic disarms |
| Demons | Demon portals near your territory, and heavy use of Regret gear | Hordes that ignore salt and cross running water | Iron, bells, Ethereal walls, closing portals |

Bigger, louder graveyards give off more Resonance, which draws more of every threat, so expansion is always a trade-off.

### Folklore boundaries

| Boundary | Stops | Weakness |
|---|---|---|
| Salt line | Forgotten Souls and lesser spirits | Washes away in rain; the Hollow dissolves it |
| Iron fence | Wraiths and strong spirits | Also blocks your own phasing and your residents |
| Running water (moat) | All spirits | Demons and Ghost Hunters cross freely |
| Bell tower | Stuns everything nearby when rung | Needs a haunted or possessed ringer; long cooldown |
| Threshold | Enemies can't enter a doorway uninvited | Broken if the door is destroyed |
| Mirror | Redirects or traps a spirit that looks into it | Shatters after a few uses |

**Spirit roads.** Hostile spirits travel in straight lines and are slow to turn, so zigzag walls, offset gates, hedge mazes, and spirit screens (a short wall just inside a gate) are real defensive architecture. In code, this is pathfinding with a heavy penalty on turns.

**Memory-backed walls.** Block HP scales with local Remembrance. Walls carved with epitaphs, buildings tied to a resident's story, and areas near tended graves hold longest, while forgotten corners fail first. Memory lanterns burn memory fragments to push back the Hollow, at the cost of material you might need elsewhere.

**Haunting your own defenses.** Everything from the scare paths works at home. Haunted furniture and Wisp Wiring become traps, possessed statues and suits of armor become guards, and telekinesis lets you hurl objects or hold a gate shut mid-raid. Wind chimes act as early warnings.

## Dungeons

Dungeons run from early crypts to late-game demon portals and are the main source of relics, rare materials, and memory sets that unlock new residents.

| Dungeon | Stage | Enemies and hazards | Rewards |
|---|---|---|---|
| Crypt | Early game | Skeleton raiders and archers (the dead who wouldn't let go of their bodies), rickety bone traps | Skeleton skulls, rusty swords, ancient relics, memory sets |
| Memory pocket | Mid game | A battlefield, beach, or hospital memory turned hostile; the environment itself is the puzzle | Dense memory fragments, unique residents, Nostalgia |
| Demon portal | Late game, hard | Fire demons, imps, and horde spawns; hellish smoke and lava | Demon horns, hellstone, ember |

Closing a demon portal permanently lowers demon raids in that region, which gives late-game players a reason to push outward rather than turtle.

## The Underveil

*Proposal, Nov 19, 2026. Everything here is a draft for Scott to accept, cut, or change; the calls that most need a decision are under Open questions.*

The Underveil is a vast underground afterlife beneath the surface Veil, where the forgotten dead have organized into clans and fight over the last scraps of memory. It gives the game a second half that the surface can't: politics, alliances, and large-scale battles, while keeping the rule that you win by scaring, not by killing.

### Where it comes from

When the Hollow eats an unremembered chunk, the chunk doesn't vanish; it sinks. The Underveil is where forgotten places and forgotten people end up: drowned chapels, collapsed barrows, whole streets nobody thinks about any more, wedged together in the dark. The dead who live there have no living to remember them, so they cling to **Memory Veins**, glowing seams where a sunken place still holds a little remembrance. A clan that holds veins stays whole. A clan that loses them fades. That is what every war down here is about.

This ties the Underveil to the surface loop in both directions. Neglect on the surface feeds the Underveil, and what happens below reaches back up (see Rewards).

### Getting there and getting around

- **Descents.** The three caverns under Millbrook (Fungal Grotto, Flooded Ossuary, Crystal Hollow) become the first descents. Each opens a passage to a different part of the Underveil, so the clans you already met in the slice are the clans you meet first.
- **Regions.** The Underveil is a network of large regions (cavern halls, fungal forests, flooded naves, barrow halls), each its own voxel map loaded on descent, joined by tunnels and underground rivers. Each region shows which clans hold it, how many veins it has, and whether a battle is happening there.
- **Daytime content.** Underground is always shaded, so day, which drains you on the surface, becomes Underveil time. Night stays scaring time above. That gives the day/night rhythm two halves instead of one long shelter.
- **Folklore still applies.** Running water still stops spirits, so **underground rivers are the borders** between clan territories, and fords and bridges are where battles happen. Salt, iron, and bells work as they do above.

### The clans

Five clans for the first Underveil run, covering every stance Scott described (two of them for the war), plus the existing Crystal Hollow sentinels as unaligned wildlife. All are original designs.

| Clan | Stance | Who they are | Home | Look and feel |
|---|---|---|---|---|
| **The Mycelial Kin** | Friendly | Gentle dead who let fungus grow through them so they'd never be fully forgotten; the Spore Keeper is one of them | Glowcap Warrens, through the Fungal Grotto | Teal mushroom caps for hats, spore lanterns, slow and kind |
| **The Drowned Parish** | At war | A whole congregation drowned when their chapel flooded; the Ferryman rows for them | The Drowned Nave, through the Flooded Ossuary | Waterlogged Sunday clothes, hymnals, bell ropes, orange votive glow |
| **The Barrow Host** | At war | Ancient chieftains and their warbands from burial mounds that sank whole | The Barrow Halls | Bronze lanterns, bone-and-iron crowns, earthen shields, war horns |
| **The Bonewardens** | Hostile | Skeletons who refused to let go of their bodies and despise ghosts for letting go (the Crypt's skeleton raiders are their outcasts) | Ossuary Deep | Bone armor, rattling patrols, cold white light |
| **The Velvet Wake** | Deceptive | An endless funeral party: charming, generous mourners who host every visitor | The Candle Court | Black lace, veils, candelabras, a feast that never ends |

**The Parish–Barrow war.** The Drowned Parish and the Barrow Host have fought for generations over the **Sunken Ford**, the richest Memory Vein in the upper Underveil. The war is uneven by design: the drowned are the one kind of dead that *can* move through water, so rivers are their highways, while the Barrow Host cannot cross them and fights for bridges and fords. Each side has a cause the player can sympathize with, and each will ask for help.

**The Bonewardens** attack ghosts on sight and raid the edges of other clans' land. They can't be befriended at first. Breaking enough of their patrols, or returning their outcasts' bones, opens a grudging truce (a stance change Scott may or may not want; see Open questions).

**The Velvet Wake** is friendly on the surface. They trade, offer shortcuts and gossip, and say kind things about you. In fact they feed on their guests' remembrance (staying too long at the feast quietly drains your Presence), and they sell your secrets to both sides of the war. Players expose them with the same **Read** skill used on villagers: tells such as a veil that slips, candles that burn downward, or a mourner whose story changes. Catching a lie and confronting them turns them hostile but frees the souls they've been keeping.

**Crystal sentinels** stay as they are in the slice: unaligned guardians that react to footsteps and defend crystal deposits without taking sides.

### Clan standing

Each clan has a **Standing** with you from Hated to Kin, shown in the journal. Helping, trading, returning lost memories to a clan, and winning its battles raise it. Scaring its people, siding with its enemies, and being caught in a lie lower it. The Velvet Wake shows a *false* Standing until you expose them, so the journal itself lies to you about them.

Standing gates trade, recipes, clan quests, safe passage through territory, and recruits.

### How a ghost fights a war: Resolve

The dead don't have Nerve the way the living do, but they have **Resolve**: how firmly they hold onto who they were. Every undead unit has Resolve, and a unit whose Resolve breaks routs: it drops its weapon, forgets why it was fighting, and flees toward home. Resolve is the only "health bar" that matters in a battle.

That makes battles a scale-up of the core scare instead of a combat system bolted on beside it:

- **Read.** Each clan fears something: the Drowned Parish fears silence (the bells stopping), the Barrow Host fears being nameless, the Bonewardens fear their bones being scattered, and the Kin fear fire. Learn it by watching and listening to the clan, as with villagers.
- **Build.** Your abilities scale to armies. *Haunting:* snuff a clan's braziers, ring or silence its bells, haunt its war drums so they beat out of time. *Possession:* possess a banner bearer and walk them off the field (their unit follows), or a captain (the Hostile Takeover capstone turns them on their own side). *Telekinesis:* drop stalactites, collapse a tunnel mouth, Hold a bridge gate shut.
- **Break.** When a flank's Resolve is low and its fear is in play, a big scare breaks it, and a breaking unit lowers the Resolve of the units around it. Routs spread like the chain reactions on the surface: one well-timed scare can collapse a whole battle line. Battles are graded like scares (Spooked, Terrified, Legendary) by how much you broke with how little.

**Ghosts can also do real damage** *(decided Nov 19, 2026)*. Every undead unit has a **Form** bar alongside Resolve, and taking either to zero takes it out of the fight:

| | Form hits zero | Resolve hits zero |
|---|---|---|
| What happens | Scattered: the unit bursts into wisps and drifts back to its clan's Memory Vein, out of this battle | Routed: the unit flees home and spreads fear to its neighbors |
| How you cause it | Spectral tool swings (the sledgehammer hits hardest, the scythe sweeps), BOO's burst at close range, telekinetic throws, collapsing rock | Clan fears, haunted war gear, possessed banner bearers and captains, big scares |
| Scale | One unit at a time, or a small group | Spreads through the crowd |
| Effect on the war | Costs the clan strength in this region | Costs the clan strength and Standing in this region, and lowers its Resolve in the next battle |

Both work, and they work together: damage lowers Resolve a little (getting hit by a ghost is frightening), and a shaken unit takes extra damage. Fighting is the reliable way through a skirmish or a Bonewarden patrol. Breaking Resolve is how one ghost swings a battle of hundreds. Under the "scare to grow" pillar, Fright still comes only from scares and breaks; scattering a unit pays materials (bone, bronze, drowned silver) rather than Fright.

Scattered undead aren't gone forever, since the dead can't die twice: they re-form at their vein over time, which is why holding veins decides wars. A clan that loses its veins can't re-form, and that is how a clan fades.

You never need to destroy hundreds of skeletons one by one. You can fight your way through a skirmish, but a ghost wins a war by finding the right moment to make an army forget why it came.

Ghosts take damage in battles from clan weapons and clan magic, so a battle is also dangerous for you. Wading into the middle of a melee is a bad idea; picking the moment and the spot is the skill. Tool tiers and gear from clan Standing raise your damage and defense down here.

### Battle scale

| Scale | Size | Where | What the player does |
|---|---|---|---|
| Skirmish | Up to about 40 total | Patrols, raids, ambushes, anywhere | Fight and scare individual undead up close |
| Battle | 100 to 300 per side | Contested border regions, fords, bridges | Break flanks, take out captains, shape the line |
| Great Battle | About 1,000 total across two or three clans | Scripted set pieces at turning points of a war (the Sunken Ford) | Sway the outcome of the war |

### Wars without you

Each clan's strength in each region is simulated all the time, even when you are on the surface. Every in-game hour, clans with more Memory Veins grow, clans that lost veins fade, and fronts move along region borders. A journal **war map** shows who holds what. Arriving at a region where a front is active turns those numbers into a real battle, and the result of that battle (or the simulated result if you stay away) changes the map.

Wars can end: a clan can be pushed back to its home region, sign a truce you broker, or (if nobody helps it) fade entirely, which leaves its memories for the Hollow and its territory for its neighbors.

### Rewards

- **Fright** still levels your paths: scares in the Underveil pay out to whichever paths you used, as on the surface.
- **Underveil materials:** Memory Vein shards (dense memory fragments), deepstone, glowcaps, drowned silver, barrow bronze, and bone.
- **Clan recipes and relics** from Standing: a Kin spore lantern, a Parish bell, a Barrow war horn, and other original relics for your displays.
- **Recruits.** A clan you are Kin with lets some of its dead come home with you. Giving one a grave on the surface makes them remembered again and turns them into a named resident with a skill from their clan. This is the main way to grow your graveyard beyond the village's own dead.
- **Holding the line below.** Memory Veins held by clans friendly to you slow Hollow erosion in the surface chunks above them, so underground politics protect your base.

### How the battles work technically

Hundreds of units per clan is beyond Godot's normal node-per-character approach, so the Underveil uses a three-tier simulation:

| Tier | Who | Simulation | Rendering |
|---|---|---|---|
| Near | Up to about 32 units closest to the ghost, plus anyone being read, possessed, or talked to | Full CPU actors (`CharacterBody3D`) with AI, physics, dialogue, and all scare interactions | Rigged glTF characters from Blender |
| Crowd | Everyone else in the loaded region (hundreds per clan) | GPU compute shader through `RenderingDevice`: steering, separation, flow-field movement, melee contact, and Resolve | `MultiMeshInstance3D` per clan and unit type, with vertex-animation textures baked by Blender scripts |
| Abstract | Every region not loaded | CPU war simulation: clan strength, veins, and fronts per region | None, or the war map |

- **Flow fields** are baked per clan objective on a coarse grid of the region (one field per goal, shared by all units heading there), so pathfinding cost doesn't grow with unit count.
- **Resolve runs on the GPU too:** every unit samples nearby routing units in the same spatial hash it uses for separation, which is what makes routs cascade across hundreds of units for free.
- **Ghost hits reach the crowd:** single-target hits land on near-tier actors. Area effects (BOO bursts, telekinetic throws, rockfalls, scares) are written each frame into a small GPU buffer of hit spheres, and every crowd unit inside one loses Form or Resolve in the same compute pass.
- **Terrain** for the crowd is a baked height and occupancy texture of the region, rebaked when blocks change.
- **Promotion and demotion:** units move between the crowd and near tiers as the ghost moves, swapping a MultiMesh instance for a real actor and back, carrying their state across.
- **Readback stays small:** the CPU reads a compact summary (deaths, routs, front-line positions, per-clan counts) a few times a second, never the full unit buffer every frame.
- **Headless tests:** Godot's headless mode has no `RenderingDevice`, so the crowd sim also has a slower CPU reference implementation with the same data layout. Unit tests and `--autotest` run on the CPU version; a `--battle-bench` mode runs the GPU version on real hardware and logs frame times.
- **Budget:** 60 fps at 1080p on a mid-range GPU with 1,000 crowd units and 32 near actors, on both Windows (Vulkan) and macOS (Metal). The project uses the Forward+ renderer, which supports compute; a Web build would need the CPU path with a much smaller army.
- **Pipeline fit:** Blender scripts produce the clan characters, bake their vertex-animation textures, and write region layouts and clan population as JSON, as for Millbrook.

## Cosmetics and relic displays

Cosmetics let players dress their ghost and their workers, and relic displays turn trophies into a Horror Level stat for the base.

- **Cosmetics:** masks, gloves, hats, and accessories equipped on your ghost or individual worker ghosts. They are purely visual, so players can mix freely.
- **Relic displays:** display cases with custom shelf layouts for rare trophies from dungeons and legendary scares. Each displayed relic adds Horror Level, which slightly boosts scare power inside your consecrated ground and attracts residents who appreciate a good collection.

**IP note.** The cosmetics board uses Jason's mask, Freddy's glove, Chucky, Michael Myers, and Ghostface. Those are licensed film characters, so they can't ship without licenses from their rights holders. The better move is to invent your own relics that play on the same slasher-movie archetypes (a masked killer, a cursed doll, a clawed glove) with original designs. Original relics also become your game's own collectible icons.

## Development roadmap

Build the smallest thing that proves scaring is fun before adding the base, defense, and later biomes.

**Underveil.** Before any Underveil content is built, a battle prototype has to pass a **battle-fun gate**, the same way scaring had to pass the scare-fun gate: one flat cavern region, two clans of about 500 each, flow fields, melee, Resolve and rout cascades, MultiMesh rendering, promotion and demotion around the ghost, and `--battle-bench` frame times on Windows and macOS. If breaking a flank with one well-timed scare doesn't feel great, rethink the design before making clans. If it does, run 2 of task1 to task5 builds the upper Underveil: the five clans, the Glowcap Warrens, Drowned Nave, Barrow Halls, and Sunken Ford regions, and the war map.

The prototype needs only one biome, a ghost that drifts and phases, mining with memory fragments, and the first two Haunting levels against a few villagers who have fears, an Unease meter, visible reactions, and simple memory of your tricks. If scaring a villager with a creaking door and a slamming wardrobe isn't fun, no amount of graveyard building will fix it, so that gate comes first. Chunk-based voxel meshing and a turn-penalized pathfinder for spirit roads are the two technical risks worth spiking early. The project is built in Godot, so the first spike compares the community Voxel Tools module against a custom chunk mesher before committing.

## Agent workstreams

Development runs as one Claude Code orchestrator session that writes task specs and owns architecture, a pool of parallel Haiku subagents that each build one spec'd task in its own git worktree, and a reviewer that gates every merge. Haiku gets work that is well defined, testable, and small in footprint; design calls, cross-cutting systems, and anything about how the game feels stay with the orchestrator and Scott.

The orchestrator fans spec'd tasks out to Haiku workers, the reviewer checks each diff, and only passing work reaches main; failures go back with notes, and design questions go to Scott.

### Roles

| Role | Model | Owns | Never does |
|---|---|---|---|
| Scott (director) | n/a | Design decisions, game feel, playtests, phase gates | Routine implementation |
| Orchestrator | Opus (main session) | Breaking each phase into task specs, interface contracts, core architecture, merges | Bulk feature code Haiku can do |
| godot-worker | Haiku | One task spec per run, in an isolated worktree, with its tests | Touching files outside its spec, design choices |
| godot-explorer | Haiku, read-only | Codebase lookups so the orchestrator's context stays clean | Edits |
| test-writer | Haiku | Unit tests from a spec's acceptance criteria, written before or alongside the feature | Changing feature code |
| reviewer | Sonnet, read-only plus test runs | Checking each diff against its spec and contracts, running the tests, passing or failing it | Fixing code itself |

### What makes a good Haiku task

- **One feature with a file list:** the spec names the files the worker may touch, so parallel workers don't collide.
- **Interfaces already decided:** the orchestrator writes the signal names, node structure, and data formats first, in a contracts folder every worker reads.
- **A pass/fail check:** each spec ends with acceptance tests or a headless Godot run that proves it works.
- **No judgment about fun:** tuning numbers, scare feel, and art direction come back to Scott as open questions in the worker's report.

**Godot-specific rules.** Scene files (.tscn) merge poorly, so each scene has one owning task at a time and logic lives in scripts. Block types, items, abilities, and recipes live as data resources, which makes them ideal parallel Haiku work: one worker per batch of definitions, with no shared code touched.

### Task assignments by phase

| Phase | Parallel Haiku tasks | Stays with the orchestrator and Scott |
|---|---|---|
| Prototype | Block type registry and definitions; memory fragment data and journal screen; drifting and phasing controller from spec; mining and drop tables; villager Nerve, Unease, and fear components; Creak and Flicker abilities; tests for each | Voxel module vs. custom mesher spike; chunk architecture; NPC reaction state machine design; the scare-fun gate |
| Vertical slice | Mausoleum and gravestone blueprints; worker ghost gather and haul behaviors; tool tiers and recipes; salt line and iron fence blocks; Possession and Telekinesis levels 1 and 2; crypt room prefabs and skeleton variants; inventory and crafting screens | Spirit-road pathfinder core; Remembrance system; town adaptation and legend system design; balancing the loop |
| Alpha | Suburb and city prop sets; Ghost Hunter gear and enemy variants; Heat counters and UI; building tiers 1 to 3 block sets; path levels 3 to 5 from the ability tables; legend and rumor text templates | World generation for new biomes; erosion and the Hollow; save system; performance |
| Beta | Hellscape props; demon and imp variants; Ethereal blocks; original relic and cosmetic definitions; regression test expansion; bug-fix tasks from triage | Demon portal encounters; final balance; release builds |

**How it runs.** Each worker is a project subagent in `.claude/agents/` with model set to haiku and isolation set to worktree, so it gets its own copy of the repo. Claude Code allows up to 20 subagents running at once by default, which is far more than the merge and review step can absorb, so batches of 4 to 6 workers per phase step is a sensible starting point. The orchestrator can run headless in tmux on a disposable VM: it pulls the next batch of specs, dispatches workers, sends each diff to the reviewer, merges passing work, and leaves failures and design questions for Scott.

The main risk is spec quality: Haiku executes a clear spec well and a vague one badly, so the orchestrator's time goes into contracts and specs, and the reviewer rejects anything that drifts from them.

## Open questions

- [ ] Working title?
- [ ] Engine: Godot (decided). Still open: a voxel module or a custom chunk mesher?
- [ ] Single-player first, or co-op from the start?
- [ ] Should your own identity fade too (a personal Remembrance meter), or only the world?
- [ ] Is there an ending, such as helping residents move on and eventually moving on yourself, or is it fully open-ended?
- [ ] Should a fourth path (Manifestation: moans, apparitions, size changes) exist, or stay folded into Presence?
- [ ] Do the living ever fight back directly outside Ghost Hunter raids?
- [ ] Underveil: is Hollow-eaten land sinking into the Underveil the right origin story?
- [ ] Underveil: are the five clans (Mycelial Kin, Drowned Parish, Barrow Host, Bonewardens, Velvet Wake) the right cast, and do the names fit?
- [x] Underveil: ghosts can damage undead (Form) as well as break Resolve. *Decided Nov 19, 2026.*
- [x] Underveil: a handful of large linked regions, each its own voxel map. *Decided Nov 19, 2026.*
- [ ] Underveil: does scattering undead pay Fright, or only materials (proposed)?
- [ ] Underveil: can Bonewardens ever become friendly, and can the player end a clan entirely?
- [ ] Underveil: is day-underground, night-on-the-surface the right rhythm, or should the Underveil have its own clock?
