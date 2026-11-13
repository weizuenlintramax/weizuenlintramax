"""Tic-tac-toe played through GitHub issues.

A visitor opens an issue titled ``ttt|move|<0-8>``. The visitor plays X, the bot
answers as O, and the board in README.md is re-rendered. When a game ends, the
result is recorded and a fresh board starts.

Usage:
  python scripts/ttt.py           # play the move in $ISSUE_TITLE by $ISSUE_USER
  python scripts/ttt.py --render  # only re-render README.md from the saved state
"""
import json
import os
import random
import re
import sys
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "weizuenlintramax/weizuenlintramax")
STATE_PATH = Path("tictactoe/state.json")
README_PATH = Path("README.md")
REPLY_PATH = Path("reply.md")
START, END = "<!-- TTT:START -->", "<!-- TTT:END -->"
LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
CELL_NAMES = ["top-left", "top", "top-right", "left", "center", "right",
              "bottom-left", "bottom", "bottom-right"]
EMOJI = {"X": "❌", "O": "⭕"}


def new_state():
    return {"board": [""] * 9, "stats": {"human": 0, "bot": 0, "draw": 0},
            "last_game": "No games finished yet. Be the first!", "moves": []}


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return new_state()


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def outcome(board):
    for a, b, c in LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return "draw" if all(board) else None


def bot_move(board):
    empty = [i for i in range(9) if not board[i]]
    for mark in ("O", "X"):  # win if possible, otherwise block
        for i in empty:
            trial = board[:]
            trial[i] = mark
            if outcome(trial) == mark:
                return i
    if 4 in empty:
        return 4
    return random.choice(empty)


def move_url(cell):
    body = "Just+press+%22Submit+new+issue%22.+No+need+to+write+anything."
    return f"https://github.com/{REPO}/issues/new?title=ttt%7Cmove%7C{cell}&body={body}"


def render(state):
    board = state["board"]
    rows = []
    for r in range(3):
        cells = []
        for c in range(3):
            i = r * 3 + c
            mark = board[i]
            inner = EMOJI[mark] if mark else f'<a href="{move_url(i)}">⬜</a>'
            cells.append(f"<td>{inner}</td>")
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    stats = state["stats"]
    recent = state["moves"][-5:][::-1]
    recent_md = "\n".join(f"- {m}" for m in recent) or "- No moves yet."
    return "\n".join([
        START,
        '<h3 align="center">🎮 Tic-Tac-Toe: you ❌ vs bot ⭕</h3>',
        '<p align="center">Click an empty square, then press <b>Submit new issue</b>. '
        "The bot plays back in about a minute.</p>",
        '<div align="center">',
        "  <table>",
        *rows,
        "  </table>",
        "</div>",
        "",
        f'<p align="center">Last game: {state["last_game"]}<br/>'
        f'Humans 🏆 {stats["human"]} · Bot 🤖 {stats["bot"]} · Draws 🤝 {stats["draw"]}</p>',
        "",
        "<details>",
        "<summary>Recent moves</summary>",
        "",
        recent_md,
        "",
        "</details>",
        END,
    ])


def write_readme(state):
    text = README_PATH.read_text(encoding="utf-8")
    block = render(state)
    if START in text and END in text:
        before = text.split(START)[0]
        after = text.split(END, 1)[1]
        text = before + block + after
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    README_PATH.write_text(text, encoding="utf-8")


def play(state, title, user):
    match = re.fullmatch(r"ttt\|move\|([0-8])", title.strip())
    if not match:
        return "🤔 I couldn't read that move. Use the squares on the profile page to play."
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}(\[bot\])?", user):
        return "🤔 Unknown player."
    cell = int(match.group(1))
    board = state["board"]
    if board[cell]:
        return "🚫 That square is already taken. Pick an empty one on the profile page."

    board[cell] = "X"
    state["moves"].append(f"@{user} played ❌ {CELL_NAMES[cell]}")
    result = outcome(board)
    reply = f"You played ❌ {CELL_NAMES[cell]}."
    if result is None:
        bot = bot_move(board)
        board[bot] = "O"
        state["moves"].append(f"🤖 bot played ⭕ {CELL_NAMES[bot]}")
        reply += f" The bot answered ⭕ {CELL_NAMES[bot]}."
        result = outcome(board)

    if result is not None:
        if result == "X":
            state["stats"]["human"] += 1
            state["last_game"] = f"@{user} beat the bot 🎉"
            reply += " **You won!** 🎉"
        elif result == "O":
            state["stats"]["bot"] += 1
            state["last_game"] = f"the bot beat @{user} 🤖"
            reply += " **The bot won.** 🤖 Try again!"
        else:
            state["stats"]["draw"] += 1
            state["last_game"] = f"@{user} drew with the bot 🤝"
            reply += " **It's a draw.** 🤝"
        state["board"] = [""] * 9
        reply += " A new board is ready."
    state["moves"] = state["moves"][-20:]
    return reply + f"\n\n[Back to the board](https://github.com/{REPO.split('/')[0]})"


def main():
    state = load_state()
    if "--render" in sys.argv:
        write_readme(state)
        save_state(state)
        return
    reply = play(state, os.environ.get("ISSUE_TITLE", ""), os.environ.get("ISSUE_USER", ""))
    save_state(state)
    write_readme(state)
    REPLY_PATH.write_text(reply + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
