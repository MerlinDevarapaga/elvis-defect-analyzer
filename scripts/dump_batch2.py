import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('all_defects_batch2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for tid, d in data.items():
    print(f"=== TICKET {tid} ===")
    print(f"Title: {d.get('Title','')}")
    print(f"Priority: {d.get('PriorityID','')} | IntPriority: {d.get('IntPriority','')}")
    print(f"FGroup: {d.get('FGroup','')} | Component: {d.get('Component','')} | SubComp: {d.get('SubComponent','')}")
    print(f"State: {d.get('StateID','')} | Step: {d.get('TicketStepID','')} | Owner: {d.get('Owner','')}")
    print(f"Occurrence: {d.get('Occurance','')}")
    print(f"Product: {d.get('Product','')} | SubProject: {d.get('SubProject','')}")
    desc = d.get('ProblemDescription', '') or ''
    print(f"Description: {desc[:700]}")
    print(f"Cause: {d.get('Cause','')}")
    print(f"BugTaxonomy: {d.get('BugTaxonomy','')}")
    print(f"Measures: {str(d.get('Measures',''))[:500]}")
    print(f"Avoidance: {str(d.get('Avoidance',''))[:300]}")
    print(f"RespNote: {str(d.get('RespNote',''))[:500]}")
    print(f"Result: {str(d.get('Result',''))[:500]}")
    print(f"InternalStatement: {str(d.get('InternalStatement',''))[:400]}")
    print(f"OfficialStatement: {str(d.get('OfficialStatement',''))[:400]}")
    print(f"Reason: {d.get('Reason','')}")
    print(f"FixedInVersion: {d.get('FixedInVersion','')}")
    print(f"PlannedFixedVersion: {d.get('PlannedFixedVersion','')}")
    print(f"PlannedFixedDate: {d.get('PlannedFixedDate','')}")
    print(f"ReproNote: {str(d.get('ReproNote',''))[:300]}")
    print(f"CauseID: {d.get('CauseID','')}")
    print(f"EnterDateTime: {d.get('EnterDateTime','')}")
    print()
