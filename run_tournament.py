#!/usr/bin/env python3
"""
Round-robin tournament for Lab 2 (blind adversary).
Runs all pairwise matchups in both roles, multiple rounds each.
"""

import subprocess
import sys
import re
from itertools import permutations

AGENTS = ["22120016", "23120215", "23120216"]
ROUNDS_PER_MATCHUP = 5  # 5 rounds each to average out randomness
ARENA_FLAGS = [
    "--no-viz",
    "--pacman-speed", "2",
    "--capture-distance", "2",
    "--pacman-obs-radius", "5",
    "--ghost-obs-radius", "5",
    "--start-mode", "stochastic",
    "--step-timeout", "3.0",
]


def run_match(seek_id, hide_id):
    """Run one match and return (winner_role, steps)."""
    cmd = [
        sys.executable, "arena.py",
        "--seek", seek_id,
        "--hide", hide_id,
    ] + ARENA_FLAGS

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120,
        cwd="src"
    )
    output = result.stdout + result.stderr

    steps = 200
    m = re.search(r"Total Steps:\s*(\d+)", output)
    if m:
        steps = int(m.group(1))

    if "Pacman" in output and "WINNER" in output:
        # Check who won
        winner_line = [l for l in output.split("\n") if "WINNER" in l]
        if winner_line:
            if "(Pacman)" in winner_line[0]:
                return "pacman_wins", steps
            elif "(Ghost)" in winner_line[0]:
                return "ghost_wins", steps

    # Fallback: check result string
    if "ghost_wins" in output or "Ghost" in output:
        return "ghost_wins", steps
    return "pacman_wins", steps


