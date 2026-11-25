"""第一步：检查原始数据。只使用 Python 标准库，不需要安装依赖。

运行后在 outputs/step01 中保存检查结果与划分清单，不修改原始数据。
"""

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FEATURES = ["Temperature", "Humidity", "Light", "CO2", "HumidityRatio"]
EXPECTED = {"datatraining.txt": 8143, "datatest.txt": 2665, "datatest2.txt": 9752}


def read_data(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        # 原文件表头有7列，每条数据却有8项：最前面是原始记录编号。
        records = []
        for source_row, values in enumerate(reader, 1):
            if len(values) != len(header) + 1:
                raise ValueError(f"{path.name} 数据行 {source_row} 列数异常")
            item = dict(zip(["original_index"] + header, values))
            item["source_row"] = source_row  # 文件内数据行序号，从1开始，不含表头
            item["date"] = datetime.fromisoformat(item["date"])
            item["Occupancy"] = int(item["Occupancy"])
            if item["Occupancy"] not in (0, 1):
                raise ValueError("发现不合法标签")
            for column in FEATURES:
                item[column] = float(item[column]) if item[column].strip() else None
            records.append(item)
    return records


def main():
    output_dir = ROOT / "outputs" / "step01"
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    split_manifest = []
    for filename, expected_count in EXPECTED.items():
        records = read_data(ROOT / "data" / filename)
        if len(records) != expected_count:
            raise ValueError(f"{filename} 实际行数与题目说明不符")
        ordered = sorted(records, key=lambda item: item["date"])
        intervals = Counter(
            (right["date"] - left["date"]).total_seconds()
            for left, right in zip(ordered, ordered[1:])
        )
        positives = sum(item["Occupancy"] for item in records)
        results[filename] = {
            "samples": len(records),
            "start": ordered[0]["date"].isoformat(sep=" "),
            "end": ordered[-1]["date"].isoformat(sep=" "),
            "occupied": positives,
            "occupied_ratio": positives / len(records),
            "missing_features": {c: sum(r[c] is None for r in records) for c in FEATURES},
            "duplicate_timestamps": len(records) - len({r["date"] for r in records}),
            "interval_seconds_counts": dict(sorted(intervals.items())),
        }
        cutoff = int(len(ordered) * 0.8)
        for position, item in enumerate(ordered):
            split = ("train" if position < cutoff else "validation") if filename == "datatraining.txt" else "test"
            split_manifest.append({
                "source_file": filename,
                "source_row": item["source_row"],
                "original_index": item["original_index"],
                "date": item["date"].isoformat(sep=" "),
                "split": split,
            })
        print(f"{filename}: {len(records)} rows, occupied={positives / len(records):.2%}, missing={sum(results[filename]['missing_features'].values())}")
    results["training_split"] = {"train": 6514, "validation": 1629, "rule": "sort by date; first floor(80% * n) train, remainder validation"}
    for name, value in [("data_check.json", results), ("split_manifest.json", split_manifest)]:
        (output_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Training split: 6514 train / 1629 validation")
    print("Saved to outputs/step01")


if __name__ == "__main__":
    main()
