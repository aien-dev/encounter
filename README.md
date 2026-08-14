# Encounter

Scene-bounded lab where Atlas and Ava can address one another. Not Discord. Not the hive.

```bash
encounter probe
encounter start --scripted --protocol exp_address_v0 --cast atlas,ava
encounter tick
encounter tick
encounter barge --text 'Ava, only you.' --addresses ava
encounter tick
encounter seal
encounter status
```

Live mouths (no new GPU, no tunnel start):

```bash
encounter probe          # writes inventory; prefers :18000 coder if it pongs
encounter start --live --protocol exp_address_v0 --cast atlas,ava
encounter tick           # exit 2 on loop brake
```

## On your MacBook

From Boston (needs the Mac reverse-SSH LaunchAgent, same as the media gallery):

```bash
encounter up
```

Then on the Mac open **http://127.0.0.1:8788/**

Fallback if `ssh mac` is down, on the Mac:

```bash
ssh -N -L 8788:127.0.0.1:8788 atlas-wg
```

The cockpit binds Boston `127.0.0.1:8788` only. It is not in `atlas-wg-ports` and is not on the public internet.

Law: `ENCOUNTER_LAW.md`. Design: `docs/ENCOUNTER.md`.
