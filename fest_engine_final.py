"""
Fest Engine - one file version (Python + Streamlit), version 2 with a better interface.
Run with:   streamlit run fest_engine_final.py
Part 1 is the maths (pure Python). Part 2 is the web page.
"""
import pandas as pd
import streamlit as st

# ======================= PART 1: THE MATHS =======================
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


# ======================= PART 2: THE WEB PAGE =======================
import html

st.set_page_config(page_title="Fest Engine", layout="wide")

LEVEL_COLOURS = ["#d5ecee", "#fbdce8", "#e1e4fa", "#fdeccb", "#daf0d8", "#efdcf5"]

# Styling (works in both light and dark theme)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;700;800&display=swap');
html, body, .stApp { font-family: 'Figtree', 'Segoe UI', system-ui, sans-serif; }
.block-container { padding-top: 2rem; max-width: 1200px; }
footer { visibility: hidden; }
.hero { border-left: 6px solid #d6246e; padding: 4px 0 4px 18px; margin-bottom: 20px; }
.hero h1 { margin: 0; padding: 0; font-size: 2.5rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.1; }
.hero h1 span { color: #d6246e; }
.hero p { margin: 6px 0 0 0; opacity: .75; max-width: 62ch; }
.card { border: 1px solid rgba(128,128,128,.3); border-radius: 8px; padding: 16px 20px; margin-bottom: 14px; background: rgba(128,128,128,.07); }
.card h3 { margin: 0 0 8px 0; }
.step { display: flex; gap: 12px; margin: 10px 0; align-items: flex-start; }
.num { background: #0e7c86; color: #fff; font-weight: 800; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; flex: none; }
.scroll { overflow-x: auto; }
table.sched { border-collapse: collapse; width: 100%; font-size: 14px; }
.sched th { background: #0e7c86; color: #fff; text-align: left; padding: 9px 12px; border: 1px solid rgba(128,128,128,.35); }
.sched td { padding: 9px 12px; border: 1px solid rgba(128,128,128,.35); vertical-align: top; color: #14262b; min-width: 140px; }
.sched td.slot { font-weight: 700; background: rgba(128,128,128,.15); color: inherit; min-width: 80px; }
.sched td.free { background: rgba(128,128,128,.07); color: inherit; opacity: .5; }
.sched .who { display: block; font-size: 12px; opacity: .7; margin-top: 2px; }
.chain { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 6px 0 16px 0; }
.pill { background: rgba(14,124,134,.16); border: 1px solid rgba(14,124,134,.55); border-radius: 4px; padding: 3px 11px; font-size: 14px; }
.arrow { color: #d6246e; font-weight: 800; }
</style>
""", unsafe_allow_html=True)


def esc(text):
    return html.escape(str(text))


def chain_html(names_in_order):
    parts = []
    for i, nm in enumerate(names_in_order):
        if i > 0:
            parts.append('<span class="arrow">&rarr;</span>')
        parts.append(f'<span class="pill">{esc(nm)}</span>')
    return '<div class="chain">' + "".join(parts) + "</div>"


# --- Data kept between clicks ---
if "events" not in st.session_state:
    st.session_state.events = []   # [(name, volunteers_needed), ...]
    st.session_state.rules = []    # [(earlier, later), ...]

events = st.session_state.events
rules = st.session_state.rules
names = [e[0] for e in events]

st.markdown(
    '<div class="hero"><h1>Fest<span>Engine</span></h1>'
    '<p>Can discrete maths organise a college fest? Add events, say which must come first, '
    'and get a complete schedule with rooms and volunteers.</p></div>',
    unsafe_allow_html=True)

# --- Sidebar: all the inputs ---
with st.sidebar:
    st.markdown("### Fest setup")
    c1, c2 = st.columns(2)
    rooms = c1.number_input("Rooms", min_value=1, value=3)
    vols = c2.number_input("Volunteers", min_value=0, value=12)

    with st.expander("Events", expanded=True):
        with st.form("add_event", clear_on_submit=True):
            new_name = st.text_input("Event name")
            new_need = st.number_input("Volunteers needed", min_value=0, value=2)
            if st.form_submit_button("Add event"):
                new_name = new_name.strip()
                if new_name == "":
                    st.error("Enter an event name.")
                elif new_name in names:
                    st.error(f"{new_name} is already added.")
                else:
                    events.append((new_name, int(new_need)))
                    st.rerun()
        if names:
            gone = st.selectbox("Remove an event", [""] + names)
            if gone and st.button("Remove event"):
                st.session_state.events = [e for e in events if e[0] != gone]
                st.session_state.rules = [r for r in rules if gone not in r]
                st.rerun()

    with st.expander("Order rules", expanded=True):
        if len(names) >= 2:
            with st.form("add_rule"):
                first = st.selectbox("This event...", names, key="first")
                second = st.selectbox("...comes before this one", names, index=1, key="second")
                if st.form_submit_button("Add rule"):
                    if first == second:
                        st.error("Choose two different events.")
                    elif (first, second) in rules:
                        st.error("That rule is already added.")
                    else:
                        rules.append((first, second))
                        st.rerun()
        else:
            st.info("Add at least two events to make a rule.")
        if rules:
            labels = [f"{a} -> {b}" for a, b in rules]
            pick = st.selectbox("Remove a rule", [""] + labels)
            if pick and st.button("Remove rule"):
                rules.pop(labels.index(pick))
                st.rerun()

    with st.expander("Import from CSV"):
        st.caption("Columns: event, volunteers needed, events that must come first (separated by ;).")
        upload = st.file_uploader("CSV file", type=["csv", "txt"])
        if upload is not None and st.button("Load this file"):
            ev, ru = parse_csv(upload.getvalue().decode("utf-8"))
            st.session_state.events, st.session_state.rules = ev, ru
            st.rerun()

    b1, b2 = st.columns(2)
    if b1.button("Load example"):
        st.session_state.events, st.session_state.rules = parse_csv(EXAMPLE_CSV)
        st.rerun()
    if b2.button("Clear all"):
        st.session_state.events, st.session_state.rules = [], []
        st.rerun()

# --- Welcome screen when there is nothing yet ---
if not events:
    st.markdown("""
<div class="card">
<h3>How it works</h3>
<div class="step"><div class="num">1</div><div><b>Add your events</b> in the sidebar, with the number of volunteers each one needs.</div></div>
<div class="step"><div class="num">2</div><div><b>Add order rules</b>, like "Workshop A comes before the Final". Events with no rule between them can run together.</div></div>
<div class="step"><div class="num">3</div><div><b>Set rooms and volunteers.</b> The schedule, diagram and workload appear here automatically.</div></div>
</div>
""", unsafe_allow_html=True)
    if st.button("Load the example fest", type="primary"):
        st.session_state.events, st.session_state.rules = parse_csv(EXAMPLE_CSV)
        st.rerun()
    st.stop()

# --- The maths happens here ---
m = plan(events, rules, rooms=int(rooms), vols=int(vols))

with st.expander("Your events and rules", expanded=(m.get("error") == "loop")):
    left, right = st.columns(2)
    with left:
        st.table(pd.DataFrame(events, columns=["Event", "Volunteers needed"]))
    with right:
        if rules:
            st.table(pd.DataFrame(rules, columns=["Comes first", "Comes after"]))
        else:
            st.write("No rules yet.")

if m.get("error") == "loop":
    st.error("These rules cannot all be followed. Some events depend on each other in a loop, "
             "so no valid schedule exists.")
    st.write("Events caught in the loop: **" + ", ".join(m["loop"]) + "**")
    st.caption("A set of order rules only works if no event ends up having to come before itself. "
               "That is what makes it a partial order. Remove one of the rules in the loop.")
    st.stop()

names = m["names"]
slots = m["slots"]

# --- Summary numbers ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("Events", len(names))
k2.metric("Time slots", len(slots))
k3.metric("Longest chain", len(m["chain"]))
k4.metric("Busiest slot", f"{max(s['sum'] for s in slots)} volunteers")

extra = len(slots) - len(m["chain"])
if extra > 0:
    st.info(f"The longest chain needs {len(m['chain'])} levels, but {m['rooms']} rooms and "
            f"{m['vols']} volunteers force {extra} extra slot(s). That is the pigeonhole principle: "
            "more events than space means some must wait.")
else:
    st.success("The schedule is as short as the longest chain allows.")
for w in m["warnings"]:
    st.warning(w)

# --- Results in tabs ---
t1, t2, t3, t4, t5 = st.tabs(["Schedule", "Hasse diagram", "Order and chain", "Same time", "Volunteers"])

with t1:
    st.caption("Events in the same row have no rule between them, so they run at the same time "
               "in different rooms, with different volunteers.")
    rows = ['<div class="scroll"><table class="sched"><tr><th>Slot</th>']
    rows += [f"<th>Room {r + 1}</th>" for r in range(m["rooms"])]
    rows.append("</tr>")
    for si, slot in enumerate(slots):
        rows.append(f'<tr><td class="slot">Slot {si + 1}</td>')
        for r in range(m["rooms"]):
            if r < len(slot["items"]):
                ev = slot["items"][r]
                who = ", ".join(f"V{v + 1}" for v in m["assigned"][ev])
                colour = LEVEL_COLOURS[m["level"][ev] % 6]
                rows.append(f'<td style="background:{colour}">{esc(names[ev])}'
                            f'<span class="who">{m["need"][ev]} volunteers: {esc(who)}</span></td>')
            else:
                rows.append('<td class="free">free</td>')
        rows.append("</tr>")
    rows.append("</table></div>")
    st.markdown("".join(rows), unsafe_allow_html=True)

with t2:
    st.caption("Each arrow means 'must come before'. Arrows that follow from others are left out, "
               "so only direct links remain. Events in the same column are on the same level.")

    def q(name):
        return name.replace('"', "'")

    dot = ['digraph { rankdir=LR; bgcolor="transparent"; nodesep=0.35; ranksep=0.9;',
           'node [shape=box, style="rounded,filled", fontname="Helvetica", fontcolor="#14262b", color="#14262b"];',
           'edge [color="#d6246e", penwidth=1.4];']
    for i, name in enumerate(names):
        dot.append(f'"{q(name)}" [fillcolor="{LEVEL_COLOURS[m["level"][i] % 6]}"];')
    for L in range(m["max_level"] + 1):
        same = " ".join(f'"{q(names[i])}";' for i in range(len(names)) if m["level"][i] == L)
        dot.append("{ rank=same; " + same + " }")
    for a, b in m["hasse"]:
        dot.append(f'"{q(names[a])}" -> "{q(names[b])}";')
    dot.append("}")
    st.graphviz_chart("\n".join(dot))

with t3:
    st.subheader("Longest chain")
    st.caption(f"These events must happen one after another, so at least {len(m['chain'])} levels "
               "are unavoidable, however many rooms you have.")
    st.markdown(chain_html([names[i] for i in m["chain"]]), unsafe_allow_html=True)
    st.subheader("One valid order (topological order)")
    st.caption("Every event appears after the events it depends on. More than one valid order can exist.")
    st.markdown(chain_html([names[i] for i in m["order"]]), unsafe_allow_html=True)

with t4:
    st.caption("Two events can overlap when neither has to come before the other.")
    st.table(pd.DataFrame(
        [(name, ", ".join(mates) if mates else "must run on its own")
         for name, mates in m["alongside"].items()],
        columns=["Event", "Can run alongside"]))

with t5:
    if m["vols"] > 0:
        st.caption("How many events each volunteer works. The least busy volunteers are picked first, "
                   "so the work is shared fairly.")
        st.bar_chart(pd.Series(m["load"], index=[f"V{v + 1}" for v in range(m["vols"])]))
        st.write(f"Busiest volunteer: **{max(m['load'])}** events. Least busy: **{min(m['load'])}** events.")
    else:
        st.write("No volunteers entered.")

st.caption("Built with Python and Streamlit. Maths used: partial orders, Hasse diagrams, "
           "Warshall's algorithm, topological ordering and the pigeonhole principle.")
