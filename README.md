# Schachdle

A daily chess puzzle: guess Stockfish's evaluation of a position in five tries. After each miss,
Stockfish plays its top move and the next guess is for the new position. Guess right and a bonus
round opens: find the engine's top move for a ★.

## What is in here

| Path | What it is |
|---|---|
| `site/index.html` | The whole page. It loads one file, `puzzles/<today's date>.json`. |
| `queue.json` | The list of positions. **This is the only file an admin edits.** |
| `puzzles/` | One built puzzle per date. Written by the build tool, never by hand. |
| `tools/build.py` | Turns queue entries into puzzle files using Stockfish, and rejects bad positions. |
| `tools/publish.py` | Assembles `public/`, the folder that goes online. |
| `tools/config.json` | Launch date (puzzle #1), engine depth, rejection thresholds, your domain. |
| `.github/workflows/` | Automation: build when the queue changes, publish every day. |

## Adding a position

1. Add an entry to `queue.json`. Either give a FEN:

   ```json
   {
     "id": "carlsen-giri-28b",
     "fen": "r1q2rk1/p5bp/1p2pp2/6p1/3P4/2N2n1P/PPQ2PNB/3RR2K b - - 2 28",
     "white": "Carlsen", "black": "Giri",
     "event": "Total Chess World Championship Tour Pilot 2026", "round": 2,
     "played": "e5"
   }
   ```

   or paste the game's moves and say where to stop. `at` is the move number plus `w` or `b` for the
   side to move, and the move played in the game is picked up automatically:

   ```json
   {
     "id": "artemiev-caruana-31w",
     "moves": "1. d4 Nf6 2. c4 e6 3. Nf3 c5 ...",
     "at": "31w",
     "white": "Artemiev", "black": "Caruana", "event": "Some Open 2026", "round": 10
   }
   ```

   `id` must be unique. `date` is optional: leave it out and the position gets the first free day
   after the last scheduled one. `white`, `black`, `event`, `round`, `game` and `played` are optional. The players, round, game and
   event make up the game title shown under the board, and also feed the "Starting position" line
   shown after the game.

2. Commit and push (or open a pull request to have the positions checked first).
   The **Build puzzles** workflow analyses each new position, writes `puzzles/<date>.json`, fills in
   the date in `queue.json` and commits both. Its log shows one line per position:

   ```
   OK    artemiev-caruana-31w: 2026-11-23 (#38) evals +2.28 +2.26 +2.18 +2.22 +2.38 +2.21
   FAIL  some-id: eval jumps from +4.67 to +3.14 in one move; the engine line is unstable
   ```

3. The **Publish site** workflow puts each puzzle online the day before its date, at 09:40 UTC.

### Why a position gets rejected

- The eval swings by more than 0.6 pawns between consecutive moves of the engine line (unfair to guess).
- There is a forced mate, or the game ends, within the six positions of the line.
- A pawn can promote anywhere in the line (the board does not support promotions yet).
- The eval is beyond ±8 pawns.
- The same position is already scheduled.
- The FEN or the moves cannot be read.

A rejected entry stays in `queue.json` without a date. Fix it or delete it; the next push tries again.

### Changing or removing a scheduled puzzle

Edit or delete the entry in `queue.json`, delete its file in `puzzles/`, and push. To rebuild one
entry in place run `python tools/build.py --force <id>`. Do not change a puzzle whose date has
already been published: players may have it in progress.

## Running it on your own machine

```
pip install -r tools/requirements.txt
export STOCKFISH=/path/to/stockfish        # Stockfish 19; on Linux, tools/get_stockfish.sh fetches it
python tools/build.py --check              # analyse and validate, write nothing
python tools/build.py                      # write the puzzle files
python tools/publish.py --all              # public/ with every puzzle, for previewing
python -m http.server -d public 8000       # then open http://localhost:8000/?date=2026-11-18
```

`?date=YYYY-MM-DD` shows that date's puzzle. Online it only works for dates already published.

## Hosting

The workflows publish to GitHub Pages. One-time setup:

1. Push this repository to GitHub.
2. Repository **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Run the **Publish site** workflow once (Actions tab → Publish site → Run workflow).

### Using a GoDaddy domain

1. Put the domain in `tools/config.json`, for example `"domain": "www.example.com"`, and push.
2. In GoDaddy's DNS settings for the domain add:
   - a `CNAME` record, name `www`, value `<your-github-username>.github.io`
   - four `A` records, name `@`, values `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
     (remove GoDaddy's default "Parked" `A` record)
3. In **Settings → Pages**, enter the same domain under **Custom domain** and, once the certificate
   is issued, tick **Enforce HTTPS**.

### Keeping future answers private

The live site only ever holds puzzles up to tomorrow. The repository, however, holds all of them,
so anyone who can read the repository can read next week's evals.

- A **public** repository is free on GitHub Pages but exposes the queue.
- A **private** repository hides it. GitHub Pages on a private repository needs a paid GitHub plan;
  the alternative is to upload `public/` to any other static host (GoDaddy web hosting included)
  from the same daily workflow.

Today's answer is always inside the page's puzzle file. That is inherent to a game that runs
entirely in the browser.
