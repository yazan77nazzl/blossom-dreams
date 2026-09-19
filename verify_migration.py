#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app.database import get_db

with get_db() as conn:
    cur = conn.cursor()
    cur.execute("SELECT id, organization_id, category_id, name, slug FROM subcategories")
    rows = cur.fetchall()
    print("Subcategories:")
    for r in rows:
        print(r)

    cur.execute("SELECT id, name, category_id, nail_subcategory_id, subcategory_id FROM services")
    rows = cur.fetchall()
    print("\nServices:")
    for r in rows:
        print(r)