# Stock Aging, FSN & ABC Analysis (Odoo 17)

Technical name: `stock_aging_fsn_abc` - depends only on `stock`.
The Sales app is optional (needed only for ABC revenue).

## Install
1. Copy the `stock_aging_fsn_abc` folder into your addons path.
2. Restart Odoo, Apps > Update Apps List, install "Stock Aging, FSN & ABC Analysis".
3. Menu: Inventory > Reporting > Aging & Analysis.

## Reports
| Report | What it does | Output |
|---|---|---|
| Inventory Aging | On-hand split in 5 buckets (default 0-30/31-60/61-90/91-180/181+), qty and value, optional per lot/serial | PDF, XLSX |
| FSN | Fast / Slow / Non-moving. Turnover = qty sold in period / qty on hand. Sold = 0 -> Non-moving; turnover >= threshold (default 1.0) -> Fast; otherwise Slow | PDF, XLSX |
| ABC | Products ranked by confirmed sales-order revenue (untaxed) in the period. Default bands A 80% / B 15% / C 5%. No sales -> C | PDF, XLSX |
| Inventory Loss | Scrap + inventory adjustments (loss and gain) with value lost | PDF |

## How the numbers are computed
* **Scope**: internal locations under the selected warehouses/locations (all warehouses of the company by default).
* **Aging (FIFO)**: on hand at the "As of" date = done move lines entering the scope minus those leaving it
  (transfers inside the scope are ignored). The on-hand quantity is allocated to the most recent receipts first;
  each unit's age is the number of days since its receipt. Stock with no documented receipt goes to the oldest bucket.
* **Value** = quantity x product cost (`standard_price`) of the selected company.
* **Sales for FSN** = done moves from the scope to customer locations in the look-back window.
* **Obsolete flag**: "Flag obsolete products" sets `is_obsolete` on products whose whole stock is in the oldest bucket
  (Inventory Managers only). It never archives anything; filter products with "Obsolete" in the product search.

## Known limitations
* Valuation uses the current product cost, not historical layer cost.
* ABC does not convert foreign currencies and does not deduct returns/credit notes.
* Dates are compared in UTC.
* Only storable products are analysed.
