from Bio import SeqIO
import csv
import os
from pathlib import Path
import shutil
input = "/mnt/nw/home/m.yu/repos/foundry/detectors/datasets/vfdb/VFDB_setA_pro.fas"
out_dir = Path("detectors/datasets/vfdb/processed/")
out = out_dir/'vfdb_setA.csv'
shutil.rmtree('detectors/datasets/vfdb/processed/', ignore_errors=True)
os.mkdir('detectors/datasets/vfdb/processed/', exist_ok=True)
with open(out, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['acc', 'length', 'seq'])
    for rec in SeqIO.parse(input, 'fasta'):
        seq = str(rec.seq).replace('*', '')
        # canonical 20 residues
        if 50 <= len(seq) <= 300 and set(seq) <= set('ACDEFGHIKLMNPQRSTVWY'):
            w.writerow([rec.id.split('(')[0], len(seq), seq])
print('wrote', out)
