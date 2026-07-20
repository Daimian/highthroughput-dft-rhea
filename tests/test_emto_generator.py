import os
import pytest
from emto_generator import parse_csv

def test_parse_csv():
    csv_path = os.path.join(os.path.dirname(__file__), '..',
                            '20260718-refractory-hea-compositions-1600-highthroughput-dft.csv')
    alloys = parse_csv(csv_path)
    # NOTE: the source CSV contains 1598 data rows (DFT_0001..DFT_1598),
    # not 1597 as originally assumed in the brief.
    assert len(alloys) == 1598

    first = alloys[0]
    assert first['id'] == 'DFT_0001'
    assert first['alloy'] == 'W91Re9'
    assert first['atoms'] == ['W', 'Re']
    assert first['concs'] == [91, 9]
    assert first['composition'] == {'W': 91, 'Re': 9}

    # Check a multi-component alloy
    dft10 = alloys[9]  # DFT_0010
    assert dft10['id'] == 'DFT_0010'
    assert dft10['alloy'] == 'Nb5Ta45Mo5W45'
    assert set(dft10['atoms']) == {'Nb', 'Ta', 'Mo', 'W'}
    assert sum(dft10['concs']) == 100


import tempfile
import numpy as np
from emto_generator import generate_eos_inputs

def test_generate_eos_inputs_creates_files(tmp_path):
    # This test requires a latpath with bcc structure files.
    # Use a dummy latpath — pyemto will create the folder structure
    # and KGRN/KFCD input files even without actual structure output files.
    latpath = str(tmp_path / "lat")
    os.makedirs(latpath, exist_ok=True)
    stage_dir = str(tmp_path / "stage1")

    sws_list = list(np.linspace(2.85, 3.05, 6))
    generate_eos_inputs(
        alloy_id='DFT_0001',
        atoms=['W', 'Re'],
        concs=[91, 9],
        sws_list=sws_list,
        stage_dir=stage_dir,
        latpath=latpath,
    )

    alloy_dir = os.path.join(stage_dir, 'DFT_0001')
    assert os.path.isdir(alloy_dir)
    # Check KGRN input files were created (one per SWS point).
    # NOTE: the installed pyemto version writes '{jobname}_{sws}.kgrn'
    # files directly into the alloy folder rather than into a 'kgrn/'
    # subdirectory with '.dat' extensions as originally assumed.
    kgrn_files = [f for f in os.listdir(alloy_dir) if f.endswith('.kgrn')]
    assert len(kgrn_files) == 6
