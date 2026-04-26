import pandas as pd
import gzip
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm


def count_residues(idx_path):
    """Count unique residues by (chain, resseq) from ATOM records only.
    Takes (index, path) so we can preserve order when reassembling."""
    idx, path = idx_path
    try:
        opener = gzip.open if str(path).endswith('.gz') else open
        residues = set()

        if '.cif' in str(path):
            with opener(path, 'rt') as f:
                in_loop = False
                headers = []
                col_idx = {}
                for line in f:
                    if line.startswith('_atom_site.'):
                        headers.append(line.strip())
                        in_loop = True
                    elif in_loop and headers:
                        col_idx = {
                            h.split('.')[1]: i for i, h in enumerate(headers)}
                        in_loop = False
                        if line.startswith('ATOM'):
                            parts = line.split()
                            residues.add((
                                parts[col_idx['label_asym_id']],
                                parts[col_idx['label_seq_id']],
                            ))
                    elif line.startswith('ATOM') and col_idx:
                        parts = line.split()
                        residues.add((
                            parts[col_idx['label_asym_id']],
                            parts[col_idx['label_seq_id']],
                        ))
                    elif line.startswith('#') and col_idx:
                        break
        else:
            with opener(path, 'rt') as f:
                for line in f:
                    if line.startswith('ATOM'):
                        residues.add((line[21], line[22:27]))

        return idx, len(residues)
    except Exception:
        return idx, -1


if __name__ == '__main__':
    df = pd.read_csv('sources.csv')
    paths = list(enumerate(df['structure_path']))
    counts = [None] * len(paths)

    with ProcessPoolExecutor() as ex:
        futures = [ex.submit(count_residues, p) for p in paths]
        for fut in tqdm(as_completed(futures), total=len(futures), desc='counting residues', smoothing=0.05):
            idx, n = fut.result()
            counts[idx] = n

    df['n_residues'] = counts
    df.to_csv('with_counts.csv', index=False)
