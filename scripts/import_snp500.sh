#!/bin/bash
# For each line of snp500.txt

while IFS= read -r ticker; do
    docker exec aperilex-app-1 python scripts/import_filings.py --tickers "$ticker" --filing-types 10-Q --limit 3
    docker exec aperilex-app-1 python scripts/import_filings.py --tickers "$ticker" --filing-types 10-K --limit 1
done < ./scripts/snp500.txt
