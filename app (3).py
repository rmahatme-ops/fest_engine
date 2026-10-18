"""
Fest Engine - the web page (Streamlit).
Run with:   streamlit run app.py
The maths lives in fest_logic.py. This file only collects input and shows the answer.
"""
import pandas as pd
import streamlit as st

from fest_logic import EXAMPLE_CSV, parse_csv, plan

st.set_page_config(page_title="Fest Engine", layout="wide")

# --- Data kept between clicks ---
if "events" not in st.session_state:
    st.session_state.events = []   # [(name, volunteers_needed), ...]
    st.session_state.rules = []    # [(earlier, later), ...]

events = st.session_state.events
rules = st.session_state.rules
names = [e[0] for e in events]

st.title("Fest Engine")
st.caption("Can discrete maths organise a college fest? Add events, say which must come first, and get a schedule.")

# --- Sidebar: all the inputs ---
with st.sidebar:
    st.header("Resources")
    rooms = st.number_input("Rooms", min_value=1, value=3)
    vols = st.number_input("Volunteers", min_value=0, value=12)

    st.header("Events")
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

    st.header("Order rules")
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

    st.header("Import from CSV")
    st.caption("Columns: event, volunteers needed, events that must come first (separated by ;).")
    upload = st.file_uploader("CSV file", type=["csv", "txt"])
    if upload is not None and st.button("Load this file"):
        ev, ru = parse_csv(upload.getvalue().decode("utf-8"))
        st.session_state.events, st.session_state.rules = ev, ru
        st.rerun()

    if st.button("Try an example"):
        st.session_state.events, st.session_state.rules = parse_csv(EXAMPLE_CSV)
        st.rerun()
    if st.button("Clear all"):
        st.session_state.events, st.session_state.rules = [], []
        st.rerun()

# --- Show what has been entered ---
left, right = st.columns(2)
with left:
    st.subheader("Events")
    if events:
        st.table(pd.DataFrame(events, columns=["Event", "Volunteers needed"]))
    else:
        st.write("No events yet.")
with right:
    st.subheader("Order rules")
    if rules:
        st.table(pd.DataFrame(rules, columns=["Comes first", "Comes after"]))
    else:
        st.write("No rules yet.")

if not events:
    st.info("Add your events and rules, or press 'Try an example' in the sidebar.")
    st.stop()

# --- The maths happens here ---
m = plan(events, rules, rooms=int(rooms), vols=int(vols))

if m.get("error") == "loop":
    st.error("These rules cannot all be followed. Some events depend on each other in a loop.")
    st.write("Events caught in the loop: " + ", ".join(m["loop"]))
    st.caption("A set of order rules only works if no event ends up having to come before itself. "
               "That is what makes it a partial order.")
    st.stop()

names = m["names"]
st.divider()
st.header(f"Fest plan: {len(m['slots'])} time slots")
st.write(f"{len(names)} events, {m['rooms']} rooms, {m['vols']} volunteers. "
         "The order rules are valid, so they form a partial order.")
for w in m["warnings"]:
    st.warning(w)

# Schedule table: rows are slots, columns are rooms
st.subheader("Schedule")
st.caption("Events in the same row have no rule between them, so they run at the same time "
           "in different rooms, with different volunteers.")
table = []
for slot in m["slots"]:
    row = []
    for r in range(m["rooms"]):
        if r < len(slot["items"]):
            ev = slot["items"][r]
            who = ", ".join(f"V{v + 1}" for v in m["assigned"][ev])
            row.append(f"{names[ev]} ({who})")
        else:
            row.append("free")
    table.append(row)
st.table(pd.DataFrame(table,
                      index=[f"Slot {i + 1}" for i in range(len(table))],
                      columns=[f"Room {r + 1}" for r in range(m["rooms"])]))

# Hasse diagram, drawn from a Graphviz description (no extra install needed)
st.subheader("Hasse diagram")
st.caption("Each arrow means 'must come before'. Arrows that follow from others are left out. "
           "Events in the same column are on the same level.")
colours = ["#d5ecee", "#fbdce8", "#e1e4fa", "#fdeccb", "#daf0d8", "#efdcf5"]
dot = ['digraph { rankdir=LR; node [shape=box, style="rounded,filled", fontname="Helvetica"];']
for i, name in enumerate(names):
    safe = name.replace('"', "'")
    dot.append(f'"{safe}" [fillcolor="{colours[m["level"][i] % 6]}"];')
for L in range(m["max_level"] + 1):
    same = " ".join(f'"{names[i].replace(chr(34), chr(39))}";' for i in range(len(names)) if m["level"][i] == L)
    dot.append("{ rank=same; " + same + " }")
for a, b in m["hasse"]:
    dot.append(f'"{names[a].replace(chr(34), chr(39))}" -> "{names[b].replace(chr(34), chr(39))}" [color="#d6246e"];')
dot.append("}")
st.graphviz_chart("\n".join(dot))

st.subheader("Longest chain")
st.caption(f"These events must happen one after another, so at least {len(m['chain'])} levels "
           "are unavoidable, however many rooms you have.")
st.write(" → ".join(names[i] for i in m["chain"]))

st.subheader("One valid order (topological order)")
st.write(" → ".join(names[i] for i in m["order"]))

st.subheader("Which events can happen at the same time?")
st.caption("Two events can overlap when neither has to come before the other.")
for name, mates in m["alongside"].items():
    st.write(f"**{name}:** " + (", ".join(mates) if mates else "must run on its own"))

st.subheader("Volunteer workload")
if m["vols"] > 0:
    st.bar_chart(pd.Series(m["load"], index=[f"V{v + 1}" for v in range(m["vols"])]))
else:
    st.write("No volunteers entered.")
