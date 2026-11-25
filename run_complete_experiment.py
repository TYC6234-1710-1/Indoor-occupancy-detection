"""课程完整实验：复用首轮结果，补齐预定特征对比、误差与事件分析。

运行 .venv/Scripts/python.exe run_complete_experiment.py
不根据已观察到的测试成绩扩展参数搜索或挑选单一最优模型。
"""
import csv
import json
import platform
import time
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from step01_check_data import ROOT, FEATURES, read_data
from step02_compare_models import metrics, arrays, main as run_baselines

OUT = ROOT / 'outputs' / 'complete'
GROUPS = {'light': ['Light'], 'co2': ['CO2'], 'light_co2': ['Light', 'CO2']}
METHODS = ['light_rule', 'lr_light', 'lr_co2', 'lr_light_co2', 'logistic', 'random_forest']
LABELS = ['Light rule', 'LR: Light', 'LR: CO2', 'LR: Light + CO2', 'LR: all 5', 'Random forest']


def save_json(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def save_csv(name, rows, fields=None):
    if not rows:
        return
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_plot(fig, name):
    fig.savefig(OUT / (name + '.png'), dpi=200, bbox_inches='tight')
    fig.savefig(OUT / (name + '.svg'), bbox_inches='tight')
    plt.close(fig)


def transition_distances(rows):
    """距最近一次已观察到的状态变化的分钟数；文件开头无法确定，记-1。"""
    last, distances = None, []
    for i, row in enumerate(rows):
        if i and row['Occupancy'] != rows[i-1]['Occupancy']:
            last = row['date']
        distances.append(-1 if last is None else (row['date'] - last).total_seconds() / 60)
    return np.array(distances)


def error_analysis(data, predictions):
    slices, episodes = [], []
    lookup = {(p['source_file'], p['source_row'], p['method']): p for p in predictions}
    for filename, rows in data.items():
        if filename == 'datatraining.txt':
            continue
        distances = transition_distances(rows)
        truth = np.array([r['Occupancy'] for r in rows])
        for method in METHODS:
            pred = np.array([lookup[(filename, r['source_row'], method)]['occupancy_pred'] for r in rows])
            for label, mask in [('within_10min_after_change', (distances >= 0) & (distances <= 10)),
                                ('over_10min_after_change', distances > 10), ('initial_state_age_unknown', distances < 0)]:
                if mask.any():
                    slices.append(dict(source_file=filename, method=method, period=label, **metrics(truth[mask], pred[mask])))
            # 连续同类错误片段，最多允许61秒采样间隔。
            i = 0
            while i < len(rows):
                if truth[i] == pred[i]:
                    i += 1
                    continue
                end = i + 1
                while (end < len(rows) and truth[end] != pred[end] and truth[end] == truth[i]
                       and (rows[end]['date'] - rows[end-1]['date']).total_seconds() <= 61):
                    end += 1
                episodes.append(dict(source_file=filename, method=method, error='FP' if truth[i] == 0 else 'FN',
                                     start=str(rows[i]['date']), end=str(rows[end-1]['date']), n=end-i,
                                     elapsed_minutes=(rows[end-1]['date']-rows[i]['date']).total_seconds()/60,
                                     median_light=float(np.median([r['Light'] for r in rows[i:end]])),
                                     median_co2=float(np.median([r['CO2'] for r in rows[i:end]]))))
                i = end
    save_csv('error_slices.csv', slices)
    save_csv('error_episodes.csv', sorted(episodes, key=lambda r: (-r['n'], r['source_file'], r['start'])))
    return slices, episodes


def event_analysis(data):
    """固定前后30个采样点窗口，排除边界、不连续及窗口内其他切换。

    CO2差值以切换前5个观测的中位数为基准。使用未来观测仅作事后解释。
    """
    events, counts, profiles = [], [], {}
    fig, axes = plt.subplots(2, 2, figsize=(10, 6), sharex=True)
    for col, direction in enumerate(['entry', 'exit']):
        by_feature = {f: [] for f in ['Light', 'CO2']}
        for filename, rows in data.items():
            total = eligible = 0
            for i in range(1, len(rows)):
                if rows[i]['Occupancy'] == rows[i-1]['Occupancy']:
                    continue
                if ('entry' if rows[i]['Occupancy'] else 'exit') != direction:
                    continue
                total += 1
                if i < 30 or i + 30 >= len(rows):
                    continue
                window = rows[i-30:i+31]
                before = rows[i-1]['Occupancy']
                if (any(r['Occupancy'] != before for r in window[:30]) or
                    any(r['Occupancy'] != 1-before for r in window[30:]) or
                    any((b['date']-a['date']).total_seconds() > 61 for a, b in zip(window, window[1:]))):
                    continue
                eligible += 1
                base = float(np.median([r['CO2'] for r in rows[i-5:i]]))
                events.append(dict(source_file=filename, direction=direction, date=str(rows[i]['date']),
                                   baseline_co2=base, **{f'co2_delta_{m}min': rows[i+m]['CO2']-base for m in [5, 15, 30]}))
                for f in by_feature:
                    baseline = np.median([r[f] for r in rows[i-5:i]])
                    by_feature[f].append([r[f]-baseline for r in window])
            counts.append(dict(source_file=filename, direction=direction, total=total, eligible=eligible))
        for row, (feature, unit) in enumerate([('Light', 'Lux'), ('CO2', 'ppm')]):
            ax = axes[row, col]
            values = np.array(by_feature[feature])
            if len(values):
                med = np.median(values, axis=0)
                low, high = np.quantile(values, [.25, .75], axis=0)
                ax.plot(np.arange(-30, 31), med, color='#315a70')
                ax.fill_between(np.arange(-30, 31), low, high, color='#315a70', alpha=.18)
                profiles[direction + '_' + feature] = dict(n=len(values), median=med.tolist(), q25=low.tolist(), q75=high.tolist())
            ax.axvline(0, color='gray', linestyle='--', linewidth=1)
            ax.axhline(0, color='gray', linewidth=.6)
            ax.set(title=f'{direction}: {feature}, n={len(values)}', ylabel=f'Change ({unit})', xlabel='Samples relative to switch (~min)')
    fig.suptitle('Isolated state changes: median and interquartile range; descriptive only')
    fig.tight_layout()
    save_plot(fig, 'transition_profiles')
    save_json('transition_profiles.json', dict(counts=counts, profiles=profiles,
              note='Pooled files; within +/-30 samples no other switch. Bands are IQR across events, not confidence intervals.'))
    save_csv('transition_events.csv', events)
    return counts, events


def timeline(rows, filename, lookup, suffix):
    dates = [r['date'] for r in rows]
    fig, axes = plt.subplots(3, 1, figsize=(12, 7), sharex=True)
    axes[0].plot(dates, [r['Light'] for r in rows], color='#b07c36', linewidth=.8)
    axes[0].set_ylabel('Light (Lux)')
    axes[1].plot(dates, [r['CO2'] for r in rows], color='#315a70', linewidth=.8)
    axes[1].set_ylabel('CO2 (ppm)')
    axes[2].step(dates, [r['Occupancy'] for r in rows], where='post', label='True', color='black', linewidth=1.2)
    for method, color in [('light_rule', '#b07c36'), ('logistic', '#427c9d')]:
        axes[2].step(dates, [lookup[(filename, r['source_row'], method)]['occupancy_pred'] for r in rows],
                     where='post', label=method, color=color, alpha=.7, linewidth=.8)
    axes[2].set(yticks=[0, 1], ylabel='Occupancy')
    axes[2].legend(loc='upper right', ncol=3, fontsize=8)
    fig.suptitle(filename + ': ' + suffix)
    fig.autofmt_xdate()
    fig.tight_layout()
    save_plot(fig, 'timeline_' + filename.replace('.txt', '') + '_' + suffix)


def main():
    start = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    # 每次重跑首轮脚本，避免依赖不明来源的缓存结果。
    run_baselines()
    baseline_dir = ROOT / 'outputs' / 'step02'
    predictions = json.loads((baseline_dir / 'predictions.json').read_text(encoding='utf-8'))
    baselines = json.loads((baseline_dir / 'experiment.json').read_text(encoding='utf-8'))
    data = {f: sorted(read_data(ROOT / 'data' / f), key=lambda r: r['date'])
            for f in ['datatraining.txt', 'datatest.txt', 'datatest2.txt']}
    training = data['datatraining.txt']
    x, y = arrays(training)
    cutoff = int(len(x) * .8)
    selections, trials = {}, []
    for name, features in GROUPS.items():
        columns = [FEATURES.index(f) for f in features]
        xx = x[:, columns]
        choices = []
        for c in [.1, 1, 10]:
            model = make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=2000, random_state=42))
            model.fit(xx[:cutoff], y[:cutoff])
            result = metrics(y[cutoff:], model.predict(xx[cutoff:]))
            trials.append(dict(method='lr_'+name, C=c, validation=result))
            choices.append((result['f1'], c, model, result))
        _, c, model, result = max(choices, key=lambda r: r[0])
        selections['lr_'+name] = dict(features=features, C=c, probability_threshold=.5, validation=result)
        model.fit(xx, y)
        scaler, classifier = model.steps[0][1], model.steps[1][1]
        weights = classifier.coef_[0] / scaler.scale_
        intercept = float(classifier.intercept_[0] - weights @ scaler.mean_)
        selections['lr_'+name]['refit_coefficients_original_units'] = dict(zip(features, weights.tolist()))
        selections['lr_'+name]['refit_intercept_original_units'] = intercept
        if len(features) == 1:
            selections['lr_'+name]['refit_probability_0_5_boundary'] = float(-intercept / weights[0])
        for filename, rows in data.items():
            if filename == 'datatraining.txt':
                continue
            tx, _ = arrays(rows)
            scores = model.predict_proba(tx[:, columns])[:, 1]
            for row, score in zip(rows, scores):
                predictions.append(dict(source_file=filename, source_row=row['source_row'], date=str(row['date']),
                                        occupancy_true=row['Occupancy'], occupancy_pred=int(score >= .5),
                                        score=float(score), method='lr_'+name))
    results = []
    for dataset in ['datatest.txt', 'datatest2.txt', 'pooled']:
        for method in METHODS:
            rows = [r for r in predictions if r['method'] == method and (dataset == 'pooled' or r['source_file'] == dataset)]
            result = dict(dataset=dataset, method=method, **metrics([r['occupancy_true'] for r in rows], [r['occupancy_pred'] for r in rows]))
            results.append(result)
            print(dataset, method, f"F1={result['f1']:.4f}")
    save_csv('metrics.csv', results)
    save_csv('occupancy_predictions.csv', predictions,
             ['source_file', 'source_row', 'date', 'occupancy_true', 'occupancy_pred', 'score', 'method'])
    lookup = {(r['source_file'], r['source_row'], r['method']): r for r in predictions}
    assert len(lookup) == len(predictions) == 6 * 12417
    expected = {(filename, r['source_row']) for filename, rows in data.items() if filename != 'datatraining.txt' for r in rows}
    for method in METHODS:
        assert {(p['source_file'], p['source_row']) for p in predictions if p['method'] == method} == expected
    slices, episodes = error_analysis(data, predictions)
    counts, events = event_analysis(data)
    for filename, rows in data.items():
        if filename == 'datatraining.txt':
            continue
        timeline(rows, filename, lookup, 'full')
        # 固定选第二个日历日，避免挑选最有利的片段。
        day = sorted({r['date'].date() for r in rows})[1]
        timeline([r for r in rows if r['date'].date() == day], filename, lookup, 'second_day')
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for offset, dataset in [(-.2, 'datatest.txt'), (.2, 'datatest2.txt')]:
        values = [next(r['f1'] for r in results if r['method'] == m and r['dataset'] == dataset) for m in METHODS]
        bars = ax.bar(np.arange(6)+offset, values, width=.38, label=dataset)
        ax.bar_label(bars, fmt='%.3f', fontsize=8, padding=3)
    ax.set(xticks=np.arange(6), xticklabels=LABELS, ylabel='F1 (occupied class)', ylim=(0, 1.13))
    ax.legend(loc='upper center', ncol=2)
    fig.tight_layout()
    save_plot(fig, 'feature_comparison')
    # 原始特征分布与训练部分相关性，为报告提供可追溯数据。
    distributions = []
    for filename, rows in data.items():
        for state in [0, 1]:
            subset = [r for r in rows if r['Occupancy'] == state]
            for feature in FEATURES:
                values = np.array([r[feature] for r in subset])
                distributions.append(dict(source_file=filename, occupancy=state, feature=feature, n=len(values),
                                          mean=float(values.mean()), std=float(values.std(ddof=1)),
                                          q25=float(np.quantile(values, .25)), median=float(np.median(values)),
                                          q75=float(np.quantile(values, .75)), min=float(values.min()), max=float(values.max())))
    save_csv('feature_distributions.csv', distributions)
    save_json('experiment.json', dict(features=GROUPS, trials=trials, selections=selections,
        baseline_selections=baselines['selected'], results=results, transition_counts=counts,
        training_only_correlation=dict(features=FEATURES, matrix=np.corrcoef(x[:cutoff].T).tolist()),
        protocol='Predefined feature comparison; C in [0.1,1,10] selected by validation F1. Test results are descriptive; no test-driven search.',
        limitations=['Test outcomes were observed in prior step; this is not a new blind test.',
                     'Single room; adjacent minute samples are dependent. No IID confidence intervals.',
                     'Transition profiles use future observations for retrospective analysis only; no causal lag estimate.'],
        elapsed_seconds=time.perf_counter()-start, python=platform.python_version(),
        predictions_count=len(predictions), unique_keys_verified=True))
    print('Completed; prediction coverage and unique keys verified.')


if __name__ == '__main__':
    main()
