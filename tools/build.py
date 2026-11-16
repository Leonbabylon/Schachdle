#!/usr/bin/env python3
"""Build puzzle files from queue.json.

For every queue entry that has no puzzle file yet, this:
  1. works out the starting position (from "fen", or from "moves" + "at"),
  2. gives it the next free date if it has none (and writes that back to queue.json),
  3. runs Stockfish along its own best-move line and records eval, best move and legal moves,
  4. rejects positions that would make an unfair or broken puzzle,
  5. writes puzzles/YYYY-MM-DD.json.

Usage:
  python tools/build.py            build everything that is missing
  python tools/build.py --check    analyse and validate, but write nothing
  python tools/build.py --force ID rebuild one entry even though its file exists

The engine is found from $STOCKFISH, then ./stockfish/stockfish, then "stockfish" on PATH.
"""
import argparse, datetime as dt, json, os, re, shutil, sys
import chess, chess.engine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "tools", "config.json")))
QUEUE = os.path.join(ROOT, "queue.json")
PUZZLES = os.path.join(ROOT, "puzzles")


class Reject(Exception):
    pass


def find_engine():
    for cand in (os.environ.get("STOCKFISH"), os.path.join(ROOT, "stockfish", "stockfish"), shutil.which("stockfish")):
        if cand and os.path.exists(cand):
            return cand
    sys.exit("Stockfish not found. Set STOCKFISH=/path/to/stockfish or run tools/get_stockfish.sh")


def start_position(entry):
    """Return (board, move played in the game or None)."""
    if entry.get("fen"):
        try:
            board = chess.Board(entry["fen"])
        except ValueError as e:
            raise Reject(f"bad FEN: {e}")
        return board, entry.get("played")
    if entry.get("moves") and entry.get("at"):
        m = re.fullmatch(r"(\d+)([wb])", str(entry["at"]).strip().lower())
        if not m:
            raise Reject('"at" must look like 28b (move number, then w or b for the side to move)')
        num, side = int(m.group(1)), m.group(2) == "w"
        board = chess.Board()
        text = re.sub(r"\{[^}]*\}|\([^)]*\)|\$\d+", " ", entry["moves"])
        for tok in text.split():
            tok = re.sub(r"^\d+\.+", "", tok).rstrip("!?")
            if not tok or tok in ("1-0", "0-1", "1/2-1/2", "*"):
                continue
            if board.fullmove_number == num and board.turn == side:
                return board, entry.get("played") or tok
            try:
                board.push_san(tok)
            except ValueError:
                raise Reject(f"illegal or unreadable move {tok!r} at move {board.fullmove_number}")
        raise Reject(f'the game ends before {entry["at"]}')
    raise Reject('needs either "fen", or "moves" plus "at"')


def position_key(fen):
    return " ".join(fen.split()[:4])  # pieces, side, castling, en passant