def main():
    # Results storage
    # results[seek_id][hide_id] = list of (winner_role, steps)
    results = {a: {b: [] for b in AGENTS if b != a} for a in AGENTS}

    total_matches = len(AGENTS) * (len(AGENTS) - 1) * ROUNDS_PER_MATCHUP
    match_num = 0

    print(f"{'='*70}")
    print(f"  LAB 2 TOURNAMENT: {', '.join(AGENTS)}")
    print(f"  {ROUNDS_PER_MATCHUP} rounds per matchup, {total_matches} matches total")
    print(f"  Settings: obs-radius=5, speed=2, capture-dist=2, stochastic starts")
    print(f"{'='*70}\n")

    for seek_id in AGENTS:
        for hide_id in AGENTS:
            if seek_id == hide_id:
                continue
            for rnd in range(ROUNDS_PER_MATCHUP):
                match_num += 1
                print(f"  [{match_num:2d}/{total_matches}] Seek={seek_id} vs Hide={hide_id} (round {rnd+1})...", end=" ", flush=True)
                try:
                    winner, steps = run_match(seek_id, hide_id)
                    results[seek_id][hide_id].append((winner, steps))
                    tag = "Pacman(Seek) wins" if winner == "pacman_wins" else "Ghost(Hide) wins"
                    print(f"{tag} in {steps} steps")
                except subprocess.TimeoutExpired:
                    print("TIMEOUT (counted as ghost win)")
                    results[seek_id][hide_id].append(("ghost_wins", 200))
                except Exception as e:
                    print(f"ERROR: {e}")
                    results[seek_id][hide_id].append(("ghost_wins", 200))

    # ── Compile statistics ────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"{'DETAILED RESULTS':^70}")
    print(f"{'='*70}\n")

    for seek_id in AGENTS:
        for hide_id in AGENTS:
            if seek_id == hide_id:
                continue
            matches = results[seek_id][hide_id]
            pac_wins = sum(1 for w, _ in matches if w == "pacman_wins")
            ghost_wins = sum(1 for w, _ in matches if w == "ghost_wins")
            avg_steps = sum(s for _, s in matches) / len(matches) if matches else 0
            pac_win_steps = [s for w, s in matches if w == "pacman_wins"]
            ghost_win_steps = [s for w, s in matches if w == "ghost_wins"]
            avg_pac = sum(pac_win_steps) / len(pac_win_steps) if pac_win_steps else 0
            avg_ghost = sum(ghost_win_steps) / len(ghost_win_steps) if ghost_win_steps else 0

            print(f"  Seek={seek_id} vs Hide={hide_id}: "
                  f"Pacman wins {pac_wins}/{len(matches)}, "
                  f"Ghost wins {ghost_wins}/{len(matches)}, "
                  f"avg steps={avg_steps:.1f}")

    # ── Per-agent summary ─────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"{'AGENT RANKINGS':^70}")
    print(f"{'='*70}\n")

    agent_stats = {}
    for agent in AGENTS:
        # As Pacman (Seek): how many matches did this agent's Pacman win?
        seek_wins = 0
        seek_total = 0
        seek_steps_when_won = []
        for hide_id in AGENTS:
            if hide_id == agent:
                continue
            for w, s in results[agent][hide_id]:
                seek_total += 1
                if w == "pacman_wins":
                    seek_wins += 1
                    seek_steps_when_won.append(s)

        # As Ghost (Hide): how many matches did this agent's Ghost win?
        hide_wins = 0
        hide_total = 0
        hide_steps_survived = []
        for seek_id in AGENTS:
            if seek_id == agent:
                continue
            for w, s in results[seek_id][agent]:
                hide_total += 1
                if w == "ghost_wins":
                    hide_wins += 1
                hide_steps_survived.append(s)

        seek_wr = (seek_wins / seek_total * 100) if seek_total else 0
        hide_wr = (hide_wins / hide_total * 100) if hide_total else 0
        avg_seek_steps = sum(seek_steps_when_won) / len(seek_steps_when_won) if seek_steps_when_won else 200
        avg_hide_steps = sum(hide_steps_survived) / len(hide_steps_survived) if hide_steps_survived else 0

        agent_stats[agent] = {
            "seek_wr": seek_wr,
            "hide_wr": hide_wr,
            "seek_wins": seek_wins,
            "seek_total": seek_total,
            "hide_wins": hide_wins,
            "hide_total": hide_total,
            "avg_seek_steps": avg_seek_steps,
            "avg_hide_steps": avg_hide_steps,
            "combined_wr": (seek_wr + hide_wr) / 2,
        }

    # Print table
    print(f"  {'Agent':<12} {'Seek WR':>10} {'Seek Wins':>10} {'Avg Steps':>10} "
          f"{'Hide WR':>10} {'Hide Wins':>10} {'Avg Surv':>10} {'Combined':>10}")
    print(f"  {'─'*12} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")

    # Sort by combined win rate
    ranked = sorted(agent_stats.items(), key=lambda x: x[1]["combined_wr"], reverse=True)
    for rank, (agent, s) in enumerate(ranked, 1):
        print(f"  {agent:<12} {s['seek_wr']:>9.1f}% {s['seek_wins']:>5}/{s['seek_total']:<4} "
              f"{s['avg_seek_steps']:>10.1f} {s['hide_wr']:>9.1f}% {s['hide_wins']:>5}/{s['hide_total']:<4} "
              f"{s['avg_hide_steps']:>10.1f} {s['combined_wr']:>9.1f}%")

    print(f"\n{'='*70}")
    best = ranked[0]
    print(f"  🏆 BEST OVERALL: {best[0]} (combined win rate: {best[1]['combined_wr']:.1f}%)")
    print(f"{'='*70}\n")

    # Match results matrix (Lab 2 format: 0 = Hide wins, 1 = Seek wins)
    print(f"{'MATCH RESULTS MATRIX (majority vote per matchup)':^70}")
    print(f"{'0 = Hide wins, 1 = Seek wins':^70}\n")

    header = f"  {'Hide \\\\ Seek':<12}"
    for a in AGENTS:
        header += f" {a:>10}"
    print(header)
    print(f"  {'─'*12}" + "─"*10*len(AGENTS))

    for hide_id in AGENTS:
        row = f"  {hide_id:<12}"
        for seek_id in AGENTS:
            if seek_id == hide_id:
                row += f" {'–':>10}"
            else:
                matches = results[seek_id][hide_id]
                pac_wins = sum(1 for w, _ in matches if w == "pacman_wins")
                majority = 1 if pac_wins > len(matches) / 2 else 0
                row += f" {majority:>10}"
        print(row)
    print()


if __name__ == "__main__":
    main()
