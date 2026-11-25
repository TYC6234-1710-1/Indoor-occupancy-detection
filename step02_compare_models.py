r"""第二步：只在验证集选配置，完整训练文件重训后评价两个测试集。

运行：.venv\Scripts\python.exe step02_compare_models.py
本轮仅比较三种方法，特征消融与滞后分析在后续步骤完成。
"""

import json
import platform
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from step01_check_data import ROOT, FEATURES, read_data


def metrics(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return dict(n=len(y), precision=float(precision_score(y, pred, zero_division=0)),
                recall=float(recall_score(y, pred, zero_division=0)),
                f1=float(f1_score(y, pred, zero_division=0)),
                fpr=float(fp / (fp + tn)) if fp + tn else None,
                tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp))


def arrays(rows):
    return np.array([[r[f] for f in FEATURES] for r in rows]), np.array([r['Occupancy'] for r in rows])


def main():
    start = time.perf_counter()
    output = ROOT / 'outputs' / 'step02'
    output.mkdir(parents=True, exist_ok=True)
    train = sorted(read_data(ROOT / 'data' / 'datatraining.txt'), key=lambda r: r['date'])
    x, y = arrays(train)
    cutoff = int(len(train) * .8)
    xt, xv, yt, yv = x[:cutoff], x[cutoff:], y[:cutoff], y[cutoff:]
    # 候选阈值只来自训练部分；按验证集F1选择，相同分数取较低阈值。
    light_index = FEATURES.index('Light')
    candidates = np.unique(np.quantile(xt[:, light_index], np.linspace(0, 1, 201)))
    best_threshold = max(candidates, key=lambda t: f1_score(yv, xv[:, light_index] > t, zero_division=0))
    selections = {'light_rule': {'threshold': float(best_threshold), 'validation': metrics(yv, xv[:, light_index] > best_threshold)}}
    fitted = {}
    all_trials = []
    # 分类概率阈值预先固定为0.5；仅模型参数通过验证集选择。
    for name, configs in [('logistic', [{'C': c} for c in [.1, 1, 10]]),
                          ('random_forest', [{'max_depth': d, 'min_samples_leaf': leaf} for d in [5, None] for leaf in [1, 5]])]:
        trials = []
        for config in configs:
            model = (make_pipeline(StandardScaler(), LogisticRegression(**config, max_iter=2000, random_state=42))
                     if name == 'logistic' else RandomForestClassifier(**config, n_estimators=200, random_state=42, n_jobs=2))
            model.fit(xt, yt)
            result = metrics(yv, model.predict(xv))
            trials.append((result['f1'], model, config, result))
            all_trials.append({'method': name, 'config': config, 'validation': result})
        _, model, config, result = max(trials, key=lambda row: row[0])
        selections[name] = {'config': config, 'probability_threshold': .5, 'validation': result}
        model.fit(x, y)  # 配置固定后才使用完整训练文件重训，包括标准化器。
        fitted[name] = model
    (output / 'selected_configs.json').write_text(json.dumps(selections, indent=2), encoding='utf-8')
    results, predictions = [], []
    pooled = {name: ([], []) for name in selections}
    for filename in ['datatest.txt', 'datatest2.txt']:
        rows = read_data(ROOT / 'data' / filename)
        xx, yy = arrays(rows)
        for name in selections:
            score = ((xx[:, light_index] > best_threshold).astype(float) if name == 'light_rule'
                     else fitted[name].predict_proba(xx)[:, 1])
            pred = (score >= .5).astype(int)
            result = {'dataset': filename, 'method': name, **metrics(yy, pred)}
            results.append(result)
            pooled[name][0].extend(yy.tolist())
            pooled[name][1].extend(pred.tolist())
            for row, label, value in zip(rows, pred, score):
                predictions.append(dict(source_file=filename, source_row=row['source_row'],
                                        date=str(row['date']), occupancy_true=row['Occupancy'],
                                        occupancy_pred=int(label), score=float(value), method=name))
            print(f"{filename} {name}: F1={result['f1']:.4f}, recall={result['recall']:.4f}, FP={result['fp']}, FN={result['fn']}")
    for name, (truth, pred) in pooled.items():
        assert len(truth) == 12417
        results.append({'dataset': 'pooled', 'method': name, **metrics(truth, pred)})
    assert len(predictions) == 12417 * 3
    metadata = {'python': platform.python_version(), 'sklearn': sklearn.__version__, 'numpy': np.__version__,
                'features': FEATURES, 'seed': 42, 'selection_metric': 'validation F1',
                'score_note': 'light_rule score is binary rule output; other scores are estimated probabilities',
                'trials': all_trials, 'selected': selections, 'test_results': results,
                'elapsed_seconds': time.perf_counter() - start}
    (output / 'experiment.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'predictions.json').write_text(json.dumps(predictions, ensure_ascii=False), encoding='utf-8')
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, filename in zip(axes, ['datatest.txt', 'datatest2.txt']):
        group = [r for r in results if r['dataset'] == filename]
        bars = ax.bar(['Light rule', 'Logistic', 'Random forest'], [r['f1'] for r in group], color=['#91999d', '#427c9d', '#315a70'])
        ax.bar_label(bars, fmt='%.3f', padding=4)
        ax.set(title=filename, ylim=(0, 1.12), ylabel='F1 (occupied class)')
        ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(output / 'model_comparison.png', dpi=180)
    plt.close(fig)
    print(f"Light rule: Light > {best_threshold:.3f} lux")
    print(f"Outputs: {output}")


if __name__ == '__main__':
    main()