def analyse_line(engine, board):
    line, board = [], board.copy()
    for ply in range(CFG["line_length"]):
        if board.is_game_over():
            raise Reject(f"the game is over {ply} move(s) into the engine line")
        legal = list(board.legal_moves)
        if any(mv.promotion for mv in legal):
            raise Reject(f"a pawn can promote {ply} move(s) into the line; the board does not support promotions")
        engine.configure({"Clear Hash": None})
        info = engine.analyse(board, chess.engine.Limit(depth=CFG["depth"]))
        score = info["score"].white()
        if score.is_mate():
            raise Reject(f"forced mate {ply} move(s) into the line; a mate has no pawn evaluation to guess")
        ev = round(score.score() / 100, 2)
        if abs(ev) > CFG["max_abs_eval"]:
            raise Reject(f"eval {ev:+.2f} is beyond ±{CFG['max_abs_eval']}; too one-sided")
        if line and abs(ev - line[-1]["eval"]) > CFG["max_step_swing"]:
            raise Reject(f"eval jumps from {line[-1]['eval']:+.2f} to {ev:+.2f} in one move; the engine line is unstable")
        best = info["pv"][0]
        line.append({"fen": board.fen(), "eval": ev, "best": best.uci(), "moves": {mv.uci(): board.san(mv) for mv in legal}})
        board.push(best)
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only; write nothing")
    ap.add_argument("--force", metavar="ID", help="rebuild this entry")
    args = ap.parse_args()

    queue = json.load(open(QUEUE))
    entries = queue["positions"]
    os.makedirs(PUZZLES, exist_ok=True)
    launch = dt.date.fromisoformat(CFG["launch_date"])
    today = dt.datetime.now(dt.timezone.utc).date()

    ids = [e.get("id") for e in entries]
    problems = [f"duplicate or missing id: {i!r}" for i in set(ids) if not i or ids.count(i) > 1]
    dates = [e["date"] for e in entries if e.get("date")]
    problems += [f"two entries share the date {d}" for d in set(dates) if dates.count(d) > 1]
    if problems:
        sys.exit("queue.json: " + "; ".join(problems))

    built = {}  # date -> puzzle file contents
    for name in os.listdir(PUZZLES):
        if name.endswith(".json"):
            built[name[:-5]] = json.load(open(os.path.join(PUZZLES, name)))
    seen = {position_key(p["line"][0]["fen"]): d for d, p in built.items()}

    todo = [e for e in entries if not e.get("date") or e["date"] not in built or built[e["date"]].get("id") != e["id"] or args.force == e["id"]]
    if not todo:
        print("Nothing to build: every queue entry already has its puzzle file.")
        return

    engine = chess.engine.SimpleEngine.popen_uci(find_engine())
    engine.configure({"Threads": min(4, os.cpu_count() or 1), "Hash": 512})
    failed, changed = [], False
    try:
        for e in todo:
            try:
                board, played = start_position(e)
                key = position_key(board.fen())
                if key in seen and seen[key] != e.get("date"):
                    raise Reject(f"same position as the puzzle for {seen[key]}")
                if not e.get("date"):
                    taken = set(built) | {x["date"] for x in entries if x.get("date")}
                    day = max([today] + [dt.date.fromisoformat(d) for d in taken]) + dt.timedelta(days=1)
                    date = day.isoformat()
                else:
                    date = e["date"]
                    dt.date.fromisoformat(date)
                number = (dt.date.fromisoformat(date) - launch).days + 1
                if number < 1:
                    raise Reject(f"{date} is before the launch date {CFG['launch_date']}")
                line = analyse_line(engine, board)
                source = {k: e[k] for k in ("white", "black", "event", "round") if e.get(k)}
                if played:
                    source["played"] = played
                puzzle = {"id": e["id"], "date": date, "number": number, "engine": CFG["engine_name"], "depth": CFG["depth"], "source": source, "line": line}
                evals = " ".join(f"{p['eval']:+.2f}" for p in line)
                print(f"OK    {e['id']}: {date} (#{number}) evals {evals}")
                if not args.check:
                    json.dump(puzzle, open(os.path.join(PUZZLES, date + ".json"), "w"), ensure_ascii=False, separators=(",", ":"))
                    if e.get("date") != date:
                        e["date"] = date
                        changed = True
                built[date] = puzzle
                seen[key] = date
            except Reject as r:
                failed.append(e.get("id"))
                print(f"FAIL  {e.get('id')}: {r}")
    finally:
        engine.quit()
    if changed and not args.check:
        with open(QUEUE, "w") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
            f.write("\n")

    # a heads-up, not a failure: the next seven days all leaning the same way makes guessing easy
    upcoming = [built[d]["line"][0]["eval"] for d in sorted(built) if d >= today.isoformat()][:7]
    if len(upcoming) >= 5 and (all(v > 0.3 for v in upcoming) or all(v < -0.3 for v in upcoming)):
        print("NOTE  the next week of puzzles all favour the same side; consider mixing in others.")
    if failed:
        sys.exit(f"{len(failed)} position(s) rejected: {', '.join(map(str, failed))}")


if __name__ == "__main__":
    main()
