"""Diagnose F8 balance violations in Doh-KDVP.xml.
Shows exactly which rows cause the balance to go negative (long) or positive (short).
"""
import xml.etree.ElementTree as ET

NS = '{http://edavki.durs.si/Documents/Schemas/Doh_KDVP_9.xsd}'
tree = ET.parse(r"C:\git\ib-edavki\Doh-KDVP.xml")

violations = []
for item in tree.findall(f'.//{NS}KDVPItem'):
    sec = item.find(f'{NS}Securities')
    sec_short = item.find(f'{NS}SecuritiesShort')
    
    if sec is not None:
        tag_type = "LONG"
        sec_elem = sec
    elif sec_short is not None:
        tag_type = "SHORT"
        sec_elem = sec_short
    else:
        continue
    
    code = sec_elem.findtext(f'{NS}Code', '?')
    isin = sec_elem.findtext(f'{NS}ISIN', '?')
    
    rows = sec_elem.findall(f'{NS}Row')
    for row in rows:
        rid = row.findtext(f'{NS}ID', '?')
        f8 = float(row.findtext(f'{NS}F8', '0'))
        
        purchase = row.find(f'{NS}Purchase')
        sale = row.find(f'{NS}Sale')
        
        if purchase is not None:
            date = purchase.findtext(f'{NS}F1', '?')
            qty = float(purchase.findtext(f'{NS}F3', '0'))
            price = float(purchase.findtext(f'{NS}F4', '0'))
            action = "BUY"
        elif sale is not None:
            date = sale.findtext(f'{NS}F6', '?')
            qty = float(sale.findtext(f'{NS}F7', '0'))
            price = float(sale.findtext(f'{NS}F9', '0'))
            action = "SELL"
        else:
            continue
        
        is_violation = False
        if tag_type == "LONG" and f8 < -0.001:
            is_violation = True
            reason = f"LONG balance went negative: F8={f8}"
        elif tag_type == "SHORT" and f8 > 0.001:
            is_violation = True
            reason = f"SHORT balance went positive: F8={f8}"
        
        if is_violation:
            violations.append({
                'code': code, 'isin': isin, 'type': tag_type,
                'row': int(rid), 'date': date, 'action': action,
                'qty': qty, 'price': price, 'f8': f8, 'reason': reason
            })

print(f"Found {len(violations)} F8 balance violations:\n")
for v in violations:
    print(f"  {v['code']:6s} ({v['type']:5s}) row {v['row']:3d}: {v['action']:4s} {v['qty']:>8.0f} @ €{v['price']:.4f} on {v['date']}  → F8={v['f8']:+.4f}  *** {v['reason']}")

# Now show context around each violation (3 rows before, the violation, 3 rows after)
print("\n" + "=" * 100)
print("DETAILED CONTEXT AROUND VIOLATIONS:")
print("=" * 100)

violated_keys = set((v['code'], v['type']) for v in violations)
for code, tag_type in sorted(violated_keys):
    sec_tag = 'Securities' if tag_type == 'LONG' else 'SecuritiesShort'
    for item in tree.findall(f'.//{NS}KDVPItem'):
        sec_elem = item.find(f'{NS}{sec_tag}')
        if sec_elem is None:
            continue
        c = sec_elem.findtext(f'{NS}Code', '')
        if c != code:
            continue
        
        rows = sec_elem.findall(f'{NS}Row')
        # Find violation row indices
        viol_indices = set()
        for i, row in enumerate(rows):
            f8 = float(row.findtext(f'{NS}F8', '0'))
            if (tag_type == "LONG" and f8 < -0.001) or (tag_type == "SHORT" and f8 > 0.001):
                viol_indices.add(i)
        
        # Show context
        show_indices = set()
        for vi in viol_indices:
            for delta in range(-5, 6):
                idx = vi + delta
                if 0 <= idx < len(rows):
                    show_indices.add(idx)
        
        print(f"\n── {code} ({tag_type}) ──")
        for i in sorted(show_indices):
            row = rows[i]
            rid = row.findtext(f'{NS}ID', '?')
            f8 = float(row.findtext(f'{NS}F8', '0'))
            purchase = row.find(f'{NS}Purchase')
            sale = row.find(f'{NS}Sale')
            
            if purchase is not None:
                date = purchase.findtext(f'{NS}F1', '?')
                qty = float(purchase.findtext(f'{NS}F3', '0'))
                desc = f"BUY  {qty:>8.0f}"
            elif sale is not None:
                date = sale.findtext(f'{NS}F6', '?')
                qty = float(sale.findtext(f'{NS}F7', '0'))
                desc = f"SELL {qty:>8.0f}"
            else:
                desc = "???"
                date = "?"
            
            marker = "  *** VIOLATION" if i in viol_indices else ""
            print(f"  row {int(rid):3d}: {date}  {desc}  F8={f8:>+10.4f}{marker}")
