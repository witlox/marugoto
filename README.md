# Marugoto [![Build Status](https://travis-ci.org/witlox/marugoto.svg?branch=master)](https://travis-ci.org/witlox/marugoto)

Backend service for hosting games. Within Marugoto you are able to create new games based on Directed Acyclic Graphs (DAGs). 
Marugoto hosts an API with which you can define and interact within games. The API is based on [Swagger2](swagger/api.yaml).

## Game structure

A game has paths, these paths are connections of waypoints. Each waypoint in the game can pose a task that needs to be solved,
or an interaction with a Non-Playable Character(NPC). During the traversal of the game graph, a player can (or must) interact
with an NPC (can or must is based on the dialog setup of the NPC). A player finished a game, when she/he reaches a finish, which
is a waypoint that has no other destinations, tasks and NPC interactions. Tasks are principally blocking progress to a next waypoint,
but there may be more waypoint available besides the one blocked by a task. Task to waypoint blocking is 1-on-1. Solutions to a 
task can be [fuzzified](https://en.wikipedia.org/wiki/Fuzzy_logic) in order to allow for broader input acceptance. At any given point
in a game, an NPC can start interacting with the player. NPC dialogs have waypoints associated with them, on which a dialog will
be initiated. Completion of specific steps in a dialog may enable waypoints further along in the game.

## Single player and multi-player games

A game is a 'static' DAG, which can be instantiated as a 'playable' game. A game instance can have a 'game master', which
is a player that hosts a multi-player game. This 'game master' can view all information of all players in a game. Game instances
can also have a start and end timestamp, which will only allow the game to be played during a time slot. 

## Players and state

Currently players register using an e-mail address and a password. When joining a game instance the player will need to 
give first and last name pseudonyms for their in game character. A player can play multiple instances of the same game
concurrently. All NPCs in a game have a state per game instance, in which they keep track of their interactions with players.
Waypoints and NPCs can add items to the players inventory in game. Interactions with NPCs are added to the player state as well.

## Weighed paths and energy

Every game path can have a weight (this is a regular DAG weight expressed as a float). When creating a game it can be 
initiated with a total amount of 'energy' that a player starts with. If the amount of starting energy is set, each path
that is traversed and has a weight, will deduct the weight from the total amount of energy. If the deduction would lead
to a negative number, the path will be blocked.
