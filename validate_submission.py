"""独立核验最终预测的覆盖、标识、标签、分数及汇总指标。"""
import csv
import json
import math
from collections import Counter, defaultdict

from step01_check_data import ROOT, read_data


def main():
    folder = ROOT / 'outputs' / 'complete'
    expected = {(f, r['source_row']): r for f in ['datatest.txt', 'datatest2.txt']
                for r in read_data(ROOT / 'data' / f)}
    seen = defaultdict(set)
    counts = defaultdict(Counter)
    with (folder / 'occupancy_predictions.csv').open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ['source_file', 'source_row', 'date', 'occupancy_true', 'occupancy_pred', 'score', 'method']
        for r in reader:
            key = (r['source_file'], int(r['source_row']))
            method = r['method']
            assert key in expected and key not in seen[method], (method, key)
            seen[method].add(key)
            original = expected[key]
            truth, pred, score = int(r['occupancy_true']), int(r['occupancy_pred']), float(r['score'])
            assert truth == original['Occupancy'] and r['date'] == str(original['date'])
            assert pred in [0, 1] and math.isfinite(score) and 0 <= score <= 1
            assert pred == int(score >= .5)
            outcome = ('tp' if pred else 'fn') if truth else ('fp' if pred else 'tn')
            for dataset in [r['source_file'], 'pooled']:
                counts[(dataset, method)][outcome] += 1
    assert len(seen) == 6
    assert all(keys == set(expected) for keys in seen.values())
    with (folder / 'metrics.csv').open(encoding='utf-8-sig', newline='') as handle:
        for r in csv.DictReader(handle):
            c = counts[(r['dataset'], r['method'])]
            assert sum(c.values()) == int(r['n'])
            assert all(c[k] == int(r[k]) for k in ['tp', 'tn', 'fp', 'fn'])
            tp, fp, fn, tn = (c[k] for k in ['tp', 'fp', 'fn', 'tn'])
            recomputed = dict(precision=tp/(tp+fp) if tp+fp else 0,
                              recall=tp/(tp+fn) if tp+fn else 0,
                              f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,
                              fpr=fp/(fp+tn))
            assert all(math.isclose(float(r[k]), v, abs_tol=1e-12) for k, v in recomputed.items())
    report = dict(passed=True, methods=sorted(seen), rows_per_method=len(expected),
                  total_rows=sum(map(len, seen.values())),
                  checks=['exact sample coverage', 'unique identifiers', 'true labels and timestamps',
                          'finite scores and classification threshold', 'confusion counts',
                          'independently recomputed per-file and pooled metrics'])
    (folder / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
