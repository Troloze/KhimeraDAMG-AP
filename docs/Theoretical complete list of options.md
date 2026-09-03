This is a speculative list with all options I wish to include in the game.
It is not final.
# Options
## Basic Options
### Win Condition
Enum: "spider's net", "the black widow", "mechanical mayhem", "all ship stages", "harvest event".
### Shuffle Books
Boolean
All books become ap locations. 
### Shuffle Fairies
Enum: "false", "fairies-only", "fairies-reward" 
When not false, all fairies become ap locations.
"Fairies-only" will randomize the fairies but not the berserk costume
"Fairies-reward" will randomize the fairies and place the berserk costume on the item pool.
### Fairy Queen Reward Cost
Dictionary: Access cost default
Number of fairy items required before you can get the queen's reward.
### Shuffle Detonators
Enum: "disabled", "other_detonators", "shuffle"
If enabled shuffle the detonators
"other_detonators": All detonators will act as detonators, but the mountain range exploded will be randomized.
"shuffle": Detonators act as locations and detonator items will be shuffled into the poll
### Shuffle Gourmet Gal
Boolean
All gourmet gal encounters become ap locations, adds 4 gourmet food items to the item pool.
### Shuffle Lucky Doll
Enum: "false", "final-reward-only", "progressive"
When not false, will place the Lucky Chax Doll in the item pool.
"final-reward-only" will only place the Lucky Chax Doll in the pool, with no changes to the trading up quest.
"progressive" will place 10 "progressive-trade" items in the item pool alongside the Lucky Chax Doll. Every step of the trading up quest becomes a location. 
### Shuffle Costumes
Boolean
Adds the witch and maid costumes in the item poll.
If Halloween event is enabled, will also shuffle the true witch costume.
Does not affect the berserk costume or assistant costume (DLC).
### Shuffle Default Costume
Boolean
Does nothing if shuffle costumes is not enabled.
Default costume is required to access Chelshia's home.
### Cakeboy Progression Locations
integer 0 <= n <= 25
Creates a location for every 1000 points reached in cakeboy
## Clear Options
### Clear Rank As Locations
Boolean
Adds locations for getting C, B and A ranks on a stage.
D rank will issue only the level clear location.
Getting a big rank will send all lower rank locations as well.
### No Death As Locations
Boolean
Adds a new location for getting the no death badge on each stage
### No Death Min HP
int: 4 <= x <= 8
Only relevant when no death as locations is enabled.
Hides the No Death locations behind an HP threshold in logic.
### Berserk Clear as Locations
Boolean
Adds a new location for getting the berserk badge on each stage.
Requires the berserk costume.
### Berserk Clear Min HP
int: 4 <= x <= 8
Only relevant when berserk clear as locations is enabled.
Hides the berserk clear locations behind an HP threshold in logic.
### No Hit As Locations
Boolean
Adds a new location for getting a no hit clear on each stage.
Does not work if you're using the berserk costume.
### No Hit Logic
Enum: "full", "main", "basic", "none"
Hides the no hit locations behind unlocked skills
"full" Requires all skills to be unlocked. (basic + main + extra)
"main" Requires the starting set + main stage skills (basic + main)
"basic" Requires only the starting skill set, relevant for movement randomizer.
"none" No Hit is always seen as accessible in logic. Good Luck.
## Access Options
### Black Widow Access
Enum: "vanilla", "vanilla+", "always", "custom"
Required condition in order to enter the final boss stage.
"vanilla": 4 of any main stages.
"vanilla+": 4 of any stages.
"always": Always available
"collectables": Uses collectable count as a gate.
### Black Widow Access Cost
Dictionary: Access cost default
Only used when Ship Access is set to custom
### Mechanical Mayhem Access
Enum: "vanilla", "vanilla+", "always", "custom"
Required condition in order to enter the final boss stage.
"vanilla": 5 of any main stages.
"vanilla+": 5 of any stages.
"always": Always available
"collectables": Uses collectable count as a gate.
### Mechanical Mayhem Access Cost
Dictionary: Access cost default
Only used when Boss Rush Access is set to custom
### Spiders Web Access
Enum: "vanilla", "vanilla+", "custom"
Required condition in order to enter the final boss stage.
"vanilla": All 6 main stages.
"vanilla+": 6 of any stages.
"custom": Uses collectable count as a gate.
### Spiders Web Access Cost
Dictionary: Access cost default
Only used when Final Boss Access is set to custom
## Map Randomizer Options
### Entrance Randomizer
enum: "disabled", "per-type", "all-stages", "chaos"
Whether or not stage entrances get randomized. Final stage does not get randomized.
"per-type" will shuffle stages based on their type (main, side, ship). Does not apply to home, ragazza town, or fairy domain.
"all-stages" will shuffle all stages among themselves, except for home, ragazza town, or fairy domain.
"chaos" will shuffle everything including home, ragazza town and fairy domain.
### Mountain Randomizer
Boolean
Whether the detonator mountains will be placed in their vanilla locations or somewhere else
### Extra Mountains
Integer: 0 <= n <= 4
The amount of extra mountains placed on the map.
Forces Shuffle Detonators on.
Forces Mountain Randomizer on.
### Map Starting Position Randomizer
Boolean
Whether Chelshia's start position on the map is randomized. 
You will always have access to at least 3 different stage entrances.
### Stage Position Randomizer
Boolean
Forces Entrance Randomizer to chaos.
### Full Map Randomizer
Boolean
Fully randomizes the map layout, including paths.
Forces Entrance Randomizer to chaos.
Forces Mountain Randomizer on.
Forces Map Start Position Randomizer on.
Forces Stage Position Randomizer on.
## Movement Randomizer Options
### Shuffle Dash
Enum: "disabled", "enabled", "enabled-directional"
Places the ability to dash in the item pool
### Shuffle Wings
Boolean
Places the ability to air jump in the item pool
### Shuffle Combat
Boolean.
Shuffles most combat abilities into the item pool. The basic punch stays.
## Harvest Event Options
### Enable Harvest Event
Boolean
Allows the Halloween event to be accessed.
All options in the Halloween section require this to be turned on.
### Harvest Event Access
Enum: "always", "custom", "costume"
What is required for you to be able to access the Halloween event.
"always": Always available
"custom": Uses collectable count as a gate.
"costume": Requires either the witch costume or the true witch costume.
### Harvest Event Access Cost
Dictionary: Access cost default
Only used when Final Boss Access is set to collectables
If candy is present and more than 0, shuffle candy is forced to be enabled.
### Shuffle Candy
Boolean
Adds the candies to the item pool
## Sanity Options
### Checkpointsanity
Boolean.
Makes every checkpoint a location.
If checkpoints are disabled, the locations are sent on level clear.
### Roomsanity
Boolean.
Makes every individual room send a location.
### Enemysanity
Enum: "none", "type", "stage", "instance"
Makes defeating an enemy a location. "Type" will have one location for every type of enemy; "stage" will have one for every type of enemy per stage; and "instance" will have one location for every instance of the enemy.
### Collectablesanity
List: \["coin", "gems", "food"] (Could also work as a bit flag int)
Creates a location for every instance of different types of collectables.
Only applies to collectables placed directly on the map, or hidden by secret walls.
## Filler Options
### Trap percentage:
Integer
The amount of filler items to be replaced with traps.
### \<trap> Weight
Enum: "Huge", "High", "Medium", "Small", "Disabled"
Determines how many of \<trap> will be added to the pool.
One of these options will exist for every trap implemented.
# Other Information
## Access cost default type: 
dictionary: {
	"stage": int, 
	"stage_main": int,
	"stage_extra": int,
	"fairies": int,
	"books": int,
	"candies": int
}

`stage` is the sum of `stage_main` and `stage_extra`
if you had something like:
```python
cost:
	stage: 3
	stage_main: 1
	stage_extra: 1
	...
```
Then it requires at least 3 of any stages, but also requires at least one of main and one of extra.

Does not use OptionDict, but rather OptionCounter, so it is editable in the GUI.
