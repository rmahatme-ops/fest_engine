"""
Fest Engine - the maths part (pure Python, no libraries needed).

Events are the elements of a set. "A comes before B" is a relation on that set.
If the rules make sense, that relation is a partial order (a poset).

Run this file on its own to see a text version:   python fest_logic.py
"""

EXAMPLE_CSV = """event,volunteers,prerequisites
Registration,4,
Opening Ceremony,5,Registration
Workshop A,3,Opening Ceremony
Workshop B,3,Workshop A
Coding Contest,4,Opening Ceremony
Quiz,3,Opening Ceremony
Dance Round,6,Opening Ceremony
Dance Finals,6,Dance Round
Final Competition,5,Workshop B;Coding Contest
Prize Ceremony,4,Final Competition;Dance Finals;Quiz"""


def parse_csv(text):
    """Turn CSV text into (events, rules).
    events = [(name, volunteers_needed), ...]
    rules  = [(earlier_event, later_event), ...]
    """
    lines = text.strip().splitlines()[1:]          # skip the header line
    events, rules = [], []

    def known(name):
        return any(e[0] == name for e in events)

    for line in lines:                              # pass 1: add every event
        parts = line.split(",")
        name = parts[0].strip()
        if name == "" or known(name):
            continue
        need = int(parts[1]) if len(parts) > 1 and parts[1].strip().isdigit() else 1
        events.append((name, need))

    for line in lines:                              # pass 2: add the rules
        parts = line.split(",")
        name = parts[0].strip()
        if name == "" or len(parts) < 3:
            continue
        for pre in parts[2].split(";"):
            pre = pre.strip()
            if pre == "" or pre == name:
                continue
            if not known(pre):
                events.append((pre, 1))
            if (pre, name) not in rules:
                rules.append((pre, name))
    return events, rules


def plan(events, rules, rooms=3, vols=12):
    """Build the whole fest plan. Returns a dictionary of results,
    or {"error": "loop", "loop": [...]} if the rules contradict each other."""
    names = [e[0] for e in events]
    need = [e[1] for e in events]
    n = len(names)
    if n == 0:
        return {"error": "empty"}
    idx = {name: i for i, name in enumerate(names)}

    # R[a][b] is True when event a must come (somewhere) before event b
    R = [[False] * n for _ in range(n)]
    pre = [[] for _ in range(n)]       # events that must come directly before
    succ = [[] for _ in range(n)]      # events that come directly after
    for a_name, b_name in rules:
        a, b = idx[a_name], idx[b_name]
        R[a][b] = True
        succ[a].append(b)
        pre[b].append(a)

    # Warshall's algorithm: transitive closure
    # (if A is before B and B is before C, then A is before C)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if R[i][k] and R[k][j]:
                    R[i][j] = True

    # A partial order cannot loop: an event cannot have to come before itself
    loop = [names[i] for i in range(n) if R[i][i]]
    if loop:
        return {"error": "loop", "loop": loop}

    # Topological order (Kahn's algorithm) and the level of every event
    indeg = [len(p) for p in pre]
    level = [0] * n
    queue = [i for i in range(n) if indeg[i] == 0]
    order = []
    while queue:
        x = queue.pop(0)
        order.append(x)
        for y in succ[x]:
            level[y] = max(level[y], level[x] + 1)
            indeg[y] -= 1
            if indeg[y] == 0:
                queue.append(y)
    max_level = max(level)

    # Longest chain: these events must happen one after another
    cur = level.index(max_level)
    chain = [cur]
    while level[cur] > 0:
        cur = [p for p in pre[cur] if level[p] == level[cur] - 1][0]
        chain.append(cur)
    chain.reverse()

    # Time slots: events on the same level do not depend on each other, so they
    # may run together if there are enough rooms and volunteers. If not, split.
    slots, warnings = [], []
    for L in range(max_level + 1):
        group = sorted((i for i in range(n) if level[i] == L), key=lambda i: -need[i])
        here = []
        for ev in group:
            if need[ev] > vols:
                warnings.append(f"{names[ev]} needs {need[ev]} volunteers but only {vols} are available.")
            for s in here:
                if len(s["items"]) < rooms and s["sum"] + need[ev] <= vols:
                    s["items"].append(ev)
                    s["sum"] += need[ev]
                    break
            else:
                here.append({"level": L, "items": [ev], "sum": need[ev]})
        slots.extend(here)

    # Volunteers: in each slot give every event different people, least busy first
    load = [0] * vols
    assigned = {}
    for slot in slots:
        pool = sorted(range(vols), key=lambda v: (load[v], v))
        nxt = 0
        for ev in slot["items"]:
            team = pool[nxt:nxt + need[ev]]
            nxt += len(team)
            for v in team:
                load[v] += 1
            assigned[ev] = team

    # Hasse diagram: keep a link a -> b only if nothing sits in between
    hasse = [(i, j) for i in range(n) for j in range(n)
             if R[i][j] and not any(R[i][k] and R[k][j] for k in range(n))]

    # Events that can happen at the same time (incomparable: neither before the other)
    alongside = {names[a]: [names[b] for b in range(n)
                            if a != b and not R[a][b] and not R[b][a]]
                 for a in range(n)}

    return {"names": names, "need": need, "level": level, "max_level": max_level,
            "order": order, "chain": chain, "slots": slots, "warnings": warnings,
            "assigned": assigned, "load": load, "hasse": hasse,
            "alongside": alongside, "rooms": rooms, "vols": vols}


def print_plan(m):
    """Plain text version of the answer."""
    if m.get("error") == "loop":
        print("These rules cannot all be followed. Events in a loop:", ", ".join(m["loop"]))
        return
    if m.get("error"):
        print("Add some events first.")
        return
    names = m["names"]
    print(f"Fest plan: {len(m['slots'])} time slots "
          f"({len(names)} events, {m['rooms']} rooms, {m['vols']} volunteers)\n")
    for w in m["warnings"]:
        print("WARNING:", w)
    print("SCHEDULE")
    for si, slot in enumerate(m["slots"], 1):
        cells = []
        for ev in slot["items"]:
            who = ", ".join(f"V{v + 1}" for v in m["assigned"][ev])
            cells.append(f"{names[ev]} [{who}]")
        print(f"  Slot {si}: " + "  |  ".join(cells))
    print("\nLONGEST CHAIN:", " -> ".join(names[i] for i in m["chain"]))
    print("ONE VALID ORDER:", " -> ".join(names[i] for i in m["order"]))
    print("\nHASSE DIAGRAM LINKS")
    for a, b in m["hasse"]:
        print(f"  {names[a]} -> {names[b]}")
    print("\nCAN HAPPEN AT THE SAME TIME")
    for name, mates in m["alongside"].items():
        print(f"  {name}: {', '.join(mates) if mates else 'must run on its own'}")


if __name__ == "__main__":
    ev, ru = parse_csv(EXAMPLE_CSV)
    print_plan(plan(ev, ru, rooms=3, vols=12))
