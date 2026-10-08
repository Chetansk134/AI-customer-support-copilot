import traceback

import memory

CID = 999
try:
    print("Adding a memory...")
    res = memory.add_memory(
        CID, "Ticket 'Charged twice this month': a duplicate $49 charge was refunded; the refund takes 5-7 business days."
    )
    print("add result:", res)
    print("Searching...")
    print("found:", memory.get_memories(CID, "refund duplicate charge"))
except Exception:
    traceback.print_exc()