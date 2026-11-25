"""将报告、源码、原始输入与结果按原有相对路径打包，附文件哈希。"""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent


def main():
    destination = ROOT / 'deliverables'
    destination.mkdir(exist_ok=True)
    selected = [ROOT / name for name in [
        'README.md', 'requirements.txt', 'requirements-report.txt',
        'step01_check_data.py', 'step02_compare_models.py',
        'run_complete_experiment.py', 'validate_submission.py',
        'build_course_report.py', 'package_submission.py',
        '数据来源与说明.md', '许可与署名.txt', '文件核验.json',
        'reports/室内占用检测课程项目实验报告.docx', 'reports/report_review.json']]
    for pattern in ['data/*.txt', 'outputs/step01/*.json', 'outputs/step02/*.json',
                    'outputs/step02/*.png', 'outputs/complete/*', 'docs/*.md']:
        selected.extend(p for p in ROOT.glob(pattern) if p.is_file())
    assert all(p.is_file() for p in selected)
    review_path = ROOT / 'reports/report_review.json'
    assert review_path.is_file(), '需要先完成逐页排版检查'
    review = json.loads(review_path.read_text(encoding='utf-8'))
    assert review['reviewed_all_pages']
    report = ROOT / 'reports/室内占用检测课程项目实验报告.docx'
    assert hashlib.sha256(report.read_bytes()).hexdigest() == review['report_sha256'], '报告已变化，需要重新检查排版'
    validation = json.loads((ROOT / 'outputs/complete/validation.json').read_text(encoding='utf-8'))
    assert validation['passed']
    manifest = dict(report='reports/室内占用检测课程项目实验报告.docx',
                    predictions='outputs/complete/occupancy_predictions.csv',
                    predictions_per_method=validation['rows_per_method'],
                    total_predictions=validation['total_rows'],
                    files=[dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size,
                                sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                           for p in sorted(set(selected))])
    manifest_path = destination / '提交文件清单.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    output = destination / '室内占用检测课程项目提交包.zip'
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for p in sorted(set(selected)):
            archive.write(p, p.relative_to(ROOT).as_posix())
        archive.write(manifest_path, '提交文件清单.json')
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(set(selected)) + 1
    print(f'Package verified: {output}; {len(set(selected))} files + manifest')


if __name__ == '__main__':
    main()
