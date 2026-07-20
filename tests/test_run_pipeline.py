import pytest
from run_pipeline import parse_args


def test_stage1_generate():
    args = parse_args(['--stage', '1', '--generate', '--latpath', '/tmp/lat'])
    assert args.stage == 1
    assert args.generate is True
    assert args.analyze is False
    assert args.retry is False
    assert args.latpath == '/tmp/lat'


def test_stage1_analyze():
    args = parse_args(['--stage', '1', '--analyze'])
    assert args.stage == 1
    assert args.analyze is True


def test_stage1_retry():
    args = parse_args(['--stage', '1', '--retry', '--latpath', '/tmp/lat'])
    assert args.retry is True


def test_errors_all_stages():
    args = parse_args(['--errors'])
    assert args.errors is True
    assert args.stage is None


def test_errors_specific_stage():
    args = parse_args(['--errors', '--stage', '2'])
    assert args.errors is True
    assert args.stage == 2
